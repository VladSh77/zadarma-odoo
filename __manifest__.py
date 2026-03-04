{
    'name': 'Zadarma Odoo Integration (Campscout)',
    'version': '17.0.1.2.0',
    'category': 'Sales/CRM',
    'summary': 'Zadarma VoIP Integration: Lead Automation, RODO, and Call Statistics',
    'description': """
        - Automated Lead creation for unknown numbers.
        - RODO/GDPR compliance logging.
        - Smart Business Logic for Partner/Lead linking.
        - SIP Mapping on User level and Security Locks.
    """,
    'author': 'Campscout Dev Team',
    'website': 'https://campscout.eu',
    'depends': [
        'base',
        'mail',
        'crm',
    ],
    'data': [
        'security/zadarma_security.xml',
        'security/ir.model.access.csv',
        'views/zadarma_views.xml',
        'views/res_company_views.xml',
        'views/partner_lead_views.xml',
        'views/res_users_views.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
