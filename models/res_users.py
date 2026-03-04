from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    zadarma_internal_number = fields.Char(
        string='Zadarma SIP', 
        help="Внутрішній номер АТС (наприклад, 101)"
    )
