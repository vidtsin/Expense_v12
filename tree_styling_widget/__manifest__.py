# -*- coding: utf-8 -*-
{
    'name': "Dynamic Styling (Tree View)",

    'summary': """
        Apply CSS styling to the cells base on cell value""",

    'description': """
        Apply CSS styling to the cells base on cell value
    """,

    'author': "Hung Hing Off-set Printing Ltd.",
    'website': "http://www.hunghingprinting.com",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
}