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
    _order = 'start_time desc'

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

class ZadarmaAPI(models.AbstractModel):
    _name = 'zadarma.api'
    _description = 'Zadarma API Helper'

    def make_callback(self, partner_phone):
        company = self.env.company
        user = self.env.user
        
        api_key = (company.zadarma_api_key or '').strip()
        api_secret = (company.zadarma_api_secret or '').strip()
        internal = (user.zadarma_internal_number or '').strip()
        
        # 1. Очищення номера та виправлення префікса 4848
        clean_to = ''.join(c for c in partner_phone if c.isdigit())
        if clean_to.startswith('48') and len(clean_to) == 11:
            clean_to = clean_to[2:]

        if not internal:
            return {'status': 'error', 'message': 'SIP номер не вказаний'}

        method = "/v1/request/callback/"
        params_str = f"from={internal}&to={clean_to}"
        
        md5_params = hashlib.md5(params_str.encode('utf-8')).hexdigest()
        data_to_sign = method + params_str + md5_params
        hmac_h = hmac.new(api_secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha1).hexdigest()
        signature = base64.b64encode(hmac_h.encode('utf-8')).decode('utf-8')
        
        headers = {'Authorization': f"{api_key}:{signature}"}
        url = f"https://api.zadarma.com{method}?{params_str}"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            resp_data = response.json()
            
            # 2. Пошук партнера та створення запису для статистики
            active_id = self.env.context.get('active_id')
            active_model = self.env.context.get('active_model')
            partner = False

            if active_model == 'res.partner' and active_id:
                partner = self.env['res.partner'].browse(active_id)
            else:
                # Якщо клікнули не з картки, шукаємо за номером
                partner = self.env['res.partner'].search(['|', ('phone', 'ilike', clean_to), ('mobile', 'ilike', clean_to)], limit=1)

            if resp_data.get('status') == 'success':
                # Створюємо запис у моделі zadarma.call (це і є ваша статистика)
                self.env['zadarma.call'].create({
                    'name': f"Вихідний дзвінок на {partner_phone}",
                    'caller_number': internal,
                    'called_number': clean_to,
                    'partner_id': partner.id if partner else False,
                    'status': 'success',
                    'start_time': fields.Datetime.now(),
                })
                
                # Записуємо в Chatter (історію) картки клієнта
                if partner:
                    partner.message_post(body=f"📞 <b>Zadarma:</b> Ініційовано вихідний дзвінок на номер {partner_phone}")
            
            return resp_data
        except Exception as e:
            _logger.error(f"Zadarma Error: {str(e)}")
            return {'status': 'error', 'message': str(e)}
