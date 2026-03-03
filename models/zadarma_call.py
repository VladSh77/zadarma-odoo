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
    recording_attachment_id = fields.Many2one('ir.attachment', string='Recording Attachment')

class ZadarmaAPI(models.AbstractModel):
    _name = 'zadarma.api'
    _description = 'Zadarma API Helper'

    def make_callback(self, partner_phone):
        company = self.env.company
        user = self.env.user
        
        # Видаляємо можливі невидимі пробіли в ключах
        api_key = (company.zadarma_api_key or '').strip()
        api_secret = (company.zadarma_api_secret or '').strip()
        internal = (user.zadarma_internal_number or '').strip()
        
        if not internal:
            return {'status': 'error', 'message': 'SIP номер не вказаний у профілі'}

        # Форматуємо номер: тільки цифри та плюс
        to_number = ''.join(c for c in partner_phone if c.isdigit() or c == '+')
        method = "/v1/request/callback/"
        
        # Створюємо словник параметрів (сортування за алфавітом важливе!)
        params = {
            'from': internal,
            'to': to_number
        }
        params_list = sorted(params.items())
        params_str = "&".join([f"{k}={v}" for k, v in params_list])
        
        # Алгоритм Zadarma: MD5 від рядка параметрів
        md5_hash = hashlib.md5(params_str.encode('utf-8')).hexdigest()
        
        # Рядок для підпису: METHOD + PARAMS_STR + MD5_PARAMS
        data_to_sign = method + params_str + md5_hash
        
        # HMAC-SHA1 підпис
        hmac_sha1 = hmac.new(api_secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha1).hexdigest()
        
        # Base64 кодування результату
        signature = base64.b64encode(hmac_sha1.encode('utf-8')).decode('utf-8')
        
        headers = {'Authorization': f"{api_key}:{signature}"}
        url = f"https://api.zadarma.com{method}"
        
        try:
            _logger.info(f"Zadarma Outgoing: URL={url}, Params={params_str}")
            # Надсилаємо запит (requests сам закодує + у %2B для передачі)
            response = requests.get(url, params=params, headers=headers, timeout=15)
            res_json = response.json()
            _logger.info(f"Zadarma Response: {res_json}")
            return res_json
        except Exception as e:
            _logger.error(f"Zadarma Request Failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}
