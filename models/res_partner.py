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
        
        target_phone = self.phone or self.mobile
        key = company.zadarma_key
        secret = company.zadarma_secret
        sip = user.zadarma_internal_number

        if not (key and secret and sip and target_phone):
            return False

        api_method = "/v1/request/callback/"
        params = {
            'from': sip,
            'to': target_phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', ''),
        }
        
        # Сортування параметрів для підпису
        sorted_params = urlencode(sorted(params.items()))
        data_to_sign = f"{api_method}{sorted_params}{hashlib.md5(sorted_params.encode()).hexdigest()}"
        
        signature = base64.b64encode(
            hmac.new(secret.encode(), data_to_sign.encode(), hashlib.sha1).hexdigest().encode()
        ).decode()

        headers = {'Authorization': f"{key}:{signature}"}
        
        try:
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            res_data = response.json()
            if res_data.get('status') == 'success':
                _logger.info("Zadarma Call Success: %s", res_data)
            else:
                _logger.error("Zadarma Call Error: %s", res_data)
        except Exception as e:
            _logger.error("Zadarma API Connection Failed: %s", str(e))
        
        return True
