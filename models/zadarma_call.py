from odoo import models, api

class ZadarmaAPI(models.AbstractModel):
    _name = 'zadarma.api'
    _description = 'Zadarma API Helper'

    def make_callback(self, partner_phone):
        """Метод для ініціації дзвінка (поки що пуста логіка)"""
        return {'status': 'success'}
