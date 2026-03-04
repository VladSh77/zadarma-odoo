import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class ZadarmaWebhook(http.Controller):
    @http.route('/zadarma/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def handle_webhook(self):
        data = request.jsonrequest
        event = data.get('event')
        _logger.info("Zadarma Webhook received: %s", event)
        
        company = request.env['res.company'].sudo().search([], limit=1)
        
        if event == 'NOTIFY_START':
            self._handle_start(data, company)
        elif event in ['NOTIFY_END', 'NOTIFY_OUT_END']:
            self._handle_end(data, company)
            
        return {'status': 'success'}

    def _handle_start(self, data, company):
        number = data.get('caller_id') or data.get('called_number')
        if not number: return
        
        if number.startswith('+4848'): number = number.replace('+4848', '+48', 1)
        
        partner = request.env['res.partner'].sudo().search([('phone', 'ilike', number)], limit=1)
        lead = False
        if not partner:
            lead = request.env['crm.lead'].sudo().search([('phone', 'ilike', number)], limit=1)
            if not lead:
                lead = request.env['crm.lead'].sudo().create({
                    'name': f'Вхідний дзвінок: {number}',
                    'phone': number,
                    'description': 'Автоматично створено через Zadarma v1.2',
                })

        rodo_msg = " [RODO Warning Played]" if number.startswith('+48') else ""

        request.env['zadarma.call'].sudo().create({
            'call_id_external': data.get('call_id'),
            'date_start': fields.Datetime.now(),
            'direction': 'inbound' if data.get('event') == 'NOTIFY_START' else 'outbound',
            'phone_number': number,
            'partner_id': partner.id if partner else False,
            'lead_id': lead.id if lead else False,
        })
        
        msg = f"📞 Дзвінок: {number}{rodo_msg}"
        if partner: partner.message_post(body=msg)
        if lead: lead.message_post(body=msg)

    def _handle_end(self, data, company):
        call = request.env['zadarma.call'].sudo().search([('call_id_external', '=', data.get('call_id'))], limit=1)
        if call:
            call.write({
                'duration': int(data.get('duration', 0)),
                'status': 'answered' if int(data.get('duration', 0)) > 0 else 'no_answer',
            })
