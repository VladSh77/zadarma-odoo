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
        # Цей принт з'явиться в логах Docker навіть без фільтрації
        print("\n!!! TRIGGERED action_zadarma_call for partner ID: %s !!!\n" % self.id)
        _logger.info("Zadarma Button Clicked for Partner: %s", self.name)
        
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

        if not (key and secret and sip and target_phone):
            _logger.error("Zadarma: Missing Data. SIP: %s, Phone: %s, Key: %s", sip, target_phone, bool(key))
            return False

        api_method = "/v1/request/callback/"
        params = {'from': sip, 'to': target_phone}
        
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
            _logger.info("Zadarma API: Sending POST to %s", api_method)
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            _logger.info("Zadarma API Response: %s", response.json())
        except Exception as e:
            _logger.error("Zadarma API Exception: %s", str(e))
        
        return True
