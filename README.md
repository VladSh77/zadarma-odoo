# Odoo 17 Zadarma Telephony — Auto-Log, Recording, Click-to-Call, SMS

![Odoo Version](https://img.shields.io/badge/Odoo-17.0%20Community-purple)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Zadarma](https://img.shields.io/badge/Zadarma-API%20v1-red)
![License](https://img.shields.io/badge/License-LGPL--3-green.svg)
![Status](https://img.shields.io/badge/Status-Production-brightgreen)

**Developed by [Fayna Digital](https://www.fayna.agency) for CampScout**
**Author: Volodymyr Shevchenko**

---

Cloud PBX **Zadarma** integration for Odoo 17 CRM. Every inbound and outbound call is auto-logged, linked to `res.partner` and `crm.lead`, with full MP3 recording attached to chatter. Supports click-to-call from partner card, SMS through Zadarma API, and auto-lead creation on missed calls from unknown numbers.

Reference deployment: [CampScout](https://campscout.eu).

---

## Features

- **Auto-log calls** — Zadarma webhook → `zadarma.call` records (`NOTIFY_START`, `NOTIFY_ANSWER`, `NOTIFY_END`, `NOTIFY_RECORD`)
- **Call recording** — MP3 auto-downloaded, attached to chatter of partner/lead
- **Click-to-call** — button on `res.partner` form → Zadarma API initiates call on manager's extension
- **Auto-lead** — unknown caller → new `crm.lead` with UTM=phone, assigned to manager by extension
- **SMS through Zadarma** — `zadarma.sms.message` model + bulk send wizard
- **Manager detection** — extension → `res.users` mapping, auto-attribution
- **Bulk historical import** — Zadarma Statistics API chunk-based import with progress and resume
- **SMS analytics** — delivery rate, status breakdown per partner
- **Call disposition tracking** — answered / busy / no_answer / failed

---

## Architecture

```
zadarma-odoo/
├── models/
│   ├── zadarma_call.py                # Main call model (one record per call)
│   ├── zadarma_import.py              # TransientModel wizard for bulk historical import
│   ├── res_company.py                 # Company fields: Zadarma credentials
│   ├── res_users.py                   # User extension mapping
│   ├── res_partner.py                 # Phone-normalized matching
│   └── partner_lead_ext.py            # Auto-lead creation from missed calls
├── controllers/
│   └── main.py                        # /zadarma/webhook endpoint
├── views/
│   ├── zadarma_views.xml              # Call tree/form, action button
│   ├── sms_stats_views.xml            # SMS analytics
│   ├── res_company_views.xml          # Credentials config
│   ├── res_users_views.xml            # Extension mapping
│   ├── partner_lead_views.xml         # Partner + lead extensions
│   └── zadarma_import_views.xml       # Import wizard
├── security/
│   ├── zadarma_security.xml
│   └── ir.model.access.csv
├── static/description/
└── docs/
    ├── ARCHITECTURE.md
    ├── DEPLOYMENT.md
    └── RUNBOOK.md
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| ERP Framework | Odoo 17.0 Community |
| Core deps | `base`, `crm`, `mail`, `sms` |
| PBX | Zadarma cloud (SIP + webhooks) |
| API version | Zadarma API v1 |
| Signature | HMAC-SHA1 |
| Recording format | MP3 (stored as `ir.attachment` permanent) |
| Auto-attribution | Extension → `res.users.zadarma_extension` |
| Module version | 17.0.1.6.0 |
| License | LGPL-3 |

---

## Installation

### 1. Clone into custom-addons

```bash
cd /opt/<client>/custom-addons
git clone https://github.com/VladSh77/zadarma-odoo.git zadarma_odoo
```

### 2. Install module

```bash
docker exec <client>_web odoo -c /etc/odoo/odoo.conf -d <db> \
    -i zadarma_odoo --stop-after-init --no-http
```

Or UI: **Apps → Update Apps List → search `Zadarma` → Install**.

### 3. Restart Odoo

```bash
docker restart <client>_web
```

---

## Configuration

### Step 1 — Generate Zadarma API credentials

1. Log in to [my.zadarma.com](https://my.zadarma.com) → **Settings → API**
2. Generate **API Key** and **API Secret**
3. Copy both

### Step 2 — Configure in Odoo

**Settings → Users & Companies → Companies → [active company] → tab «Zadarma»**:

| Field | Value |
|-------|-------|
| Zadarma User Key | paste API Key |
| Zadarma User Secret | paste API Secret |
| Zadarma Webhook Secret | generated random string (e.g. `openssl rand -hex 32`) |

### Step 3 — Assign extensions to users

For each manager:

1. **Settings → Users → [user] → tab «Zadarma»**
2. **Zadarma Extension** = internal number (e.g. `100`, `101`)
3. Must match extension configured in Zadarma PBX for that manager

### Step 4 — Register webhook in Zadarma

[my.zadarma.com](https://my.zadarma.com) → **Integrations → CRM / External systems → Webhooks**:

- URL: `https://<your-odoo>.com/zadarma/webhook`
- Events: enable `NOTIFY_START`, `NOTIFY_ANSWER`, `NOTIFY_END`, `NOTIFY_RECORD`
- Secret: paste same webhook secret from Odoo config

---

## Usage

### Inbound call

1. Customer calls your Zadarma number
2. Zadarma PBX routes → picks manager extension
3. Webhook `/zadarma/webhook` receives sequence of events:
   - `NOTIFY_START` → `zadarma.call` created, partner identified or lead auto-created
   - `NOTIFY_ANSWER` → manager attributed by extension
   - `NOTIFY_END` → duration, disposition recorded
   - `NOTIFY_RECORD` → MP3 fetched, attached to chatter
4. Chatter message appears on partner/lead with call details + audio player

### Click-to-call

1. Open partner (`res.partner`) form
2. Click **Call** button (phone icon next to number)
3. Zadarma API initiates call:
   - Rings manager's extension first
   - On answer → connects to partner's PSTN
4. Standard webhook chain follows (just with `direction='out'`)

### SMS

```python
# From Odoo shell or flow code
env['zadarma.sms.message'].create({
    'partner_id': partner.id,
    'phone': partner.phone,
    'body': 'Your appointment confirmed for tomorrow 14:00',
}).send()
```

### Bulk historical import

**Menu → Zadarma → Import Calls**:

1. Set date range (from / to)
2. Click **Run** — uses Zadarma Statistics API, chunk size 50
3. Progress bar updates; can pause/resume
4. 10-30 minutes for thousands of calls

---

## Webhook Flow (technical)

```
1. Customer dials +48 XXX XXX XXX (your Zadarma number)
2. Zadarma PBX routes call
3. POST https://<odoo>/zadarma/webhook (with HMAC-SHA1 signature)
4. Controller verify_signature() → reject if bad
5. Dispatch by event_type:
   ├── NOTIFY_START:
   │   ├── Create zadarma.call (status='ringing')
   │   ├── Normalize phone → search res.partner
   │   ├── If no partner:
   │   │   └── Create crm.lead (UTM=phone, assigned by extension)
   │
   ├── NOTIFY_ANSWER:
   │   └── Update call (status='answered', user_id from extension)
   │
   ├── NOTIFY_END:
   │   ├── Update call (ended_at, duration_sec, disposition)
   │   └── Post chatter message on partner / lead
   │
   └── NOTIFY_RECORD:
       ├── Fetch recording_url from Zadarma API
       ├── Download MP3 bytes
       ├── Create ir.attachment (public=False, permanent)
       └── Link to call.recording_attachment_id
       └── Post chatter: "Recording available"
6. Return 200 OK
```

---

## Click-to-Call Flow (technical)

```
1. User clicks Call button on res.partner form
2. Frontend action → zadarma.call.make_call(partner_id)
3. Backend:
   a. Resolve caller: env.user.zadarma_extension
   b. Resolve callee: partner.phone (normalized E.164)
   c. Call ZadarmaAPI.click_to_call(sip_from, sip_to)
4. Zadarma API:
   a. Initiates call to manager's SIP extension
   b. On manager pickup → connects to callee PSTN
5. Normal inbound webhook chain follows (direction='out')
```

---

## Local Development

```bash
git clone https://github.com/VladSh77/zadarma-odoo.git
cd zadarma-odoo

# Ephemeral Odoo with module mounted:
docker run -d --name test_odoo -v $(pwd)/..:/mnt/custom-addons \
    -p 8069:8069 odoo:17

# Simulate webhook:
curl -X POST http://localhost:8069/zadarma/webhook \
    -d 'event=NOTIFY_START&call_start=2026-01-01+12:00:00&caller_id=+48123456789&called_did=+48987654321'
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| Webhook not arriving | Public URL unreachable from Zadarma | `curl -vI https://<odoo>.com/zadarma/webhook` externally; check SSL / firewall |
| Signature verification fails | Webhook secret mismatch | Re-sync secret between Odoo config and Zadarma webhook settings (exact match, no whitespace) |
| Recording not attached | NOTIFY_RECORD not enabled OR tariff doesn't include recording | my.zadarma.com → Webhooks → enable NOTIFY_RECORD; check tariff |
| Recording download fails | Zadarma `allowed_ips` filter blocks VPS | Add your Odoo VPS IP to API whitelist in my.zadarma.com |
| Click-to-call does nothing | Manager missing extension / not set up in PBX | Settings → Users → manager → set `Zadarma Extension`; verify in PBX |
| SMS fail delivery | Phone format wrong (need E.164 `+XX...`) | Normalize via `zadarma.call._normalize_phone(phone)` |
| Too many 429 errors on bulk import | Zadarma API rate limit (~60 req/min) | Wizard already chunks at 50; if still hitting limit, increase sleep interval in `zadarma_import.py` |

---

## CRM Access

Standard Odoo CRM permissions — no module-specific group required. Users with `sales_team.group_sale_salesman` or higher:

- See call records linked to their partners / leads
- Initiate click-to-call
- Read SMS history

**Manager** (`sales_team.group_sale_manager`):

- View all calls regardless of assignment
- Bulk import historical calls
- Reassign calls to different users

**Settings admin**:

- Configure Zadarma credentials
- Map extensions to users
- Enable/disable webhook integration

---

## Roadmap — Adapter Pattern Migration

This module will be **refactored under adapter pattern** (see [ADR-003](https://github.com/VladSh77/fayna-digital-docs/blob/main/adr/ADR-003-adapter-pattern.md)):

```
Future state:
  fayna_telephony_base (abstract: call model, provider contract)
    ├── fayna_telephony_zadarma  (this module, rename)
    ├── fayna_telephony_binotel  (future)
    ├── fayna_telephony_ringostat (future)
    └── fayna_telephony_kyivstar (future)
```

Trigger for refactor: when a client requests different provider. Non-blocking currently.

---

## Module Ecosystem

| Related module | Role |
|----------------|------|
| [fayna-sendpulse-odoo](https://github.com/VladSh77/fayna-sendpulse-odoo) | Messenger sibling (both land in Odoo CRM) |
| [omnichannel-bridge](https://github.com/VladSh77/omnichannel-bridge) | Omnichannel aggregator (voice is a separate channel for now, not bridged) |
| [fayna-rodo-compliance](https://github.com/VladSh77/fayna-rodo-compliance) | Consent logging (future: record voice call consent per PL PKE) |
| [campscout-management](https://github.com/VladSh77/campscout-management) | Uses this for CampScout inbound sales calls |

Architecture docs: [fayna-digital-docs](https://github.com/VladSh77/fayna-digital-docs) (private).

---

## License

LGPL-3 — see [LICENSE](LICENSE)

---

*Developed by [Fayna Digital](https://www.fayna.agency) · Volodymyr Shevchenko*
