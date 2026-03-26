# zadarma_odoo — Технічна документація

**Версія:** 1.3.0
**Odoo:** 17.0
**Репозиторій:** https://github.com/VladSh77/zadarma-odoo
**Production:** https://campscout.eu
**Шлях на сервері:** `/opt/campscout/custom-addons/zadarma_odoo`

---

## Призначення

Інтеграція телефонії Zadarma з Odoo для CampScout:
- Автоматичне збереження всіх дзвінків (вхідних і вихідних) через webhook
- Прив'язка дзвінків до контактів і лідів CRM
- Нотатки в chatter при кожному дзвінку
- Кнопка виклику з картки контакту через Zadarma API
- Ручний імпорт історії дзвінків за обраний період

---

## Структура файлів

```
zadarma_odoo/
├── __init__.py
├── __manifest__.py
├── hooks.py                          # post_init_hook — деактивація binotel view
├── controllers/
│   └── webhook.py                    # Обробник подій від Zadarma
├── models/
│   ├── __init__.py
│   ├── zadarma_call.py               # Модель запису дзвінка
│   ├── res_company.py                # API ключі на рівні компанії
│   ├── res_users.py                  # SIP номер користувача
│   ├── res_partner.py                # Кнопка виклику + stat button
│   ├── partner_lead_ext.py           # Розширення партнера і ліда (лічильники)
│   └── zadarma_import.py             # TransientModel wizard імпорту
├── views/
│   ├── zadarma_views.xml             # Список та форма дзвінків, меню
│   ├── res_company_views.xml         # Вкладка Zadarma в налаштуваннях компанії
│   ├── res_users_views.xml           # Поле SIP в профілі користувача
│   ├── partner_lead_views.xml        # Кнопки на картці партнера і ліда
│   └── zadarma_import_views.xml      # Форма wizard імпорту
├── security/
│   ├── zadarma_security.xml          # Групи доступу
│   └── ir.model.access.csv           # Права на моделі
└── migrations/
    └── 1.3.0/
        └── post-migrate.py           # Деактивація binotel_connect кнопок
```

---

## Налаштування

### 1. API ключі Zadarma
`Налаштування → Компанії → [компанія] → вкладка "Zadarma Settings"`
- **Zadarma Key** — API ключ з особистого кабінету Zadarma → API
- **Zadarma Secret** — API secret

### 2. SIP номер користувача
`Налаштування → Користувачі → [користувач] → поле "Zadarma SIP ID"`
Приклад: `101` — внутрішній номер SIP для вихідних дзвінків.

### 3. Webhook у Zadarma
Кабінет Zadarma → Налаштування → API → Webhook:
- **URL:** `https://campscout.eu/zadarma/webhook`
- **Events:** `NOTIFY_START`, `NOTIFY_END`

---

## Моделі

### `zadarma.call` — запис дзвінка

| Поле | Тип | Опис |
|------|-----|------|
| `call_id` | Char | ID дзвінка (Zadarma `call_id` або `pbx_call_id`) |
| `date_start` | Datetime | Час початку |
| `phone_number` | Char | Номер зовнішнього абонента |
| `direction` | Selection | `inbound` / `outbound` |
| `duration` | Integer | Тривалість у секундах |
| `status` | Char | `answered`, `cancel`, `no answer`, `failed` |
| `partner_id` | Many2one | Прив'язаний контакт (`res.partner`) |
| `lead_id` | Many2one | Прив'язаний лід (`crm.lead`) |
| `user_id` | Many2one | Відповідальний менеджер |
| `recording_url` | Char | URL запису розмови (лише через webhook) |
| `name` | Char (compute) | "Дзвінок {phone} ({date})" |

### `res.company` — розширення
- `zadarma_api_key` — API ключ
- `zadarma_api_secret` — API secret

### `res.users` — розширення
- `zadarma_internal_number` — SIP ID для вихідних дзвінків

### `res.partner` — розширення
- `zadarma_call_ids` — One2many до `zadarma.call`
- `zadarma_call_count` — обчислюване число дзвінків (для stat button)
- `action_zadarma_call()` — ініціює вихідний дзвінок через Zadarma API

### `crm.lead` — розширення
- `zadarma_call_ids` — One2many до `zadarma.call`
- `zadarma_call_count` — обчислюване число дзвінків

### `zadarma.import` — TransientModel (wizard)
| Поле | Тип | Опис |
|------|-----|------|
| `date_from` | Date | Початок діапазону (default: -30 днів) |
| `date_to` | Date | Кінець діапазону (default: сьогодні) |
| `result_message` | Text | Результат після виконання |

