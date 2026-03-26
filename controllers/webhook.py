# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from markupsafe import Markup
import logging
import re

_logger = logging.getLogger(__name__)

INTERNAL_NUMBER_MAX_LENGTH = 5


class ZadarmaWebhook(http.Controller):

    @http.route('/zadarma/webhook', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def zadarma_webhook(self, **kwargs):
        params = request.params
        if request.httprequest.method == 'GET' and params.get('zd_echo'):
            return params.get('zd_echo')

        _logger.info("Zadarma webhook received: event=%s, params=%s", params.get('event'), dict(params))

        event = params.get('event')
        try:
            if event == 'NOTIFY_END':
                self._process_call_end(params)
            elif event == 'NOTIFY_OUT_END' and params.get('calltype') == 'callback_leg2':
                self._process_outbound_call_end(params)
        except Exception as e:
            _logger.error("Zadarma webhook processing error: %s", str(e))

        return "OK"

    def _normalize_phone(self, phone):
        if not phone:
            return False
        return re.sub(r'\D', '', str(phone))

    def _find_partner(self, norm_phone):
        if not norm_phone:
            return request.env['res.partner'].sudo().browse()
        suffix = norm_phone[-9:]
        request.env.cr.execute("""
            SELECT id FROM res_partner
            WHERE active = true
              AND (
                regexp_replace(phone, '[^0-9]', '', 'g') LIKE %s
                OR regexp_replace(mobile, '[^0-9]', '', 'g') LIKE %s
              )
            LIMIT 1
        """, [f'%{suffix}', f'%{suffix}'])
        row = request.env.cr.fetchone()
        return request.env['res.partner'].sudo().browse(row[0]) if row else request.env['res.partner'].sudo().browse()

    def _find_user_by_sip(self, sip):
        if not sip:
            return request.env['res.users'].sudo().browse()
        return request.env['res.users'].sudo().search([
            ('zadarma_internal_number', '=', str(sip).strip())
        ], limit=1)

    def _post_chatter(self, lead, partner, direction, phone, duration, status, recording_url=None):
        direction_label = 'Вихідний' if direction == 'outbound' else 'Вхідний'
        minutes, seconds = divmod(duration, 60)
        duration_str = f"{minutes}хв {seconds}с" if minutes else f"{seconds}с"
        body = Markup(
            "<b>📞 {direction} дзвінок</b><br/>"
            "Номер: {phone}<br/>"
            "Тривалість: {duration}<br/>"
            "Статус: {status}"
        ).format(direction=direction_label, phone=phone, duration=duration_str, status=status or '—')
        if recording_url:
            body += Markup('<br/><a href="{url}">Слухати запис</a>').format(url=recording_url)
        chatter_target = lead if lead else partner
        if chatter_target:
            chatter_target.sudo().message_post(body=body, subtype_xmlid='mail.mt_note')

    def _process_call_end(self, data):
        # Inbound PBX calls (NOTIFY_END)
        call_id = data.get('call_id') or data.get('pbx_call_id')
        if not call_id or not data.get('call_start'):
            _logger.warning("Zadarma webhook: missing call_id/pbx_call_id or call_start. Payload: %s", dict(data))
            return

        env = request.env
        is_outbound = len(re.sub(r'\D', '', str(data.get('caller_id', '')))) <= INTERNAL_NUMBER_MAX_LENGTH
        phone = data.get('called_did') if is_outbound else data.get('caller_id')
        direction = 'outbound' if is_outbound else 'inbound'
        sip = data.get('caller_id') if is_outbound else None

        norm_phone = self._normalize_phone(phone)
        if not norm_phone:
            _logger.warning("Zadarma webhook: empty phone. caller_id=%s called_did=%s",
                            data.get('caller_id'), data.get('called_did'))
            return

        partner = self._find_partner(norm_phone)
        user = self._find_user_by_sip(sip) if sip else env['res.users'].sudo().browse()

        lead = env['crm.lead'].sudo().search([
            ('partner_id', '=', partner.id), ('type', '=', 'lead'), ('probability', '<', 100)
        ], limit=1) if partner else env['crm.lead'].sudo().browse()

        if not partner and not lead:
            lead = env['crm.lead'].sudo().create({
                'name': f'Дзвінок: {phone}', 'contact_name': phone, 'phone': phone,
            })

        duration = int(data.get('duration', 0))
        env['zadarma.call'].sudo().create({
            'call_id': call_id,
            'date_start': data.get('call_start'),
            'phone_number': phone,
            'direction': direction,
            'duration': duration,
            'status': data.get('disposition'),
            'partner_id': partner.id if partner else False,
            'lead_id': lead.id if lead else False,
            'user_id': user.id if user else False,
            'recording_url': data.get('recording'),
        })
        _logger.info("Zadarma: Saved %s call for %s", direction, phone)
        self._post_chatter(lead, partner, direction, phone, duration,
                           data.get('disposition'), data.get('recording'))

    def _process_outbound_call_end(self, data):
        # Outbound callback calls (NOTIFY_OUT_END, calltype=callback_leg2)
        call_id = data.get('pbx_call_id') or data.get('call_id')
        if not call_id or not data.get('call_start'):
            return

        env = request.env

        # Skip if already saved (can arrive with NOTIFY_END too)
        if env['zadarma.call'].sudo().search([('call_id', '=', call_id)], limit=1):
            return

        phone = self._normalize_phone(data.get('destination'))
        sip = data.get('internal')
        if not phone:
            return

        partner = self._find_partner(phone)
        user = self._find_user_by_sip(sip)

        lead = env['crm.lead'].sudo().search([
            ('partner_id', '=', partner.id), ('type', '=', 'lead'), ('probability', '<', 100)
        ], limit=1) if partner else env['crm.lead'].sudo().browse()

        duration = int(data.get('duration', 0))
        env['zadarma.call'].sudo().create({
            'call_id': call_id,
            'date_start': data.get('call_start'),
            'phone_number': phone,
            'direction': 'outbound',
            'duration': duration,
            'status': data.get('disposition'),
            'partner_id': partner.id if partner else False,
            'lead_id': lead.id if lead else False,
            'user_id': user.id if user else False,
        })
        _logger.info("Zadarma: Saved outbound call for %s by SIP %s", phone, sip)
        self._post_chatter(lead, partner, 'outbound', phone, duration, data.get('disposition'))
