import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime

from odoo import http
from odoo.http import request
from pytz import UTC

_logger = logging.getLogger(__name__)


class ZadarmaWebhook(http.Controller):
    @http.route(
        "/zadarma/webhook",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
    )
    def webhook_handler(self, **kwargs):
        """
        Обробка вебхуків від Zadarma:
        - GET: верифікація URL (zd_echo)
        - POST: сповіщення про дзвінки
        """
        try:
            # 1. Обробка GET-запиту для верифікації URL
            if request.httprequest.method == "GET":
                zd_echo = kwargs.get("zd_echo")
                if zd_echo:
                    _logger.info("URL verification received: %s", zd_echo)
                    return request.make_response(
                        zd_echo, [("Content-Type", "text/plain")]
                    )
                return request.make_response("OK", [("Content-Type", "text/plain")])

            # 2. Обробка POST-запиту (сповіщення про дзвінки)
            elif request.httprequest.method == "POST":
                # Отримуємо дані з форми (application/x-www-form-urlencoded)
                data = kwargs
                if not data:
                    # Якщо дані пусті, пробуємо JSON
                    try:
                        data = json.loads(request.httprequest.data)
                    except Exception:
                        pass

                _logger.info("Received Zadarma webhook: %s", data)

                # 3. Перевірка підпису (Signature)
                signature = request.httprequest.headers.get("Signature")
                if not self._verify_signature_sudo(data, signature):
                    _logger.warning("Invalid signature for webhook")
                    return request.make_response(
                        json.dumps({"status": "error", "message": "Invalid signature"}),
                        [("Content-Type", "application/json")],
                        status=403,
                    )

                # 4. Обробка різних типів подій
                event = data.get("event")
                if event == "NOTIFY_START":
                    self._handle_call_start(data)
                elif event == "NOTIFY_END":
                    self._handle_call_end(data)
                elif event == "NOTIFY_RECORD":
                    self._handle_call_record(data)
                else:
                    _logger.info("Unhandled event type: %s", event)

                return request.make_response(
                    json.dumps({"status": "success"}),
                    [("Content-Type", "application/json")],
                )

        except Exception as e:
            _logger.error("Error processing webhook: %s", str(e))
            return request.make_response(
                json.dumps({"status": "error", "message": str(e)}),
                [("Content-Type", "application/json")],
                status=500,
            )

    def _verify_signature_sudo(self, data, signature):
        """Перевірка підпису Zadarma з використанням sudo()"""
        if not signature:
            return False

        try:
            # Отримуємо секрет першої компанії
            company = request.env["res.company"].sudo().search([], limit=1)
            if not company or not company.zadarma_api_secret:
                _logger.error("No Zadarma API secret configured")
                return False

            secret = company.zadarma_api_secret

            # Формуємо рядок для підпису: відсортовані параметри
            # Важливо: значення мають бути рядками, None перетворюємо на ''
            sorted_items = sorted(data.items())
            data_parts = []
            for k, v in sorted_items:
                if v is None:
                    v = ""
                elif not isinstance(v, str):
                    v = str(v)
                data_parts.append(f"{k}={v}")
            data_string = "&".join(data_parts)

            # Обчислюємо підпис
            expected = hmac.new(
                secret.encode("utf-8"), data_string.encode("utf-8"), hashlib.sha1
            ).digest()
            expected_base64 = base64.b64encode(expected).decode("utf-8")

            return hmac.compare_digest(signature, expected_base64)

        except Exception as e:
            _logger.error("Error verifying signature: %s", str(e))
            return False

    def _parse_zadarma_datetime(self, dt_str):
        """Конвертує рядок часу з Zadarma в UTC datetime"""
        if not dt_str:
            return False

        try:
            # Припускаємо, що Zadarma надсилає час у форматі 'YYYY-MM-DD HH:MM:SS'
            # Перевіряємо, чи є таймзона в рядку
            if (
                "+" in dt_str or "-" in dt_str[10:]
            ):  # проста перевірка на наявність зміщення
                # Якщо час вже з таймзоною
                dt = datetime.fromisoformat(dt_str.replace(" ", "T"))
            else:
                # Якщо без таймзони — вважаємо, що це UTC (рекомендовано налаштувати в Zadarma)
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                dt = dt.replace(tzinfo=UTC)

            # Конвертуємо в UTC, якщо потрібно
            if dt.tzinfo:
                dt = dt.astimezone(UTC)
                dt = dt.replace(tzinfo=None)

            return dt

        except Exception as e:
            _logger.error("Error parsing datetime %s: %s", dt_str, str(e))
            return False

    def _handle_call_start(self, data):
        """Обробка початку дзвінка"""
        call_id = data.get("call_id")
        _logger.info("Call started: %s", call_id)

        try:
            start_time = self._parse_zadarma_datetime(data.get("call_start"))
            if not start_time:
                start_time = datetime.utcnow()

            # Створення запису дзвінка з sudo()
            call = (
                request.env["zadarma.call"]
                .sudo()
                .create(
                    {
                        "call_id": call_id,
                        "start_time": start_time,
                        "caller_number": data.get("caller_id"),
                        "called_number": data.get("called_did"),
                        "call_type": "incoming"
                        if data.get("call_type") == "inbound"
                        else "outgoing",
                        "status": "answered"
                        if data.get("disposition") == "answered"
                        else "missed",
                    }
                )
            )

            _logger.info("Created call record: %s", call.id)

        except Exception as e:
            _logger.error("Error creating call record: %s", str(e))

    def _handle_call_end(self, data):
        """Обробка завершення дзвінка"""
        call_id = data.get("call_id")
        _logger.info("Call ended: %s", call_id)

        try:
            call = (
                request.env["zadarma.call"]
                .sudo()
                .search([("call_id", "=", call_id)], limit=1)
            )
            if call:
                end_time = self._parse_zadarma_datetime(data.get("call_end"))
                call.write(
                    {
                        "end_time": end_time,
                        "duration": int(data.get("duration", 0)),
                    }
                )
                _logger.info("Updated call record: %s", call.id)
        except Exception as e:
            _logger.error("Error updating call record: %s", str(e))

    def _handle_call_record(self, data):
        """Обробка запису розмови"""
        call_id = data.get("call_id")
        recording_url = data.get("link")
        _logger.info("Call recording for %s: %s", call_id, recording_url)

        try:
            call = (
                request.env["zadarma.call"]
                .sudo()
                .search([("call_id", "=", call_id)], limit=1)
            )
            if call:
                call.write(
                    {
                        "recording_url": recording_url,
                    }
                )
                _logger.info("Saved recording URL for call: %s", call.id)
        except Exception as e:
            _logger.error("Error saving recording URL: %s", str(e))
