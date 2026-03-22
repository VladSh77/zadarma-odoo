# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging
import re

_logger = logging.getLogger(__name__)

# Internal SIP extension numbers have at most this many digits.
# Used to distinguish inbound (external caller) from outbound (internal caller).
INTERNAL_NUMBER_MAX_LENGTH = 5


class ZadarmaWebhook(http.Controller):

    @http.route('/zadarma/webhook', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def zadarma_webhook(self, **kwargs):
        params = request.params
        if request.httprequest.method == 'GET' and params.get('zd_echo'):
            return params.get('zd_echo')

        if params.get('event') == 'NOTIFY_END':
            try:
                self._process_call_end(params)
            except Exception as e:
                _logger.error("Zadarma webhook processing error: %s", str(e))

        return "OK"

    def _normalize_phone(self, phone):
        if not phone:
            return False
        return re.sub(r'\D', '', str(phone))

    def _process_call_end(self, data):
        required_fields = ('call_id', 'call_start', 'duration')
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            _logger.warning("Zadarma webhook: missing required fields %s, skipping.", missing)
            return

        env = request.env
        is_outbound = len(str(data.get('caller_id', ''))) <= INTERNAL_NUMBER_MAX_LENGTH
        phone = data.get('called_did') if is_outbound else data.get('caller_id')
        direction = 'outbound' if is_outbound else 'inbound'

        norm_phone = self._normalize_phone(phone)
        if not norm_phone:
            return

        # 1. Find partner by last 9 digits of phone number
        partner = env['res.partner'].sudo().search([
            '|', ('phone', 'ilike', norm_phone[-9:]),
            ('mobile', 'ilike', norm_phone[-9:])
        ], limit=1)

        # 2. Find open lead for this partner, or create a new lead if unknown caller
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

        # 3. Save call record
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
