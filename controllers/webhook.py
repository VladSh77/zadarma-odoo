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

        _logger.info("Zadarma webhook received: event=%s, params=%s", params.get('event'), dict(params))

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
        # Zadarma sends call_id for answered calls, pbx_call_id for missed/cancelled calls
        call_id = data.get('call_id') or data.get('pbx_call_id')
        if not call_id or not data.get('call_start'):
            _logger.warning(
                "Zadarma webhook: missing call_id/pbx_call_id or call_start, skipping. Full payload: %s",
                dict(data),
            )
            return

        env = request.env
        is_outbound = len(str(data.get('caller_id', ''))) <= INTERNAL_NUMBER_MAX_LENGTH
        phone = data.get('called_did') if is_outbound else data.get('caller_id')
        direction = 'outbound' if is_outbound else 'inbound'

        norm_phone = self._normalize_phone(phone)
        if not norm_phone:
            _logger.warning("Zadarma webhook: empty phone after normalization, caller_id=%s called_did=%s",
                            data.get('caller_id'), data.get('called_did'))
            return

        # 1. Find partner by last 9 digits, stripping non-digits from stored phone numbers
        suffix = norm_phone[-9:]
        env.cr.execute("""
            SELECT id FROM res_partner
            WHERE active = true
              AND (
                regexp_replace(phone, '[^0-9]', '', 'g') LIKE %s
                OR regexp_replace(mobile, '[^0-9]', '', 'g') LIKE %s
              )
            LIMIT 1
        """, [f'%{suffix}', f'%{suffix}'])
        row = env.cr.fetchone()
        partner = env['res.partner'].sudo().browse(row[0]) if row else env['res.partner'].sudo().browse()

        # 2. Find open lead for this partner, or create a new lead if unknown caller
        lead = env['crm.lead'].sudo().search([
            ('partner_id', '=', partner.id),
            ('type', '=', 'lead'),
            ('probability', '<', 100)
        ], limit=1) if partner else env['crm.lead'].sudo().browse()

        if not partner and not lead:
            lead = env['crm.lead'].sudo().create({
                'name': f'Дзвінок: {phone}',
                'contact_name': phone,
                'phone': phone,
            })

        # 3. Save call record
        duration = int(data.get('duration', 0))
        call = env['zadarma.call'].sudo().create({
            'call_id': call_id,
            'date_start': data.get('call_start'),
            'phone_number': phone,
            'direction': direction,
            'duration': duration,
            'status': data.get('disposition'),
            'partner_id': partner.id if partner else False,
            'lead_id': lead.id if lead else False,
            'recording_url': data.get('recording'),
        })
        _logger.info("Zadarma: Saved %s call for %s with recording: %s", direction, phone, data.get('recording'))

        # 4. Post chatter message on lead or partner
        direction_label = 'Вихідний' if direction == 'outbound' else 'Вхідний'
        minutes, seconds = divmod(duration, 60)
        duration_str = f"{minutes}хв {seconds}с" if minutes else f"{seconds}с"
        body = (
            f"<b>📞 {direction_label} дзвінок</b><br/>"
            f"Номер: {phone}<br/>"
            f"Тривалість: {duration_str}<br/>"
            f"Статус: {data.get('disposition', '—')}"
        )
        if data.get('recording'):
            body += f'<br/><a href="{data["recording"]}">Слухати запис</a>'

        chatter_target = lead if lead else partner
        if chatter_target:
            chatter_target.sudo().message_post(body=body, subtype_xmlid='mail.mt_note')
