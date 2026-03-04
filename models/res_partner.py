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
        
        def clean_phone(phone):
            if not phone: return False
            return ''.join(filter(str.isdigit, str(phone)))

        key = company.zadarma_api_key
        secret = company.zadarma_api_secret
        internal = clean_phone(user.zadarma_internal_number)
        target = clean_phone(self.phone or self.mobile)

        if not (key and secret and internal and target):
            return False

        # Формуємо ПОВНИЙ SIP ID, як він виглядає в кабінеті Zadarma
        sip_full = f"402022-{internal}"

        api_method = "/v1/request/callback/"
        params = {
            'from': sip_full,
            'to': target,
        }
        
        # 1. Сортуємо параметри
        sorted_dict = dict(sorted(params.items()))
        query_string = urlencode(sorted_dict)
        
        # 2. Формуємо MD5 від query_string
        md5_params = hashlib.md5(query_string.encode('utf-8')).hexdigest()
        
        # 3. Рядок для підпису: METHOD + QUERY + MD5(QUERY)
        data_to_sign = f"{api_method}{query_string}{md5_params}"
        
        # 4. HMAC-SHA1: беремо HEX-результат (hexdigest)
        h = hmac.new(secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha1)
        signature_hex = h.hexdigest()
        
        # 5. Base64 від HEX-результату
        signature = base64.b64encode(signature_hex.encode('utf-8')).decode('utf-8')

        headers = {'Authorization': f"{key}:{signature}"}
        
        try:
            _logger.info("Zadarma Final Attempt: From %s To %s", sip_full, target)
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            _logger.info("Zadarma Response: %s", response.json())
        except Exception as e:
            _logger.error("Zadarma API Error: %s", str(e))
        
        return True
