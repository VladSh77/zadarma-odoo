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
        
        # Очищення номерів від зайвих символів
        def clean_phone(phone):
            if not phone: return False
            return ''.join(filter(str.isdigit, str(phone)))

        key = company.zadarma_api_key
        secret = company.zadarma_api_secret
        sip = clean_phone(user.zadarma_internal_number)
        target_phone = clean_phone(self.phone or self.mobile)

        if not (key and secret and sip and target_phone):
            _logger.warning("Zadarma Call: Missing credentials. SIP: %s, Target: %s", sip, target_phone)
            return False

        api_method = "/v1/request/callback/"
        params = {
            'from': sip,
            'to': target_phone,
        }
        
        # 1. Сортуємо параметри за алфавітом
        sorted_params = urlencode(sorted(params.items()))
        
        # 2. Формуємо рядок для підпису: метод + сортовані параметри + MD5 від сортованих параметрів
        md5_params = hashlib.md5(sorted_params.encode()).hexdigest()
        data_to_sign = f"{api_method}{sorted_params}{md5_params}"
        
        # 3. HMAC-SHA1 підпис
        h = hmac.new(secret.encode(), data_to_sign.encode(), hashlib.sha1)
        signature = base64.b64encode(h.hexdigest().encode()).decode()

        headers = {
            'Authorization': f"{key}:{signature}",
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            _logger.info("Zadarma Call: Sending request from %s to %s", sip, target_phone)
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            res_data = response.json()
            _logger.info("Zadarma Call Response: %s", res_data)
        except Exception as e:
            _logger.error("Zadarma API Connection Failed: %s", str(e))
        
        return True
