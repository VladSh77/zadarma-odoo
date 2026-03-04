from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    zadarma_call_count = fields.Integer(compute='_compute_zadarma_call_count', string='Zadarma Calls')

    def _compute_zadarma_call_count(self):
        for partner in self:
            partner.zadarma_call_count = self.env['zadarma.call'].search_count([('partner_id', '=', partner.id)])

    def action_view_zadarma_calls(self):
        self.ensure_one()
        return {
            'name': 'Zadarma Calls',
            'type': 'ir.actions.act_window',
            'res_model': 'zadarma.call',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    zadarma_call_count = fields.Integer(compute='_compute_zadarma_call_count', string='Zadarma Calls')

    def _compute_zadarma_call_count(self):
        for lead in self:
            lead.zadarma_call_count = self.env['zadarma.call'].search_count([('lead_id', '=', lead.id)])

    def action_view_zadarma_calls(self):
        self.ensure_one()
        return {
            'name': 'Zadarma Calls',
            'type': 'ir.actions.act_window',
            'res_model': 'zadarma.call',
            'view_mode': 'tree,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }
