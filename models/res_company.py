from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    zadarma_api_key = fields.Char(string='Zadarma API Key')
    zadarma_api_secret = fields.Char(string='Zadarma API Secret', password=True)
    zadarma_sandbox = fields.Boolean(string='Sandbox Mode', default=False)
    
    # SIP Mapping: відповідність внутрішніх номерів (101) ID користувачів Odoo
    zadarma_sip_mapping = fields.Text(
        string='SIP Mapping', 
        help="Format: SIP:User_ID (e.g., 101:2, 102:5). Used to assign leads to users."
    )
