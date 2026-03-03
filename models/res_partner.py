from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_zadarma_call(self):
        """Метод, який викликається кнопкою з інтерфейсу"""
        self.ensure_one()
        return self.env['zadarma.api'].make_callback(self.phone or self.mobile)
