"""API Dynamic Path Normalizer and Parameter Detector.

Converts concrete URI paths (e.g., /users/1002, /orders/uuid) into parameterized
templates (/users/{id}, /orders/{uuid}) and evaluates endpoint sensitivity/risk.
"""

import hashlib
import re
from typing import List, Tuple
from backend.app.schemas.inventory import RiskLevel

# Pattern matchers for dynamic path segments
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
NUMERIC_ID_PATTERN = re.compile(r"^\d+$")
PREFIXED_ID_PATTERN = re.compile(
    r"^(usr|user|ord|order|prod|item|acc|cst|doc|dep|sub|inv|txn|cust|c)_[0-9a-zA-Z]+$",
    re.IGNORECASE,
)
HEX_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{16,64}$")
FILE_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+\.(pdf|csv|json|xml|png|jpg|txt|zip)$", re.IGNORECASE)

# Risk heuristic keywords
CRITICAL_KEYWORDS = {"admin", "internal", "debug", "root", "system", "env", "config"}
HIGH_KEYWORDS = {
    "auth", "login", "password", "token", "session", "credential", "secret",
    "payment", "checkout", "charge", "transfer", "withdraw", "card", "billing"
}
MEDIUM_KEYWORDS = {"export", "download", "dump", "backup", "import", "upload", "kyc"}


def parameterize_path(path: str) -> str:
    """Replaces dynamic entity IDs, UUIDs, and hashes with parameterized template tokens."""
    if not path or path == "/":
        return "/"

    segments = path.strip("/").split("/")
    template_segments = []

    for seg in segments:
        if UUID_PATTERN.match(seg):
            template_segments.append("{uuid}")
        elif NUMERIC_ID_PATTERN.match(seg):
            template_segments.append("{id}")
        elif PREFIXED_ID_PATTERN.match(seg):
            template_segments.append("{id}")
        elif HEX_HASH_PATTERN.match(seg):
            template_segments.append("{hash}")
        elif FILE_PATTERN.match(seg):
            template_segments.append("{file}")
        elif seg.startswith("{") and seg.endswith("}"):
            # Already parameterized
            template_segments.append(seg)
        else:
            template_segments.append(seg)

    return "/" + "/".join(template_segments)


def generate_endpoint_id(method: str, path_template: str) -> str:
    """Generates a stable deterministic endpoint identifier."""
    key = f"{method.upper()}:{path_template.lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def evaluate_endpoint_risk(method: str, path_template: str) -> Tuple[RiskLevel, List[str]]:
    """Evaluates risk classification and tags based on endpoint sensitivity."""
    path_lower = path_template.lower()
    tags = []
    risk = RiskLevel.LOW

    # Check Critical
    for kw in CRITICAL_KEYWORDS:
        if f"/{kw}" in path_lower or f"/{kw}/" in path_lower or path_lower.endswith(f"/{kw}"):
            risk = RiskLevel.CRITICAL
            tags.append("administrative")
            break

    # Check High if not already critical
    if risk != RiskLevel.CRITICAL:
        for kw in HIGH_KEYWORDS:
            if kw in path_lower:
                risk = RiskLevel.HIGH
                if kw in {"auth", "login", "password", "token", "credential"}:
                    tags.append("authentication")
                elif kw in {"payment", "checkout", "charge", "transfer", "billing"}:
                    tags.append("financial")
                break

    # Check Medium
    if risk == RiskLevel.LOW:
        for kw in MEDIUM_KEYWORDS:
            if kw in path_lower:
                risk = RiskLevel.MEDIUM
                tags.append("data-transfer")
                break

    # High write impact methods
    if method in {"DELETE", "PUT", "PATCH"} and risk == RiskLevel.LOW:
        risk = RiskLevel.MEDIUM
        tags.append("state-mutation")

    if not tags:
        tags.append("standard-api")

    return risk, sorted(list(set(tags)))
