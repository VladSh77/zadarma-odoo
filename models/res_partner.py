from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_zadarma_call(self):
        """Метод для кнопки виклику Zadarma"""
        self.ensure_one()
        _logger.info(">>> Ініціація дзвінка для: %s", self.name)
        return True
