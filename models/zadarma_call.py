from odoo import models, fields, api
import requests
import hashlib
import hmac
import base64
import logging
from collections import OrderedDict

_logger = logging.getLogger(__name__)

class ZadarmaCall(models.Model):
    _name = 'zadarma.call'
    _description = 'Zadarma Call Log'

    name = fields.Char(string='Call ID Reference')
    call_id = fields.Char(string='Zadarma Call ID')
    caller_number = fields.Char(string='Caller Number')
    called_number = fields.Char(string='Called Number')
    call_type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], string='Call Type', default='outbound')
    start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now)
    end_time = fields.Datetime(string='End Time')
    duration = fields.Integer(string='Duration (sec)')
    status = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string='Status', default='success')
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    recording_url = fields.Char(string='Recording URL')

class ZadarmaAPI(models.AbstractModel):
    _name = 'zadarma.api'
    _description = 'Zadarma API Helper'

    def _get_auth_headers(self, company, method, params):
        api_key = company.zadarma_api_key or ''
        api_secret = company.zadarma_api_secret or ''
        sorted_params = OrderedDict(sorted(params.items()))
        params_str = "&".join([f"{k}={v}" for k, v in sorted_params.items()])
        md5_params = hashlib.md5(params_str.encode('utf-8')).hexdigest()
        data_to_sign = method + params_str + md5_params
        hmac_h = hmac.new(api_secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha1).hexdigest()
        signature_base64 = base64.b64encode(hmac_h.encode('utf-8')).decode('utf-8')
        return {'Authorization': f"{api_key}:{signature_base64}"}

    def make_callback(self, partner_phone):
        company = self.env.company
        user = self.env.user
        internal_number = user.zadarma_internal_number
        if not internal_number:
            return {'status': 'error', 'message': 'SIP номер не вказаний'}
        
        # ВИПРАВЛЕННЯ: беремо номер як є, тільки прибираємо пробіли
        clean_phone = partner_phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        method = "/v1/request/callback/"
        params_dict = {'from': internal_number, 'to': clean_phone}
        headers = self._get_auth_headers(company, method, params_dict)
        url = f"https://api.zadarma.com{method}"
        
        try:
            # requests автоматично закодує '+' у '%2B'
            response = requests.get(url, params=params_dict, headers=headers, timeout=15)
            return response.json()
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
