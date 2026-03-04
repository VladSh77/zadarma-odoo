from odoo import models, fields, api, _
import requests
import base64
import hashlib
import hmac

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_zadarma_call(self):
        self.ensure_one()
        user = self.env.user
        if not user.zadarma_internal_number:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Помилка'),
                    'message': _('Будь ласка, вкажіть ваш SIP ID у налаштуваннях користувача.'),
                    'type': 'danger',
                }
            }

        company = self.env.company
        key = company.zadarma_key
        secret = company.zadarma_secret
        
        if not key or not secret:
            return False

        target_phone = self.phone or self.mobile
        if not target_phone:
            return False

        # API Zadarma: Callback
        api_url = "/v1/request/callback/"
        params = {
            'from': user.zadarma_internal_number,
            'to': target_phone,
        }
        
        # Спрощена авторизація для прикладу (буде доопрацьована в разі помилок підпису)
        # Наразі ми просто ініціюємо логіку виклику
        _logger = self.env['logging.getLogger'](__name__)
        _logger.info("Initiating Zadarma call from %s to %s", user.zadarma_internal_number, target_phone)
        
        # Тут буде реальний POST запит до API у наступному кроці
        return True
