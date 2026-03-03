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

    def _get_auth_headers(self, company, method, params=''):
        api_key = company.zadarma_api_key
        api_secret = company.zadarma_api_secret
        data = method + params
        sha1 = hashlib.sha1(data.encode('utf-8')).hexdigest()
        signature = hmac.new(api_secret.encode('utf-8'), sha1.encode('utf-8'), hashlib.sha1).digest()
        signature_base64 = base64.b64encode(signature).decode('utf-8')
        return {'Authorization': f"{api_key}:{signature_base64}"}

    def make_callback(self, partner_phone):
        company = self.env.company
        user = self.env.user
        
        # Беремо SIP номер з картки користувача
        internal_number = user.zadarma_internal_number
        
        if not internal_number:
            return {'status': 'error', 'message': 'Ваш внутрішній номер (SIP) не вказаний у профілі!'}
        
        if not company.zadarma_api_key or not company.zadarma_api_secret:
            return {'status': 'error', 'message': 'API ключі не налаштовані в компанії'}

        url = "https://api.zadarma.com/v1/request/callback/"
        # Очищуємо номер телефону від зайвих символів
        clean_phone = ''.join(filter(str.isdigit, partner_phone))
        params = f"from={internal_number}&to={clean_phone}"
        
        headers = self._get_auth_headers(company, "/v1/request/callback/", params)
        
        try:
            _logger.info(f"Zadarma Call: From {internal_number} to {clean_phone}")
            response = requests.get(f"{url}?{params}", headers=headers, timeout=10)
            res_data = response.json()
            _logger.info(f"Zadarma Response: {res_data}")
            return res_data
        except Exception as e:
            _logger.error(f"Zadarma API Error: {str(e)}")
            return {'status': 'error', 'message': str(e)}
