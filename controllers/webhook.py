# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class ZadarmaWebhook(http.Controller):

    @http.route('/zadarma/webhook', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def zadarma_webhook(self, **kwargs):
        params = request.params
        
        # Підтвердження для Zadarma
        if request.httprequest.method == 'GET' and params.get('zd_echo'):
            return params.get('zd_echo')

        # Обробка завершення дзвінка
        if params.get('event') == 'NOTIFY_END':
            self._process_call_end(params)
            
        return "OK"

    def _process_call_end(self, data):
        env = request.env
        phone = data.get('caller_id') or data.get('called_did')
        if not phone:
            return

        # 1. Пошук партнера
        partner = env['res.partner'].sudo().search([
            '|', ('phone', 'ilike', phone), ('mobile', 'ilike', phone)
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

        # 3. Реєстрація дзвінка
        env['zadarma.call'].sudo().create({
            'call_id': data.get('pbx_call_id'),
            'date_start': data.get('call_start'),
            'phone_number': phone,
            'direction': 'inbound' if data.get('event') == 'NOTIFY_END' else 'outbound',
            'duration': int(data.get('duration', 0)),
            'status': data.get('disposition'),
            'partner_id': partner.id if partner else False,
            'lead_id': lead.id if lead else False,
        })
        _logger.info("Zadarma: Registered call for %s", phone)
