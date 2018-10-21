# -*- coding: utf-8 -*-
# Copyright 2018 J3 Solution
#   (http://www.eficent.com)
# © 2016 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Stock Forecast with Source',
    'version': '10.0.1.0.0',
    'license': 'LGPL-3',
    'author': "Mark Robinson, J3 Solution",
    'category': 'Inventory',
    'depends': ['stock', 'sale', 'mrp', 'purchase'],
    'data': [
        'report/report_stock_forecast.xml',
    ],
    'installable': True,
}
