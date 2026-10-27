"""SentinelAPI Quarantine Isolation Manager.

Manages entities isolated in quarantine pending SOC investigation or behavioral clearance.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple
from backend.app.schemas.policy import QuarantineEntry

logger = logging.getLogger("sentinelapi.policy.quarantine_manager")


class QuarantineManager:
    """Manages quarantined IP addresses and client identities."""

    def __init__(self):
        # client_ip -> QuarantineEntry
        self._quarantined: Dict[str, QuarantineEntry] = {}
        self._lock = asyncio.Lock()

    async def quarantine(
        self,
        client_ip: str,
        client_id: Optional[str] = None,
        reason: str = "Quarantined for suspicious activity",
        policy_id: Optional[str] = None,
    ) -> QuarantineEntry:
        """Places a client in quarantine."""
        async with self._lock:
            entry = QuarantineEntry(
                client_ip=client_ip,
                client_id=client_id,
                quarantined_at=datetime.now(timezone.utc),
                reason=reason,
                policy_id=policy_id,
                is_active=True,
            )
            self._quarantined[client_ip] = entry
            logger.warning(
                f"[QUARANTINE ENFORCED] IP={client_ip} ClientID={client_id} Reason='{reason}' Policy={policy_id}"
            )
            return entry

    async def is_quarantined(self, client_ip: str) -> Tuple[bool, Optional[QuarantineEntry]]:
        """Checks if a client IP is currently quarantined."""
        async with self._lock:
            entry = self._quarantined.get(client_ip)
            if entry and entry.is_active:
                return True, entry
            return False, None

    async def release(self, client_ip: str) -> bool:
        """Releases a client IP from quarantine."""
        async with self._lock:
            if client_ip in self._quarantined:
                self._quarantined[client_ip].is_active = False
                del self._quarantined[client_ip]
                logger.info(f"[QUARANTINE RELEASED] IP={client_ip} released by operator.")
                return True
            return False

    async def list_active(self) -> List[QuarantineEntry]:
        """Returns all currently quarantined entries."""
        async with self._lock:
            return [e for e in self._quarantined.values() if e.is_active]

    async def count_active(self) -> int:
        """Returns the number of active quarantined entries."""
        async with self._lock:
            return len([e for e in self._quarantined.values() if e.is_active])

    async def clear_all(self) -> None:
        """Clears all quarantine records (useful for testing)."""
        async with self._lock:
            self._quarantined.clear()


# Global singleton instance
quarantine_manager = QuarantineManager()
