from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    zadarma_api_key = fields.Char(string='Zadarma API Key')
    zadarma_api_secret = fields.Char(string='Zadarma API Secret')
