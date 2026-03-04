import logging
import hashlib
import hmac
import base64
import requests
from urllib.parse import urlencode
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_zadarma_call(self):
        self.ensure_one()
        user = self.env.user
        company = self.env.company
        
        key = company.zadarma_api_key
        secret = company.zadarma_api_secret
        # Беремо SIP ID як він вписаний (має бути 402022-100)
        sip_id = str(user.zadarma_internal_number or '').strip()
        target = ''.join(filter(str.isdigit, str(self.phone or self.mobile)))

        if not (key and secret and sip_id and target):
            return False

        api_method = "/v1/request/callback/"
        params = {
            'from': sip_id,
            'to': target,
        }
        
        # Сортування параметрів (Zadarma вимагає алфавітний порядок)
        sorted_keys = sorted(params.keys())
        query_string = urlencode([(k, params[k]) for k in sorted_keys])
        
        md5_params = hashlib.md5(query_string.encode('utf-8')).hexdigest()
        data_to_sign = f"{api_method}{query_string}{md5_params}"
        
        # Генерація підпису за стандартом Zadarma
        h = hmac.new(secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha1)
        signature = base64.b64encode(h.hexdigest().encode('utf-8')).decode('utf-8')

        headers = {
            'Authorization': f"{key}:{signature}",
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            _logger.info("Zadarma API: From %s To %s (Signature: %s)", sip_id, target, signature)
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            _logger.info("Zadarma API Response: %s", response.json())
        except Exception as e:
            _logger.error("Zadarma API Connection Error: %s", str(e))
        
        return True
