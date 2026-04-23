import base64
import hashlib
import hmac
import logging
from urllib.parse import urlencode

import requests
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ZadarmaDashboard(models.TransientModel):
    _name = 'zadarma.dashboard'
    _description = 'Zadarma & TurboSMS Dashboard'

    zadarma_balance = fields.Char(string='Баланс Zadarma', readonly=True)
    turbosms_balance = fields.Char(string='Баланс TurboSMS', readonly=True)

    @api.model
    def _get_zadarma_balance(self):
        company = self.env.company
        key = company.zadarma_api_key
        secret = company.zadarma_api_secret
        if not (key and secret):
            return 'API не налаштовано'
        try:
            method = '/v1/info/balance/'
            params = {}
            qs = urlencode(sorted(params.items()))
            md5 = hashlib.md5(qs.encode()).hexdigest()  # noqa: S324 Zadarma API signature
            sign = method + qs + md5
            sig = hmac.new(secret.encode(), sign.encode(), hashlib.sha1).hexdigest()
            sig_b64 = base64.b64encode(sig.encode()).decode()
            url = f'https://api.zadarma.com{method}'
            if qs:
                url += f'?{qs}'
            resp = requests.get(
                url,
                headers={'Authorization': f'{key}:{sig_b64}'},
                timeout=10,
            )
            data = resp.json()
            if data.get('status') == 'success':
                balance = data.get('balance', '?')
                currency = data.get('currency', 'USD')
                return f'{balance} {currency}'
            return f'Помилка: {data.get("message", "unknown")}'
        except Exception as e:
            _logger.warning('Zadarma balance error: %s', e)
            return f'Помилка: {e}'

    @api.model
    def _get_turbosms_balance(self):
        provider = self.env['kw.sms.provider'].search([('state', '=', 'enabled')], limit=1)
        if not provider or not provider.turbosms_token:
            return 'Не налаштовано'
        try:
            resp = requests.post(
                'https://api.turbosms.ua/user/balance.json',
                headers={
                    'Authorization': f'Basic {provider.turbosms_token}',
                    'Content-Type': 'application/json',
                },
                json={},
                timeout=10,
            )
            data = resp.json()
            if data.get('response_code') == 0:
                bal = data['response_result']['balance']
                return f'{bal} грн'
            return f'Помилка: {data.get("response_status")}'
        except Exception as e:
            _logger.warning('TurboSMS balance error: %s', e)
            return f'Помилка: {e}'

    @api.model
    def open_dashboard(self):
        rec = self.create(
            {
                'zadarma_balance': self._get_zadarma_balance(),
                'turbosms_balance': self._get_turbosms_balance(),
            }
        )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Баланси',
            'res_model': 'zadarma.dashboard',
            'res_id': rec.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_refresh(self):
        self.write(
            {
                'zadarma_balance': self._get_zadarma_balance(),
                'turbosms_balance': self._get_turbosms_balance(),
            }
        )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Баланси',
            'res_model': 'zadarma.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
