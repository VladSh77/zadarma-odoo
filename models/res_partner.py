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
        sip = clean_phone(user.zadarma_internal_number)
        target_phone = clean_phone(self.phone or self.mobile)

        _logger.info("Zadarma Call Attempt: SIP=%s, Target=%s, HasKey=%s, HasSecret=%s", 
                     sip, target_phone, bool(key), bool(secret))

        if not (key and secret and sip and target_phone):
            _logger.warning("Zadarma Call: Cancelled due to missing data.")
            return False

        api_method = "/v1/request/callback/"
        params = {
            'from': sip,
            'to': target_phone,
        }
        
        sorted_params = urlencode(sorted(params.items()))
        md5_params = hashlib.md5(sorted_params.encode()).hexdigest()
        data_to_sign = f"{api_method}{sorted_params}{md5_params}"
        
        sign_hash = hmac.new(secret.encode(), data_to_sign.encode(), hashlib.sha1).hexdigest()
        signature = base64.b64encode(sign_hash.encode()).decode()

        headers = {
            'Authorization': f"{key}:{signature}",
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            _logger.info("Zadarma API POST: %s Headers: %s", api_method, headers)
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            res_data = response.json()
            _logger.info("Zadarma API Response Data: %s", res_data)
        except Exception as e:
            _logger.error("Zadarma API Exception: %s", str(e))
        
        return True
