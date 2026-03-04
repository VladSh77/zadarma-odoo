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

        # ПРАВИЛЬНИЙ ФОРМАТ SIP: додаємо дефіс, як у вашому кабінеті
        sip_login = f"402022-{internal}"

        api_method = "/v1/request/callback/"
        params = {
            'from': sip_login,
            'to': target,
        }
        
        # Сортування параметрів
        sorted_dict = dict(sorted(params.items()))
        query_string = urlencode(sorted_dict)
        
        # MD5 від query_string
        md5_params = hashlib.md5(query_string.encode('utf-8')).hexdigest()
        
        # Рядок для підпису
        data_to_sign = f"{api_method}{query_string}{md5_params}"
        
        # HMAC-SHA1 -> HEX (lowercase) -> Base64
        h = hmac.new(secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha1)
        signature = base64.b64encode(h.hexdigest().encode('utf-8')).decode('utf-8')

        headers = {'Authorization': f"{key}:{signature}"}
        
        try:
            _logger.info("Zadarma API Request: %s Header: %s", params, headers['Authorization'])
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            _logger.info("Zadarma API Final Result: %s", response.json())
        except Exception as e:
            _logger.error("Zadarma API Exception: %s", str(e))
        
        return True
