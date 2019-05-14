# -*- coding: utf-8 -*-
{
    'name': "E-expense(HH)",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'hr',
                'tree_styling_widget',
                'checkbox_remover',
                'dynamic_action_menu',
                # 'web_one2many_kanban'
                ],

    # always loaded
    'data': [
        'wizard/hhexpense_reject_reason_views.xml',

        'security/hhexpense_security.xml',
        'security/ir.model.access.csv',

        # 'views/attachment1.xml',
        'views/hhexpense_acc_date.xml',
        'views/hhexpense_attachment.xml',
        'views/hhexpense.xml',
        'views/hhexpense_config.xml',
        'views/hhexpense_employee.xml',
        'views/hhexpense_approving_manager.xml',
        'views/hhexpense_china_bank_acc.xml',

        'views/template.xml',

        # 'views/res_config.xml',

        # 'report/print_expense_templates.xml',
        # 'report/print_expense_chinese_templates.xml',
        # 'report/print_expense_line_hsbc.xml',
        # 'report/print_expense_line_hsbc_old_way.xml',
        # 'report/test_learning_report.xml',

        'views/email/email_testing.xml',
        # 'views/email/submitEmailEmployeeDemo.xml',
        'views/email/submitEmailManagerDemo.xml',
        'views/email/approveEmailEmployeeDemo.xml',
        # 'views/email/approveEmailReviewerDemo.xml',
        'views/email/rejectEmailEmployeeDemo.xml',
        'views/email/resubmitEmailManagerDemo.xml',
        # 'views/email/resubmitEmailReviewerDemo.xml',
        'views/email/reviewEmailVerifierDemo.xml',
        # 'views/email/verifyEmailReviewerDemo.xml',
        'views/email/paidEmailGuserDemo.xml',

        # 'views/email/approveEmailManagerDemo.xml',
        # 'views/email/resetEmailEmployeeDemo.xml',
        # 'views/email/rejectEmailManagerDemo.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
}