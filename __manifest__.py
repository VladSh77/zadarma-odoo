{
    "name": "Zadarma Integration for Campscout",
    "version": "17.0.1.0.1",
    "category": "Discuss",
    "summary": "Integrate Zadarma telephony with Campscout Odoo",
    "description": """
        Zadarma telephony integration module for Campscout
        - Click-to-call from contacts
        - Call history in chatter
        - Automatic contact creation from calls
        - Call recordings in attachments
        - Webhook support for real-time call updates
    """,
    "author": "Campscout",
    "website": "https://campscout.eu",
    "license": "LGPL-3",
    "depends": ["contacts", "hr", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/zadarma_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
