{
    "name": "Zadarma Odoo Integration",
    "version": "17.0.1.0.0",
    "category": "Discuss",
    "summary": "Integrate Zadarma telephony with Odoo",
    "description": """
        Zadarma telephony integration module
        - Click-to-call from contacts
        - Call history in chatter
        - Automatic contact creation from calls
        - Call recordings in attachments
    """,
    "author": "Your Company",
    "website": "https://yourcompany.com",
    "license": "LGPL-3",
    "depends": ["contacts", "hr", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/zadarma_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
