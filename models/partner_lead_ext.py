from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    zadarma_call_ids = fields.One2many('zadarma.call', 'partner_id', string='Zadarma Calls')
    zadarma_call_count = fields.Integer(compute='_compute_zadarma_call_count')

    def _compute_zadarma_call_count(self):
        for record in self:
            record.zadarma_call_count = self.env['zadarma.call'].search_count([('partner_id', '=', record.id)])

    def action_view_zadarma_calls(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Дзвінки Zadarma',
            'res_model': 'zadarma.call',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    zadarma_call_ids = fields.One2many('zadarma.call', 'lead_id', string='Zadarma Calls')
    zadarma_call_count = fields.Integer(compute='_compute_zadarma_call_count')

    def _compute_zadarma_call_count(self):
        for record in self:
            record.zadarma_call_count = self.env['zadarma.call'].search_count([('lead_id', '=', record.id)])

    def action_view_zadarma_calls(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Дзвінки Zadarma',
            'res_model': 'zadarma.call',
            'view_mode': 'tree,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }
