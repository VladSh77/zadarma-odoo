# CHANGELOG — zadarma_odoo

Формат: `## [version] — YYYY-MM-DD`

---

## [17.0.1.7.0] — 2026-04-22

### Added

- **Баланси dashboard** (`zadarma.dashboard`) — новий меню-пункт «Баланси» у Zadarma root showing:
  - Zadarma API balance (HMAC-SHA1 signed request)
  - TurboSMS balance (через `kw.sms.provider`)
- Кнопка «Оновити» для refresh
- Access: `base.group_user` (всі authenticated)

### Origin

Цей код був розроблений **2026-04-20 напряму на проді** (AI-помилка, workflow violation). 2026-04-22 rescued з прода → git → origin. Детально у `DevJournal/sessions/LOG.md` `#INCIDENT-AI-2026-04-20`.

### Dependencies

- `kw.sms.provider` (third-party KW Labs TurboSMS module) — для turbosms balance fetching

### Files

- `models/zadarma_dashboard.py` — 109 lines
- `views/zadarma_dashboard_views.xml` — 38 lines
- `models/__init__.py` — +1 import
- `security/ir.model.access.csv` — +1 grant
- `__manifest__.py` — +1 view у data

---

## [17.0.1.6.0] — 2026-04-22

### Змінено (Fayna brand alignment)

- **Manifest:** `name` → `Fayna Zadarma Telephony` (додано префікс Fayna, прибрано «(Campscout)» з name — він у summary);
- **Manifest:** `author` → `Fayna Digital — Volodymyr Shevchenko` (раніше `Fayna`, занадто коротко);
- **Manifest:** `website` → `https://fayna.agency` (fix stale `fayna.company`);
- **Manifest:** version schema `17.0.X.Y.Z` (раніше `1.5.0` без Odoo prefix);
- **Manifest:** додано повний `description` з переліком можливостей;
- `static/description/index.html` — canonical Fayna-style (green #20ac41 badge, wordmark, meta, features cards, flow, requirements);
- README h1 → `Fayna Zadarma Telephony — Odoo 17`.

### Причина

Вирівняння з canonical Fayna module standard (memory `reference_fayna_odoo_module_style.md`). Всі наші модулі мають єдиний brand-формат.

## [ops] — 2026-04-10

- Git sync only: локально, **`origin/main`** і **`/opt/campscout/custom-addons/zadarma_odoo`** узгоджені (**`git pull --ff-only`**); змін коду **немає**.
- Зведений лог: `DevJournal/sessions/LOG.md` (розділ **2026-04-10**).

---

## [1.5.0] — 2026-03-26

- Docs: README повністю переписано — professional header, badges, features, quick setup
- Docs: LGPL-3.0 license файл
- Fix: Click-to-Call — номер клієнта передається з `+` prefix → CallerID routing в Zadarma обирає правильний транк
- Feat: `NOTIFY_RECORD` → MP3 завантажується у Odoo filestore через `ir.attachment`, `recording_url` вказує на постійний internal URL
- Fix: Zadarma API повертає `links[]` (масив), а не `link` (рядок) — виправлено парсинг
- Fix: Chatter нотатки публікуються від імені менеджера (`with_user(user.id)`), не від Public User
- Fix: `_find_partner` ORDER BY — пріоритет контактів з нечисловими іменами
- Fix: Callback API — додано параметр `sip=` для CallerID-by-destination і prefix dialling
- Fix: `_zadarma_get_recording_url` — пошук компанії з `zadarma_api_key`, не `search([])`
- Fix: прибрано надлишкове агресивне логування

## [1.3.0] — 2026-03-26

- Feat: поле `recording_url` у `zadarma.call`
- Feat: відображення посилання на запис у form view

## [1.2.0] — 2026-03-26

- Feat: Click-to-Call через Zadarma Callback API
- Feat: ретроспективний імпорт дзвінків (`zadarma.import`)
- Feat: Rate limit handling (HTTP 429 — 3 спроби з затримками 3/6/9 сек)

## [1.1.0] — 2026-03-26

- Feat: обробка webhook `NOTIFY_END`, `NOTIFY_OUT_END`
- Feat: авто-створення лідів для невідомих номерів
- Feat: Chatter нотатки від імені менеджера
- Feat: пошук менеджера за SIP ID

## [1.0.0] — 2026-03-26

- Feat: початкова версія — модель `zadarma.call`, базові views, security
- Feat: HMAC-SHA1 аутентифікація
- Feat: Smart prefix логіка (визначення напрямку дзвінка за довжиною caller_id)
