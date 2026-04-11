# CHANGELOG — zadarma_odoo

Формат: `## [version] — YYYY-MM-DD`

---

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
