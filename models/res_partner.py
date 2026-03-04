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
        
        # Очищуємо лише номер клієнта (тільки цифри)
        def clean_target(phone):
            if not phone: return False
            return ''.join(filter(str.isdigit, str(phone)))

        key = company.zadarma_api_key
        secret = company.zadarma_api_secret
        # Для SIP ID залишаємо дефіс, як у кабінеті (напр. 402022-100)
        sip_id = str(user.zadarma_internal_number or '').strip()
        target = clean_target(self.phone or self.mobile)

        if not (key and secret and sip_id and target):
            _logger.warning("Zadarma: Missing data. SIP: %s, Target: %s", sip_id, target)
            return False

        api_method = "/v1/request/callback/"
        params = {
            'from': sip_id,
            'to': target,
        }
        
        # 1. Сортуємо параметри
        sorted_dict = dict(sorted(params.items()))
        query_string = urlencode(sorted_dict)
        
        # 2. MD5 від query_string (lowercase hex)
        md5_params = hashlib.md5(query_string.encode('utf-8')).hexdigest()
        
        # 3. Рядок для підпису за офіційним SDK Python
        data_to_sign = f"{api_method}{query_string}{md5_params}"
        
        # 4. HMAC-SHA1 hexdigest
        h = hmac.new(secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha1)
        signature_hex = h.hexdigest()
        
        # 5. Base64 від отриманого HEX-рядка
        signature = base64.b64encode(signature_hex.encode('utf-8')).decode('utf-8')

        headers = {'Authorization': f"{key}:{signature}"}
        
        try:
            _logger.info("Zadarma API: Calling From %s To %s", sip_id, target)
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            _logger.info("Zadarma API Response: %s", response.json())
        except Exception as e:
            _logger.error("Zadarma API Connection Error: %s", str(e))
        
        return True
