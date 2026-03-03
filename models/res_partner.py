from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    zadarma_call_ids = fields.One2many(
        'zadarma.call', 
        'partner_id', 
        string='Дзвінки Zadarma'
    )
