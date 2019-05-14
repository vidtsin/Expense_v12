from odoo import api, models


class HHExpenseReportHSBCPDF(models.AbstractModel):
    _name = 'report.hhexpense.print_hsbc_file'

    @api.model
    def get_report_values(self, docids, data=None):
        data = data if data is not None else {}
        print("what is it? data? ", data)
        # expense_user_name = self.env['hhexpense.hhexpense'].browse(data.get('form', {}).get('price_list', False))
        # products = self.env['product.product'].browse(data.get('ids', data.get('active_ids')))
        # quantities = self._get_quantity(data)

        mydocs = "13579"
        testvalues = "a string"
        othervalues = "another string"

        return {
            'doc_ids': docids,
            'doc_model': 'hhexpense.line',
            'docs': mydocs,
            'data': dict(
                data,
                testvalue=testvalues,
                othervalue=othervalues,
                # categories_data=self._get_categories(pricelist, products, quantities)
            ),
        }

    # @api.model
    # def get_report_values(self, docids, data=None):
    #     payslips = self.env['hr.payslip'].browse(docids)
    #     return {
    #         'doc_ids': docids,
    #         'doc_model': 'hr.payslip',
    #         'docs': payslips,
    #         'data': data,
    #         'get_details_by_rule_category': self.get_details_by_rule_category(payslips.mapped('details_by_salary_rule_category').filtered(lambda r: r.appears_on_payslip)),
    #         'get_lines_by_contribution_register': self.get_lines_by_contribution_register(payslips.mapped('line_ids').filtered(lambda r: r.appears_on_payslip)),
    #     }

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        print('>>>>>>>>>>.....', report_obj)
        report = report_obj._get_report_from_name('hhexpense.print_hsbc_file')
        print('>>>>>>>>>>', report)
        thisisdata = self.env.user.name
        print("(report) get user name:", thisisdata)
        # needed_data_array = []
        docargs = {
            # 'doc_ids': docids,
            'doc_ids': self.ids,
            # 'doc_model': self.model,
            'doc_model': report.hhexpense.line,
            'docs': self,
            # 'data': needed_data_array,
            'user_name': thisisdata
        }
        return report_obj.render('hhexpense.print_hsbc_file', docargs)
