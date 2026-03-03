from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    zadarma_internal_number = fields.Char(string='Zadarma Internal Number (SIP)')
