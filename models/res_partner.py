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
        
        # Використовуємо значення з налаштувань Odoo як є (має бути 402022-100)
        sip_id = str(user.zadarma_internal_number or '').strip()
        target = ''.join(filter(str.isdigit, str(self.phone or self.mobile)))

        if not (key and secret and sip_id and target):
            _logger.warning("Zadarma API: Missing required parameters")
            return False

        api_method = "/v1/request/callback/"
        params = {'from': sip_id, 'to': target}
        
        # 1. Сортуємо параметри
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        
        # 2. Формуємо підпис
        md5_string = hashlib.md5(query_string.encode('utf8')).hexdigest()
        sign_string = api_method + query_string + md5_string
        hmac_hash = hmac.new(secret.encode('utf8'), sign_string.encode('utf8'), hashlib.sha1).hexdigest()
        signature = base64.b64encode(hmac_hash.encode('utf8')).decode('utf8')

        headers = {'Authorization': f"{key}:{signature}"}
        
        try:
            # 3. ВИКОРИСТОВУЄМО GET ЗАПИТ з додаванням query_string до URL!
            url = f"https://api.zadarma.com{api_method}?{query_string}"
            _logger.info("Zadarma API Call (GET): %s", url)
            response = requests.get(url, headers=headers, timeout=10)
            _logger.info("Zadarma API Result: %s", response.json())
        except Exception as e:
            _logger.error("Zadarma API Exception: %s", str(e))
        
        return True
