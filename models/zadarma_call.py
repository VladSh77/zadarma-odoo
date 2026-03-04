from odoo import models, fields

class ZadarmaCall(models.Model):
    _name = 'zadarma.call'
    _description = 'Zadarma Call'
    _order = 'date_start desc'

    call_id = fields.Char(string='Call ID', index=True)
    date_start = fields.Datetime(string='Дата початку')
    phone_number = fields.Char(string='Номер телефону', index=True)
    direction = fields.Selection([
        ('inbound', 'Вхідний'),
        ('outbound', 'Вихідний')
    ], string='Тип')
    duration = fields.Integer(string='Тривалість (сек)')
    status = fields.Char(string='Статус')
    partner_id = fields.Many2one('res.partner', string='Контакт')
    lead_id = fields.Many2one('crm.lead', string='Лід')
    user_id = fields.Many2one('res.users', string='Відповідальний')
