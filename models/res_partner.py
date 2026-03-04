import logging
import hashlib
import hmac
import base64
import requests
from urllib.parse import urlencode
from collections import OrderedDict
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
        
        # Беремо цифри, додаємо префікс
        internal_line = ''.join(filter(str.isdigit, str(user.zadarma_internal_number or '')))
        target = ''.join(filter(str.isdigit, str(self.phone or self.mobile)))

        if not (key and secret and internal_line and target):
            return False

        sip_id = f"402022-{internal_line}"
        api_method = "/v1/request/callback/"
        params = {'from': sip_id, 'to': target}
        
        # ЛОГІКА З ОФІЦІЙНОГО SDK ZADARMA
        # 1. Сортуємо параметри за ключем
        ordered_params = OrderedDict(sorted(params.items()))
        
        # 2. Формуємо рядок запиту (query string)
        query_string = urlencode(ordered_params)
        
        # 3. Рахуємо MD5 від рядка запиту
        md5_string = hashlib.md5(query_string.encode('utf8')).hexdigest()
        
        # 4. Формуємо рядок для підпису
        sign_string = api_method + query_string + md5_string
        
        # 5. HMAC-SHA1 hexdigest (як в їхньому коді!)
        hmac_hash = hmac.new(secret.encode('utf8'), sign_string.encode('utf8'), hashlib.sha1).hexdigest()
        
        # 6. Кодуємо в Base64
        signature = base64.b64encode(hmac_hash.encode('utf8')).decode('utf8')

        headers = {'Authorization': f"{key}:{signature}"}
        
        try:
            _logger.info("Zadarma API: Sending call from %s to %s", sip_id, target)
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            _logger.info("Zadarma API Result: %s", response.json())
        except Exception as e:
            _logger.error("Zadarma API Exception: %s", str(e))
        
        return True
