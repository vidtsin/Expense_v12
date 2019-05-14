from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    accept_email_of_draft_status = fields.Boolean(string='When status change to or change from DRAFT status, '
                                                         'you will receive an email.', store=True)

    accept_email_of_submitted_status = fields.Boolean(string='When status change to or change from SUBMITTED status, '
                                                             'you will receive an email.', store=True)

    accept_email_of_approved_status = fields.Boolean(string='When status change to or change from APPROVED status, '
                                                            'you will receive an email.', store=True)

    accept_email_of_rejected_status = fields.Boolean(string='When status change to or change from REJECTED status, '
                                                            'you will receive an email.', store=True)

    accept_email_of_reviewed_status = fields.Boolean(string='When status change to or change from REVIEWED status, '
                                                            'you will receive an email.', store=True)

    accept_email_of_verified_status = fields.Boolean(string='When status change to or change from VERIFIED status, '
                                                            'you will receive an email.', store=True)

    accept_email_of_paid_status = fields.Boolean(string='When status change to or change from PAID status, '
                                                        'you will receive an email.', store=True)

    accept_email_of_posted_status = fields.Boolean(string='When status change to or change from POSTED status, '
                                                          'you will receive an email.', store=True)

    # lower_limiting_value = fields.Integer(string='Lower Limiting Value(HKD)', store=True)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            accept_email_of_draft_status=self.env['ir.config_parameter'].sudo().get_param(
                'hhexpense.accept_email_of_draft_status'),
            accept_email_of_submitted_status=self.env['ir.config_parameter'].sudo().get_param(
                'hhexpense.accept_email_of_submitted_status'),
            accept_email_of_approved_status=self.env['ir.config_parameter'].sudo().get_param(
                'hhexpense.accept_email_of_approved_status'),
            accept_email_of_rejected_status=self.env['ir.config_parameter'].sudo().get_param(
                'hhexpense.accept_email_of_rejected_status'),
            accept_email_of_reviewed_status=self.env['ir.config_parameter'].sudo().get_param(
                'hhexpense.accept_email_of_reviewed_status'),
            accept_email_of_verified_status=self.env['ir.config_parameter'].sudo().get_param(
                'hhexpense.accept_email_of_verified_status'),
            accept_email_of_paid_status=self.env['ir.config_parameter'].sudo().get_param(
                'hhexpense.accept_email_of_paid_status'),
            accept_email_of_posted_status=self.env['ir.config_parameter'].sudo().get_param(
                'hhexpense.accept_email_of_posted_status'),
            # lower_limiting_value=self.env['ir.config_parameter'].sudo().get_param(
            #     'hhexpense.lower_limiting_value'),
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('hhexpense.accept_email_of_draft_status',
                                                         self.accept_email_of_draft_status)
        self.env['ir.config_parameter'].sudo().set_param('hhexpense.accept_email_of_submitted_status',
                                                         self.accept_email_of_submitted_status)
        self.env['ir.config_parameter'].sudo().set_param('hhexpense.accept_email_of_approved_status',
                                                         self.accept_email_of_approved_status)
        self.env['ir.config_parameter'].sudo().set_param('hhexpense.accept_email_of_rejected_status',
                                                         self.accept_email_of_rejected_status)
        self.env['ir.config_parameter'].sudo().set_param('hhexpense.accept_email_of_reviewed_status',
                                                         self.accept_email_of_reviewed_status)
        self.env['ir.config_parameter'].sudo().set_param('hhexpense.accept_email_of_verified_status',
                                                         self.accept_email_of_verified_status)
        self.env['ir.config_parameter'].sudo().set_param('hhexpense.accept_email_of_paid_status',
                                                         self.accept_email_of_paid_status)
        self.env['ir.config_parameter'].sudo().set_param('hhexpense.accept_email_of_posted_status',
                                                         self.accept_email_of_posted_status)
        # self.env['ir.config_parameter'].sudo().set_param('hhexpense.lower_limiting_value',
        #                                                  int(self.lower_limiting_value))
