# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class ZadarmaWebhook(http.Controller):

    @http.route('/zadarma/webhook', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def zadarma_webhook(self, **kwargs):
        # 1. Перевірка для активації (Крок 1 на скріншоті)
        if request.httprequest.method == 'GET' and kwargs.get('zd_echo'):
            return kwargs.get('zd_echo')

        # 2. Обробка вхідних повідомлень про дзвінки (POST)
        data = request.params
        _logger.info("Zadarma Webhook received: %s", data)
        
        # Тут пізніше додамо логіку створення лідів та запису дзвінків
        
        return "OK"
