# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, registry
import psycopg2


class HHExpenseChinaBankAcc(models.Model):
    _inherit = 'hr.employee'

    # employee_name = fields.Char(string='Employee Name')
    # employee_email = fields.Char(string='Email')
    # china_bank_acc = fields.Char(string='China Bank Account')
    rmb_account_no = fields.Char(string='RMB Bank Account')

    # def update_china_bank_acc_list(self):
    #     connect_employee_db = psycopg2.connect(host="172.17.10.198", database="HungHingEmployee", user="odooNew",
    #                                            password="odoo")
    #     employee_db_cur = connect_employee_db.cursor()
    #     employee_db_cur.execute(
    #         """SELECT name, email, china_bank_acc FROM hunghing_employee_info """)
    #     china_bank_acc = employee_db_cur.fetchall()
    #
    #     odoo_cr = self.env.cr
    #     odoo_cr.execute("""delete from hhexpense_china_bank_acc""")
    #
    #     for acc in china_bank_acc:
    #         print(acc)
    #         if acc[2] is not None:
    #             vals = {'employee_name': acc[0], 'employee_email': acc[1],
    #                     'china_bank_acc': acc[2]}
    #             self.create(vals)
    #             # print('record for ', employee[0], ' has been updated')
    #     print('>>>record for china bank account has been updated')