from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    zadarma_api_key = fields.Char(string='Zadarma Key')
    zadarma_api_secret = fields.Char(string='Zadarma Secret')
    zadarma_callerid_rules = fields.Text(
        string='CallerID Rules',
        help='Одне правило на рядок: PREFIX:CALLERID\nПриклад:\n380:+380630202948\n48:+48459568854',
    )
