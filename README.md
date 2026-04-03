# Zadarma VoIP Integration for Odoo 17

![Odoo Version](https://img.shields.io/badge/Odoo-17.0%20Community-purple)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-LGPL%203.0-blue.svg)
![Status](https://img.shields.io/badge/Status-Production-brightgreen)
![Version](https://img.shields.io/badge/Version-1.5.0-informational)

**Developed by [Fayna Digital](https://fayna.agency) for [CampScout](https://campscout.eu)**  
**Author: Volodymyr Shevchenko**

---

Custom Odoo 17 module that integrates **Zadarma cloud PBX** with Odoo CRM.  
All inbound and outbound calls are automatically logged, linked to partners and leads, and call recordings are stored permanently in the Odoo filestore.

## Features

- Automatic logging of inbound/outbound calls via Zadarma Webhook
- Call-to-partner linking (`res.partner`) and lead linking (`crm.lead`)
- Auto-creation of a lead for unknown callers
- Chatter notes posted on behalf of the responsible manager (by SIP ID)
- **Click-to-Call** via Zadarma Callback API with CallerID routing (`+380` UA / `+48` PL)
- Call recordings downloaded to Odoo filestore (permanent storage, not temporary Zadarma URL)
- Retrospective import of calls for any date range (with HTTP 429 rate-limit handling)
- Deduplication by `call_id` (handles Callback API leg1/leg2 split)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| ERP Framework | Odoo 17.0 Community |
| VoIP System | Zadarma Cloud PBX (Webhook + Callback API) |
| Call Records | `ir.attachment` → Odoo Filestore |
| Auth Scheme | HMAC-SHA1 (API key + secret) |
| Language | Python 3.10+ |
| License | LGPL-3.0 |

---

## Quick Setup

1. **Zadarma API credentials** → `Settings → Company → Zadarma tab`
2. **SIP ID per manager** → `Settings → Users → [user] → Zadarma SIP ID`
3. **Webhook URL in Zadarma cabinet** → `https://your-domain/zadarma/webhook`  
   Events: `NOTIFY_END`, `NOTIFY_OUT_END`, `NOTIFY_RECORD`
4. **CallerID routing** → configure prefix rules per SIP extension in Zadarma cabinet

Full setup details: [Налаштування](#налаштування)

---

## Module Info

**Module:** `zadarma_odoo` · **Version:** 1.5.0 · **Platform:** Odoo 17.0  
**Client:** CampScout (campscout.eu) · **Repository:** https://github.com/VladSh77/zadarma-odoo

---

## Technical Documentation

1. [Огляд модуля](#огляд-модуля)
2. [Архітектура](#архітектура)
3. [Моделі даних](#моделі-даних)
4. [Webhook — обробка подій](#webhook--обробка-подій)
5. [Click-to-Call](#click-to-call)
6. [Імпорт дзвінків](#імпорт-дзвінків)
7. [Записи розмов](#записи-розмов)
8. [Налаштування](#налаштування)
9. [Логіка визначення напрямку дзвінка](#логіка-визначення-напрямку-дзвінка)
10. [Логіка пошуку контакту](#логіка-пошуку-контакту)
11. [Відомі обмеження](#відомі-обмеження)
12. [Changelog](#changelog)

---

## Огляд модуля

Модуль інтегрує хмарну АТС **Zadarma** з Odoo CRM. Забезпечує:

- Автоматичне збереження вхідних і вихідних дзвінків через webhook
- Прив'язку дзвінків до контактів (`res.partner`) і лідів (`crm.lead`)
- Авто-створення ліда при дзвінку з невідомого номера
- Нотатки у Chatter з деталями дзвінка (від імені менеджера)
- Click-to-Call через Zadarma Callback API
- Ретроспективний імпорт дзвінків за довільний період
- Завантаження записів розмов у Odoo filestore (постійне зберігання)
- Визначення відповідального менеджера за SIP-номером

---

## Архітектура

```
zadarma_odoo/
├── __manifest__.py
├── __init__.py
├── controllers/
│   ├── __init__.py
│   └── webhook.py          # HTTP endpoint для webhook-подій Zadarma
├── models/
│   ├── __init__.py
│   ├── zadarma_call.py     # Модель запису дзвінка
│   ├── zadarma_import.py   # TransientModel для імпорту
│   ├── res_company.py      # API credentials на компанії
│   ├── res_users.py        # SIP ID на користувачі
│   ├── res_partner.py      # Click-to-Call
│   └── partner_lead_ext.py # Лічильник дзвінків на партнері і ліді
├── views/
│   ├── zadarma_views.xml
│   ├── zadarma_import_views.xml
│   ├── res_company_views.xml
│   ├── res_users_views.xml
│   └── partner_lead_views.xml
├── security/
│   ├── zadarma_security.xml
│   └── ir.model.access.csv
└── static/description/
    └── index.html
```

**Залежності Odoo:** `base`, `crm`, `mail`

---

## Моделі даних

### `zadarma.call` — Запис дзвінка

| Поле | Тип | Опис |
|------|-----|------|
| `name` | Char (computed) | `"Дзвінок {phone} ({date})"` |
| `call_id` | Char, index | Унікальний ID дзвінка від Zadarma (`pbx_call_id`) |
| `date_start` | Datetime | Час початку дзвінка |
| `phone_number` | Char, index | Номер зовнішнього абонента |
| `direction` | Selection | `inbound` / `outbound` |
| `duration` | Integer | Тривалість у секундах |
| `status` | Char | `answered`, `cancel`, `busy`, тощо |
| `partner_id` | Many2one → res.partner | Прив'язаний контакт |
| `lead_id` | Many2one → crm.lead | Прив'язаний лід |
| `user_id` | Many2one → res.users | Менеджер (визначається за SIP) |
| `recording_url` | Char | `/web/content/{attachment_id}?download=true` |

Сортування за замовчуванням: `date_start DESC`.

### `res.company` — розширення

| Поле | Тип | Опис |
|------|-----|------|
| `zadarma_api_key` | Char | API Key з кабінету Zadarma |
| `zadarma_api_secret` | Char | API Secret з кабінету Zadarma |
| `zadarma_callerid_rules` | Text | Зарезервоване поле (CallerID routing налаштовується в Zadarma) |

### `res.users` — розширення

| Поле | Тип | Опис |
|------|-----|------|
| `zadarma_internal_number` | Char | SIP ID менеджера (наприклад, `100`) |

### `res.partner` / `crm.lead` — розширення

| Поле | Тип | Опис |
|------|-----|------|
| `zadarma_call_ids` | One2many → zadarma.call | Всі дзвінки контакту/ліда |
| `zadarma_call_count` | Integer (computed) | Кількість дзвінків |

---

## Webhook — обробка подій

**URL:** `POST https://your-domain/zadarma/webhook`
**Auth:** public (без авторизації Odoo)
**CSRF:** вимкнено
**Echo-верифікація:** GET з параметром `zd_echo` → повертає значення (перевірка Zadarma)

### Оброблювані події

#### `NOTIFY_END` — вхідний PBX-дзвінок завершено

**Параметри:** `call_id`/`pbx_call_id`, `call_start`, `caller_id`, `called_did`, `duration`, `disposition`, `recording`

**Логіка:**
1. Визначення напрямку: якщо `caller_id` ≤ 5 цифр — внутрішній SIP → вихідний
2. Вхідний: `phone = caller_id` (зовнішній номер)
3. Пошук партнера за номером телефону (SQL з нормалізацією)
4. Пошук активного ліда партнера (`probability < 100`)
5. Якщо партнер і лід не знайдені — авто-створення ліда `"Дзвінок: {phone}"`
6. Збереження `zadarma.call`
7. Нотатка у Chatter від імені менеджера або OdooBot

#### `NOTIFY_OUT_END` (calltype=`callback_leg2`) — вихідний callback

Zadarma Callback API створює два виклики:
- **leg1**: Zadarma дзвонить на SIP менеджера
- **leg2**: Zadarma дзвонить клієнту

Зберігається тільки **leg2** (реальний вихідний дзвінок).

**Параметри:** `pbx_call_id`, `call_start`, `internal` (SIP менеджера), `destination` (номер клієнта), `duration`, `disposition`, `is_recorded`, `call_id_with_rec`

**Логіка:**
1. Перевірка дублікату за `call_id` (leg1 і leg2 мають однаковий `pbx_call_id`)
2. `phone = destination` (нормалізований)
3. `sip = internal` → пошук менеджера за `zadarma_internal_number`
4. Збереження `zadarma.call`
5. Нотатка у Chatter

#### `NOTIFY_RECORD` — запис розмови готовий

Надсилається Zadarma через ~5–10 секунд після завершення дзвінка (якщо `is_recorded=1`).

**Параметри:** `pbx_call_id`, `call_id_with_rec`

**Логіка:**
1. Пошук `zadarma.call` за `pbx_call_id`
2. Запит тимчасового URL через API `/v1/pbx/record/request/`
3. Завантаження MP3 (timeout: 60s)
4. Збереження як `ir.attachment` (`res_model='zadarma.call'`, `res_id=call.id`)
5. `recording_url = '/web/content/{attachment_id}?download=true'`
6. Fallback: при помилці завантаження — зберігається тимчасовий URL

> **Важливо:** тимчасовий URL Zadarma діє лише **30 хвилин**. Тому файл завантажується і зберігається постійно в Odoo filestore.

---

## Click-to-Call

**Метод:** `action_zadarma_call()` на `res.partner`

**API Zadarma:** `GET /v1/request/callback/?from={SIP}&to={PHONE}&sip={SIP}`

**Формат номера клієнта:** `+{цифри}` — обов'язково з `+`, інакше Zadarma не застосовує CallerID routing rules.

**Підпис запиту (HMAC-SHA1):**
```
query_string = urlencode(sorted(params))
md5          = MD5(query_string)
sign_str     = METHOD + query_string + md5
hmac_hex     = HMAC-SHA1(secret, sign_str).hexdigest()
signature    = Base64(hmac_hex)
Authorization: {key}:{signature}
```

**CallerID routing (в Zadarma, не в коді):**
- `+380*` → CallerID `+380630202948` (Україна)
- `+48*` → CallerID `+48459568854` (Польща)

**Параметр `sip=`:** активує CallerID-by-destination і prefix dialling конкретного SIP-розширення.

**Callback flow:**
```
action_zadarma_call()
    → POST /v1/request/callback/ (from=SIP, to=+PHONE, sip=SIP)
    → Zadarma дзвонить на SIP менеджера (leg1)
    → Менеджер бере трубку
    → Zadarma дзвонить клієнту з правильним CallerID (leg2)
    → NOTIFY_OUT_END (leg2) → збереження в Odoo
    → NOTIFY_RECORD → завантаження запису
```

---

## Імпорт дзвінків

**Модель:** `zadarma.import` (TransientModel)
**Меню:** Zadarma → Імпорт дзвінків
**API Zadarma:** `GET /v1/statistics/pbx/`

| Параметр форми | Default | Опис |
|---|---|---|
| `date_from` | -30 днів | Початок діапазону |
| `date_to` | сьогодні | Кінець діапазону |

**Особливості:**
- Пагінація: `skip/limit=1000`, затримка 1с між сторінками (rate limit)
- При HTTP 429: 3 спроби з затримками 3/6/9 секунд
- Дедублікація: існуючі `call_id` пропускаються
- Визначення напрямку: `sip ≤ 5 цифр` → вихідний
- Нотатки в Chatter позначаються як `(імпорт)` і публікуються від поточного користувача

---

## Записи розмов

### Повний потік отримання запису:

```
Дзвінок завершується
    └── NOTIFY_OUT_END / NOTIFY_END (is_recorded=1, call_id_with_rec=XXX)
        └── NOTIFY_RECORD (5-10 сек пізніше)
            └── GET /v1/pbx/record/request/?call_id=XXX&pbx_call_id=YYY
                └── {"status":"success","links":["https://api.zadarma.com/...mp3"],"lifetime_till":"...+30хв"}
                    └── requests.get(url, timeout=60)
                        └── ir.attachment.create(datas=base64(mp3))
                            └── zadarma.call.recording_url = '/web/content/{id}?download=true'
```

### Зберігання:
- **Місце:** Odoo filestore (`/var/lib/odoo/filestore/{db}/`)
- **Прив'язка:** `ir.attachment.res_model = 'zadarma.call'`, `res_id = call.id`
- **Доступ:** через стандартний Odoo endpoint `/web/content/`

---

## Налаштування

### 1. Zadarma API credentials
`Налаштування → Компанія → вкладка Zadarma`
- **Zadarma Key** і **Zadarma Secret** з кабінету Zadarma → API → Ключі

### 2. SIP ID менеджерів
`Налаштування → Користувачі → [менеджер] → Zadarma SIP ID`
- Значення: `100`, `101`, `102`, `103` (внутрішні номери АТС)

### 3. Webhook URL у кабінеті Zadarma
`Zadarma → АТС → Налаштування → Webhook / API`
```
https://campscout.eu/zadarma/webhook
```
Активувати події: `NOTIFY_START`, `NOTIFY_ANSWER`, `NOTIFY_END`, `NOTIFY_OUT_START`, `NOTIFY_OUT_END`, `NOTIFY_RECORD`

### 4. CallerID routing у Zadarma
`Zadarma → АТС → SIP-розширення → [кожен SIP] → CallerID за напрямком: УВІМК.`

Налаштувати правила:
- Префікс `+380` → CallerID `+380630202948`
- Префікс `+48` → CallerID `+48459568854`

Увімкнути на кожному розширенні (100, 101, 102, 103).

### 5. Запис розмов у Zadarma
Увімкнути запис дзвінків у налаштуваннях АТС Zadarma.

---

## Логіка визначення напрямку дзвінка

### Webhook (`NOTIFY_END`):
```python
INTERNAL_NUMBER_MAX_LENGTH = 5
is_outbound = len(re.sub(r'\D', '', str(caller_id))) <= 5
# Вихідний: caller_id = "100" (SIP), called_did = номер клієнта
# Вхідний:  caller_id = "+48573134144" (зовнішній номер)
```

### Imпорт (`/v1/statistics/pbx/`):
```python
is_outbound = len(re.sub(r'\D', '', sip)) <= 5
# Вихідний: phone = destination
# Вхідний:  phone = sip
```

---

## Логіка пошуку контакту

```sql
SELECT id FROM res_partner
WHERE active = true
  AND (
    regexp_replace(phone, '[^0-9]', '', 'g') LIKE '%{suffix}'
    OR regexp_replace(mobile, '[^0-9]', '', 'g') LIKE '%{suffix}'
  )
ORDER BY
  (CASE WHEN name ~ '^[0-9 +().-]+$' THEN 1 ELSE 0 END) ASC,
  id ASC
LIMIT 1
```

- `suffix` = останні 9 цифр номера (відсікає різні коди країн)
- **ORDER BY**: пріоритет контактів з нечисловими іменами (реальні люди перед технічними записами типу `"48889448977"`)

---

## Відомі обмеження

1. **Один SIP на менеджера** — `zadarma_internal_number` зберігає один номер.
2. **Запис лише для callback** — вхідні дзвінки (`NOTIFY_END`) отримують поле `recording` напряму; для вихідних використовується `NOTIFY_RECORD`.
3. **Filestore розмір** — записи розмов займають місце на диску. Для довгострокового зберігання розгляньте S3/зовнішнє сховище.
4. **`zadarma_callerid_rules`** — поле присутнє в БД але не використовується кодом.
5. **Часова зона** — дати від Zadarma приходять у форматі без timezone; Odoo зберігає в UTC.

---

## Changelog

### v1.5.0 (2026-03-26)
- **[FIX]** Click-to-Call: номер клієнта передається з `+` prefix → CallerID routing в Zadarma коректно обирає транк (+380 → Україна, +48 → Польща)
- **[FEAT]** Обробка `NOTIFY_RECORD`: MP3 завантажується у Odoo filestore через `ir.attachment`, `recording_url` вказує на постійний internal URL
- **[FIX]** Zadarma API повертає `links[]` (масив), а не `link` (рядок) — виправлено парсинг
- **[FIX]** Chatter нотатки публікуються від імені менеджера (`with_user(user.id)`), а не від Public User
- **[FIX]** `_find_partner` ORDER BY: пріоритет контактів з нечисловими іменами — усуває вибір технічних партнерів-дублікатів
- **[FIX]** Callback API: доданий параметр `sip=` для активації CallerID-by-destination і prefix dialling
- **[FIX]** `_zadarma_get_recording_url`: пошук компанії з наявним `zadarma_api_key` замість `search([])`
- **[DEBUG→CLEAN]** Прибрано надлишкове агресивне логування з попередніх версій

### v1.3.0
- Додано поле `recording_url` у `zadarma.call`
- Відображення посилання на запис у form view

### v1.2.0
- Click-to-Call через Zadarma Callback API
- Ретроспективний імпорт дзвінків (`zadarma.import`)
- Rate limit handling (HTTP 429)

### v1.1.0
- Обробка webhook `NOTIFY_END`, `NOTIFY_OUT_END`
- Авто-створення лідів для невідомих номерів
- Chatter нотатки
- Пошук менеджера за SIP ID

### v1.0.0
- Початкова версія: модель `zadarma.call`, базові views, security
