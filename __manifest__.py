{
    "name": "Zadarma Integration for Campscout",
    "version": "17.0.1.0.2",
    "category": "Discuss",
    "summary": "Integrate Zadarma telephony with Campscout Odoo",
    "author": "Campscout",
    "website": "https://campscout.eu",
    "license": "LGPL-3",
    "depends": ["contacts", "hr", "mail"],
    "data": [
        "security/zadarma_security.xml",
        "security/ir.model.access.csv",
        "views/zadarma_views.xml",
        "views/res_company_views.xml",
        "views/res_partner_views.xml",
        "views/res_users_views.xml",
    ],
    "static": [
        "static/description/icon.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
