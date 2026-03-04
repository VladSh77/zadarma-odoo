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
        _logger.info("Zadarma Call Initiated for Partner: %s", self.name)
        
        user = self.env.user
        company = self.env.company
        
        def clean_phone(phone):
            if not phone: return False
            return ''.join(filter(str.isdigit, str(phone)))

        key = company.zadarma_api_key
        secret = company.zadarma_api_secret
        sip = clean_phone(user.zadarma_internal_number)
        target_phone = clean_phone(self.phone or self.mobile)

        if not (key and secret and sip and target_phone):
            _logger.warning("Zadarma: Missing Data. SIP: %s, Target: %s", sip, target_phone)
            return False

        api_method = "/v1/request/callback/"
        params = {
            'from': sip,
            'to': target_phone,
        }
        
        # Сортуємо параметри та створюємо рядок запиту
        sorted_dict = dict(sorted(params.items()))
        query_string = urlencode(sorted_dict)
        
        # Рядок для підпису: метод + query_string + md5(query_string)
        md5_params = hashlib.md5(query_string.encode('utf-8')).hexdigest()
        data_to_sign = f"{api_method}{query_string}{md5_params}"
        
        # КРИТИЧНО: HMAC-SHA1 має повертати digest (бінарний), а не hexdigest
        h = hmac.new(secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha1)
        signature = base64.b64encode(h.hexdigest().encode('utf-8')).decode('utf-8')

        headers = {
            'Authorization': f"{key}:{signature}",
        }
        
        try:
            _logger.info("Zadarma API: POST %s with params %s", api_method, params)
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            res_data = response.json()
            _logger.info("Zadarma API Final Response: %s", res_data)
        except Exception as e:
            _logger.error("Zadarma API Exception: %s", str(e))
        
        return True
