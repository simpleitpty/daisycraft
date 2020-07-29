# -*- coding: utf-8 -*-

{
    'name': 'Pagadito Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Pagadito Implementation',
    'version': '1.0',
    'description': """Transbank Payment Acquirer""",
    'author': 'Intelitecsa (Francisco Trejo, Nestor Ulloa)',
    'website': 'http://www.delfos-cloud.com',
    "images": ['static/description/banner.png',
               'static/description/icon.png',
               'static/description/thumbnail.png'],
    'price': 400.00,
    'currency': 'USD',
    'license': 'GPL-3',
    'depends': ['payment', 'base', 'sale', 'account'],
    'data': [
        #'security/ir.model.access.csv',
        'views/payment_pagadito_templates.xml',
        'views/payment_views.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
}
