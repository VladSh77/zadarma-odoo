from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class ZadarmaWebhook(http.Controller):
    @http.route('/zadarma/webhook', type='http', auth='public', methods=['POST', 'GET'], csrf=False)
    def zadarma_webhook(self, **post):
        _logger.info(f"Zadarma Webhook Data: {post}")
        
        # 1. Валідація вебхука (Zadarma перевіряє посилання перед збереженням)
        if request.httprequest.method == 'GET':
            if 'zd_echo' in post:
                return post.get('zd_echo')
            return "Zadarma Webhook is active!"

        # 2. Обробка завершеного дзвінка
        event = post.get('event')
        
        # Zadarma надсилає різні івенти: NOTIFY_END (вхідні), NOTIFY_OUT_END (вихідні)
        if event in ['NOTIFY_END', 'NOTIFY_OUT_END', 'NOTIFY_RECORD']:
            call_id = post.get('pbx_call_id')
            caller_id = post.get('caller_id', '')
            destination = post.get('destination', '') or post.get('called_did', '')
            duration = post.get('duration', 0)
            disposition = post.get('disposition', '')
            internal = post.get('internal')
            
            # Визначаємо статус
            status = 'success' if disposition == 'answered' else 'failed'
            
            # Визначаємо тип дзвінка
            call_type = 'outbound' if event == 'NOTIFY_OUT_END' else 'inbound'
            
            # Шукаємо клієнта по номеру (останні 9 цифр)
            partner = False
            phone_to_search = destination if call_type == 'outbound' else caller_id
            if phone_to_search:
                search_phone = phone_to_search[-9:]
                partner = request.env['res.partner'].sudo().search([
                    '|', ('phone', 'ilike', search_phone), ('mobile', 'ilike', search_phone)
                ], limit=1)
                
            # Шукаємо менеджера по внутрішньому SIP
            user = False
            if internal:
                user = request.env['res.users'].sudo().search([('zadarma_internal_number', '=', internal)], limit=1)

            # Перевіряємо, чи вже є такий запис (може бути при NOTIFY_RECORD)
            existing_call = request.env['zadarma.call'].sudo().search([('call_id', '=', call_id)], limit=1)
            
            call_data = {
                'name': f"{call_type.capitalize()} Call: {caller_id} -> {destination}",
                'call_id': call_id,
                'caller_number': caller_id,
                'called_number': destination,
                'duration': int(duration) if duration else 0,
                'status': status,
                'call_type': call_type,
            }
            if partner:
                call_data['partner_id'] = partner.id
            if user:
                call_data['user_id'] = user.id

            # Збереження лінка на запис розмови (якщо є)
            if post.get('is_recorded') == '1' and post.get('call_id_with_rec'):
                # Формуємо URL для прослуховування 
                # (для завантаження потрібен додатковий API запит, поки зберігаємо ID)
                call_data['recording_url'] = post.get('call_id_with_rec')

            if existing_call:
                existing_call.write(call_data)
            else:
                request.env['zadarma.call'].sudo().create(call_data)

        return "OK"
