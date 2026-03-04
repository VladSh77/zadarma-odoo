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
        
        # Отримуємо лише цифри лінії (напр. 100)
        internal_line = ''.join(filter(str.isdigit, str(user.zadarma_internal_number or '')))
        target = ''.join(filter(str.isdigit, str(self.phone or self.mobile)))

        if not (key and secret and internal_line and target):
            _logger.warning("Zadarma Call: Missing data. Line: %s, Target: %s", internal_line, target)
            return False

        # АВТОМАТИЧНЕ ДОДАВАННЯ ПРЕФІКСА
        sip_id = f"402022-{internal_line}"

        api_method = "/v1/request/callback/"
        params = {
            'from': sip_id,
            'to': target,
        }
        
        # 1. Сортування параметрів
        sorted_dict = dict(sorted(params.items()))
        query_string = urlencode(sorted_dict)
        
        # 2. Формування MD5
        md5_params = hashlib.md5(query_string.encode('utf-8')).hexdigest()
        
        # 3. Рядок для підпису
        data_to_sign = f"{api_method}{query_string}{md5_params}"
        
        # 4. HMAC-SHA1 (БІНАРНИЙ DIGEST) -> BASE64
        h = hmac.new(secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha1)
        signature = base64.b64encode(h.digest()).decode('utf-8')

        headers = {'Authorization': f"{key}:{signature}"}
        
        try:
            _logger.info("Zadarma API: Sending call from %s to %s", sip_id, target)
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            _logger.info("Zadarma API Response: %s", response.json())
        except Exception as e:
            _logger.error("Zadarma API Connection Error: %s", str(e))
        
        return True
