"""
ABHA / Aadhaar handling for the kiosk.

- ABHA numbers are health identifiers designed to be stored; they are kept in
  one canonical format (XX-XXXX-XXXX-XXXX) so lookups match however the
  patient typed it, and are only ever *shown* masked.
- Aadhaar numbers are never stored. The Aadhaar Act restricts storing the full
  number, so the kiosk keeps an HMAC of it (keyed with SECRET_KEY) for lookup
  and the last four digits for display — the same "XXXX XXXX 1234" the masked
  card itself shows.

Nothing here verifies an identity against ABDM or UIDAI.
"""
import hashlib
import hmac
import os
import re
from typing import Optional


def digits(raw: Optional[str]) -> str:
    return re.sub(r"\D", "", raw or "")


def normalize_abha(raw: Optional[str]) -> Optional[str]:
    d = digits(raw)
    if len(d) != 14:
        return None
    return f"{d[:2]}-{d[2:6]}-{d[6:10]}-{d[10:]}"


def mask_abha(abha: Optional[str]) -> Optional[str]:
    d = digits(abha)
    return f"XX-XXXX-XXXX-{d[-4:]}" if len(d) >= 4 else None


def normalize_aadhaar(raw: Optional[str]) -> Optional[str]:
    d = digits(raw)
    return d if len(d) == 12 else None


def aadhaar_hash(aadhaar_digits: str) -> str:
    key = os.getenv("SECRET_KEY", "medikiosk_super_secret_key_change_in_production").encode()
    return hmac.new(key, aadhaar_digits.encode(), hashlib.sha256).hexdigest()


def mask_aadhaar(last4: Optional[str]) -> Optional[str]:
    return f"XXXX XXXX {last4}" if last4 else None
