# -*- coding: utf-8 -*-
import re
# import cx_Oracle
from odoo import models, fields, api
from odoo.osv import expression


class HHExpenseDebitCategory(models.Model):
    _name = 'hhexpense.debit.category'
    
    # expense_line_debit = fields.One2many('hhexpense.line', inverse_name='expense_debit_id')

    ledger_code = fields.Char(required=True, help="All should be B02. (no need change)")
    expense_type = fields.Char(required=True, help="AKA: Which department you are in? (must be unique)")
    expense_category = fields.Char(required=True, help="For different type of the expense, it has own category list. "
                                                       "(can be same)")
    debit_acc = fields.Char(string="Dr Acc", required=True, help="Debit Account, decided by 'expense_type' and 'expense_category'."
                                                "(must be unique)")
    check_user_in_acc_group = fields.Boolean(compute="_check_user_in_acc_group",
                                             help="check user group, if not Acc, 'expense_category' becomes readonly")

    # -------------------------------------------- Define methods here -------------------------------------------------
    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "%s" % rec.expense_category))
        return res

    # Show all information
    # @api.multi
    # def name_get(self):
    #     res = []
    #     for rec in self:
    #         res.append((rec.id, "%s-%s,Debit Acc:%s" % (rec.expense_type, rec.expense_category, rec.debit_acc)))
    #     return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """ name_search(name='', args=None, operator='ilike', limit=100) -> records

        Search for records that have a display name matching the given
        ``name`` pattern when compared with the given ``operator``, while also
        matching the optional search domain (``args``).

        This is used for example to provide suggestions based on a partial
        value for a relational field. Sometimes be seen as the inverse
        function of :meth:`~.name_get`, but it is not guaranteed to be.

        This method is equivalent to calling :meth:`~.search` with a search
        domain based on ``display_name`` and then :meth:`~.name_get` on the
        result of the search.

        :param str name: the name pattern to match
        :param list args: optional search domain (see :meth:`~.search` for
                          syntax), specifying further restrictions
        :param str operator: domain operator for matching ``name``, such as
                             ``'like'`` or ``'='``.
        :param int limit: optional max number of records to return
        :rtype: list
        :return: list of pairs ``(id, text_repr)`` for all matching records.
        """
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            category = self.env['hhexpense.debit.category']
            if operator in positive_operators:
                category = self.search([('expense_category', '=', name)] + args, limit=limit)
                print("did you running this one? so what is category now? ", category)
            if not category and operator not in expression.NEGATIVE_TERM_OPERATORS:
                category = self.search(args + [('expense_category', operator, name)], limit=limit)
                print("this is operator: ", operator)
                print("you are running this one, what about now? category is....? ", category)
                print("OK, fine, give me your args value now. ", args)
            elif not category and operator in expression.NEGATIVE_TERM_OPERATORS:
                category = self.search(args + [('expense_category', operator, name)], limit=limit)
                print("you are running that one")
            if not category and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                print("oops")
                if res:
                    category = self.search([('expense_category', '=', res.group(2))] + args, limit=limit)
                    print("You are not supposed to see this message")
        else:
            category = self.search(args, limit=limit)
            print("Didn't detect any input/change yet")
        return category.name_get()

    @api.multi
    def _check_user_in_acc_group(self):
        if self.env.user.has_group('hhexpense.group_hhexpense_reviewers') or self.env.user.has_group('hhexpense.group_hhexpense_verifiers'):
            # print("user name: ", self.env['hhexpense.hhexpense'].uid)
            print("--user name: ", self.env.user.name)
            print("--user name: ", self.env.uid)
            print("yes! This is a Reviewer")
            self.check_user_in_acc_group = True
        else:
            print("Nope! This is not a Reviewer")
            self.check_user_in_acc_group = False


# class HHExpenseCreditAcc(models.Model):
#     _name = 'hhexpense.credit.acc'
#
#     expense_line_credit = fields.One2many('hhexpense.line', inverse_name='expense_credit_id')
#
#     credit_acc = fields.Char(string="Cr Acc", required=True)
#     credit_desc = fields.Char(string="Cr Acc Desc", required=True)
#     check_user_in_acc_group = fields.Boolean(compute="_check_user_in_acc_group",
#                                              help="check user group, if not Acc, 'expense_category' becomes readonly")


class HHExpenseConvertDepartmentToExpenseType(models.Model):
    _name = 'hhexpense.convert.deptoexp'
    
    user_department = fields.Char()
    convert_to_expense_type = fields.Char()
    check_user_in_acc_group_deptoexp = fields.Boolean(compute="_check_user_in_acc_group_deptoexp",
                                                      help="check user group, if not Acc, 'user_department' becomes readonly")

    # expense_id = fields.One2many('hhexpense.hhexpense', inverse_name='expense_deptoexp_id')

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "%s" % rec.user_department))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """ name_search(name='', args=None, operator='ilike', limit=100) -> records

        Search for records that have a display name matching the given
        ``name`` pattern when compared with the given ``operator``, while also
        matching the optional search domain (``args``).

        This is used for example to provide suggestions based on a partial
        value for a relational field. Sometimes be seen as the inverse
        function of :meth:`~.name_get`, but it is not guaranteed to be.

        This method is equivalent to calling :meth:`~.search` with a search
        domain based on ``display_name`` and then :meth:`~.name_get` on the
        result of the search.

        :param str name: the name pattern to match
        :param list args: optional search domain (see :meth:`~.search` for
                          syntax), specifying further restrictions
        :param str operator: domain operator for matching ``name``, such as
                             ``'like'`` or ``'='``.
        :param int limit: optional max number of records to return
        :rtype: list
        :return: list of pairs ``(id, text_repr)`` for all matching records.
        """
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            department = self.env['hhexpense.convert.deptoexp']
            if operator in positive_operators:
                department = self.search([('user_department', '=', name)] + args, limit=limit)
                print("did you running this one? so what is category now? ", department)
            if not department and operator not in expression.NEGATIVE_TERM_OPERATORS:
                department = self.search(args + [('user_department', operator, name)], limit=limit)
                print("this is operator: ", operator)
                print("you are running this one, what about now? category is....? ", department)
                print("OK, fine, give me your args value now. ", args)
            elif not department and operator in expression.NEGATIVE_TERM_OPERATORS:
                department = self.search(args + [('user_department', operator, name)], limit=limit)
                print("you are running that one")
            if not department and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                print("oops")
                if res:
                    department = self.search([('user_department', '=', res.group(2))] + args, limit=limit)
                    print("You are not supposed to see this message")
        else:
            department = self.search(args, limit=limit)
            print("Didn't detect any input/change yet")
        return department.name_get()

    @api.multi
    def _check_user_in_acc_group_deptoexp(self):
        if self.env.user.has_group('hhexpense.group_hhexpense_reviewers') or self.env.user.has_group(
                'hhexpense.group_hhexpense_verifiers'):
            # print("user name: ", self.env['hhexpense.hhexpense'].uid)
            print("^^user name: ", self.env.user.name)
            print("^^user name: ", self.env.uid)
            print("(deptoexp)yes! This is a Reviewer")
            self.check_user_in_acc_group_deptoexp = True
            print(self.check_user_in_acc_group_deptoexp)
        else:
            print("(deptoexp)Nope! This is not a Reviewer")
            self.check_user_in_acc_group_deptoexp = False
            print(self.check_user_in_acc_group_deptoexp)
    

class HHExpenseGetCurrencyExchangeRate(models.Model):
    _name = 'hhexpense.currency.rate'
    
    _rec_name = 'currency'

    currency = fields.Char(string='Currency')
    exchange_rate = fields.Float(string='HH exchange rate', digits=(12, 6))
    rate_month = fields.Char()
    check_user_in_acc_group_currency_rate = fields.Boolean(compute="_check_user_in_acc_group_currency_rate",
                                                           help="check user group, if not Acc,"
                                                                "'currency' becomes readonly")

    @api.multi
    def update_currency_rate(self):
        print('currency updated')
        # # Using "sys_curr_exch" table's data in "HHERP - Oracle" database
        # # Connect to database
        # connect_erp = cx_Oracle.connect('HHERP/MIS5072@172.17.0.21:1521/orcl')
        # print("'HHERP - Oracle' database is connected, version number: ", connect_erp.version)
        # # Opens a cursor/pointer for statements to use.
        # cursor_erp = connect_erp.cursor()
        # # Find out year_month value, we need it as one of the three filter condition in later SQL query
        # list_store_erp_acc_mth = []
        # cursor_erp.execute("""select DISTINCT acc_mth from sys_curr_exch""")
        # for acc_month in cursor_erp:
        #     # print(acc_month)
        #     list_store_erp_acc_mth.append(acc_month[0])
        # print("list_store_erp_acc_mth has: ", list_store_erp_acc_mth)
        # list_store_erp_acc_mth.sort()
        # year_month = list_store_erp_acc_mth[len(list_store_erp_acc_mth) - 1]
        # print("year_month is: ", year_month)
        # # (year=int(year_month[0:3]), month=int(year_month[4:5]))
        # # convert_y_m_to_datetime = datetime.strptime(str(year_month), '%Y%m').strftime('%Y%m')
        #
        # # For each record (currency - exchange_rate), compare 3 filters
        # # then get the corresponding HHERP exchange rate
        # for rec in self:
        #     # Get current record's currency, we will use it as a filter in later SQL query
        #     setted_currency = str(rec.currency).upper()
        #     # Now, we need SQL query to obtain "HH exchange rate". Query has 3 conditions, it works as primary key
        #     # After below code executed, the result would be sth like this:
        #     # ('HH', 'RMB', 201806, 1.2255, None, 'WING', datetime.datetime(2018, 6, 6, 13, 47, 31), None, None)
        #     cursor_erp.execute(
        #         """
        #         select * from sys_curr_exch
        #         where co_code = :company_code and curr_code = :currency_code and acc_mth = :account_month
        #         """,
        #         {
        #             'company_code': 'HH',
        #             'currency_code': setted_currency,
        #             'account_month': year_month
        #         }
        #     )
        #     # Use for loop to access data inside the cursor and start calculate the total amount(in HKD)
        #     for row in cursor_erp:
        #         # type(row) is "tuple", so we can use row[index] to get the value you want
        #         # and now we can calculate current sub-record's amount in HKD
        #         print("haha! For this currency in Odoo      : ", setted_currency)
        #         print("@ @ @currency in ERP database is     : ", row[1])
        #         print("@ @ @exchange rate in ERP database is: ", row[3])
        #         rec.exchange_rate = row[3]
        #         rec.rate_month = year_month
        # # Operation done, close the connection with database
        # connect_erp.close()

    @api.multi
    def _check_user_in_acc_group_currency_rate(self):
        if self.env.user.has_group('hhexpense.group_hhexpense_reviewers') or self.env.user.has_group(
                'hhexpense.group_hhexpense_verifiers'):
            # print("user name: ", self.env['hhexpense.hhexpense'].uid)
            print("**user name: ", self.env.user.name)
            print("**user name: ", self.env.uid)
            print("(currency_rate)yes! This is a Reviewer")
            self.check_user_in_acc_group_deptoexp = True
            print(self.check_user_in_acc_group_deptoexp)
        else:
            print("(currency_rate)Nope! This is not a Reviewer")
            self.check_user_in_acc_group_deptoexp = False
            print(self.check_user_in_acc_group_deptoexp)


