from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HHExpenseRejectWizard(models.TransientModel):
    _name = "hhexpense.reject.wizard"

    manager_reject_reason = fields.Char(string='Reject Reason')
    reviewer_reject_reason = fields.Char(string='Reject Reason')
    expense_ids = fields.Many2many('hhexpense.hhexpense')
    reviewer_reject_history = fields.Boolean()

    @api.model
    def default_get(self, fields):
        # This function will trigger action: "open form view to let user input reject reason"
        res = super(HHExpenseRejectWizard, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        # print(active_model)
        if active_model == 'hhexpense.hhexpense':
            active_ids = self.env.context.get('active_ids', [])
            print("-type of active_ids and its value :", type(active_ids), active_ids)
        else:
            active_ids = []
            expense_line_id = self.env.context.get('active_ids', [])
            expense_id = self.env['hhexpense.line'].search([('id', '=', expense_line_id)]).expense_id.id
            active_ids.append(expense_id)
            print("~type of active_ids and its value :", type(active_ids), active_ids)
        reject_model = self.env.context.get('hhexpense_reject_model')
        if reject_model == 'hhexpense.hhexpense':
            res.update({
                'expense_ids': active_ids,
            })
        return res

    @api.multi
    def reject_expense(self):
        self.ensure_one()
        # If operator is manager
        if self.env.user.has_group('hhexpense.group_hhexpense_manager'):
            if not self.manager_reject_reason:
                print("[This message is come from 'hhexpense_reject_reason.py'] You have to input reject reason")
                raise UserError(_("You have to input reject reason!"))
            else:
                if self.expense_ids:
                    # Pass reject reason to "reject_expense" method in hhexpense model
                    self.expense_ids.reject_expense(self.manager_reject_reason)
                    print("[This message is come from 'hhexpense_reject_reason.py'] Now, expense rejected by manager,"
                          "record goes to Guser, this moment's reviewer_reject_history value is :", 
                          self.reviewer_reject_history)
                    # self.expense_ids.reviewer_reject_history = False
                return {'type': 'ir.actions.act_window_close'}
        # If operator is reviewer
        else:
            if not self.reviewer_reject_reason:
                print("[This message is come from 'hhexpense_reject_reason.py'] You have to input reject reason")
                raise UserError(_("You have to input reject reason!"))
            else:
                if self.expense_ids:
                    # Pass reject reason to "reject_expense" method in hhexpense model
                    self.reviewer_reject_history = True
                    self.expense_ids.reject_expense(self.reviewer_reject_reason)
                    print("[This message is come from 'hhexpense_reject_reason.py'] Now, expense rejected by account,"
                          "record goes to Guser, passing reviewer_reject_history value to hhexpense model")
                    print("[This message is come from 'hhexpense_reject_reason.py'] "
                          "This moment's reviewer_reject_history value: ", self.reviewer_reject_history)
                return {'type': 'ir.actions.act_window_close'}
