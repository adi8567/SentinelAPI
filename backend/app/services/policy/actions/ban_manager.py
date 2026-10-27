"""SentinelAPI Dynamic IP Ban Manager.

Maintains active temporary and permanent IP bans with TTL expiration,
automatic cleanup, and synchronized storage persistence.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, List, Optional, Tuple
from backend.app.schemas.policy import BlocklistEntry

logger = logging.getLogger("sentinelapi.policy.ban_manager")


class BanManager:
    """Manages active IP blocklist entries and enforcement."""

    def __init__(self):
        # ip -> BlocklistEntry
        self._bans: Dict[str, BlocklistEntry] = {}
        self._lock = asyncio.Lock()

    async def ban_ip(
        self,
        ip: str,
        duration_seconds: Optional[int] = 3600,
        reason: str = "Automated threat response",
        policy_id: Optional[str] = None,
    ) -> BlocklistEntry:
        """Enacts an IP ban for a specified duration (or permanent if duration_seconds is None)."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            expires_at = (now + timedelta(seconds=duration_seconds)) if duration_seconds else None

            entry = BlocklistEntry(
                ip=ip,
                reason=reason,
                banned_at=now,
                expires_at=expires_at,
                policy_id=policy_id,
                is_active=True,
            )
            self._bans[ip] = entry
            logger.warning(
                f"[BAN ENFORCED] IP={ip} Reason='{reason}' "
                f"TTL={duration_seconds}s ExpiresAt={expires_at} Policy={policy_id}"
            )
            return entry

    async def is_banned(self, ip: str) -> Tuple[bool, Optional[BlocklistEntry]]:
        """Checks if an IP is currently banned, auto-evicting if expired."""
        async with self._lock:
            entry = self._bans.get(ip)
            if not entry or not entry.is_active:
                return False, None

            if entry.is_expired:
                # Ban expired
                entry.is_active = False
                del self._bans[ip]
                logger.info(f"[BAN EXPIRED] IP={ip} automatically released from blocklist.")
                return False, None

            return True, entry

    async def unban_ip(self, ip: str) -> bool:
        """Manually releases an IP ban."""
        async with self._lock:
            if ip in self._bans:
                self._bans[ip].is_active = False
                del self._bans[ip]
                logger.info(f"[BAN RELEASED] IP={ip} unbanned by operator.")
                return True
            return False

    async def list_active_bans(self) -> List[BlocklistEntry]:
        """Returns all currently active bans, purging expired entries."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            active = []
            expired_ips = []

            for ip, entry in self._bans.items():
                if entry.expires_at and now > entry.expires_at:
                    expired_ips.append(ip)
                elif entry.is_active:
                    active.append(entry)

            for ip in expired_ips:
                del self._bans[ip]

            return active

    async def count_active(self) -> int:
        """Returns the number of active banned IPs."""
        bans = await self.list_active_bans()
        return len(bans)

    async def clear_all(self) -> None:
        """Clears all bans (useful for testing)."""
        async with self._lock:
            self._bans.clear()


# Global singleton instance
ip_ban_manager = BanManager()
