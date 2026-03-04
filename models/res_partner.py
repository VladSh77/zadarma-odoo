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
        # Отримуємо номер лінії (100, 101 або 102)
        internal_number = clean_phone(user.zadarma_internal_number)
        target_phone = clean_phone(self.phone or self.mobile)

        if not (key and secret and internal_number and target_phone):
            return False

        # Для Zadarma Callback 'from' має бути повним логіном лінії (наприклад 402022-100)
        # Оскільки префікс 402022 спільний, ми можемо додати його тут
        sip_login = f"402022{internal_number}"

        api_method = "/v1/request/callback/"
        params = {
            'from': sip_login,
            'to': target_phone,
        }
        
        sorted_dict = dict(sorted(params.items()))
        query_string = urlencode(sorted_dict)
        md5_params = hashlib.md5(query_string.encode('utf-8')).hexdigest()
        data_to_sign = f"{api_method}{query_string}{md5_params}"
        
        # Використовуємо .digest() для отримання бінарного хешу (вимога Zadarma)
        sign_hash = hmac.new(secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha1).digest()
        signature = base64.b64encode(sign_hash).decode('utf-8')

        headers = {'Authorization': f"{key}:{signature}"}
        
        try:
            response = requests.post(f"https://api.zadarma.com{api_method}", data=params, headers=headers, timeout=10)
            _logger.info("Zadarma Call: From %s To %s Result: %s", sip_login, target_phone, response.json())
        except Exception as e:
            _logger.error("Zadarma API Error: %s", str(e))
        
        return True
