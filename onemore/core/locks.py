from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta

from redis import Redis
from redis.exceptions import RedisError

from onemore.core.config import get_settings
from onemore.core.errors import AppError


class KeyedLocks:
    """Process-local fallback; PostgreSQL/Redis remains the production lock boundary."""

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._locks: dict[str, threading.RLock] = defaultdict(threading.RLock)

    @contextmanager
    def acquire(self, key: str) -> Iterator[None]:
        with self._guard:
            lock = self._locks[key]
        with lock:
            yield


class HybridKeyedLocks:
    """Redis distributed lock with a development/test process-local fallback."""

    def __init__(self, namespace: str) -> None:
        self.namespace = namespace
        self.settings = get_settings()
        self._local = KeyedLocks()
        self._redis: Redis | None = None
        self._redis_disabled_until = 0.0
        if self.settings.distributed_locks_enabled and self.settings.env != "test":
            self._redis = Redis.from_url(
                self.settings.redis_url,
                socket_connect_timeout=0.15,
                socket_timeout=0.5,
                decode_responses=True,
            )

    @contextmanager
    def acquire(self, key: str) -> Iterator[None]:
        if self._redis is None or time.monotonic() < self._redis_disabled_until:
            with self._local.acquire(key):
                yield
            return

        lock = self._redis.lock(
            f"onemore:lock:{self.namespace}:{key}",
            timeout=self.settings.distributed_lock_timeout_seconds,
            blocking_timeout=self.settings.distributed_lock_wait_seconds,
            thread_local=False,
        )
        try:
            acquired = bool(lock.acquire(blocking=True))
        except RedisError as exc:
            if self.settings.is_production:
                raise AppError("LOCK_SERVICE_UNAVAILABLE", "并发控制服务暂时不可用", 503) from exc
            self._redis_disabled_until = time.monotonic() + 30
            with self._local.acquire(key):
                yield
            return

        if not acquired:
            raise AppError(
                "RESOURCE_BUSY",
                "资源正在处理中，请稍后重试",
                409,
                {"resource": self.namespace},
            )
        try:
            yield
        finally:
            with suppress(RedisError):
                lock.release()


class LocalSlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window = timedelta(seconds=window_seconds)
        self._guard = threading.Lock()
        self._calls: dict[str, deque[datetime]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = datetime.now(UTC)
        with self._guard:
            calls = self._calls[key]
            cutoff = now - self.window
            while calls and calls[0] < cutoff:
                calls.popleft()
            if len(calls) >= self.limit:
                raise AppError("RATE_LIMITED", "请求过于频繁，请稍后再试", 429)
            calls.append(now)


class SlidingWindowRateLimiter:
    _SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local cutoff = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)
if count >= limit then return 0 end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, tonumber(ARGV[5]))
return 1
"""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.settings = get_settings()
        self._local = LocalSlidingWindowRateLimiter(limit, window_seconds)
        self._redis: Redis | None = None
        self._redis_disabled_until = 0.0
        if self.settings.distributed_locks_enabled and self.settings.env != "test":
            self._redis = Redis.from_url(
                self.settings.redis_url,
                socket_connect_timeout=0.15,
                socket_timeout=0.5,
                decode_responses=True,
            )

    def check(self, key: str) -> None:
        if self._redis is None or time.monotonic() < self._redis_disabled_until:
            self._local.check(key)
            return
        now_ms = int(time.time() * 1000)
        try:
            allowed = self._redis.eval(
                self._SCRIPT,
                1,
                f"onemore:rate:executor:{key}",
                str(now_ms),
                str(now_ms - self.window_seconds * 1000),
                str(self.limit),
                f"{now_ms}:{uuid.uuid4()}",
                str(self.window_seconds + 1),
            )
        except RedisError as exc:
            if self.settings.is_production:
                raise AppError("RATE_LIMIT_SERVICE_UNAVAILABLE", "限流服务暂时不可用", 503) from exc
            self._redis_disabled_until = time.monotonic() + 30
            self._local.check(key)
            return
        if not allowed:
            raise AppError("RATE_LIMITED", "请求过于频繁，请稍后再试", 429)


user_locks = HybridKeyedLocks("user")
gathering_locks = HybridKeyedLocks("gathering")
action_locks = HybridKeyedLocks("action")
identity_locks = HybridKeyedLocks("campus-identity")