Метод `action_import()` — виконує імпорт з Zadarma API.

---

## Webhook — логіка обробки

**Endpoint:** `POST https://campscout.eu/zadarma/webhook`
**Контролер:** [controllers/webhook.py](controllers/webhook.py)
**Auth:** public (без авторизації, верифікація через GET `?zd_echo=...`)

### Підтримувані події

| Event | Дія |
|-------|-----|
| `NOTIFY_END` | Зберігає дзвінок, шукає партнера, створює лід, пише chatter |
| GET `?zd_echo=X` | Повертає `X` для верифікації webhook у кабінеті Zadarma |

### Алгоритм `_process_call_end`

```
1. Валідація: call_id або pbx_call_id + call_start — обов'язкові
2. Визначення напрямку:
   - caller_id ≤ 5 цифр → OUTBOUND (внутрішній SIP дзвонить назовні)
   - caller_id > 5 цифр → INBOUND (зовнішній номер дзвонить на CampScout)
3. Пошук партнера: SQL + regexp_replace (ігнорує форматування номера)
4. Пошук відкритого ліда для знайденого партнера
5. Якщо ні партнер ні лід — створення нового ліда
6. Збереження zadarma.call
7. Нотатка в chatter ліда або партнера
```

### Важлива особливість Zadarma API
Zadarma надсилає **різні ID залежно від типу дзвінка:**
- `call_id` — є тільки у відповіджених дзвінків
- `pbx_call_id` — є у ВСІХ дзвінках, включно з пропущеними (`cancel`, `no answer`)

Код: `call_id = data.get('call_id') or data.get('pbx_call_id')`

---

## Пошук партнера за телефоном

Використовується SQL з `regexp_replace` — знаходить контакти незалежно від форматування:

```sql
SELECT id FROM res_partner
WHERE active = true
  AND (
    regexp_replace(phone, '[^0-9]', '', 'g') LIKE '%886736530'
    OR regexp_replace(mobile, '[^0-9]', '', 'g') LIKE '%886736530'
  )
LIMIT 1
```

Порівняння по **останніх 9 цифрах** — підтримує `+48 886 736 530`, `+48886736530`, `048886736530`.

---

## Вихідний дзвінок (кнопка на партнері)

Кнопки `fa-phone` після полів `phone` і `mobile` на картці контакту.
Реалізація: [models/res_partner.py](models/res_partner.py) → `action_zadarma_call()`

**Алгоритм:**
1. Бере `zadarma_api_key` / `zadarma_api_secret` з компанії
2. Бере `zadarma_internal_number` з поточного користувача
3. Підпис: `HMAC-SHA1(base64)` + `MD5` згідно Zadarma SDK
4. `GET https://api.zadarma.com/v1/request/callback/?from={sip}&to={phone}`

---

## Імпорт історії дзвінків

**Меню:** Zadarma → Імпорт дзвінків
**Реалізація:** [models/zadarma_import.py](models/zadarma_import.py)

Endpoint: `GET /v1/statistics/pbx/` з пагінацією (1000 записів / запит, пауза 1с між сторінками).
При помилці 429 — автоматичний retry (3 спроби, затримка 3/6/9 секунд).

**Логіка:**
- Пропускає записи, де `call_id` вже є в БД
- Визначає напрямок по довжині `sip` (≤5 цифр = outbound)
- Пошук партнера через той самий SQL що і webhook
- Chatter нотатка з позначкою "(імпорт)"
- Повертає кількість імпортованих і вже існуючих

**Обмеження:** `recording_url` не заповнюється — Zadarma API повертає лише `is_recorded: true/false`, без URL.

---

## Деплой

```bash
# Тільки зміни коду (без нових моделей/views):
cd /opt/campscout/custom-addons/zadarma_odoo && git pull
docker compose -f /opt/campscout/docker-compose.yml restart web

# Нові моделі, XML або migration:
cd /opt/campscout/custom-addons/zadarma_odoo && git pull
cd /opt/campscout
docker compose stop web
docker compose run --rm web odoo --update zadarma_odoo --stop-after-init -d campscout
docker compose start web
```

---

## Конфлікти з іншими модулями

| Модуль | Конфлікт | Вирішення |
|--------|----------|-----------|
| `binotel_connect` | Додає 2 кнопки дзвінка на партнера → разом 3 кнопки | Migration 1.3.0 деактивує `binotel_connect.view_partner_form_inherit` |
| `kw_phone` / `kw_phone_search` | Немає конфлікту | — |
