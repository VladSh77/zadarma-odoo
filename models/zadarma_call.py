from odoo import models, fields, api

class ZadarmaCall(models.Model):
    _name = 'zadarma.call'
    _description = 'Zadarma Call Log'

    name = fields.Char(string='Call ID Reference')
    call_id = fields.Char(string='Zadarma Call ID')
    caller_number = fields.Char(string='Caller Number')
    called_number = fields.Char(string='Called Number')
    start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now)
    end_time = fields.Datetime(string='End Time')
    duration = fields.Integer(string='Duration (sec)')
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed')
    ], string='Status', default='success')

class ZadarmaAPI(models.AbstractModel):
    _name = 'zadarma.api'
    _description = 'Zadarma API Helper'

    def make_callback(self, partner_phone):
        """Метод для ініціації дзвінка"""
        return {'status': 'success'}
