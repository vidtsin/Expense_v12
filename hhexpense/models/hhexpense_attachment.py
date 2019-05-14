# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import os
# for get user_agent
    # from odoo import http
    # import httpagentparser


class HHExpenseAttachment(models.Model):
    # _name = 'hhexpense.attachment'
    _inherit = 'ir.attachment'

    hhexpense = fields.Many2one('hhexpense.hhexpense', ondelete='cascade')
    state = fields.Char(compute='_compute_state')
    is_guser = fields.Char(compute='_compute_is_guser')

    @api.onchange('datas')
    def auto_fill_name(self):
        file_type = isinstance(self.datas_fname, bool)
        print(file_type)
        if file_type:
            print('not select file yet')
        else:
            self.name = os.path.splitext(self.datas_fname)[0]

    @api.depends('res_model', 'res_id')
    def _compute_state(self):
        # print("Triggered")
        # print(self.hhexpense.id)
        for attachment in self:
            if attachment.res_model and attachment.res_id:
                record = attachment.env[attachment.res_model].browse(attachment.res_id)
                attachment.state = record.state

    @api.depends('res_model', 'res_id')
    def _compute_is_guser(self):
        for attachment in self:
            if attachment.res_model and attachment.res_id:
                record = attachment.env[attachment.res_model].browse(attachment.res_id)
                attachment.is_guser = record.is_guser

    @api.model
    def create(self, values):
        # print(self.state)
        # remove computed field depending of datas
        for field in ('file_size', 'checksum'):
            values.pop(field, False)
        values = self._check_contents(values)
        self.browse().check('write', values=values)
        simple_type = values['mimetype'].split('/')[0]
        # print(type(values))
        if ('res_model' in values) and (values['res_model'] != 'hhexpense.hhexpense'):
            pass
        else:
            if values['datas'] is False:
                raise UserError(_("You must forget to upload your file!"))
            elif(values['mimetype'] == 'application/pdf') or (simple_type == 'image'):
                print('File type validated')
                pass
            else:
                print(self)
                raise UserError(_("You can only upload PDF or Image!"))
        return super(HHExpenseAttachment, self).create(values)

    @api.multi
    def preview_file(self):
        print('preview la')
        url = f'http://localhost:8069/web/content/{self.id}'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Preview attachment',
            'url': url,
            'target': 'new',
        }

        # get user_agent
        # user_agent = http.request.httprequest.environ.get('HTTP_USER_AGENT', '')
        # print(user_agent)
        # # split browser name from user_agents
        # parse_result = httpagentparser.simple_detect(user_agent)
        # print(parse_result)
        # browser = (parse_result[1].split())[0].lower()
        # print(browser)

        # get base_url from odoo system
        # base_url = http.request.env['ir.config_parameter'].get_param('web.base.url')
        # webbrowser.open_new_tab('%s/web/content/%s' % (base_url, self.id))

    @api.multi
    def download_file(self):
        print('download la')
        url = f'http://localhost:8069/web/content/{self.id}?download=1'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Download attachment',
            'url': url,
            'target': 'current',
        }
