# -*- coding: utf-8 -*-
import hashlib
import hmac
import base64
import logging
import re
import time
from urllib.parse import urlencode
from datetime import datetime, timedelta

import requests
from markupsafe import Markup

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

INTERNAL_NUMBER_MAX_LENGTH = 5


class ZadarmaImport(models.TransientModel):
    _name = 'zadarma.import'
    _description = 'Імпорт дзвінків Zadarma'

    date_from = fields.Date(string='Від', required=True,
                            default=lambda self: fields.Date.today() - timedelta(days=30))
    date_to = fields.Date(string='До', required=True,
                          default=fields.Date.today)
    result_message = fields.Text(string='Результат', readonly=True)

    def _zadarma_get(self, method, params):
        company = self.env.company
        key = company.zadarma_api_key
        secret = company.zadarma_api_secret
        if not key or not secret:
            raise UserError('Вкажіть Zadarma API Key та Secret у налаштуваннях компанії.')
        qs = urlencode(sorted(params.items()))
        md5 = hashlib.md5(qs.encode()).hexdigest()
        sign_str = method + qs + md5
        sig = base64.b64encode(
            hmac.new(secret.encode(), sign_str.encode(), hashlib.sha1).hexdigest().encode()
        ).decode()
        for attempt in range(3):
            response = requests.get(
                f'https://api.zadarma.com{method}?{qs}',
                headers={'Authorization': f'{key}:{sig}'},
                timeout=15,
            )
            if response.status_code == 429:
                wait = 3 * (attempt + 1)
                _logger.warning("Zadarma API rate limit (429), waiting %ss...", wait)
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        raise UserError('Zadarma API rate limit перевищено. Спробуйте через кілька хвилин.')

    def _normalize_phone(self, phone):
        if not phone:
            return False
        return re.sub(r'\D', '', str(phone))

    def _find_partner(self, norm_phone):
        if not norm_phone:
            return self.env['res.partner'].browse()
        suffix = norm_phone[-9:]
        self.env.cr.execute("""
            SELECT id FROM res_partner
            WHERE active = true
              AND (
                regexp_replace(phone, '[^0-9]', '', 'g') LIKE %s
                OR regexp_replace(mobile, '[^0-9]', '', 'g') LIKE %s
              )
            ORDER BY
                (CASE WHEN name ~ '^[0-9 +().-]+$' THEN 1 ELSE 0 END) ASC,
                id ASC
            LIMIT 1
        """, [f'%{suffix}', f'%{suffix}'])
        row = self.env.cr.fetchone()
        return self.env['res.partner'].browse(row[0]) if row else self.env['res.partner'].browse()

    def action_import(self):
        self.ensure_one()
        start = f"{self.date_from} 00:00:00"
        end = f"{self.date_to} 23:59:59"

        imported = 0
        skipped = 0
        skip = 0
        limit = 1000

        while True:
            data = self._zadarma_get('/v1/statistics/pbx/', {
                'start': start, 'end': end, 'skip': skip, 'limit': limit,
            })
            stats = data.get('stats', [])
            if not stats:
                break

            for call in stats:
                call_id = call.get('call_id')
                if not call_id:
                    continue

                # Skip if already in Odoo
                if self.env['zadarma.call'].sudo().search([('call_id', '=', call_id)], limit=1):
                    skipped += 1
                    continue

                sip = str(call.get('sip', ''))
                is_outbound = len(re.sub(r'\D', '', sip)) <= INTERNAL_NUMBER_MAX_LENGTH
                phone = str(call.get('destination', '')) if is_outbound else sip
                direction = 'outbound' if is_outbound else 'inbound'
                norm_phone = self._normalize_phone(phone)

                if not norm_phone:
                    continue

                partner = self._find_partner(norm_phone)
                lead = self.env['crm.lead'].sudo().search([
                    ('partner_id', '=', partner.id),
                    ('type', '=', 'lead'),
                    ('probability', '<', 100),
                ], limit=1) if partner else self.env['crm.lead'].sudo().browse()

                duration = int(call.get('seconds', 0) or call.get('billseconds', 0))
                status = call.get('disposition', '')

                call_record = self.env['zadarma.call'].sudo().create({
                    'call_id': call_id,
                    'date_start': call.get('callstart'),
                    'phone_number': phone,
                    'direction': direction,
                    'duration': duration,
                    'status': status,
                    'partner_id': partner.id if partner else False,
                    'lead_id': lead.id if lead else False,
                })

                # Post chatter note
                direction_label = 'Вихідний' if is_outbound else 'Вхідний'
                minutes, seconds = divmod(duration, 60)
                duration_str = f"{minutes}хв {seconds}с" if minutes else f"{seconds}с"
                body = Markup(
                    "<b>📞 {direction} дзвінок (імпорт)</b><br/>"
                    "Номер: {phone}<br/>"
                    "Тривалість: {duration}<br/>"
                    "Статус: {status}"
                ).format(
                    direction=direction_label,
                    phone=phone,
                    duration=duration_str,
                    status=status,
                )
                chatter_target = lead if lead else partner
                if chatter_target:
                    chatter_target.with_user(self.env.uid).message_post(body=body, subtype_xmlid='mail.mt_note')

                imported += 1

            if len(stats) < limit:
                break
            skip += limit
            time.sleep(1)  # avoid rate limiting between pages

        self.result_message = f"Імпортовано: {imported} дзвінків. Вже існували: {skipped}."
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'zadarma.import',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
