# Zadarma Integration for Campscout (Odoo 17)

![Odoo Version](https://img.shields.io/badge/Odoo-17.0-purple.svg)
![License](https://img.shields.io/badge/License-LGPL--3-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)

Модуль інтеграції хмарної АТС **Zadarma** з **Campscout** на базі Odoo 17.

## Функціонал

- **Click-to-Call**: Кнопка дзвінка прямо в картці контакту. Натискаєш — АТС з'єднує менеджера з клієнтом.
- **Вхідні вебхуки (NOTIFY_END)**: Автоматична обробка завершених дзвінків — і вхідних, і вихідних.
- **Автоматизація лідів**: При дзвінку з невідомого номера автоматично створюється новий лід у CRM.
- **Збереження записів розмов**: Посилання на аудіозапис зберігається в картці дзвінка.
- **Статистика дзвінків**: Лічильник та вкладка "Дзвінки Zadarma" у картці контакту і ліда.

## Технічна архітектура

- **res.company** — зберігає API Key та Secret для авторизації в Zadarma.
- **res.users** — внутрішній SIP-номер менеджера.
- **res.partner** — кнопка Click-to-Call, One2many до `zadarma.call`.
- **crm.lead** — One2many до `zadarma.call`.
- **zadarma.call** — основна модель журналу дзвінків: `call_id`, `date_start`, `duration`, `direction`, `status`, `partner_id`, `lead_id`, `recording_url`.

### Авторизація API

Підпис запитів реалізований згідно з офіційною документацією Zadarma:
`HMAC-SHA1(api_method + query_string + md5(query_string))` → `Base64`.

### Логіка визначення напрямку дзвінка

Zadarma надсилає `caller_id`. Якщо він короткий (≤ 5 цифр) — це внутрішній SIP-номер менеджера, тобто дзвінок **вихідний**. Якщо довгий — зовнішній абонент, тобто дзвінок **вхідний**.

## Налаштування

1. **API ключі**: Налаштування → Компанія → вкладка Zadarma → вписати Key та Secret.
2. **SIP номери**: Картка кожного користувача → поле "Zadarma SIP ID" (наприклад, `101`).
3. **Вебхук**: У кабінеті Zadarma вказати URL: `https://your-domain/zadarma/webhook`

## Залежності

- Odoo модулі: `base`, `crm`, `mail`
- Python: `requests` (включено в стандартний Odoo)

---
**Developed by Campscout Tech Team** [campscout.eu](https://campscout.eu) | dev@campscout.eu
