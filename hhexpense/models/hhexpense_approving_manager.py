# -*- coding: utf-8 -*-
from odoo.api import Environment
from odoo import models, fields, api, _, registry
from odoo.exceptions import UserError
import datetime
import threading
import psycopg2
from functools import partial


class HHExpenseApprovingManager(models.Model):
    _name = 'hhexpense.approving.manager'

    employee_name = fields.Char(string='Employee Name')
    employee_email = fields.Char(string='Email')
    approving_manager_name = fields.Char(string='Approving Manager')
    approving_manager_email = fields.Char(string='Approving Email')

    def update_approving_manager_list(self):
        connect_employee_db = psycopg2.connect(host="172.17.10.198", database="HungHingEmployee", user="odooNew",
                                               password="odoo")
        employee_db_cur = connect_employee_db.cursor()
        employee_db_cur.execute(
            """SELECT name, email, approving_manager_name, approving_manager_email, department FROM hunghing_employee_info """)
        approving_manager = employee_db_cur.fetchall()

        odoo_cr = self.env.cr
        odoo_cr.execute("""delete from hhexpense_approving_manager""")

        for employee in approving_manager:
            # print(employee)
            if employee[2] is not None and employee[4].upper() != 'ACCOUNTING':
                vals = {'employee_name': employee[0], 'employee_email': employee[1],
                        'approving_manager_name': employee[2], 'approving_manager_email': employee[3]}
                self.create(vals)
                # print('record for ', employee[0], ' has been updated')
        print('>>>record for managers has been updated')


class HHExpenseReviewingAccountant(models.Model):
    _name = 'hhexpense.reviewing.accountant'

    manager_name = fields.Char(string='Manager Name')
    manager_email = fields.Char(string='Manager Email')
    reviewing_accountant_name = fields.Char(string='Reviewing Accountant')
    reviewing_accountant_email = fields.Char(string='Reviewing Email')

    def update_reviewing_accountant_list(self):
        # default review_accountant
        review_accountant = ['Shirley', 'shirley.pun@hunghingprinting.com']

        # get all manager
        connect_employee_db = psycopg2.connect(host="172.17.10.198", database="HungHingEmployee", user="odooNew",
                                               password="odoo")
        employee_db_cur = connect_employee_db.cursor()
        employee_db_cur.execute(
            """SELECT distinct department, approving_manager_name, approving_manager_email FROM hunghing_employee_info """)
        approving_manager = employee_db_cur.fetchall()

        # clear all records and recreate
        odoo_cr = self.env.cr
        odoo_cr.execute("""delete from hhexpense_reviewing_accountant""")
        # print('all records have been cleared')

        for manager in approving_manager:
            # print(manager)
            if manager[0].upper() != 'ACCOUNTING' and manager[1] is not None:
                vals = {'manager_name': manager[1], 'manager_email': manager[2],
                        'reviewing_accountant_name': review_accountant[0],
                        'reviewing_accountant_email': review_accountant[1]}
                self.create(vals)
        print('>>>record for managers has been updated')


class HHExpenseVerifyingAccountant(models.Model):
    _name = 'hhexpense.verifying.accountant'

    reviewer_name = fields.Char(string='Reviewer Name')
    reviewer_email = fields.Char(string='Reviewer Email')
    verifying_accountant_name = fields.Char(string='Verifying Accountant')
    verifying_accountant_email = fields.Char(string='Verifying Email')

    def update_verifying_accountant_list(self):
        # default review_accountant
        review_accountant = ['Shirley', 'shirley.pun@hunghingprinting.com']
        # default verifying_accountant
        verifying_accountant = ['Kenneth', 'kenneth.chan@hunghingprinting.com']

        # clear all records and recreate
        odoo_cr = self.env.cr
        odoo_cr.execute("""delete from hhexpense_verifying_accountant""")

        vals = {'reviewer_name': review_accountant[0], 'reviewer_email': review_accountant[1],
                'verifying_accountant_name': verifying_accountant[0],
                'verifying_accountant_email': verifying_accountant[1]}
        self.create(vals)
        print('>>>record for verifier has been updated')
