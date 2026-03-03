from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class ZadarmaWebhook(http.Controller):
    @http.route('/zadarma/webhook', type='http', auth='public', methods=['POST', 'GET'], csrf=False)
    def zadarma_webhook(self, **post):
        if request.httprequest.method == 'GET':
            if 'zd_echo' in post: return post.get('zd_echo')
            return "Zadarma Webhook is active!"

        event = post.get('event')
        if event in ['NOTIFY_END', 'NOTIFY_OUT_END', 'NOTIFY_RECORD']:
            caller_id = post.get('caller_id', '')
            destination = post.get('destination', '') or post.get('called_did', '')
            
            # ФІЛЬТР: Ігноруємо технічні дзвінки (0 на 100)
            if caller_id == '0' or destination == '100' and not destination.startswith('+'):
                return "OK"

            call_id = post.get('pbx_call_id')
            duration = post.get('duration', 0)
            disposition = post.get('disposition', '')
            call_type = 'outbound' if event == 'NOTIFY_OUT_END' else 'inbound'
            
            # Пошук партнера
            search_phone = ''.join(filter(str.isdigit, destination if call_type == 'outbound' else caller_id))[-9:]
            partner = request.env['res.partner'].sudo().search(['|', ('phone', 'ilike', search_phone), ('mobile', 'ilike', search_phone)], limit=1)

            vals = {
                'name': f"{call_type.capitalize()} call to {destination}" if call_type == 'outbound' else f"Inbound from {caller_id}",
                'call_id': call_id,
                'caller_number': caller_id,
                'called_number': destination,
                'duration': int(duration),
                'status': 'success' if disposition == 'answered' else 'failed',
                'call_type': call_type,
                'partner_id': partner.id if partner else False,
            }

            existing = request.env['zadarma.call'].sudo().search([('call_id', '=', call_id)], limit=1)
            if existing:
                existing.write(vals)
            else:
                new_call = request.env['zadarma.call'].sudo().create(vals)
                if partner:
                    partner.sudo().message_post(body=f"<b>📞 Дзвінок Zadarma:</b> {vals['name']}<br/>Тривалість: {duration} сек.<br/>Статус: {vals['status']}")

        return "OK"
