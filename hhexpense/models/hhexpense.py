# -*- coding: utf-8 -*-
from odoo.api import Environment
from odoo import models, fields, api, _, registry
from odoo.exceptions import UserError
import datetime
import threading
import psycopg2
import os
from functools import partial
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell
import collections
import csv
import re

# using python to handle email sending function, not Odoo
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class HHExpense(models.Model):
    _name = 'hhexpense.hhexpense'

    # all of following order rules will work
    _order = "create_date desc"  # _order = "write_date desc" # _order = "id desc"

    # --------------------------------------------- Local attributes ---------------------------------------------------
    expense_num = fields.Char(string='Expense Track No.', compute="_compute_generate_expense_num", store=True)
    rec_approver_name = fields.Char(string="Approved By", readonly=True)
    rec_reviewer_name = fields.Char(string="Reviewed By", readonly=True)
    name = fields.Char(string='Expense Summary', readonly=True, required=True,
                       states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('reviewed', 'Reviewed'),
        ('verified', 'Verified'),
        ('paid', 'Paid'),
        ('posted', 'Posted'),
        ('rejected', 'Rejected')
    ], default='draft', string='Status', copy=False, index=True, readonly=True, store=True,
        help="Status of the expense.")
    # For following field(similar field in Odoo), why Odoo use this? "fields.Date.context_today"
    expense_create_date = fields.Date(readonly=True, default=fields.datetime.now(), string="Create Date")
    attachment_num = fields.Integer(compute='_calculate_attachment_num', string='Number of Attachments')
    expense_attachment = fields.One2many('ir.attachment', inverse_name='hhexpense')
    company_id = fields.Many2one('res.company', string='Company id', default=lambda self: self.env.user.company_id)
    expense_line = fields.One2many('hhexpense.line', inverse_name='expense_id', readonly=True,
                                   states={'draft': [('readonly', False)],
                                           'rejected': [('readonly', False)],
                                           'approved': [('readonly', False)],
                                           'reviewed': [('readonly', False)]},
                                   string='Expenses Details',
                                   help="This is where you input your expense's detail information")
    # ------ Employee information ------
    employee_id = fields.Many2one('hr.employee', string="Employee's id", required=True, readonly=True,
                                  default=lambda self: self.env['hr.employee'].search(
                                      [('user_id', '=', self.env.uid)], limit=1))
    employee_name = fields.Char(readonly=True, string='Employee Name',
                                default=lambda self: self.env['hr.employee'].search([
                                    ('user_id', '=', self.env.uid)], limit=1).name)

    # expense_deptoexp_id = fields.Many2one('hhexpense.convert.deptoexp', ondelete='set null', string="Department",
    #                                       readonly=True, required=True,
    #                                       states={'draft': [('readonly', False)]}
    #                                       )
    # expense_deptoexp_id = fields.Char(readonly=True, string='Department',
    #                             default=lambda self: self.env['hhemployee.hhemployee'].search(
    #                                 [('user_id', '=', self.env.uid)]).department_id.name)

    # Following line is the old way to obtain department information
    employee_department = fields.Char(compute='_compute_dep_from_employee_info', store=True)
    # Following 2 line is an easier way(making more sense) to obtain/access employee department information
    # Try to clean up after launch program
    # department_id = fields.Many2one('hr.department', default=lambda self: self.env.user.employee_ids.department_id.name)
    # department_name = fields.Char(related="department_id.name", store=True)
    # employee_department = fields.Char(string="Department", readonly=True, store=True)
    # employee_department = fields.Char(string="Department", required=True, readonly=True,
    #                                   default=lambda self: self.env['hr.department'].
    #                                   search([('user_id', '=', self.env.uid)]).department_id.name)
    is_marketing = fields.Boolean(default=False)
    # Q: Why following not working?
    #   team_name = fields.Char(default=lambda self: self.env['hhexpense.team'].
    #   search([('employee_name', '=', self.employee_name)]).team)
    # A: When initializing program, all field value is false/inaccessible,
    #   that's why you cannot use self.employee_name value as a comparison value
    team_name = fields.Char(readonly=True, string="Team",
                            default=lambda self: self.env['hhexpense.team'].search([
        ('employee_name', '=', self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).name)
    ], limit=1).team)
    analysis_code = fields.Char(readonly=True, string="Team",
                            default=lambda self: self.env['hhexpense.team'].search([
        ('employee_name', '=', self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).name)
    ], limit=1).analysis_code)
    # ------ Bank/cash/cashless workflow related ------
    calculate_total_amount = fields.Float(string='Total Amount(HKD+RMB)', store=True,
                                          compute='_compute_total_amount', digits=(12, 2))
    calculate_hkd_total_amount = fields.Float(string='Total HKD Amount', store=True,
                                              compute='_compute_hkd_total_amount', digits=(12, 2))
    calculate_rmb_total_amount = fields.Float(string='Total RMB Amount', store=True,
                                              compute='_compute_rmb_total_amount', digits=(12, 2))
    has_rmb_record = fields.Boolean(default=False, compute='_compute_has_rmb_record', readonly=True, store=True)
    #
    # ------ Reject function ------
    reject_reason = fields.Char(string='Reject Reason', readonly=True)
    # For following two field, its usage is that if this expense rejected before, submit process will change
    reject_wizard_ids = fields.Many2many("hhexpense.reject.wizard")
    reviewer_reject_history_copy = fields.Boolean()
    # ------ Attachment related ------
    confirm_invoice = fields.Boolean('Receipt', readonly=True, store=True, compute='_compute_invoice')
    is_guser = fields.Boolean('Is Guser', readonly=True, compute='_check_user_in_guser_group')
    # ------ Define url-related ------
    # tag for email reminder
    day = 3
    time_interval = day * 24 * 60 * 60
    resubmit_tag = fields.Char()
    # parameters for url attached in email
    current_menu_id = fields.Char()
    current_action_id = fields.Char()
    # all url might will be used in email
    to_approve_url = fields.Char()
    # approve_url = fields.Char()
    approved_url = fields.Char()
    to_review_url = fields.Char()
    to_verify_url = fields.Char()
    to_pay_url = fields.Char()
    rejected_url = fields.Char()
    # all approving email might will be used in email
    my_email = fields.Char(default=lambda self: self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)]).work_email)
    manager_name = fields.Char()
    manager_email = fields.Char()
    reviewer_name = fields.Char(default='Shirley')
    reviewer_email = fields.Char(default='shirley.pun@hunghingprinting.com')
    verifier_name = fields.Char(default='Kenneth')
    verifier_email = fields.Char(default='kenneth.chan@hunghingprinting.com')

    # get payment_approved_date from hhexpense_acc_date
    payment_approved_date = fields.Date(string='Payment Approved Date', store=True)

    # get batch number from hhexpense_line
    batch_number_copy = fields.Char()

    # kanban view test
    # label_one = fields.Char(string="HSsss", default="HS")

    # -------------------------------------------- Define methods here -------------------------------------------------
    # @api.depends('expense_create_date')
    @api.depends('employee_name')
    def _compute_generate_expense_num(self):
        # this function will be used to generate an unique expense No. (used for Accountant check expense later on)
        # import random
        # num = random.randint(100,2000)
        # print("RAND", num)

        # if self.expense_num:
        #     pass
        # else:
        print("Generating an unique expense No.")

        # Use list to store current existing record's expense No.
        expense_list = []
        expense_num_list = []
        expense_num_test_list = []
        # have to be search from database
        mst_rec = self.env['hhexpense.hhexpense'].search([])
        for rec in mst_rec:
            expense_list.append(rec.id)
            # if you print another compute field, you will find out "calculate_total_amount" value are also wrong,
            # thus, we believe it is Odoo structure (related to compute field) issue
            # print("record id, name and expense number :", rec.id, rec.name, rec.expense_num, rec.calculate_total_amount)
            expense_num_list.append(int(rec.expense_num))
        # print("expense list                       :", expense_list)
        # print("expense no list                    :", expense_num_list)

        if len(expense_list) > 1:
            for rec in self:
                rec.expense_num = max(expense_num_list) + 1
                # why after I add if condition, it will not work anymore, only the first record has expense number,
                # and also seems that somehow it affect reject function, it can not reject
                # if rec.expense_num != '':
                #     # pass
                #     print("this record already have batch number. skip!")
                # else:
                #     rec.expense_num = max(expense_num_list) + 1
                #     print("add one by one", rec.expense_num)
        else:
            # self.expense_num = 1000
            self.update({'expense_num': 1000})
            print("the first record", self.expense_num)

        # mst_rec = self.env['hhexpense.hhexpense'].search([])
        # max_num = max([rec.expense_num for rec in mst_rec], default=1000)
        # for rec in mst_rec:
        #     print(rec.name, max_num)
        #     rec.update({"expense_num": max_num})
        #     max_num += 1

    @api.depends('state')
    def send_email(self):
        # This function is not using, but keep it for now
        print("run")
        # if self.state == "paid":
        #     self.pay_expense()
        #     print("email send")

    @api.onchange('employee_department')
    def _onchange_display_team_field(self):
        # If current user's dempartment is Marketing, set is_marketing to True, "Team" field shows up
        if self.employee_department == "Marketing":
            self.is_marketing = True
            print("Employee need input Team information")
        else:
            self.is_marketing = False
            print("Employee no need input Team information")

    @api.depends('employee_name')
    def _compute_dep_from_employee_info(self):

        # why following code not working? Error: No access right
        # hehe = self.env['hr.employee'].search([('user_id', '=', self.env.uid)]).department_id.name
        # why following code not working? Error: IndexError: string index out of range
        # hehe = self.env['hr.employee'].sudo().search(['name', '=', str(self.env.user.name)]).department_id.name
        # print("This user's department is:", hehe)
        find = 0
        emp_info = self.env['hr.employee'].sudo().search([])
        # print("user name    : ", self.env.user.name)
        for rec in self:
            for emp in emp_info:
                # print("employee_name: ", emp.name)
                # print("employee_depa: ", emp.department_id.name)
                if emp.name == self.env.user.name:
                    # Capture employee's department information successfully, it suppose always can find
                    rec.employee_department = emp.department_id.name
                    find = 1
        if find != 1:
            print("Error: Can't capture employee's department information")

    # Following are old method that match for bank-cash workflow
    @api.depends('expense_line')
    def _compute_hkd_total_amount(self):
        total_amount = 0
        for exp in self:
            for exp_line in exp.expense_line:
                if exp_line.expense_line_currency.currency == "RMB":
                    pass
                else:
                    total_amount = total_amount + exp_line.expense_line_calculate
        self.update({'calculate_hkd_total_amount': total_amount})

    @api.depends('expense_line')
    def _compute_rmb_total_amount(self):
        total_amount = 0
        for exp in self:
            for exp_line in exp.expense_line:
                if exp_line.expense_line_currency.currency == "RMB":
                    total_amount = total_amount + exp_line.expense_line_cost
                else:
                    pass
        self.update({'calculate_rmb_total_amount': total_amount})

    @api.depends('expense_line')
    def _compute_has_rmb_record(self):
        for rec in self:
            for sub_rec in rec.expense_line:
                print("sub_rec.expense_line_currency.currency: ", sub_rec.expense_line_currency.currency)
                if sub_rec.expense_line_currency.currency == "RMB":
                    rec.has_rmb_record = True
                    print("This expense contains RMB record")
                else:
                    print("This expense do not has RMB record")

    @api.depends('expense_line')
    def _compute_total_amount(self):
        total_amount = 0
        for exp in self:
            for exp_line in exp.expense_line:
                print("rate check", exp_line.expense_line_currency.exchange_rate)
                total_amount = total_amount + exp_line.expense_line_cost * exp_line.expense_line_currency.exchange_rate
        self.update({'calculate_total_amount': total_amount})

    @api.depends('expense_line')
    def _compute_invoice(self):
        invoice = False
        for expense_rec in self:
            for expense_line_rec in expense_rec.expense_line:
                # if any of sub-record choose "Yes", confirm_invoice will be set to True
                if expense_line_rec.confirm_item_invoice == 1:
                    invoice = True
                    print("This expense contains record that require receipt")
        self.update({'confirm_invoice': invoice})

    @api.multi
    def hhexpense_action_get_attachment_view(self):
        # By now, since we only need "check Guser group" function here, not like "check Acc group" function
        # it is declared as local variable rather than a attribute
        self.ensure_one()
        # if self.state in ['draft', 'rejected']:
        #     res = self.env['ir.actions.act_window'].for_xml_id('hhexpense', 'hhexpense_attachment_action')
        # else:
        #     res = self.env['ir.actions.act_window'].for_xml_id('hhexpense', 'hhexpense_attachment_action_nomodify')
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hhexpense.hhexpense'), ('res_id', 'in', self.ids)]
        res['context'] = {
            'default_res_model': 'hhexpense.hhexpense',
            'default_res_id': self.id,
        }
        for expense in self:
            # If there is no attachment for this expense and it is not a draft expense,
            # user is not allowed to go to the attachment view
            if (self.attachment_num == 0) and (expense.state not in ['draft', 'rejected']):
                if self.is_guser is False:
                    raise UserError(_("There are no attachment for this expense"))
                else:
                    raise UserError(_(
                        "You cannot add any attachment now because the expense is " + self.state + "!"))
            else:
                # checking: if current user is not a guser, can only view attachment
                if (self.is_guser is False) or (expense.state not in ['draft', 'rejected']):
                    print("current user is not a guser, can only view attachment")
                    res['context'] = {
                        'default_res_model': 'hhexpense.hhexpense',
                        'default_res_id': self.id,
                        'create': False,
                        'edit': False,
                        'delete': False,
                    }
                    return res
                else:
                    print("do nothing")
                    return res

    @api.multi
    def _check_user_in_guser_group(self):
        if self.env.user.has_group('hhexpense.group_hhexpense_user'):
            print("yes! This is a Guser")
            self.is_guser = True
            return True
        else:
            print("Nope! This is not a Guser")
            self.is_guser = False
            return False

    @api.multi
    def _calculate_attachment_num(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'hhexpense.hhexpense'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_num = attachment.get(expense.id, 0)

    # ----------------- Using python lib to handle email function, not Odoo ----------------
    def hh_send_email(self):
        # # Email address
        # email_from_address = "Notification@hunghingprinting.com"
        # # email_to_address = "david.yao@hunghingprinting.com"
        # # email_to_address = ""
        #
        # # Create message container - the correct MIME type is multipart/alternative.
        # msg_container = MIMEMultipart('alternative')
        # # Q: Why "To" and ""Subject" object are defined inside if condition, not like "From" subject?
        # # A: "To" and ""Subject" object is not fixed (depends on email), if you define them outside and assign
        # # value to them inside the if condition, under debug mode, you will find msg_container object
        # # contains 2 "To" and 2 "Subject" value, one is from outside, another one is from "assign" statement inside
        # # if condition. As a result, you will find error that program cannot get correct "Subject" value to use
        # # e.g. define: outside if condition: msg_container['Subject'] = ""
        # #              inside if condition: msg_container['Subject'] = "hi"
        # #      Result: inside condition, "Subject" value unable to get correctly --- always "", not "hi"
        # msg_container['From'] = email_from_address
        # cc_address = ""
        #
        # # Create empty email body
        # html_body = ''' '''
        #
        # # Changeable args --- based on what email are sending (the purpose of email)
        # # After setting up args, program will write different email body (html_body) based on condition
        # if self.state == "submitted":
        #     # user case 1: user submit expense to manager, inform manager
        #
        #     # ---------------------------Test Version---------------------------------------
        #     # email_to_address = self.manager_email
        #     # msg_container['To'] = email_to_address
        #     #
        #     # #  condition booleans below
        #     # amt_limit = self.calculate_total_amount >= 3000
        #     # emp_dept = self.employee_department == "Marketing"
        #     # email_cc = email_to_address != 'edward.man@toppwork.com'
        #     #
        #     # if amt_limit and emp_dept and email_cc:
        #     #     cc_address = "edward.man@toppwork.com"
        #     #     msg_container['Cc'] = cc_address
        #     # -------------------------------------------------------------------------------------
        #
        #
        #     # # ---------------------------Production Version---------------------------------------
        #     email_to_address = self.manager_email
        #     msg_container['To'] = email_to_address
        #
        #     #  condition booleans below
        #     amt_limit = self.calculate_total_amount >= 3000
        #     emp_dept = self.employee_department == "Marketing"
        #     email_cc = email_to_address != 'christopher.yum@hunghingprinting.com'
        #
        #     if amt_limit and emp_dept and email_cc:
        #         cc_address = "christopher.yum@hunghingprinting.com"
        #         msg_container['Cc'] = cc_address
        #     # --------------------------------------------------------------------------------
        #
        #
        #     msg_container['Subject'] = str(self.employee_name) + " has submitted an expense"
        #     html_body = '''
        #     <html>
        #         <head>
        #             <img src="https://image.ibb.co/dbUXzz/logo.png" alt="{company_name}"/>
        #         </head>
        #         <body>
        #             <div>
        #                 <hr>
        #                 <p>Dear {manager},</p>
        #                 <p>{employee} has <strong style="text-transform: uppercase">{state}</strong> a new expense:</p>
        #                 <p><strong>"{expense}"</strong></p>
        #                 <p>Please <a href={to_approve_url}>login</a> to the e-Expense system to view the details.</p>
        #                 <p>Thank you for your attention.</p>
        #                 <br/>
        #                 <p >For enquiry please contact Accounting Department: Shirley Pun ({test_fake_email}) / ext.631</p>
        #                 <hr>
        #             </div>
        #         </body>
        #         <footer>
        #             <div style="font-size:13px; color:#999999;">
        #                 * This is a system-generated message, please do not reply.
        #             </div>
        #         </footer>
        #     </html>
        #     '''
        # elif self.state == "approved" or self.state == "rejected":
        #     # Combine them together cuz their email format are same
        #     # user case 2: manager approved expense, inform user
        #     # user case 3: manager rejected user expense, inform user
        #     # user case 4: reviewer rejected user expense, inform user
        #     email_to_address = self.employee_id.work_email
        #     msg_container['To'] = email_to_address
        #     msg_container['Subject'] = "Your expense (" + self.name + ") has been " + self.state
        #     html_body = '''
        #     <html>
        #         <head>
        #             <img src="https://image.ibb.co/dbUXzz/logo.png" alt="{company_name}"/>
        #         </head>
        #         <body>
        #             <div>
        #                 <hr>
        #                 <p>Dear {employee},</p>
        #                 <p>{current_user} has <strong style="text-transform: uppercase">{state}</strong> the below expense:</p>
        #                 <p><strong>"{expense}"</strong></p>
        #                 <p>Please <a href={to_approve_url}>login</a> to the e-Expense system to view the details.</p>
        #                 <p>Thank you for your attention.</p>
        #                 <br/>
        #                 <p >For enquiry please contact Accounting Department: Shirley Pun ({test_fake_email}) / ext.631</p>
        #                 <hr>
        #             </div>
        #         </body>
        #         <footer>
        #             <div style="font-size:13px; color:#999999;">
        #                 * This is a system-generated message, please do not reply.
        #             </div>
        #         </footer>
        #     </html>
        #     '''
        # elif self.state == "reviewed" and self.batch_number_copy != "":
        #     # user case 5: reviewer approved expense, expense needs to be verified, inform verifier
        #     email_to_address = self.verifier_email
        #     msg_container['To'] = email_to_address
        #     msg_container['Subject'] = "Expenses are waiting for your approval " \
        #                                "(Batch number: " + self.batch_number_copy + ")"
        #     html_body = '''
        #     <html>
        #         <head>
        #             <img src="https://image.ibb.co/dbUXzz/logo.png" alt="{company_name}"/>
        #         </head>
        #         <body>
        #             <div>
        #                 <hr>
        #                 <p>Dear {verfier_name},</p>
        #                 <p>Expenses have been <strong style="text-transform: uppercase">{state}</strong> and is waiting for your verification,</p>
        #                 <p>Please <a href={to_verify_url}>login</a> to the e-Expense system and cross-check with the Report.</p>
        #                 <p>Thank you for your attention.</p>
        #                 <br/>
        #                 <p >For enquiry please contact Accounting Department: Shirley Pun ({test_fake_email}) / ext.631</p>
        #                 <hr>
        #             </div>
        #         </body>
        #         <footer>
        #             <div style="font-size:13px; color:#999999;">
        #                 * This is a system-generated message, please do not reply.
        #             </div>
        #         </footer>
        #     </html>
        #     '''
        # elif self.state == "posted":
        #     # user case 6: reviewer has input payment_date, which means expense has been paid, inform user
        #     email_to_address = self.employee_id.work_email
        #     msg_container['To'] = email_to_address
        #     msg_container['Subject'] = "Your expense (" + self.name + ") has been " + self.state
        #     # Hard code "PAID" cuz the stare is actually posted, not paid, need clean these two state later(paid&posted)
        #     html_body = '''
        #     <html>
        #         <head>
        #             <img src="https://image.ibb.co/dbUXzz/logo.png" alt="{company_name}"/>
        #         </head>
        #         <body>
        #             <div>
        #                 <hr>
        #                 <p>Dear {employee},</p>
        #                 <p>Your expense:</p>
        #                 <p><strong>"{expense}"</strong></p>
        #                 <p>has been <strong>PAID</strong> on <strong>{payment_approved_date}</strong>, please check your bank account.</p>
        #                 <p>You may also wish to <a href={approved_url}>login</a> to the e-Expense system to check the details.</p>
        #                 <p>Thank you for your attention.</p>
        #                 <br/>
        #                 <p >For enquiry please contact Accounting Department: Shirley Pun ({test_fake_email}) / ext.631</p>
        #                 <hr>
        #             </div>
        #         </body>
        #         <footer>
        #             <div style="font-size:13px; color:#999999;">
        #                 * This is a system-generated message, please do not reply.
        #             </div>
        #         </footer>
        #     </html>
        #     '''
        #
        # # Following warning message purpose never show up cuz those args are purpose able to get value
        # if msg_container['To'] == "":
        #     raise UserError(_("Unable to obtain 'send to' email address! something goes wrong!"))
        # if msg_container['Subject'] == "":
        #     raise UserError(_("Unable to obtain 'subject' info. for sending email! something goes wrong!"))
        #
        # # current_user is used in case 2,3,4, purpose: get manager/reviewer name, simplify code
        # email_body = html_body.format(
        #     company_name=self.company_id.name,
        #     manager=self.manager_name,
        #     employee=self.employee_name,
        #     state=self.state,
        #     expense=self.name,
        #     to_approve_url=self.to_approve_url,
        #     test_fake_email="shirley.pun@hunghingprinting.com",
        #     current_user=self.env.user.name,
        #     payment_approved_date=self.payment_approved_date,
        #     approved_url=self.approved_url,
        #     verfier_name=self.verifier_name,
        #     to_verify_url=self.to_verify_url,
        #     nothing_but_test="1"
        # )
        # # print("get current user name: ", self.env.user.name)
        #
        # # Attach parts into message container.
        # msg_container.attach(MIMEText(email_body, 'html'))
        #
        # # check element before send
        # print("email_from_address, email_to_address, cc_address: ", email_from_address, email_to_address, cc_address)
        #
        # # return
        #
        # # Send email via own email server
        # server = smtplib.SMTP('mail.hunghingprinting.com', 25)
        # server.starttls()
        # server.login(email_from_address, "P@ssw0rd,123")
        # # sendmail function takes 3 arguments: sender's address, recipient's address and message to send
        # # why we need as_string() function tho?
        #
        # # ------------------------For Test Version Only ------------------------------------
        # email_list = ['team@123.com', 'team1@123.com', 'team2@123.com', 'team3@123.com', 'team4@123.com',
        #               'dave@123.com']
        # if email_to_address in email_list:
        #     email_to_address = 'edward.man@hunghingprinting.com'
        # #-----------------------------------------------------------------------------------
        #
        # full_email_to_address = []
        # full_email_to_address.append(email_to_address)
        # full_email_to_address.append(cc_address)
        # print("full address: ", full_email_to_address)
        # server.sendmail(email_from_address, full_email_to_address, msg_container.as_string())
        # server.quit()
        print("email send")

    # -------------------- Email templates for different state and user --------------------
    # timer
    def timer(self, former_state):
        t = threading.Timer(7 * 60 * 60, partial(self.resend_email, former_state))
        return t

    @api.multi
    def send_my_test_email(self):
        # Now let us find the e-mail template
        # To find the template we should use self.env.ref to search the template in the database.
        # It is important to first name the module where the template is in followed by a dot (.)
        # and then the name of the e-mail template(its id). Otherwise Odoo will not find your template.
        my_test_template = self.env.ref('hhexpense.mail_template_test_email_template')
        # As a result we will get the variable which contains the link to our e-mail template.
        # Because we only have a ‘pointer’ to this e-mail template we should still find the record itself
        # in the database and trigger the function ‘send_mail’ to push the e-mail out.
        # some explanation:
        # self.env['mail.template'].browse(my_test_template.id) --> find email,
        # send_mail(self.id) --> render email and 'push' it to user,
        # This is exactly what the function ‘send_mail’ does.
        # Since the function ‘send_mail’ needs to know which record it should get data from (to parse it
        # in the e-mail template with jinja2) we will pass along the ID of the current record with self.id.
        self.env['mail.template'].browse(my_test_template.id).send_mail(self.id)

    # resend email
    def resend_email(self, former_state):
        with api.Environment.manage():
            with registry(self.env.cr.dbname).cursor() as new_cr:
                self.env = api.Environment(new_cr, self.env.uid, self.env.context)
                print('*****************************coming into timer for expense:', self.name,
                      '************************************')
                print(datetime.datetime.now())
                print(self.time_interval / 3600, ' hours after: expense ', self.name, self.state,
                      '----in timer function')
                if self.state == former_state:
                    print('expense', self.name, 'state not change, before:', former_state, '---after:', self.state)
                    if self.state == 'submitted':
                        if self.resubmit_tag:
                            print('>>>>>resend_mail_resubmit_manager_template for expense', self.name)
                            # self.send_mail_resubmit_manager_template()
                        else:
                            print('>>>>>resend_mail_submit_manager_template for expense', self.name)
                            # self.send_mail_submit_manager_template()
                    if self.state == 'approved':
                        if self.resubmit_tag:
                            print('>>>>>resend_mail_resubmit_reviewer_template', self.name)
                            # self.send_mail_resubmit_reviewer_template()
                        else:
                            print('>>>>>resend_mail_approve_reviewer_template for expense', self.name)
                            # self.send_mail_approve_reviewer_template()
                    if self.state == 'reviewed':
                        print('>>>>>resend_mail_review_verifier_template for expense', self.name)
                        # self.send_mail_review_verifier_template()
                    if self.state == 'verified':
                        print('>>>>>resend_mail_verify_reviewer_template for expense', self.name)
                        # self.send_mail_verify_reviewer_template()
                else:
                    print('expense', self.name, 'state changed, before:', former_state, '---after:', self.state)
                    if former_state == 'rejected':
                        if self.resubmit_tag == 'manager':
                            print('>>>>>resend_mail_resubmit_manager_template for expense', self.name)
                            # self.send_mail_resubmit_manager_template()
                        else:
                            print('>>>>>resend_mail_resubmit_reviewer_template', self.name)
                            # self.send_mail_resubmit_reviewer_template()
                    else:
                        print('expense', self.name, 'no need to resend email, state changed, before:', former_state,
                              '---after:', self.state)

    # submit
    @api.multi
    def send_mail_submit_manager_template(self):
        template = self.env['mail.template'].sudo().search([('name', '=', 'expense e-mail submit manager template')],
                                                           limit=1)
        self.env['mail.template'].browse(template.id).send_mail(self.id)

        print(self.time_interval / 3600, 'hours before: expense ', self.name, self.state, '----in email function')
        self.timer(self.state).start()

    # approve
    @api.multi
    def send_mail_approve_guser_template(self):
        template = self.env['mail.template'].sudo().search([('name', '=', 'expense e-mail approve employee template')],
                                                           limit=1)
        self.env['mail.template'].browse(template.id).send_mail(self.id)

    @api.multi
    def send_mail_approve_reviewer_template(self):
        template = self.env['mail.template'].sudo().search([('name', '=', 'expense e-mail approve reviewer template')],
                                                           limit=1)
        self.env['mail.template'].browse(template.id).send_mail(self.id)

        # print(self.time_interval / 3600, 'hours before: expense ', self.name, self.state, '----in email function')
        # self.timer(self.state).start()

    # reject
    # @api.multi
    def send_mail_reject_guser_template(self):
        print("ww")
        template = self.env['mail.template'].sudo().search([('name', '=', 'expense e-mail reject employee template')],
                                                           limit=1)
        self.env['mail.template'].browse(template.id).send_mail(self.id)

    @api.multi
    def send_mail_resubmit_manager_template(self):
        template = self.env['mail.template'].sudo().search([('name', '=', 'expense e-mail resubmit manager template')],
                                                           limit=1)
        self.env['mail.template'].browse(template.id).send_mail(self.id)

        print(self.time_interval / 3600, 'hours before: expense ', self.name, self.state, '----in email function')
        self.timer(self.state).start()

    @api.multi
    def send_mail_resubmit_reviewer_template(self):
        template = self.env['mail.template'].sudo().search([('name', '=', 'expense e-mail resubmit reviewer template')],
                                                           limit=1)
        self.env['mail.template'].browse(template.id).send_mail(self.id)

        # print(self.time_interval / 3600, 'hours before: expense ', self.name, self.state, '----in email function')
        # self.timer(self.state).start()

    # review
    @api.multi
    def send_mail_review_verifier_template(self):
        template = self.env['mail.template'].sudo().search([('name', '=', 'expense e-mail review verifier template')],
                                                           limit=1)
        self.env['mail.template'].browse(template.id).send_mail(self.id)

        # print(self.time_interval / 3600, 'hours before: expense ', self.name, self.state, '----in email function')
        # self.timer(self.state).start()

    # verify
    @api.multi
    def send_mail_verify_reviewer_template(self):
        template = self.env['mail.template'].sudo().search([('name', '=', 'expense e-mail verify reviewer template')],
                                                           limit=1)
        self.env['mail.template'].browse(template.id).send_mail(self.id)

        print(self.time_interval / 3600, 'hours before: expense ', self.name, self.state, '----in email function')
        self.timer(self.state).start()

    # payment
    @api.multi
    def send_mail_paid_guser_template(self):
        template = self.env['mail.template'].sudo().search([('name', '=', 'expense e-mail paid guser template')],
                                                           limit=1)
        self.env['mail.template'].browse(template.id).send_mail(self.id)

    @api.multi
    def get_to_approve_url(self):

        # dynamically change login IP address
        # import socket
        # print(socket.gethostname()) ( e.g.HKHHD0044 )
        # print(socket.gethostbyname(socket.gethostname())) ( e.g.192.168.56.1 )

        self.current_menu_id = self.env['ir.ui.menu'].search([('name', '=', 'E-Expense(HH)')]).id
        self.current_action_id = self.env['ir.actions.act_window'].search(
            [('name', '=', 'Expenses to Approve')]).id
        self.to_approve_url = f"http://172.17.0.91:8072/web#id={self.id}&view_type=form&model=hhexpense.hhexpense&" \
                              f"action={self.current_action_id}&menu_id={self.current_menu_id}"
        print('url>>>>>', self.to_approve_url)

        # get manager info
        print(self.my_email)
        self.my_email = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)]).work_email
        manager = self.env['hhexpense.approving.manager'].sudo().search([('employee_email', '=', self.my_email)])
        # print("e ", self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)]).work_email)
        # print(self.env.uid)
        # print(self.my_email)
        # manager = self.env['hhexpense.approving.manager'].search([])
        # for m in manager:
        #     if m.employee_email == self.my_email:
        #         print(m.approving_manager_email)
        self.manager_name = manager.approving_manager_name
        self.manager_email = manager.approving_manager_email
        print(self.manager_name, 'email is', self.manager_email)

    @api.multi
    def get_approved_url(self):
        self.current_menu_id = self.env['ir.ui.menu'].search([('name', '=', 'E-Expense(HH)')]).id
        self.current_action_id = self.env['ir.actions.act_window'].search(
            [('name', '=', 'My Expenses')]).id
        self.approved_url = f"http://172.17.0.91:8072/web#id={self.id}&view_type=form&model=hhexpense.hhexpense&" \
                            f"action={self.current_action_id}&menu_id={self.current_menu_id}"

    @api.multi
    def get_rejected_url(self):
        print("qq")
        self.current_menu_id = self.env['ir.ui.menu'].search([('name', '=', 'E-Expense(HH)')]).id
        self.current_action_id = self.env['ir.actions.act_window'].search(
            [('name', '=', 'My Expenses')]).id
        self.rejected_url = f"http://172.17.0.91:8072/web#id={self.id}&view_type=form&model=hhexpense.hhexpense&" \
                           f"action={self.current_action_id}&menu_id={self.current_menu_id}"

    @api.multi
    def get_to_review_url(self):
        self.current_menu_id = self.env['ir.ui.menu'].search([('name', '=', 'E-Expense(HH)')]).id
        self.current_action_id = self.env['ir.actions.act_window'].search(
            [('name', '=', 'Expenses to Review')]).id
        self.to_review_url = f"http://172.17.0.91:8072/web#id={self.id}&view_type=form&model=hhexpense.hhexpense&" \
                             f"action={self.current_action_id}&menu_id={self.current_menu_id}"

    @api.multi
    def get_to_verify_url(self):
        self.current_menu_id = self.env['ir.ui.menu'].search([('name', '=', 'E-Expense(HH)')]).id
        self.current_action_id = self.env['ir.actions.act_window'].search(
            [('name', '=', 'Batch to Verify')]).id
        self.to_verify_url = f"http://172.17.0.91:8072/web#view_type=list&model=hhexpense.line&" \
                             f"action={self.current_action_id}&menu_id={self.current_menu_id}"

    @api.multi
    def get_to_pay_url(self):
        self.current_menu_id = self.env['ir.ui.menu'].search([('name', '=', 'E-Expense(HH)')]).id
        self.current_action_id = self.env['ir.actions.act_window'].search(
            [('name', '=', 'Bank Expenses Details')]).id
        self.to_pay_url = f"http://172.17.0.91:8072/web#id={self.id}&view_type=form&model=hhexpense.hhexpense&" \
                          f"action={self.current_action_id}&menu_id={self.current_menu_id}"

    # -------------------- Buttons: Submit/Approve/Reject/Resubmit --------------------
    @api.multi
    def submit_expense(self):
        if any(expense.state != 'draft' for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        if (self.confirm_invoice is True) and (self.attachment_num == 0):
            raise UserError(_("Please attach the corresponding receipts for your expenses!"))
        # Update record's state
        for expense_rec in self:
            expense_rec.state = 'submitted'
        self.get_to_approve_url()
        # self.send_mail_submit_manager_template()
        # self.send_my_test_email()
        self.hh_send_email()

        # Following code is trying to return a pop up window after submission
        # print(self.state)
        # return {
        #            'type': 'ir.actions.client',
        #            'tag': 'ailsa',
        #            'res_model': 'hhexpense.hhexpense',
        #            'name': 'Expense Submitted',
        #            'params': {
        #                'title': 'Expense Submitted',
        #                'text': "Your expense "
        #                        + self.name
        #                        + "has been successfully submitted to your manager",
        #                'sticky': False
        #            }
        #        }

    @api.multi
    def approve_expense(self):
        # Update record's state
        self.write({'state': 'approved'})
        # Add current approver data to "rec_approver_name" field
        self.rec_approver_name = self.env.user.name
        print("current approver is: ", self.rec_approver_name)
        self.get_to_review_url()
        self.get_approved_url()
        # self.send_mail_approve_reviewer_template()
        # self.send_mail_approve_guser_template()
        self.hh_send_email()

    @api.multi
    def review_expense(self):
        # Review will not trigger email that send to verifier, instead, this email will triggered
        # when reviewer download HSBC file (after generating batch number), it will call "review_expense_email" function

        # Update record's state
        self.state = 'reviewed'
        # Add current reviewer data to "record's reviewer name" field
        self.rec_reviewer_name = self.env.user.name
        print("current reviewer: ", self.rec_reviewer_name)

    @api.multi
    def review_expense_email(self):
        # this function called after generating batch number --- send email to verifier
        # check out "hhexpense.anticipated.date" model, at the end of "generate_batch_number" function
        self.get_to_verify_url()
        # self.send_mail_review_verifier_template()
        self.hh_send_email()
        print('already send reviewed expense (', self.name, ') to verifier')

    @api.multi
    def pay_expense(self):
        print('now send paid message to users')
        self.get_approved_url()
        # self.send_mail_paid_guser_template()
        self.hh_send_email()
        print('already notify user about the payment', self.id)
        # count_sub_rec_num = len(self.expense_line)
        # print("how many sub-record under this master record? ", count_sub_rec_num)
        # count_rec_ready = 0
        # # Calculate how many sub record is paid
        # for exp_line in self.expense_line:
        #     if exp_line.pay_bank_cash == "Bank" and exp_line.expense_line_is_processing:
        #         count_rec_ready += 1
        #     if exp_line.pay_bank_cash == "Cash" and exp_line.expense_line_is_paid:
        #         count_rec_ready += 1
        # if count_sub_rec_num == count_rec_ready:
        #     print("Able to mark as paid")
        #     self.get_approved_url()
        #     self.send_mail_paid_guser_template()
        #     # Update record's state
        #     self.state = 'paid'
        # else:
        #     print("Only when all sub records is paid, this expense can be marked as paid")
        #     raise UserError(_('Only when all sub records is paid, this expense can be marked as paid'))

    @api.multi
    def reject_expense(self, reason):
        print("Begin 'reject' process")

        # Record down "reject reason" to 'hhexpense' model
        self.reject_reason = reason
        # print("This expense's reject reason has recorded into 'hhexpense' model :", self.reject_reason)

        # Mark this record's status to 'rejected'
        self.state = 'rejected'

        # Depends on actor's role, maybe it require some other data manipulation
        # If 'reject' action's actor is reviewer
        if self.env.user.has_group('hhexpense.group_hhexpense_reviewers'):

            # Find out current expense line's batch number if any
            current_expense_line_batch_number = ''
            for sub_rec in self.expense_line:
                if sub_rec.batch_number:
                    print("current expense line already have batch number")
                    print("current expense line's batch number is :", sub_rec.expense_line_name, sub_rec.batch_number)
                    current_expense_line_batch_number = sub_rec.batch_number
                else:
                    print("current expense line do not have batch number")

            # If this is 'no batch number' case, i.e. reject action is triggered from "Expenses to review" page
            # Nothing else needs to be done

            # If this is 'already has batch number' case, i.e. reject action is triggered from "Expenses to review" page

            # Find all line records
            all_line_rec = self.env['hhexpense.line'].search([])

            for rec in all_line_rec:
                #  Line records that contains batch number (under the same batch)
                if rec.has_batch_number is True and rec.batch_number == current_expense_line_batch_number:
                    print("Records that have same batch number with currently rejected record are :",
                          rec.expense_line_name, rec.batch_number)
                    # After finding the records we want, we gonna clean their batch info
                    if rec.batch_number != '':
                        rec.has_batch_number = False
                        rec.batch_number = ''
                    if rec.anticipated_date:
                        rec.anticipated_date = ''

            # If this is 'already has batch number' case, i.e. reject action is triggered from "Expenses to reject" page

        # If 'reject' action's actor is manager
        else:
            print('It is rejected by manager, no batch number, thus no other action required, just reject it.')

        #     # find all records that contains batch number and it is under the same batch
        #     all_line_rec = self.env['hhexpense.line'].search([])
        #
        #     for rec in self.expense_line:
        #         print("sub record in this expense:", rec.expense_line_name)
        #
        #     for rec in all_line_rec:
        #         if rec.batch_number is False:
        #             # self.state = 'rejected'
        #             if rec.batch_number == current_expense_line_batch_number:
        #                 print("find all rec that under certain batch number", rec.expense_line_name, rec.batch_number)
        #                 # after find correct records, we will:
        #                 # (clean batch info for these records and only reject expense that reviewer wants to)
        #
        #                 # clean batch info
        #                 if rec.batch_number != '':
        #                     rec.has_batch_number = False
        #                     rec.batch_number = ''
        #                 if rec.anticipated_date:
        #                     rec.anticipated_date = ''
        #                 # reject only that expense
        #                 self.state = 'rejected'




        # for rec in records:
        #     if rec.has_batch_number:
        #         pass
        #         # rec.batch_number = ''
        #         # rec.has_batch_number = False
        #         # # Update record's state
        #         # self.state = 'rejected'
        #         # print('for rejected record, their batch_number and has_batch_number have been cleaned')
        #     else:
        #         # Update record's state
        #         self.state = 'rejected'
        #         print('no batch number, just reject')
        self.get_rejected_url()
        # self.send_mail_reject_guser_template()
        self.hh_send_email()

    @api.multi
    def resubmit_expense(self):
        if (self.confirm_invoice is True) & (self.attachment_num == 0):
            raise UserError(_("You must upload your invoice!"))
        # For one master-expense record, it may contains lots of sub-expense records. So we need to know
        # if any of its sub-expense records has been rejected by reviewer. Thus, that's why following code line will
        # make ValueError: Expected singleton: hhexpense.reject.wizard(41, 42)
        # --> print(self.reject_wizard_ids.reviewer_reject_history)
        print("From 'hhexpense.hhexpense' model, under current master-expense record('reject_wizard_ids'), "
              "return 'reviewer_reject_history' value(True/False, each sub-expense record has a value): ",
              self.reject_wizard_ids.mapped('reviewer_reject_history'))
        if True in self.reject_wizard_ids.mapped('reviewer_reject_history'):
            self.reviewer_reject_history_copy = True
            print("This expense had been rejected by reviewer, reviewer_reject_history_copy value set to True")
        else:
            print("This expense hadn't been rejected by reviewer, reviewer_reject_history_copy value set to False")
        # For current record, if reject history find, submission will directly goes to reviewer, not manager
        if self.reviewer_reject_history_copy:
            print("Expense submitted to Reviewer (not verifier!)")
            # It goes to reviewer even it is rejected by verifier
            self.resubmit_tag = 'none manager'
            return self.write({'state': 'approved'})
            # self.send_mail_resubmit_reviewer_template()
        else:
            print("Expense submitted to Manager")
            self.resubmit_tag = 'manager'
            self.write({'state': 'submitted'})
            # self.send_mail_resubmit_manager_template()
            self.hh_send_email()

    def conditional_check_reviewer_before_post(self):
        if self.env.user.has_group('hhexpense.group_hhexpense_reviewers') and self.state == "paid":
            print("Current user is legal to do post action. Pass!")
            return True
        else:
            print("Current user is not legal to do post action. Blocked!")
            return False

    # Since our action item/menu can be made to only visible for certain view, no need for conditional checking
    # # check identity before release/verify batch
    # def conditional_check_verifier_before_release_or_post(self):
    #     if self.env.user.has_group('hhexpense.group_hhexpense_verifiers') and self.state == 'reviewed':
    #         print("Current user is legal to do RELEASE/VERIFY action. Pass!")
    #         return True
    #     else:
    #         print("Current user is not legal to do RELEASE/VERIFY action. Blocked!")
    #         return False

    # Since workflow changed, following function moved to "hhexpense.line" model
    # @api.multi
    # def get_input_payment_approved_date(self, i, len_of_records):
    #     # Within all selected/ticked master-expense records, if it is the first record (i = 1), use "w" mode open file.
    #     # The reason is that we need to check if any file exist already.
    #     # (This is what "w" operation do) if yes, we should clean the contents in the existing file and write
    #     # info. into it. If no, create a new file and write inside it.
    #     if i == 1:
    #         selected_rec_id_file = open("./flexacc_intermediate_file_get_selected_rec_id.txt", "w", encoding="utf-8")
    #     # Now, when it goes to 2, 3, 4...N's master-expense records, use "a" mode to add/append info. into file
    #     else:
    #         selected_rec_id_file = open("./flexacc_intermediate_file_get_selected_rec_id.txt", "a", encoding="utf-8")
    #
    #     # Store master-expense record's id into file, one id a line!
    #     # So, in this way, our controller can read this file later and know this is the records he needs to dealing with
    #     # i.e. the download file should contains all sub-expense records under these id
    #     selected_rec_id_file.write(str(self.id) + '\n')
    #     # Operation done, close file
    #     selected_rec_id_file.close()
    #
    #     # Now, when it goes to the last selected master record (i == len_of_record),
    #     # return a form view for user input (FlexAccount payment approve date)
    #     if i == len_of_records:
    #         return {
    #             'view_type': 'form',
    #             'view_mode': 'form',
    #             'res_model': 'hhexpense.payment.date',
    #             'type': 'ir.actions.act_window',
    #         }

    # -------------------- Overwrite method --------------------

    @api.multi
    def unlink(self):
        # Only records that under "to submit/draft" status can be deleted
        for expense in self:
            if expense.state not in ['draft', 'rejected']:
                raise UserError(_('Sorry! ' + expense.state + ' expense record cannot be deleted!'))
        super(HHExpense, self).unlink()


class HHExpenseLine(models.Model):
    _name = 'hhexpense.line'

    # _order = "create_date desc, batch_number desc"
    _rec_name = 'expense_line_name'

    expense_line_name = fields.Char(string="Description", required=True, readonly=True,
                                    states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]})
    expense_line_cost = fields.Float(string='Amount', readonly=True,
                                     states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]})
    expense_line_date = fields.Date(string="Expense Date", required=True, readonly=True,
                                    states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]})
    expense_line_remarks = fields.Text(string="Remarks", readonly=True,
                                       states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]})
    expense_line_calculate = fields.Float(string="Payout Amount", digits=(12, 2),
                                          compute="_compute_after_exchange_money", store=True)
    expense_line_hkd_display_amount = fields.Float(string="HKD Payout Amount", digits=(12, 2),
                                                   compute="_compute_copy_calculated_hkd_amount", store=True)
    expense_line_rmb_display_amount = fields.Float(string="RMB Payout Amount", digits=(12, 2),
                                                   compute="_compute_copy_calculated_rmb_amount", store=True)
    confirm_item_invoice = fields.Selection([(1, 'YES'),(0, 'NO')], string='Receipt', readonly=True, required=True,
                                            store=True,
                                            states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]})
    expense_line_currency = fields.Many2one('hhexpense.currency.rate', ondelete='set null', string='Currency',
                                            required=True, readonly=True,
                                            default=lambda self: self.env['hhexpense.currency.rate'].search(
                                                [('currency', '=', "HKD")]),
                                            states={'draft': [('readonly', False)],
                                                    'rejected': [('readonly', False)]}
                                            )
    state = fields.Char(string="Status", compute="_compute_state", store=True)
    state_display_name = fields.Char(string="Status", compute="_compute_state_display_name", store=True)

    employee_name = fields.Char(related="expense_id.employee_name", store=True)

    anticipated_date_id = fields.Many2one('hhexpense.anticipated.date',
                                          ondelete='set null')  # , string='HSBC upload date'
    anticipated_date = fields.Date(related="anticipated_date_id.name", store=True)
    payment_approved_date_id = fields.Many2one('hhexpense.payment.date',
                                               ondelete='set null')  # , string='Payment Approved Date'
    payment_approved_date = fields.Date(related="payment_approved_date_id.name", store=True)

    # expense_line_is_paid = fields.Boolean(string="Paid", default=False, readonly=True)
    # expense_line_is_processing = fields.Boolean(string="Processing", default=False, readonly=True)

    credit_acc = fields.Char(string="Cr Acc", compute="_compute_credit_acc", store=True)
    credit_acc_desc = fields.Char(string="Cr Acc. Name", compute="_compute_credit_acc_desc", store=True)
    exchange_rate = fields.Float(string="Currency Rate", readonly=True, digits=(12, 2),
                                 compute="_compute_hh_rate", store=True)
    # exchange_rate = fields.Float(string="HH exchange rate", readonly=True,
    #                              related='expense_line_currency.exchange_rate', store=True)
    pay_hkd_rmb = fields.Char(string="Paid In", compute="_compute_payment_method", readonly=True, store=True)
    expense_id = fields.Many2one('hhexpense.hhexpense', ondelete='cascade')
    # string='111Category' string="111Acc"
    expense_cate_id = fields.Many2one('hhexpense.expense.category', ondelete='set null', string='Category',
                                      required=True, readonly=True,
                                      states={'draft': [('readonly', False)],
                                              'rejected': [('readonly', False)]})
    expense_cate_acc_copy = fields.Char(string="Acc", related='expense_cate_id.acc_no', readonly=True, store=True,
                                        states={'approved': [('readonly', False)], 'reviewed': [('readonly', False)]})
    expense_debit_acc = fields.Char(string="Dr Acc")
    expense_debit_acc_name = fields.Char(string="Dr Acc Name", compute="_compute_debit_acc_name_base_on_user_input",
                                         store=True, readonly=True)
    # expense_debit_id = fields.Many2one('hhexpense.debit.category', ondelete='set null', string='Category',
    #                                    help='Choose expense category, and it will carry out a debit acc', required=True,
    #                                    readonly=True,
    #                                    states={'draft': [('readonly', False)],
    #                                            'rejected': [('readonly', False)],
    #                                            'approved': [('readonly', False)],
    #                                            'reviewed': [('readonly', False)]}
    #                                    )
    # debit_acc_copy = fields.Char(related='expense_debit_id.debit_acc', readonly=True,
    #                              states={'approved': [('readonly', False)], 'reviewed': [('readonly', False)]})
    convert_dep_to_exp_type = fields.Char(string="Type", compute='_compute_convert_dep_to_exp_type', store=True)
    corresponding_attachments_no = fields.Char(string="Receipt No.", readonly=True,
                                               states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]})

    batch_number = fields.Char(string='Batch Number', readonly=True, help='The format of batch_number is '
                                                                          '[year-month-day-hour]')
    has_batch_number = fields.Boolean(default=False)

    expense_num_copy = fields.Char(related='expense_id.expense_num', store=True)

    # ---------------------------------------------- Define methods here -----------------------------------------------
    @api.depends('expense_id.state')
    def _compute_state(self):
        for expense in self:
            if expense.expense_id.state == "draft":
                expense.state = "draft"
            elif expense.expense_id.state == "submitted":
                expense.state = "submitted"
            elif expense.expense_id.state == "approved":
                expense.state = "approved"
            elif expense.expense_id.state == "reviewed":
                expense.state = "reviewed"
            elif expense.expense_id.state == "verified":
                expense.state = "verified"
            elif expense.expense_id.state == "paid":
                expense.state = "paid"
            elif expense.expense_id.state == "posted":
                expense.state = "posted"
            else:
                expense.state = "rejected"

    @api.depends('state')
    def _compute_state_display_name(self):
        for expense in self:
            if expense.state == "draft":
                expense.state_display_name = "Draft"
            elif expense.state == "submitted":
                expense.state_display_name = "Submitted"
            elif expense.state == "approved":
                expense.state_display_name = "Approved"
            elif expense.state == "reviewed":
                expense.state_display_name = "Reviewed"
            elif expense.state == "verified":
                expense.state_display_name = "Verified"
            elif expense.state == "paid":
                expense.state_display_name = "Paid"
            elif expense.state == "posted":
                expense.state_display_name = "Posted"
            else:
                expense.state_display_name = "Rejected"



    @api.multi
    def release_expense(self):
        print('batch_number:', self.batch_number)
        # find all record included in the same batch
        batch_record = self.env['hhexpense.line'].search([('batch_number', '=', self.batch_number)])
        # reset state of corresponding expense to reviewed and clear all batch number
        for rec in batch_record:
            if rec.expense_id.state != 'reviewed':
                rec.expense_id.state = 'reviewed'
                # self.state = 'reviewed'
                print('released expense', rec.expense_id.name)
            else:
                print('same record, already released')
        print('With selected record, all other records that under same batch have been released')

    @api.onchange('expense_cate_acc_copy')
    def _onchange_debit_acc_base_on_user_input(self):
        # Purpose of this function:
            # Assigning expense_cate_acc value to expense_debit_acc
        self.expense_debit_acc = self.expense_cate_acc_copy
        print("Assigning expense_cate_acc value to expense_debit_acc, get assigned value", self.expense_debit_acc)

    @api.depends('expense_debit_acc')
    def _compute_debit_acc_name_base_on_user_input(self):
        # Purpose of this function:
            # Assigning debit acc info(this is based on user selection) to Accounting
            # This function needs "_onchange_debit_acc_base_on_user_input" function as "pre-request"

        # Get info from "hhexpense.debit.category" model, prepare for comparision
        debit_info = self.env['hhexpense.debit.category'].search([])
        for info in debit_info:
            for sub_rec in self:
                if sub_rec.expense_debit_acc == info.debit_acc:
                    sub_rec.expense_debit_acc_name = info.expense_category
                else:
                    pass

    @api.onchange('expense_debit_acc')
    def _onchange_check_debit_acc_input(self):
        # Purpose of this function: If Accounting has wrong input (debit acc), show a warning message

        # Get info from "hhexpense.debit.category" model, prepare for comparision
        debit_info = self.env['hhexpense.debit.category'].search([])
        # use a list to store all acc, will be used in comparision
        debit_acc_list = []
        for info in debit_info:
            debit_acc_list.append(info.debit_acc)
        if self.expense_debit_acc:
            if self.expense_debit_acc in debit_acc_list:
                pass
                # if self.state == "reviewed":
                #     return {
                #         'warning': {
                #             'title': "Access Warning",
                #             'message': "Sorry, you can not edit a reviewed record",
                #         }
                #     }
                # else:
                #     pass
            else:
                return {
                    'warning': {
                        'title': "Input Error",
                        'message': "Sorry, we cannot find this Dr Acc in our system, Please input a existing Dr Acc. "
                                   "You can contact Administrator to make sure this Dr Acc exist. "
                                   "Thanks for understanding",
                    }
                }

    # @api.onchange('expense_line_currency', 'expense_line_cost')
    # def _onchange_amount(self):
    #     # this function is used for old workflow -- bank/cash, it is use to keep cash record has only one decimal
    #     print("Now, currency is: ", self.expense_line_currency.currency)
    #     if self.expense_line_currency.currency == "RMB":
    #         user_input = '%.2f' % self.expense_line_cost
    #         print("Get user input value: ", user_input)
    #         user_input_amount_last_decimal = str(user_input)[-1:]
    #         if user_input_amount_last_decimal != "0":
    #             print("Warning message")
    #             self.expense_line_cost = '%.1f' % self.expense_line_cost
    #             # return {
    #             #     'warning': {
    #             #         'title': "Decimal Error",
    #             #         'message': "Sorry, we cant pay you cash with 2 decimals, "
    #             #                    "Please make sure the amount only has 1 decimal. Thanks for understanding",
    #             #     }
    #             # }
    #         else:
    #             print("last decimal value is 0, ALL GOOD")
    #     else:
    #         print("Ignore since it is a non-rmb record")

    # -------------------- Start of HSBC / Generate file related function --------------------

    # ---------------- Generating the excel report for expenses ----------------
    @api.multi
    def create_data_structure(self, records):
        """
        This function serves to create a suitable data structure. The data can then be written to the excel report in order.

        ALL_CAT_ACC_LIST is listed in lexicographical order, which can ensure the column title will be written orderly.
        Data from the recordset is extracted and stored in their respective lists to form the dictionaries.

        Logic: Each employee can create multiple expenses in a period ==> emp info is the main key of the all_exp dict
               One expense can only occupy one row ==> expense dictionary as values of emp info key
               In expense dict, we have category info as key and the cost as value and the all_exp is up

        all_exp = {
                    emp_id#emp_name: {
                                      exp_date#exp_id: { cat_acc#cat_type : cost}
                    }
        }

        """
        col_title = [[] , []]
        all_exp = {}

        # Get all employee info, used for obtain employee account info
        emp_info = self.env['hr.employee'].sudo().search([])

        def append_data_list():
            # {a: {b: 1}}
            for rec in records:
                current_emp_acc = ''
                for emp in emp_info:
                    if emp.name == rec.expense_id.employee_name:
                        current_emp_acc = emp.bank_account_id.acc_number
                        print("this employee: " + rec.expense_id.employee_name + "'s Acc No. is: " + current_emp_acc)
                cur = rec.expense_line_currency.currency
                if not cur == "RMB":
                    cur = "HKD"

                cat_key = (str(rec.expense_cate_id.acc_no), str(rec.expense_debit_acc_name))
                emp_key = (
                    str(rec.expense_id.employee_id.rmb_account_no) if cur == "RMB" else current_emp_acc,
                    rec.employee_name
                    )
                exp_key = (
                    str(rec.expense_id.expense_create_date),
                    str(rec.expense_id.expense_num),
                    str(rec.expense_id.name)
                    )
                amt = float(rec.expense_line_cost) if cur == "RMB" else float(rec.expense_line_calculate)

                # -----
                if cur not in all_exp:
                    all_exp[cur] = {}
                if emp_key not in all_exp[cur]:
                    all_exp[cur][emp_key] = {}
                if exp_key not in all_exp[cur][emp_key]:
                    all_exp[cur][emp_key][exp_key] = {}

                all_exp[cur][emp_key][exp_key][cat_key] = all_exp[cur][emp_key][exp_key].get(cat_key, 0.0) + amt

                if cur == "HKD" and cat_key not in col_title[0]:
                    col_title[0].append(cat_key)
                elif cur == "RMB" and cat_key not in col_title[1]:
                    col_title[1].append(cat_key)
            for titles in col_title:
                titles.sort()

            return

        append_data_list()

        # for emp_dict in all_exp:
        #     all_exp[emp_dict] = collections.OrderedDict(sorted(all_exp[emp_dict].items()))  # sort exp data keys
        # all_exp = collections.OrderedDict(sorted(all_exp.items()))  # sort all_exp emp data keys by ID

        # get the selected exp line id for later use
        with open('./select_rec.txt', 'w') as sr:
            for rec in records:
                id_str = str(rec.id) + '\n'
                sr.write(id_str)
        rev_name = records[0].expense_id.rec_reviewer_name

        for cur in all_exp:
            self.create_exl_report(col_title[0] if cur == "HKD" else col_title[1], all_exp[cur], rev_name, cur)
            self.create_HSBC_txt(all_exp[cur], cur)


        # return

        #
        # self.create_HSBC_txt(all_exp)

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hhexpense.anticipated.date',
            'type': 'ir.actions.act_window',
        }

    def excel_range(self, type, row1, col1, row2, col2):
        '''
        excel_range() => input coordinate and return a cell range for formatting, eg,(0,0,5,5) = A1:F4
        '''
        if type == 'sel':  # sel for select range of cells only
            return f"{xl_rowcol_to_cell(row1, col1)}:{xl_rowcol_to_cell(row2, col2)}"
        elif type == 'sum':  # sum for doing summation for the selected range of cells
            return f"=SUM({xl_rowcol_to_cell(row1, col1)}:{xl_rowcol_to_cell(row2, col2)})"

    def create_exl_report(self, col_title, all_exp, rev_name, cur):
        cat_abbr_list = {  # need an abbr list for cat_types. The key is too long for excel
            'Postage & courier': 'Post.', 'Training Expenses': 'Train.', "Workers' Welfare": 'W. Wel.',
            'Cleaning & sanitation': 'Clean.', 'Travelling': 'Travel.', 'Transportation - Air': 'T.Air',
            'Gasoline': 'Gas.', 'Road charges': 'Road.', 'Transportation - sea': 'T.Sea', 'Entertainment': 'Enter.',
            'Communication': 'Comm.', 'Messing': 'Mess.', 'Transportation - Land': 'T.Land',
            'Postage & Courier': 'Post.', 'Repair & maintenance': 'Repair', 'Printing & Stationery': 'Print.',
            'Declaration': 'Decl.', 'Transportation - other': 'T.Other', 'Oversea travelling': 'O.Trav.',
            'Sundry Expenses': 'S.Exp', 'Office Expenses': 'O.Exp'
        }

        exfile = './expense_excel_report_rmb.xlsx' if cur == "RMB" else './expense_excel_report_hkd.xlsx'
        wb = xlsxwriter.Workbook(exfile)
        ws = wb.add_worksheet()

        # The few lines below define excel format and can be used while writing cells
        merge_format1 = wb.add_format({'bold': 1, 'border': 0, 'align': 'center', 'valign': 'vcenter', 'font_size': 20})
        merge_format2 = wb.add_format({'bold': 1, 'border': 0, 'align': 'center', 'valign': 'vcenter'})
        cf1 = wb.add_format({'num_format': 2, 'align': 'center'})
        cf2 = wb.add_format({'top': 1, 'bottom': 6, 'num_format': 2, 'align': 'center'})
        bold = wb.add_format({'bold': True, 'align': 'center'})
        title_style = wb.add_format({'bold': True, 'bottom': 1, 'align': 'center'})
        c_align = wb.add_format({'align': 'center'})


        def write_col_titles():
            ws.write(8, 0, 'Name', bold)
            ws.write(8, 1, 'Date', bold)
            ws.write(8, 2, 'Ref', title_style)
            ws.write(8, 3, 'Expense Summary', title_style)
            ws.set_column(0, 1, 15)
            ws.set_column(2, 2, 5)
            ws.set_column(3, 3, 20)

            cat_col = 4
            # for the categories in col_title, write each item to a column.
            for title in col_title:
                cat_acc, cat_type = title
                cat_acc = cat_acc[:4] + '-' + cat_acc[4:]  # cat_acc needs to be in format of 1234-56...
                if cat_type in cat_abbr_list:
                    cat_type = cat_abbr_list[cat_type]  # get the cat abbr from the list
                ws.write(7, cat_col, cat_acc, bold)
                ws.write(8, cat_col, cat_type, title_style)
                ws.set_column(cat_col, cat_col, 10)
                cat_col += 1
            return cat_col - 1

        def write_cell_data():
            # write data to cells row by row
            data_row = 9
            for emp_key in all_exp:
                row_data = []
                emp_name = emp_key[1]
                ws.write(data_row, 0, emp_name)

                for exp_key in all_exp[emp_key]:
                    exp_date, exp_id, exp_des = exp_key
                    row_data.append(exp_date)
                    row_data.append(exp_id)
                    row_data.append(exp_des)

                    for title in col_title:
                        for cat_key in all_exp[emp_key][exp_key]:
                            if cat_key == title:
                                row_data.append(float(all_exp[emp_key][exp_key][cat_key]))
                                break  # break the for loop at that iterator to avoid meaningless loop (as a match has been found)
                        else:
                            row_data.append("")  # append the list with a space if no match is found
                    # col title     [  DATE      , REF,    CAT1, CAT2,  CAT3  ,CAT4,CAT5]
                    # eg row_data = ["2018-08-27", "7", "500.00", "", "450.00", "", ""]
                    ws.write_row(data_row, 1, row_data, c_align)
                    row_data = [] # clear the list if the employee has more than 1 expense in the period
                    data_row += 1

            # data_row will add 1 for the last unmatched item
            return (data_row - 1)

        def cal_total_exp_amounts(data_row, cat_col):
            # adding 2 decimal places for cost data cells
            data_range = self.excel_range('sel', 9, 4, data_row, cat_col)
            ws.conditional_format(data_range, {'type': 'cell', 'criteria': '>=', 'value': 0, 'format': cf1})

            total_col = cat_col + 1
            total_row = data_row + 1
            remark_col = cat_col + 2
            footer_row = total_row + 4
            ws.write(8, total_col, "Total", title_style)
            ws.set_column(total_col, total_col, 10)
            ws.write(8, remark_col, "Remark", title_style)
            ws.merge_range(self.excel_range('sel', 0, 0, 2, remark_col), 'Hung Hing Off-Set Printing Co. Ltd',
                           merge_format1)

            ws.merge_range(self.excel_range('sel', 3, 0, 3, remark_col),
                           "PETTY CASH EXPENSES (RMB)" if cur == "RMB" else "PETTY CASH EXPENSES (HKD)", merge_format2)
            # leave a blank, merged cell for batch number
            ws.merge_range(self.excel_range('sel', 4, 0, 4, remark_col), "", merge_format2)
            # calculate total of each expense
            for i in range(9, data_row + 1):
                ws.write_formula(i, total_col, self.excel_range('sum', i, 4, i, cat_col), cf1)

            # calculate total of each category
            for i in range(4, total_col + 1):
                ws.write_formula(total_row, i, self.excel_range('sum', 9, i, data_row, i), cf2)

            ws.merge_range(self.excel_range('sel', footer_row, 0, footer_row, 2), 'Generated by: %s' % rev_name)
            ws.merge_range(self.excel_range('sel', footer_row + 4, 0, footer_row + 4, 6),
                           'CHECKED BY:_____________________  APPROVED BY:_____________________')

            wb.close()
            return

        cat_col = write_col_titles()
        data_row = write_cell_data()
        cal_total_exp_amounts(data_row, cat_col)
        return
    # ------------------- Finished generating an excel report ------------------
    # ------------------- Generate HSBC Text File ------------------------------
    def str_replace(self, str, sstr, index, op):
        str = list(str)
        sstr = list(sstr)
        if op == '+':
            str[index:index+len(sstr)] = sstr
        elif op == '-':
            str[index-len(sstr):index] = sstr
        str = ''.join(str)
        return str

    def create_HSBC_txt(self, all_exp, cur):
        import datetime
        from pytz import timezone
        """
        Heading space occupied:
        "Auto plan Code":                             1   # "F"
        "First Party Current Account Number":         12  # Account No. that company used to pay expense
        "Payment Code":                               3   # Waiting for Accounting input/decide
        "First Party Reference":                      12  # e.g."250818"(dynamic) + "EmpExp"
        "Value Date":                                 6   # Accountant input date --- anticipated date
        "Input Medium":                               1   # "K"
        "File Name":                                  8   # "********", 8 digits
        "Total No of Instruction":                    5   # How many record you have in this file
        "Total Amount of Instruction":                10  # The total amount for this file
        "Overflow Total No of Instruction":           7   # Empty, fill with space
        "Overflow Total Amount of Instruction":       12  # Empty, fill with space
        "FILLER":                                     2   # Empty, fill with space
        "Instruction Source":                         1   # "1"
        ----------------------------------------------------------------------------------------------------------------
        Data space occupied:
        "FILLER":                                     1   # Empty, fill with space
        "Second Party Identifier":                    12  # "Reimburse"
        "Second Party Bank Account Name":             20  # employee name
        "Second Party Account":                       15  # employee Acc - bank code(3) + branch no.(3) + Acc No.(9)
        "Amount":                                     10  # total amount for one employee
        "Filler":                                     4   # Empty, fill with space
        """
        emp_dict = {}
        for emp_key in all_exp:
            for exp_key in all_exp[emp_key]:
                emp_dict[emp_key] = emp_dict.get(emp_key, 0) + sum(all_exp[emp_key][exp_key].values())

        tot_rec = str(len(emp_dict))
        tot_amt = str(format(sum(emp_dict.values()), '.2f')).replace('.', '')
        time = str(datetime.datetime.now(tz=timezone('Asia/Hong_Kong')).strftime('%d' + '%m' + '%y'))

        if cur == "RMB":
            data = ['./hsbc_rmb.txt', 'F808852339285B01', 'RmbExp']
        else:
            data = ['./hsbc_hkd.txt', 'F600331102001O03', 'HkdExp']

        txt = open(data[0], "w+", encoding='utf-8')

        sketch_hstr = data[1] + time + data[2] + 'AnTiDaK********000000000000000                     1' + '\r\n'
        sketch_hstr = self.str_replace(sketch_hstr, tot_rec, 48, '-')
        hstr = self.str_replace(sketch_hstr, tot_amt, 58, '-')
        txt.write(hstr)

        for emp_info in emp_dict:
            sketch_cstr = ' ' + 'Reimburse   ' + '                                   0000000000' \
                                                 '                      ' + '\r\n'
            acc, name = emp_info
            if len(name) > 20:
                name = name[:20]
            amt = str(format(emp_dict[emp_info], '.2f')).replace('.', '')
            sketch_cstr = self.str_replace(sketch_cstr, name, 13, '+')
            sketch_cstr = self.str_replace(sketch_cstr, acc, 33, '+')
            cstr = self.str_replace(sketch_cstr, amt, 58, '-')
            txt.write(cstr)
        txt.close()

    # Following function is used for old workflow -- bank/cash
    # def conditional_check_bank_record(self):
    #     if self.pay_bank_cash == "Bank":
    #         print("Bank conditional checking...this is an bank record. Pass!")
    #         return True
    #     else:
    #         print("Bank conditional checking...this is not an bank record. Blocked!")
    #         return False
    #         # none of following will pop up message
    #         # raise UserError(_('This action is for cash but you are dealing with bank record now.'
    #         #                   'Please select an appropriate action'))
    #         # return {
    #         #     'warning': {
    #         #         'title': "Inappropriate action",
    #         #         'message': "This action is for cash but you are dealing with bank record now."
    #         #                    "Please select an appropriate action",
    #         #     }
    #         # }
    # def conditional_check_cash_record(self):
    #     if self.pay_bank_cash == "Cash":
    #         print("Cash conditional checking...this is a cash record. Pass!")
    #         return True
    #     else:
    #         print("Cash conditional checking...this is not a cash record. Blocked!")
    #         return False

    # @api.multi
    # def get_input_anticipated_date(self, i, len_of_records):
    #     # Generate needed files
    #     # If this is the first record (actually checking: replace old file if this is the first time writing data)
    #     if i == 1:
    #         print("gagaga")
    #         # Selected record's id file
    #         temp_file_get_selected_rec_id = open("./hsbc_intermediate_file_get_selected_rec_id.txt", "w",
    #                                              encoding="utf-8")
    #         # Selected record's employee_name file
    #         temp_file_get_rec_employee_name = open("./hsbc_intermediate_file_get_rec_employee_name.txt", "w",
    #                                                encoding="utf-8")
    #         # Selected record's expense_line_calculate(converted amount, which is in HKD) file
    #         temp_file_get_converted_amount = open("./hsbc_intermediate_file_get_converted_amount.txt", "w",
    #                                               encoding="utf-8")
    #         # If this is a verified & bank record, write record's info into corresponding file
    #         if self.state == 'verified' and self.pay_bank_cash == 'Bank':
    #             print("First time, add this verified & bank record for HSBC txt file!")
    #             temp_file_get_selected_rec_id.write(str(self.id) + '\n')
    #             temp_file_get_rec_employee_name.write(str(self.expense_id.employee_name) + '\n')
    #             temp_file_get_converted_amount.write(str(self.expense_line_calculate) + '\n')
    #     else:
    #         print("xixixi")
    #         temp_file_get_selected_rec_id = open("./hsbc_intermediate_file_get_selected_rec_id.txt", "a",
    #                                              encoding="utf-8")
    #         temp_file_get_rec_employee_name = open("./hsbc_intermediate_file_get_rec_employee_name.txt", "a",
    #                                                encoding="utf-8")
    #         temp_file_get_converted_amount = open("./hsbc_intermediate_file_get_converted_amount.txt", "a",
    #                                               encoding="utf-8")
    #         if self.state == 'verified' and self.pay_bank_cash == 'Bank':
    #             print("=-=-=-=-=-= Add this verified & bank record for HSBC txt file!")
    #             temp_file_get_selected_rec_id.write(str(self.id) + '\n')
    #             temp_file_get_rec_employee_name.write(str(self.expense_id.employee_name) + '\n')
    #             temp_file_get_converted_amount.write(str(self.expense_line_calculate) + '\n')
    #
    #     # Operation done, close all files
    #     temp_file_get_selected_rec_id.close()
    #     temp_file_get_rec_employee_name.close()
    #     temp_file_get_converted_amount.close()
    #
    #     # When it goes to the last record, return a form view for user input (HSBC anticipated upload date)
    #     if i == len_of_records:
    #         return {
    #             'view_type': 'form',
    #             'view_mode': 'form',
    #             'res_model': 'hhexpense.anticipated.date',
    #             'type': 'ir.actions.act_window',
    #             'rec_info': i
    #         }

    @api.multi
    def get_input_anticipated_date(self, records):
        # Generate needed files
        # If this is the first record (actually checking: replace old file if this is the first time writing data)
        if 1 == 1:
            print("gagaga")
            # Selected record's id file
            temp_file_get_selected_rec_id = open("./hsbc_intermediate_file_get_selected_rec_id.txt", "w",
                                                 encoding="utf-8")
            # Selected record's employee_name file
            temp_file_get_rec_employee_name = open("./hsbc_intermediate_file_get_rec_employee_name.txt", "w",
                                                   encoding="utf-8")
            # Selected record's expense_line_calculate(converted amount, which is in HKD) file
            temp_file_get_converted_amount = open("./hsbc_intermediate_file_get_converted_amount.txt", "w",
                                                  encoding="utf-8")
            # If this is a verified & bank record, write record's info into corresponding file
            if self.state == 'reviewed':
                print("First time, add this verified & bank record for HSBC txt file!")
                temp_file_get_selected_rec_id.write(str(self.id) + '\n')
                temp_file_get_rec_employee_name.write(str(self.expense_id.employee_name) + '\n')
                temp_file_get_converted_amount.write(str(self.expense_line_calculate) + '\n')
            else:
                print("cant get anything! sth wrong")
        else:
            print("xixixi")
            temp_file_get_selected_rec_id = open("./hsbc_intermediate_file_get_selected_rec_id.txt", "a",
                                                 encoding="utf-8")
            temp_file_get_rec_employee_name = open("./hsbc_intermediate_file_get_rec_employee_name.txt", "a",
                                                   encoding="utf-8")
            temp_file_get_converted_amount = open("./hsbc_intermediate_file_get_converted_amount.txt", "a",
                                                  encoding="utf-8")
            if self.state == 'reviewed':
                print("=-=-=-=-=-= Add this verified & bank record for HSBC txt file!")
                temp_file_get_selected_rec_id.write(str(self.id) + '\n')
                temp_file_get_rec_employee_name.write(str(self.expense_id.employee_name) + '\n')
                temp_file_get_converted_amount.write(str(self.expense_line_calculate) + '\n')
            else:
                print("cant get anything! sth wrong again")

        # Operation done, close all files
        temp_file_get_selected_rec_id.close()
        temp_file_get_rec_employee_name.close()
        temp_file_get_converted_amount.close()

        # When it goes to the last record, return a form view for user input (HSBC anticipated upload date)
        # if i == len_of_records:
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hhexpense.anticipated.date',
            'type': 'ir.actions.act_window',
            'rec_info': i
        }

    @api.multi
    def get_input_payment_approved_date(self, i, len_of_records):
        # Within all selected/ticked sub-expense records, if it is the first record (i = 1), use "w" mode open file.
        # The reason is that we need to check if any file exist already.
        # (This is what "w" operation do) if yes, we should clean the contents in the existing file and write
        # info. into it. If no, create a new file and write inside it.
        if i == 1:
            selected_rec_id_file = open("./flexacc_intermediate_file_get_selected_rec_id.txt", "w", encoding="utf-8")
        # Now, when it goes to 2, 3, 4...N's sub-expense records, use "a" mode to add/append info. into file
        else:
            selected_rec_id_file = open("./flexacc_intermediate_file_get_selected_rec_id.txt", "a", encoding="utf-8")

        # Store sub-expense record's id into file, one id a line!
        # So, in this way, our controller can read this file later and know this is the records he needs to dealing with
        selected_rec_id_file.write(str(self.id) + '\n')
        # Operation done, close file
        selected_rec_id_file.close()

        # Now, when it goes to the last selected sub record (i == len_of_record),
        # return a form view for user input (FlexAccount payment approve date)
        if i == len_of_records:
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hhexpense.payment.date',
                'type': 'ir.actions.act_window',
            }

    # @api.multi
    # def generate_hsbcnet_txt_file(self, i, len_of_records):
    #
    #     if self.pay_bank_cash == "Bank":
    #         self.expense_line_is_processing = True
    #         print("Marked")
    #     else:
    #         # pass
    #         self.expense_line_is_processing = False
    #         print("Not Marked")
    #
    #     # print("id of record:  ", self.id)
    #     # print("position of record:  ", i)
    #     # print("length of record:    ", len_of_records)
    #     # if self.state == 'verified' and self.pay_bank_cash == 'Cash':
    #     #     print("Add this verified & bank record")
    #
    #     # Use a file to store all selected record's id
    #     # If this is the first record (actually checking: replace old file if this is the first time writing data)
    #     if i == 1:
    #         txt = open("./hsbc_intermediate.txt", "w", encoding="utf-8")
    #         # If this is a verified & bank record
    #         if self.state == 'verified' and self.pay_bank_cash == 'Bank':
    #             print("First time, add this verified & bank record for HSBC txt file!")
    #             txt.write(str(self.id) + '\n')
    #     else:
    #         txt = open("./hsbc_intermediate.txt", "a", encoding="utf-8")
    #         if self.state == 'verified' and self.pay_bank_cash == 'Bank':
    #             print("=-=-=-=-=-= Add this verified & bank record for HSBC txt file!")
    #             txt.write(str(self.id) + '\n')
    #     # Operation done, close file
    #     txt.close()
    #
    #     # Use a file to store all selected record's "expense_line_calculate" (receive amount, which is in HKD)
    #     if i == 1:
    #         txt = open("./intermediate_hsbc_cal_total_amount_bank.txt", "w", encoding="utf-8")
    #         # If this is a verified & bank record
    #         if self.state == 'verified' and self.pay_bank_cash == 'Bank':
    #             txt.write(str(self.expense_line_calculate) + '\n')
    #     else:
    #         txt = open("./intermediate_hsbc_cal_total_amount_bank.txt", "a", encoding="utf-8")
    #         # If this is a verified & bank record
    #         if self.state == 'verified' and self.pay_bank_cash == 'Bank':
    #             txt.write(str(self.expense_line_calculate) + '\n')
    #     # Operation done, close file
    #     txt.close()
    #
    #     # Use a file to store all selected record's employee name
    #     # If this is the first record (actually checking: replace old file if this is the first time writing data)
    #     if i == 1:
    #         txt = open("./intermediate_hsbc_pdf_get_employee_name.txt", "w", encoding="utf-8")
    #         # If this is a verified & bank record
    #         if self.state == 'verified' and self.pay_bank_cash == 'Bank':
    #             txt.write(str(self.expense_id.employee_name) + '\n')
    #     else:
    #         txt = open("./intermediate_hsbc_pdf_get_employee_name.txt", "a", encoding="utf-8")
    #         if self.state == 'verified' and self.pay_bank_cash == 'Bank':
    #             txt.write(str(self.expense_id.employee_name) + '\n')
    #     # Operation done, close file
    #     txt.close()
    #
    #     # Following line not work, work if you write it in different method and call it from XML
    #     # Update sub-record's state, update "expense_line_is_paid" value
    #     # self.expense_line_is_paid = True
    #
    #     # Need refresh to display, why?
    #     # if self.pay_bank_cash == "Bank":
    #     #     self.expense_line_is_processing = True
    #     #     print("Marked")
    #     # else:
    #     #     # pass
    #     #     self.expense_line_is_processing = False
    #     #     print("Not Marked")
    #
    #     # Now, when it goes to the last sub-expense record (i == len_of_sub-record),
    #     # calculate total amount, return url and then controller catch the url to do the "download txt file" action
    #     if i == len_of_records:
    #         # # Get employee name
    #         # # Open file and get all employee name (no duplicate)
    #         # txt = open('./intermediate_hsbc_pdf_get_employee_name.txt', 'r', encoding='utf-8')
    #         # # Use a list to store all different employee name, why not use "set"? not ez to access element
    #         # employee_name_list = []
    #         # for line in txt:
    #         #     pure_string = line.strip('\n')
    #         #     if pure_string not in employee_name_list:
    #         #         print("add")
    #         #         employee_name_list.append(pure_string)
    #         #     else:
    #         #         print("ignore")
    #         # txt.close()
    #         # print("Within all selected sub-expense, include following employee's records:", employee_name_list)
    #         # # calculate "total record amount that it is pay by bank" based on txt file
    #         # total_amount_bank = 0
    #         # txt = open('./intermediate_hsbc_cal_total_amount_bank.txt', 'r', encoding='utf-8')
    #         # for line in txt:
    #         #     int_line = line.strip('\n')
    #         #     total_amount_bank += float(int_line)
    #         # txt.close()
    #         # print("total_amount_bank: ", total_amount_bank)
    #         #
    #         # # Get total amount for each employee
    #         # # Compare to all record in hhexpense_line, if name is the same, add corresponding amount and calculate it.
    #         # # First, we need create a dic to store key-value pair (employee_name - total_amount),
    #         # # we use employee name from employee_name_list as key since they are unique
    #         # # dic_employee_and_own_total_amount = {emp_name:0 for emp_name in employee_name_list}
    #         # dic_employee_and_own_total_amount = {}
    #         # for each_employee in employee_name_list:
    #         #     # Then, we need a variable to store calculated amount
    #         #     print("Start calculate this employee's total amount")
    #         #     calculate_total_amount_for_this_employee = 0
    #         #     # For each sub-record in hhexpense_line, check if it is belongs to
    #         #     # current test-looping-employee (with other 2 conditions). If yes, add its amount
    #         #     get_all_sub_rec = self.env['hhexpense.line'].search([])
    #         #     for sub_rec in get_all_sub_rec:
    #         #         if sub_rec.expense_id.employee_name == each_employee \
    #         #                 and sub_rec.state == "verified" \
    #         #                 and sub_rec.pay_bank_cash == "Bank":
    #         #             print("this sub record belongs to this employee, add!")
    #         #             calculate_total_amount_for_this_employee = calculate_total_amount_for_this_employee \
    #         #                                                        + sub_rec.expense_line_calculate
    #         #     # Current test-looping-employee's calculation done, save into dict as key - pair
    #         #     dic_employee_and_own_total_amount[each_employee] = calculate_total_amount_for_this_employee
    #         # print("Within all selected sub-expense, all different 'employee - total_amount' key-value pair are:",
    #         #       dic_employee_and_own_total_amount)
    #         # # Add one more key value pair to this dictionary -- "total_amount_all_employee: total_amount_bank"
    #         # new_key = "total_amount_all_employee"
    #         # dic_employee_and_own_total_amount[new_key] = total_amount_bank
    #         # print("added new key", dic_employee_and_own_total_amount)
    #
    #         self.check_if_expenses_allowed_to_post()
    #
    #         return {
    #             'name': 'Go to website',
    #             'type': 'ir.actions.act_url',
    #             'target': 'self',
    #             'url': '/web/binary/generate_hsbcnet_txt_file'
    #         }
    #
    #         # import json
    #         # Ok, now we want controller do the rest - get data and generate a PDF report for us
    #         # We are using python way to do the post request
    #         # need_this_data = {
    #         #     'total_amount_each_employee': [dic_employee_and_own_total_amount],
    #         #     'total_amount_all_employee': total_amount_bank
    #         # }
    #         # requests.post('http://localhost:8069/web/binary/generate_hsbcnet_txt_file',
    #         #                  data=dic_employee_and_own_total_amount)
    #         # headers = {'Content-Type': 'application/json'}
    #         # r = requests.post('http://localhost:8069/web/binary/generate_hsbcnet_txt_file',
    #         #                   data=json.dumps(need_this_data), headers=headers)
    #         # a = 1

    # @api.multi
    # def generate_hsbcnet_txt_file(self, i, len_of_records):
    #
    #     self.expense_line_is_processing = True
    #
    #     # print("id of record:  ", self.id)
    #     # print("position of record:  ", i)
    #     # print("length of record:    ", len_of_records)
    #     # if self.state == 'verified' and self.pay_bank_cash == 'Cash':
    #     #     print("Add this verified & bank record")
    #
    #     # Use a file to store all selected record's id
    #     # If this is the first record (actually checking: replace old file if this is the first time writing data)
    #     if i == 1:
    #         txt = open("./hsbc_intermediate.txt", "w", encoding="utf-8")
    #         # If this is a verified & bank record
    #         if self.state == 'reviewed':
    #             print("First time, add this verified & bank record for HSBC txt file!")
    #             txt.write(str(self.id) + '\n')
    #     else:
    #         txt = open("./hsbc_intermediate.txt", "a", encoding="utf-8")
    #         if self.state == 'reviewed':
    #             print("=-=-=-=-=-= Add this verified & bank record for HSBC txt file!")
    #             txt.write(str(self.id) + '\n')
    #     # Operation done, close file
    #     txt.close()
    #
    #     # Use a file to store all selected record's "expense_line_calculate" (receive amount, which is in HKD)
    #     if i == 1:
    #         txt = open("./intermediate_hsbc_cal_total_amount_bank.txt", "w", encoding="utf-8")
    #         # If this is a verified & bank record
    #         if self.state == 'reviewed':
    #             txt.write(str(self.expense_line_calculate) + '\n')
    #     else:
    #         txt = open("./intermediate_hsbc_cal_total_amount_bank.txt", "a", encoding="utf-8")
    #         # If this is a verified & bank record
    #         if self.state == 'reviewed':
    #             txt.write(str(self.expense_line_calculate) + '\n')
    #     # Operation done, close file
    #     txt.close()
    #
    #     # Use a file to store all selected record's employee name
    #     # If this is the first record (actually checking: replace old file if this is the first time writing data)
    #     if i == 1:
    #         txt = open("./intermediate_hsbc_pdf_get_employee_name.txt", "w", encoding="utf-8")
    #         # If this is a verified & bank record
    #         if self.state == 'reviewed':
    #             txt.write(str(self.expense_id.employee_name) + '\n')
    #     else:
    #         txt = open("./intermediate_hsbc_pdf_get_employee_name.txt", "a", encoding="utf-8")
    #         if self.state == 'reviewed':
    #             txt.write(str(self.expense_id.employee_name) + '\n')
    #     # Operation done, close file
    #     txt.close()
    #
    #     # Following line not work, work if you write it in different method and call it from XML
    #     # Update sub-record's state, update "expense_line_is_paid" value
    #     # self.expense_line_is_paid = True
    #
    #     # Need refresh to display, why?
    #     # if self.pay_bank_cash == "Bank":
    #     #     self.expense_line_is_processing = True
    #     #     print("Marked")
    #     # else:
    #     #     # pass
    #     #     self.expense_line_is_processing = False
    #     #     print("Not Marked")
    #
    #     # Now, when it goes to the last sub-expense record (i == len_of_sub-record),
    #     # calculate total amount, return url and then controller catch the url to do the "download txt file" action
    #     if i == len_of_records:
    #         # # Get employee name
    #         # # Open file and get all employee name (no duplicate)
    #         # txt = open('./intermediate_hsbc_pdf_get_employee_name.txt', 'r', encoding='utf-8')
    #         # # Use a list to store all different employee name, why not use "set"? not ez to access element
    #         # employee_name_list = []
    #         # for line in txt:
    #         #     pure_string = line.strip('\n')
    #         #     if pure_string not in employee_name_list:
    #         #         print("add")
    #         #         employee_name_list.append(pure_string)
    #         #     else:
    #         #         print("ignore")
    #         # txt.close()
    #         # print("Within all selected sub-expense, include following employee's records:", employee_name_list)
    #         # # calculate "total record amount that it is pay by bank" based on txt file
    #         # total_amount_bank = 0
    #         # txt = open('./intermediate_hsbc_cal_total_amount_bank.txt', 'r', encoding='utf-8')
    #         # for line in txt:
    #         #     int_line = line.strip('\n')
    #         #     total_amount_bank += float(int_line)
    #         # txt.close()
    #         # print("total_amount_bank: ", total_amount_bank)
    #         #
    #         # # Get total amount for each employee
    #         # # Compare to all record in hhexpense_line, if name is the same, add corresponding amount and calculate it.
    #         # # First, we need create a dic to store key-value pair (employee_name - total_amount),
    #         # # we use employee name from employee_name_list as key since they are unique
    #         # # dic_employee_and_own_total_amount = {emp_name:0 for emp_name in employee_name_list}
    #         # dic_employee_and_own_total_amount = {}
    #         # for each_employee in employee_name_list:
    #         #     # Then, we need a variable to store calculated amount
    #         #     print("Start calculate this employee's total amount")
    #         #     calculate_total_amount_for_this_employee = 0
    #         #     # For each sub-record in hhexpense_line, check if it is belongs to
    #         #     # current test-looping-employee (with other 2 conditions). If yes, add its amount
    #         #     get_all_sub_rec = self.env['hhexpense.line'].search([])
    #         #     for sub_rec in get_all_sub_rec:
    #         #         if sub_rec.expense_id.employee_name == each_employee \
    #         #                 and sub_rec.state == "verified" \
    #         #                 and sub_rec.pay_bank_cash == "Bank":
    #         #             print("this sub record belongs to this employee, add!")
    #         #             calculate_total_amount_for_this_employee = calculate_total_amount_for_this_employee \
    #         #                                                        + sub_rec.expense_line_calculate
    #         #     # Current test-looping-employee's calculation done, save into dict as key - pair
    #         #     dic_employee_and_own_total_amount[each_employee] = calculate_total_amount_for_this_employee
    #         # print("Within all selected sub-expense, all different 'employee - total_amount' key-value pair are:",
    #         #       dic_employee_and_own_total_amount)
    #         # # Add one more key value pair to this dictionary -- "total_amount_all_employee: total_amount_bank"
    #         # new_key = "total_amount_all_employee"
    #         # dic_employee_and_own_total_amount[new_key] = total_amount_bank
    #         # print("added new key", dic_employee_and_own_total_amount)
    #
    #         self.check_if_expenses_allowed_to_post()
    #
    #         return {
    #             'name': 'Go to website',
    #             'type': 'ir.actions.act_url',
    #             'target': 'self',
    #             'url': '/web/binary/generate_hsbcnet_txt_file'
    #         }
    #
    #         # import json
    #         # Ok, now we want controller do the rest - get data and generate a PDF report for us
    #         # We are using python way to do the post request
    #         # need_this_data = {
    #         #     'total_amount_each_employee': [dic_employee_and_own_total_amount],
    #         #     'total_amount_all_employee': total_amount_bank
    #         # }
    #         # requests.post('http://localhost:8069/web/binary/generate_hsbcnet_txt_file',
    #         #                  data=dic_employee_and_own_total_amount)
    #         # headers = {'Content-Type': 'application/json'}
    #         # r = requests.post('http://localhost:8069/web/binary/generate_hsbcnet_txt_file',
    #         #                   data=json.dumps(need_this_data), headers=headers)
    #         # a = 1

    # @api.multi
    # def mark_cash_record_as_paid(self):
    #
    #     if self.pay_bank_cash == "Cash":
    #         self.expense_line_is_paid = True
    #         print("Cash record marked")
    #     else:
    #         self.expense_line_is_paid = False
    #         print("This is not cash record, Ignore!")
    #     self.check_if_expenses_allowed_to_post()

    # @api.multi
    # def mark_bank_record_as_processing(self):
    #     if self.pay_bank_cash == "Bank":
    #         self.expense_line_is_processing = True
    #         print("Bank record marked")
    #     else:
    #         # pass
    #         self.expense_line_is_processing = False
    #         print("This is not bank record, Ignore!")
    #     self.check_if_expenses_allowed_to_post()
    # @api.multi
    # def mark_record_as_processing(self):
    #     self.expense_line_is_processing = True
    #     print("Record marked")
    #     self.check_if_expenses_allowed_to_post()

    # def check_if_expenses_allowed_to_post(self):
    #     # Purpose of this function:
    #     # If allowed, record will be moved to paid and ready for posting
    #     # i.e. Under the same master record, this expense can be post only when
    #     # all sub bank records is processing and all sub cash records is paid
    #     print("trigger by cash action")
    #     # get all sub rec
    #     master_records = self.env['hhexpense.hhexpense'].search([])
    #     # Go through each master record in database
    #
    #     for rec in master_records:
    #         print("master rec:   ", rec.name)
    #         print("count sub rec:", len(rec.expense_line))
    #         # For each sub item in this master record
    #         for sub_rec in rec.expense_line:
    #             if sub_rec.state == "verified":
    #                 if sub_rec.pay_bank_cash == "Bank":
    #                     if not sub_rec.expense_line_is_processing:
    #                         print("bank not match")
    #                         break
    #                 elif sub_rec.pay_bank_cash == "Cash":
    #                     if not sub_rec.expense_line_is_paid:
    #                         print("cash not match")
    #                         break
    #         # no break during for-loop, thus, this record can be output. i.e. mark it as paid, ready to post
    #         else:
    #             rec.state = "paid"
    #             print("this expense is ready to post")
    #             # self.env['hhexpense.hhexpense'].pay_expense()
    #             # self.pay_expense()
    #             # print("email send")
    #     print("trigger by cash action --- done")
    def check_if_expenses_allowed_to_post(self):
        # Purpose of this function:
            # only "verified" records allowed to post
        # we actually checking the first selected record, not every record that user selected
        print("The record we are checking :", self.expense_line_name, self.state, self.has_batch_number)
        if self.state == 'verified':
            return True
        else:
            print("?")
            raise UserError(_("Sorry! only 'verified' record allowed to post"))

    # -------------------- End of HSBC / Generate file related function --------------------

    @api.depends("expense_line_currency")
    def _compute_payment_method(self):
        # Purpose of this function: Update "pay_hkd_rmb" field
        # If original currency is non-hkd
        for rec in self:
            if rec.expense_line_currency:
                if rec.expense_line_currency.currency == "RMB":
                    rec.pay_hkd_rmb = "RMB"
                    print("Detect 'RMB' currency, thus it is pay by RMB account")
                else:
                    rec.pay_hkd_rmb = "HKD"
                    print("Detect non-'RMB' currency, thus it is pay by HKD account")

    @api.depends("expense_line_currency", "pay_hkd_rmb")
    def _compute_hh_rate(self):
        for rec in self:
            if rec.expense_line_currency and rec.pay_hkd_rmb:
                if rec.expense_line_currency.currency == "RMB":
                    rec.exchange_rate = 1.0
                    print("emmm?")
                else:
                    rec.exchange_rate = rec.expense_line_currency.exchange_rate
    # @api.depends("expense_line_currency")
    # def _compute_hh_rate(self):
    #     for rec in self:
    #         if rec.expense_line_currency:
    #             rec.exchange_rate = rec.expense_line_currency.exchange_rate

    @api.depends('expense_id.employee_department')
    def _compute_convert_dep_to_exp_type(self):
        for sub_rec in self:
            get_emp_dep = sub_rec.expense_id.employee_department
        print("this employee's department is: ", get_emp_dep)
        get_convert_list = self.env['hhexpense.convert.deptoexp'].search([])
        # Find corresponding expense type for users department
        convert = ""
        for item in get_convert_list:
            # print("the whole mapping list contains :", item.user_department, item.convert_to_expense_type)
            if item.user_department == get_emp_dep:
                convert = item.convert_to_expense_type
        # Update type to current sub record
        for rec in self:
            rec.convert_dep_to_exp_type = convert
            print("Able to get value :", rec.convert_dep_to_exp_type)

    @api.multi
    @api.depends('expense_line_cost', 'exchange_rate')
    def _compute_after_exchange_money(self):
        for rec in self:
            print("------ Compute actual amount ------")
            print("(using id)Start calculation for record: ",
                  rec)  # [columns.index(('id',))] new object at location XXXXXXXXX
            print("(using ids)Start calculation for record: ", rec.ids)  # []
            if rec.pay_hkd_rmb == "HKD":
                rec.expense_line_calculate = rec.expense_line_cost * rec.exchange_rate
                print("Keep 2 decimal's value for this bank record")
            else:
                # value_translate = rec.expense_line_cost * rec.exchange_rate
                # rec.expense_line_calculate = round(round(value_translate, 1), 2)
                # print("Remove last decimal's value for this cash record, but will still has 2 decimal")

                # since RMB is pay by bank now, no needs to "round up" the amount
                value_translate = rec.expense_line_cost * rec.exchange_rate
                rec.expense_line_calculate = round(value_translate, 2)
                print("Remove last decimal's value for this cash record, but will still has 2 decimal")
            print("Calculation complete: ", rec.expense_line_calculate)
    # @api.multi
    # @api.depends('expense_line_cost', 'exchange_rate')
    # def _compute_after_exchange_money(self):
    #     for rec in self:
    #         print("------ Compute actual amount ------")
    #         print("(using id)Start calculation for record: ",
    #               rec)  # [columns.index(('id',))] new object at location XXXXXXXXX
    #         print("(using ids)Start calculation for record: ", rec.ids)  # []
    #         rec.expense_line_calculate = rec.expense_line_cost * rec.exchange_rate
    #         print("Keep 2 decimal's value for this record")
    #         print("Calculation complete: ", '%0.2f' % rec.expense_line_calculate)

    @api.depends('expense_line_calculate')
    def _compute_copy_calculated_hkd_amount(self):
        for rec in self:
            if rec.pay_hkd_rmb == "HKD":
                rec.expense_line_hkd_display_amount = rec.expense_line_calculate
                rec.expense_line_rmb_display_amount = 0
            else:
                pass
            print("this HKD record's 2 display amount would be :", rec.expense_line_hkd_display_amount,
                                                                   rec.expense_line_rmb_display_amount)

    @api.depends('expense_line_calculate')
    def _compute_copy_calculated_rmb_amount(self):
        for rec in self:
            if rec.pay_hkd_rmb == "RMB":
                rec.expense_line_hkd_display_amount = 0
                rec.expense_line_rmb_display_amount = rec.expense_line_calculate
            else:
                pass
            print("this RMB record's 2 display amount would be :", rec.expense_line_hkd_display_amount,
                                                                   rec.expense_line_rmb_display_amount)

    @api.onchange('expense_line_currency')
    def _rmb_account_check(self):
        emp_rec = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)])
        if self.expense_line_currency.currency == 'RMB' and not emp_rec.rmb_account_no:
            self.expense_line_currency = 0
            return{
                'warning': {
                    'title': 'Missing Information',
                    'message': 'An RMB bank account is required to submit expenses paid in RMB. Please contact '
                               'HR Dept. to update your bank account number.'
                }
            }

    @api.onchange('expense_line_date')
    def _onchange_check_expense_date(self):
        if self.expense_line_date:
            user_input = str(self.expense_line_date)
            # Remove all special characters, punctuation and spaces from string then read it as integer
            user_input_int = int(''.join(char for char in user_input if char.isalnum()))
            today = int(datetime.datetime.now().strftime('%Y%m%d'))
            if user_input_int > today:
                print("[This message is come from 'hhexpense.py'] dude, srs? you think expense date will later than "
                      "today?")
                self.expense_line_date = 0
                today_date = datetime.datetime.now().strftime('%Y-%m-%d')
                return {
                    'warning': {
                        'title': "Incorrect input",
                        'message': "Expense date can't be later than today("
                                   + str(today_date)
                                   + "), Please select again",
                    }
                }
        else:
            print("[This message is come from 'hhexpense.py'] Didn't detect 'expense_date' input, waiting user next "
                  "action...")

    @api.depends('expense_line_currency')
    def _compute_credit_acc(self):
        for rec in self:
            if rec.expense_line_currency:
                if rec.pay_hkd_rmb == "RMB":
                    rec.credit_acc = 21001131
                    print("It is pay by RMB, Credit acc is: ", rec.credit_acc)
                else:
                    rec.credit_acc = 21001112
                    print("It is pay by HKD, Credit acc is: ", rec.credit_acc)
    # @api.depends('expense_line_currency')
    # def _compute_credit_acc(self):
    #     for rec in self:
    #         if rec.expense_line_currency:
    #             rec.credit_acc = 21001112

    @api.depends('expense_line_currency')
    def _compute_credit_acc_desc(self):
        for rec in self:
            if rec.expense_line_currency:
                if rec.pay_hkd_rmb == "RMB":
                    rec.credit_acc_desc = "HK Shanghai Bank-RMB Saving"
                    print("--It is pay by RMB, Credit Acc Desc is: ", rec.credit_acc_desc)
                else:
                    rec.credit_acc_desc = "HK & Shanghai Banking - HKD"
                    print("--It is pay by HKD, Credit Acc Desc is: ", rec.credit_acc_desc)
    # @api.depends('expense_line_currency')
    # def _compute_credit_acc_desc(self):
    #     for rec in self:
    #         if rec.expense_line_currency:
    #             rec.credit_acc_desc = "HK & Shanghai Banking - HKD"

    # Check identical expense item record before write to database
    # @api.multi
    # @api.onchange('expense_line_name', 'expense_debit_id', 'expense_line_date', 'expense_line_cost',
    #               'expense_line_currency', 'expense_line_remarks')
    # @api.onchange('expense_line_name', 'expense_line_date', 'expense_line_cost',
    #               'expense_line_currency', 'expense_line_remarks')
    # def _check_identical_expense_item_record(self):
    #     # get data from database
    #     cr = self.env.cr
    #     cr.execute("""SELECT * FROM hhexpense_line """)
    #     records = cr.fetchall()
    #     # get all column names
    #     cr.execute("""
    #     select COLUMN_NAME from information_schema.COLUMNS where table_name = 'hhexpense_line';
    #     """)
    #     columns = cr.fetchall()
    #     three_month_ago = int((datetime.date.today() - datetime.timedelta(3 * 365 / 12)).strftime('%Y%m%d'))
    #     if (self.expense_line_name is not False) and (int(self.expense_line_cost) != int(0.0)) \
    #             and (self.expense_line_date is not False):
    #         for record in records:
    #             print('start compare with ', record[columns.index(('id',))])
    #             user_input = str(record[columns.index(('create_date',))])[:10]
    #             user_input_int = int(''.join(char for char in user_input if char.isalnum()))
    #             if (record[columns.index(('create_uid',))] == self.env.uid) and (
    #                     user_input_int >= three_month_ago):  # if it is the same person's record within 3 months
    #                 if (record[columns.index(('expense_line_name',))] == self.expense_line_name) \
    #                         and (record[columns.index(('expense_debit_id',))] == self.expense_debit_id.id) \
    #                         and (record[columns.index(('expense_line_date',))] == self.expense_line_date) \
    #                         and (record[columns.index(('expense_line_cost',))] == self.expense_line_cost) \
    #                         and (record[columns.index(('expense_line_currency',))] == self.expense_line_currency):
    #                     if (record[columns.index(('expense_line_remarks',))] is None) \
    #                             and (self.expense_line_remarks is False):
    #                         print("All field checked, is the same with", record[columns.index(('id',))])
    #                         raise UserError(_(
    #                             'Your expense item' + self.expense_line_name + ' is already exist. Please check again!'
    #                                                                            '\n If you want to continue submit, please modify your information or add remarks.'))
    #                     else:
    #                         print('remarks are different')
    #                 else:
    #                     print('records are different with', record[columns.index(('id',))])
    #             else:
    #                 print('no need to check')
    #     else:
    #         print('not fill all blanks yet')

    # PDF report test
    #
    # def gathering_data_for_hsbc_pdf_report(self, i, len_of_records):
    #     # Data gathering: employee_name, employee_account, total_amount_for_this_employee
    #     # e.g.
    #     # Data:                                               Report result:
    #     # record 1, A, bank, amount                           | A | 123456789 | total_amount(3*) |
    #     # record 1, B, bank, amount                           | B | 987654321 | total_amount(2*) |
    #     # record 1, A, bank, amount             ==>           | C | 100000001 | total_amount(1*) |
    #     # record 1, B, bank, amount
    #     # record 1, A, bank, amount
    #     # record 1, C, bank, amount
    #
    #     # Use a file to store all selected record's employee name
    #     # If this is the first record (actually checking: replace old file if this is the first time writing data)
    #     if i == 1:
    #         txt = open("./intermediate_hsbc_pdf_get_employee_name.txt", "w", encoding="utf-8")
    #         # If this is a verified & bank record
    #         if self.state == 'verified' and self.pay_bank_cash == 'Bank':
    #             txt.write(str(self.expense_id.employee_name) + '\n')
    #     else:
    #         txt = open("./intermediate_hsbc_pdf_get_employee_name.txt", "a", encoding="utf-8")
    #         if self.state == 'verified' and self.pay_bank_cash == 'Bank':
    #             txt.write(str(self.expense_id.employee_name) + '\n')
    #     # Operation done, close file
    #     txt.close()
    #
    #     # Update sub-record's state, update "expense_line_is_paid" value
    #     # self.expense_line_is_paid = True
    #
    #     # Now, when it goes to the last sub-expense record (i == len_of_sub-record),
    #     if i == len_of_records:
    #         # Get employee name
    #         # Open file and get all employee name (no duplicate)
    #         txt = open('./intermediate_hsbc_pdf_get_employee_name.txt', 'r', encoding='utf-8')
    #         # Use a list to store all different employee name, why not use "set"? not ez to access element
    #         employee_name_list = []
    #         for line in txt:
    #             pure_string = line.strip('\n')
    #             if pure_string not in employee_name_list:
    #                 print("add")
    #                 employee_name_list.append(pure_string)
    #             else:
    #                 print("ignore")
    #         txt.close()
    #         print("Within all selected sub-expense, include following employee's records:", employee_name_list)
    #
    #         # Get total amount for each employee
    #         # Compare to all record in hhexpense_line, if name is the same, add corresponding amount and calculate it.
    #         # First, we need create a dic to store key-value pair (employee_name - total_amount),
    #         # we use employee name from employee_name_list as key since they are unique
    #         # dic_employee_and_own_total_amount = {emp_name:0 for emp_name in employee_name_list}
    #         dic_employee_and_own_total_amount = {}
    #         for each_employee in employee_name_list:
    #             # Then, we need a variable to store calculated amount
    #             print("Start calculate this employee's total amount")
    #             calculate_total_amount_for_this_employee = 0
    #             # For each sub-record in hhexpense_line, check if it is belongs to
    #             # current test-looping-employee (with other 2 conditions). If yes, add its amount
    #             get_all_sub_rec = self.env['hhexpense.line'].search([])
    #             for sub_rec in get_all_sub_rec:
    #                 if sub_rec.expense_id.employee_name == each_employee \
    #                         and sub_rec.state == "verified" \
    #                         and sub_rec.pay_bank_cash == "Bank":
    #                     print("this sub record belongs to this employee, add!")
    #                     calculate_total_amount_for_this_employee = calculate_total_amount_for_this_employee \
    #                                                                + sub_rec.expense_line_calculate
    #             # Current test-looping-employee's calculation done, save into dict as key - pair
    #             dic_employee_and_own_total_amount[each_employee] = calculate_total_amount_for_this_employee
    #         print("Within all selected sub-expense, all different 'employee - total_amount' key-value pair are:",
    #               dic_employee_and_own_total_amount)
    #
    #         # Ok, now we want controller do the rest - get data and generate a PDF report for us
    #         # We are using python way to do the post request
    #         import requests
    #         r = requests.get('http://localhost:8069/web/binary/generate_hsbc_pdf_file_for_selected_expenses',
    #                          data=dic_employee_and_own_total_amount)
    #         # if you want post multiple data, follow below code structure
    #         # data = {
    #         #     'total_amount': dic_employee_and_own_total_amount,
    #         #     'test': 1,
    #         # }
    #         # r = requests.get('http://localhost:8069/web/binary/generate_hsbc_pdf_file_for_selected_expenses',
    #         #                  data=data)
    #
    #         # return {
    #         #     'name': 'Go to website - output HSBC PDF file',
    #         #     'type': 'ir.actions.act_url',
    #         #     'target': 'self',
    #         #     'target_type': 'public',
    #         #     'url': '/web/binary/generate_hsbc_pdf_file_for_selected_expenses',
    #         #     'my_data': dic_employee_and_own_total_amount
    #         # }
    #
    # PDF report test

    # ------------------ Overwrite method ------------------
    @api.multi
    def unlink(self):
        # This function used in "Expense with all of items" action/view
        for expense in self:
            if expense.state not in ['draft', 'rejected']:
                raise UserError(_('Sorry! ' + expense.state + ' record cannot be deleted!'))
        super(HHExpenseLine, self).unlink()

    def verify_expense(self):
        # self.get_to_pay_url()
        # self.send_mail_verify_reviewer_template()
        print('step into verify', self.expense_id.id)
        batch_record = self.env['hhexpense.line'].search([('batch_number', '=', self.batch_number)])
        # reset state of corresponding expense to reviewed and clear all batch number
        for rec in batch_record:
            if rec.expense_id.state != 'verified':
                rec.expense_id.state = 'verified'
            else:
                print('already verified')

