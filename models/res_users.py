from odoo import fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    zadarma_extension = fields.Char(
        string="Zadarma Extension",
        help="Internal SIP number from Zadarma (e.g., 100 or 128155)"
    )
