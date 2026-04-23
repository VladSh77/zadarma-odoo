# Fayna Zadarma Telephony — Architecture

## Призначення

Інтеграція хмарної АТС **Zadarma** з Odoo 17 CRM. Автоматичне логування дзвінків, автозбереження MP3-записів у chatter, click-to-call, SMS через Zadarma API, auto-створення lead з пропущених дзвінків.

## Ключові моделі

### `zadarma.call`

Головна модель — одна запис на дзвінок.

**Ключові поля:**
- `call_id` (Char) — Zadarma-side ID дзвінка
- `direction` (Selection: in / out / internal)
- `caller_num` / `called_num` — PSTN-номери
- `caller_partner_id` / `called_partner_id` (Many2one `res.partner`)
- `lead_id` (Many2one `crm.lead`) — пов'язаний lead (може auto-create)
- `user_id` (Many2one `res.users`) — власник дзвінка за extension
- `started_at` / `ended_at` (Datetime)
- `duration_sec` (Integer)
- `disposition` (Selection: answered / busy / no_answer / failed)
- `recording_url` (Char) — URL MP3 у Zadarma
- `recording_attachment_id` (Many2one `ir.attachment`) — локально збережений MP3
- `raw_webhook_data` (Text) — raw JSON з webhook (для debug)

### `zadarma.import` (TransientModel)

Wizard для bulk-import історичних дзвінків через Zadarma Statistics API. Chunk-based з progress і resume.

### Extensions на існуючі Odoo-моделі

- `res.company` (`res_company.py`) — Zadarma credentials (user_key, secret, webhook secret)
- `res.users` (`res_users.py`) — internal extension per-user
- `res.partner` (`res_partner.py`) — phone-normalized матчинг
- `crm.lead` (`partner_lead_ext.py`) — auto-lead творення з пропущених дзвінків, UTM=phone

## Data flow

### Вхідний дзвінок

```
Client calls +48 XXX XXX XXX
    │
    ▼
Zadarma PBX routes → picks up extension (manager)
    │
    ▼
Zadarma webhook POST /zadarma/webhook (signed)
    │ events: NOTIFY_START, NOTIFY_ANSWER, NOTIFY_END, NOTIFY_RECORD
    │
    ▼
ZadarmaController (controllers/main.py):
    │
    ├── verify signature
    ├── parse event_type
    │
    └── delegate to zadarma.call._handle_webhook_<event>()
         │
         ├── NOTIFY_START: create zadarma.call record (status='ringing')
         │   + identify caller_partner by phone (normalized)
         │   + if unknown → create crm.lead with UTM=phone
         │
         ├── NOTIFY_ANSWER: update status='answered', set user_id by extension
         │
         ├── NOTIFY_END: update ended_at, duration_sec, disposition
         │   + chatter message у partner / lead:
         │     "Вхідний дзвінок XX хв, manager Y"
         │
         └── NOTIFY_RECORD: fetch recording_url з Zadarma API
             + create ir.attachment з MP3 bytes
             + link recording_attachment_id
             + chatter message з player
```

### Вихідний дзвінок (click-to-call)

```
Manager Y клікає «Подзвонити» у картці res.partner
    │
    ▼
Action викликає zadarma.call.make_call(partner_id)
    │
    ▼
ZadarmaAPI.click_to_call(
    extension=manager.zadarma_extension,
    number=partner.phone_normalized
)
    │
    ▼
Zadarma piднімає дзвінок:
    1. Спочатку дзвонить manager extension
    2. Після answer — з'єднує з PSTN number
    │
    ▼
Далі — та сама цепочка webhook (NOTIFY_START, ..., NOTIFY_END, NOTIFY_RECORD)
як вхідний дзвінок, але direction='out'
```

### SMS

`zadarma.sms.message` модель + method `send_sms(phone, body)`. API — `send_sms_api_v1` Zadarma.

## Configuration

`res.company` fields (Settings → Companies → edit):
- `zadarma_user_key` — API key з my.zadarma.com
- `zadarma_user_secret` — API secret
- `zadarma_webhook_secret` — для signature verification

`ir.config_parameter`:
- `zadarma_odoo.auto_create_lead_on_missed` (default True) — чи auto-create lead при missed call з unknown number

## Security

- Webhook endpoint requires signed request (HMAC-SHA1 з webhook_secret)
- Credentials зберігаються у `res.company` — доступні тільки admin-group
- Recording MP3 — `ir.attachment` з ACL як у owner-partner

## Extension points

### Custom post-call hooks

```python
class ZadarmaCallExt(models.Model):
    _inherit = 'zadarma.call'

    def _post_process_call(self):
        super()._post_process_call()
        # My custom logic після NOTIFY_END
        if self.lead_id and self.duration_sec > 300:
            self.lead_id.write({'probability': 40})  # long call = warm lead
```

### Custom recording storage backend

Override `_fetch_recording_bytes(url)` щоб зберігати у S3 замість local ir.attachment.

## Відомі обмеження

- **Rate limit Zadarma API:** ~60 calls/min на інтеграцію. При bulk-import більше — треба chunk 50-60 requests + sleep.
- **Recording availability:** Zadarma тримає записи 3 місяці безкоштовно. Для permanent — attach до ir.attachment (це і робимо).
- **Click-to-call works тільки якщо:** у manager внутрішній extension призначений у Zadarma PBX + manager has `zadarma_extension` поле заповнене у Odoo.

## Планові покращення (roadmap)

- **Винести у adapter pattern:** створити `fayna_telephony_base` + rename цього в `fayna_telephony_zadarma`. Див ADR-003.
- **SIP-ступінь незалежності** через `fayna_telephony_base` — щоб можна було swap на Binotel / Ringostat / Kyivstar без data loss.
- **Call analytics dashboard** — conversion rate, avg duration, missed % per manager.

## Посилання

- Platform ADR-003 — adapter pattern
- Zadarma API docs: https://zadarma.com/support/api/
- Zadarma Webhook: https://my.zadarma.com → Integrations → External systems → Webhooks
