from odoo import api, fields, models


class ZadarmaCall(models.Model):
    _name = 'zadarma.call'
    _description = 'Zadarma Call'
    _order = 'date_start desc'

    name = fields.Char(string='Заголовок', compute='_compute_name', store=True)
    call_id = fields.Char(string='Call ID', index=True, readonly=True)
    date_start = fields.Datetime(string='Дата початку', readonly=True)
    phone_number = fields.Char(string='Номер телефону', index=True, readonly=True)
    direction = fields.Selection(
        [('inbound', 'Вхідний'), ('outbound', 'Вихідний')], string='Тип', readonly=True
    )
    duration = fields.Integer(string='Тривалість (сек)', readonly=True)
    status = fields.Char(string='Статус', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Контакт', readonly=True)
    lead_id = fields.Many2one('crm.lead', string='Лід', readonly=True)
    user_id = fields.Many2one('res.users', string='Відповідальний', readonly=True)
    recording_url = fields.Char(string='Запис розмови', readonly=True)

    @api.depends('phone_number', 'date_start')
    def _compute_name(self):
        for record in self:
            date_str = record.date_start.strftime('%Y-%m-%d %H:%M') if record.date_start else 'Н/Д'
            record.name = f'Дзвінок {record.phone_number} ({date_str})'
