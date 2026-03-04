from odoo import models, fields, api

class ZadarmaCall(models.Model):
    _name = 'zadarma.call'
    _description = 'Zadarma Call Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    call_id_external = fields.Char(string='Zadarma Call ID', readonly=True, index=True)
    date_start = fields.Datetime(string='Start Time', readonly=True, tracking=True)
    duration = fields.Integer(string='Duration (sec)', readonly=True, tracking=True)
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
        ('internal', 'Internal')
    ], string='Direction', readonly=True)
    
    status = fields.Selection([
        ('answered', 'Answered'),
        ('busy', 'Busy'),
        ('no_answer', 'No Answer'),
        ('failed', 'Failed')
    ], string='Status', readonly=True, tracking=True)

    phone_number = fields.Char(string='Phone Number', readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact', readonly=True, tracking=True)
    lead_id = fields.Many2one('crm.lead', string='Lead', readonly=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Responsible User', readonly=True)
    
    recording_url = fields.Char(string='Recording URL', readonly=True)
    
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)

    def write(self, vals):
        # Security Lock: Суворий режим Read-Only реалізуємо через XML, 
        # тут залишаємо можливість оновлення для логіки Webhook.
        return super(ZadarmaCall, self).write(vals)

    def unlink(self):
        # Заборона видалення записів про дзвінки
        return super(ZadarmaCall, self).unlink()