class HHExpenseHolidayDate(models.Model):
    _name = 'hhexpense.holiday.date'

    holiday_date = fields.Date()
    holiday_description = fields.Char()


class HHExpenseExpenseCategory(models.Model):
    _name = 'hhexpense.expense.category'

    category = fields.Char()
    acc_no = fields.Char()
    check_user_in_acc_group = fields.Boolean(compute="_check_user_in_acc_group",
                                             help="check user group, if not Acc, 'expense_category' becomes readonly")


    expense_line_id = fields.One2many('hhexpense.line', inverse_name='expense_cate_id')

    # -------------------------------------------- Define methods here -------------------------------------------------
    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "%s" % rec.category))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """ name_search(name='', args=None, operator='ilike', limit=100) -> records

        Search for records that have a display name matching the given
        ``name`` pattern when compared with the given ``operator``, while also
        matching the optional search domain (``args``).

        This is used for example to provide suggestions based on a partial
        value for a relational field. Sometimes be seen as the inverse
        function of :meth:`~.name_get`, but it is not guaranteed to be.

        This method is equivalent to calling :meth:`~.search` with a search
        domain based on ``display_name`` and then :meth:`~.name_get` on the
        result of the search.

        :param str name: the name pattern to match
        :param list args: optional search domain (see :meth:`~.search` for
                          syntax), specifying further restrictions
        :param str operator: domain operator for matching ``name``, such as
                             ``'like'`` or ``'='``.
        :param int limit: optional max number of records to return
        :rtype: list
        :return: list of pairs ``(id, text_repr)`` for all matching records.
        """
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            categories = self.env['hhexpense.expense.category']
            if operator in positive_operators:
                categories = self.search([('category', '=', name)] + args, limit=limit)
                print("did you running this one? so what is category now? ", categories)
            if not categories and operator not in expression.NEGATIVE_TERM_OPERATORS:
                categories = self.search(args + [('category', operator, name)], limit=limit)
                print("this is operator: ", operator)
                print("you are running this one, what about now? category is....? ", categories)
                print("OK, fine, give me your args value now. ", args)
            elif not categories and operator in expression.NEGATIVE_TERM_OPERATORS:
                categories = self.search(args + [('category', operator, name)], limit=limit)
                print("you are running that one")
            if not categories and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                print("oops")
                if res:
                    categories = self.search([('category', '=', res.group(2))] + args, limit=limit)
                    print("You are not supposed to see this message")
        else:
            categories = self.search(args, limit=limit)
            print("Didn't detect any input/change yet")
        return categories.name_get()

    @api.multi
    def _check_user_in_acc_group(self):
        if self.env.user.has_group('hhexpense.group_hhexpense_reviewers') or self.env.user.has_group('hhexpense.group_hhexpense_verifiers'):
            # print("user name: ", self.env['hhexpense.hhexpense'].uid)
            print("$$user name: ", self.env.user.name)
            print("$$user name: ", self.env.uid)
            print("yes! This is a Reviewer")
            self.check_user_in_acc_group = True
        else:
            print("Nope! This is not a Reviewer")
            self.check_user_in_acc_group = False


class HHExpenseTeam(models.Model):
    _name = "hhexpense.team"
    _description = "HungHing Team"

    employee_name = fields.Char('Employee Name')
    team = fields.Char('Team')
    analysis_code = fields.Char('Analysis Code')

    # @api.depends('name')
    # def _compute_analysis_code(self):
    #     mapping_analysis_code = {
    #         'USA': 90001,
    #         'USB': 90002,
    #         'European': 901,
    #         'LUX': 902,
    #         'CBA': 90301,
    #         'CBB': 90302,
    #         'Sales': 904,
    #         'Rengo': 905,
    #         'GCS': 906,
    #         'Beluga': 907}
    #     for rec in self:
    #         if rec.name:
    #             self.analysis_code = mapping_analysis_code[self.name]