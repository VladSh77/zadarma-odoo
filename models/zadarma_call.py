from odoo import models, fields, api
import requests
import hashlib
import hmac
import base64
import logging

_logger = logging.getLogger(__name__)

class ZadarmaCall(models.Model):
    _name = 'zadarma.call'
    _description = 'Zadarma Call Log'

    name = fields.Char(string='Call ID Reference')
    call_id = fields.Char(string='Zadarma Call ID')
    caller_number = fields.Char(string='Caller Number')
    called_number = fields.Char(string='Called Number')
    call_type = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound')
    ], string='Call Type', default='outbound')
    start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now)
    end_time = fields.Datetime(string='End Time')
    duration = fields.Integer(string='Duration (sec)')
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed')
    ], string='Status', default='success')
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    recording_url = fields.Char(string='Recording URL')
    recording_attachment_id = fields.Many2one('ir.attachment', string='Recording Attachment')

class ZadarmaAPI(models.AbstractModel):
    _name = 'zadarma.api'
    _description = 'Zadarma API Helper'

    def _get_auth_headers(self, company, method, params_str):
        """Генерація підпису за офіційним стандартом Zadarma"""
        api_key = company.zadarma_api_key
        api_secret = company.zadarma_api_secret
        
        # Складна формула підпису: Method + Params + MD5(Params)
        md5_params = hashlib.md5(params_str.encode('utf-8')).hexdigest()
        data_to_sign = method + params_str + md5_params
        
        signature = hmac.new(
            api_secret.encode('utf-8'), 
            data_to_sign.encode('utf-8'), 
            hashlib.sha1
        ).digest()
        
        signature_base64 = base64.b64encode(signature).decode('utf-8')
        
        return {
            'Authorization': f"{api_key}:{signature_base64}",
            'Accept': 'application/json'
        }

    def make_callback(self, partner_phone):
        company = self.env.company
        user = self.env.user
        
        internal_number = user.zadarma_internal_number
        if not internal_number:
            return {'status': 'error', 'message': 'SIP номер не вказаний у профілі'}
        
        # Очистка номера телефону
        clean_phone = ''.join(filter(str.isdigit, partner_phone))
        
        # Параметри мають бути в алфавітному порядку для стабільності підпису
        params_str = f"from={internal_number}&to={clean_phone}"
        method = "/v1/request/callback/"
        
        headers = self._get_auth_headers(company, method, params_str)
        url = f"https://api.zadarma.com{method}"
        
        try:
            _logger.info(f"Zadarma Request: {url}?{params_str}")
            response = requests.get(f"{url}?{params_str}", headers=headers, timeout=15)
            res_data = response.json()
            _logger.info(f"Zadarma Final Response: {res_data}")
            return res_data
        except Exception as e:
            _logger.error(f"Zadarma Connection Error: {str(e)}")
            return {'status': 'error', 'message': str(e)}
