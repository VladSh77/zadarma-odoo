{
    'name': 'Zadarma Odoo Integration',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Інтеграція з телефонією Zadarma: вихідні дзвінки та статистика',
    'author': 'Campscout',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        'views/zadarma_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
