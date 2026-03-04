from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    zadarma_key = fields.Char(string='Zadarma Key')
    zadarma_secret = fields.Char(string='Zadarma Secret')
