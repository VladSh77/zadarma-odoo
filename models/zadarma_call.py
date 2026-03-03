from odoo import api, fields, models


class ZadarmaCall(models.Model):
    _name = "zadarma.call"
    _description = "Zadarma Call"
    _order = "start_time desc"
    _sql_constraints = [("call_id_uniq", "unique (call_id)", "Call ID must be unique!")]

    name = fields.Char(string="Call Name", compute="_compute_name", store=True)
    call_id = fields.Char(string="Call ID", required=True, index=True)
    start_time = fields.Datetime(string="Start Time", required=True)
    end_time = fields.Datetime(string="End Time")
    duration = fields.Integer(
        string="Duration (seconds)", compute="_compute_duration", store=True
    )
    caller_number = fields.Char(string="Caller Number", index=True)
    called_number = fields.Char(string="Called Number", index=True)
    call_type = fields.Selection(
        [("incoming", "Incoming"), ("outgoing", "Outgoing"), ("internal", "Internal")],
        string="Call Type",
        required=True,
    )
    status = fields.Selection(
        [
            ("answered", "Answered"),
            ("missed", "Missed"),
            ("busy", "Busy"),
            ("failed", "Failed"),
        ],
        string="Status",
        required=True,
    )

    partner_id = fields.Many2one("res.partner", string="Contact", index=True)
    user_id = fields.Many2one("res.users", string="User", index=True)

    recording_url = fields.Char(string="Recording URL")
    recording_attachment_id = fields.Many2one("ir.attachment", string="Recording File")

    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    @api.depends(
        "caller_number", "called_number", "partner_id", "start_time", "call_type"
    )
    def _compute_name(self):
        for call in self:
            if not call.start_time:
                call.name = "New Call"
                continue

            if call.partner_id:
                call.name = f"{call.partner_id.name} - {call.start_time}"
            else:
                if call.call_type == "incoming":
                    number = call.caller_number or "Unknown"
                else:
                    number = call.called_number or "Unknown"
                call.name = f"{number} - {call.start_time}"

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for call in self:
            if call.start_time and call.end_time:
                delta = call.end_time - call.start_time
                call.duration = int(delta.total_seconds())
            else:
                call.duration = 0
