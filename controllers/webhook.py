# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging
import re

_logger = logging.getLogger(__name__)

class ZadarmaWebhook(http.Controller):

    @http.route('/zadarma/webhook', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def zadarma_webhook(self, **kwargs):
        params = request.params
        if request.httprequest.method == 'GET' and params.get('zd_echo'):
            return params.get('zd_echo')

        if params.get('event') == 'NOTIFY_END':
            self._process_call_end(params)
            
        return "OK"

    def _normalize_phone(self, phone):
        if not phone: return False
        return re.sub(r'\D', '', str(phone))

    def _process_call_end(self, data):
        env = request.env
        # Визначаємо напрямок: якщо caller_id короткий (до 5 цифр) - це внутрішній номер (виходящий)
        is_outbound = len(str(data.get('caller_id', ''))) <= 5
        phone = data.get('called_did') if is_outbound else data.get('caller_id')
        direction = 'outbound' if is_outbound else 'inbound'
        
        norm_phone = self._normalize_phone(phone)
        if not norm_phone: return

        # 1. Пошук партнера (за останніми 9 цифрами для точності)
        partner = env['res.partner'].sudo().search([
            '|', ('phone', 'ilike', norm_phone[-9:]), 
            ('mobile', 'ilike', norm_phone[-9:])
        ], limit=1)

        # 2. Пошук або створення Ліда
        lead = env['crm.lead'].sudo().search([
            ('partner_id', '=', partner.id),
            ('type', '=', 'lead'),
            ('probability', '<', 100)
        ], limit=1) if partner else None

        if not partner and not lead:
            lead = env['crm.lead'].sudo().create({
                'name': f'Дзвінок: {phone}',
                'contact_name': phone,
                'phone': phone,
            })

        # 3. Створення запису з усіма даними ТЗ
        env['zadarma.call'].sudo().create({
            'call_id': data.get('call_id'),
            'date_start': data.get('call_start'),
            'phone_number': phone,
            'direction': direction,
            'duration': int(data.get('duration', 0)),
            'status': data.get('disposition'),
            'partner_id': partner.id if partner else False,
            'lead_id': lead.id if lead else False,
            'recording_url': data.get('recording'),
        })
        _logger.info("Zadarma: Saved %s call for %s with recording: %s", direction, phone, data.get('recording'))
