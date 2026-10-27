"""SentinelAPI Dynamic Sliding-Window Rate Limiter & Throttler.

Provides adaptive rate limiting per IP or client identity with sliding time windows,
accurate retry-after calculations, and real-time state tracking.
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple
from backend.app.schemas.policy import ThrottleState


class SlidingWindowThrottler:
    """In-memory sliding window rate limiter for adaptive throttling."""

    def __init__(self, default_window_seconds: int = 60):
        self.default_window_seconds = default_window_seconds
        # key -> list of float timestamps (time.time())
        self._windows: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def record_and_check(
        self,
        key: str,
        limit_rpm: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, int]:
        """Records a request occurrence and evaluates if the client is throttled.

        Returns:
            Tuple of:
            - is_throttled: bool
            - retry_after_seconds: int
            - current_count: int
        """
        async with self._lock:
            now = time.time()
            cutoff = now - window_seconds

            # Filter old timestamps
            timestamps = self._windows.get(key, [])
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]

            current_count = len(valid_timestamps) + 1  # including this request
            valid_timestamps.append(now)
            self._windows[key] = valid_timestamps

            if current_count > limit_rpm:
                # Oldest timestamp that needs to expire
                oldest_in_window = valid_timestamps[0]
                retry_after = max(1, int(window_seconds - (now - oldest_in_window)))
                return True, retry_after, current_count

            return False, 0, current_count

    async def check_only(
        self,
        key: str,
        limit_rpm: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, int]:
        """Checks if key is currently over limit without recording a hit."""
        async with self._lock:
            now = time.time()
            cutoff = now - window_seconds
            timestamps = self._windows.get(key, [])
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]
            self._windows[key] = valid_timestamps
            count = len(valid_timestamps)

            if count >= limit_rpm:
                oldest = valid_timestamps[0] if valid_timestamps else now
                retry_after = max(1, int(window_seconds - (now - oldest)))
                return True, retry_after, count
            return False, 0, count

    async def reset(self, key: Optional[str] = None) -> None:
        """Resets throttling history for a given key or all keys."""
        async with self._lock:
            if key:
                self._windows.pop(key, None)
            else:
                self._windows.clear()

    async def get_state(self, key: str, limit_rpm: int) -> ThrottleState:
        """Returns the current ThrottleState model for a key."""
        is_throttled, retry_after, count = await self.check_only(key, limit_rpm)
        return ThrottleState(
            client_ip=key,
            rate_limit_rpm=limit_rpm,
            current_count=count,
            is_throttled=is_throttled,
            retry_after_seconds=retry_after,
        )


# Singleton instance
adaptive_throttler = SlidingWindowThrottler()
throttler = adaptive_throttler
