import logging
import hashlib
import hmac
import base64
import re
import requests
from urllib.parse import urlencode
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _zadarma_callerid_for(self, target, rules_text):
        """Return CallerID for target number based on company rules."""
        if not rules_text:
            return None
        norm = re.sub(r'\D', '', target)
        for line in rules_text.strip().splitlines():
            line = line.strip()
            if ':' not in line:
                continue
            prefix, callerid = line.split(':', 1)
            if norm.startswith(prefix.strip()):
                return callerid.strip()
        return None

    def action_zadarma_call(self):
        self.ensure_one()
        _logger.info("=== ZADARMA BUTTON CLICKED for ID %s ===", self.id)

        user = self.env.user
        company = self.env.company

        key = company.zadarma_api_key
        secret = company.zadarma_api_secret
        sip_id = str(user.zadarma_internal_number or '').strip()
        target = ''.join(filter(str.isdigit, str(self.phone or self.mobile)))

        _logger.info("ZADARMA DATA: Key_exists=%s, Secret_exists=%s, SIP='%s', Target_Phone='%s'",
                     bool(key), bool(secret), sip_id, target)

        if not (key and secret and sip_id and target):
            _logger.error("ZADARMA ERROR: Missing data! Cancelling call.")
            return False

        api_method = "/v1/request/callback/"
        params = {'from': sip_id, 'to': target}

        callerid = self._zadarma_callerid_for(target, company.zadarma_callerid_rules)
        if callerid:
            params['callerid'] = callerid
            _logger.info("Zadarma: using CallerID '%s' for destination '%s'", callerid, target)

        query_string = urlencode(sorted(params.items()))
        md5_string = hashlib.md5(query_string.encode('utf8')).hexdigest()
        sign_string = api_method + query_string + md5_string
        hmac_hash = hmac.new(secret.encode('utf8'), sign_string.encode('utf8'), hashlib.sha1).hexdigest()
        signature = base64.b64encode(hmac_hash.encode('utf8')).decode('utf8')

        headers = {'Authorization': f"{key}:{signature}"}

        try:
            url = f"https://api.zadarma.com{api_method}?{query_string}"
            _logger.info("Zadarma API Call (GET): %s", url)
            response = requests.get(url, headers=headers, timeout=10)
            _logger.info("Zadarma API Result: %s", response.json())
        except Exception as e:
            _logger.error("Zadarma API Exception: %s", str(e))

        return True
