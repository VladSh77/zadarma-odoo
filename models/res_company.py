from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    zadarma_api_key = fields.Char(
        string="Zadarma API Key", help="API key from your Zadarma personal account"
    )
    zadarma_api_secret = fields.Char(
        string="Zadarma API Secret",
        password=True,
        help="API secret from your Zadarma personal account (will be hidden)",
    )
    zadarma_sandbox = fields.Boolean(
        string="Use Sandbox",
        default=False,
        help="Use Zadarma sandbox environment for testing (https://api-sandbox.zadarma.com)",
    )
