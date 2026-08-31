"""
轻量异步熔断器 — 三态（闭路/开路/半开），配合 tenacity 重试使用。

状态转换：
  CLOSED ──failure_count >= threshold──▶ OPEN
  OPEN   ──recovery_timeout 到期─────▶ HALF_OPEN
  HALF_OPEN ──成功───────────────────▶ CLOSED
  HALF_OPEN ──失败───────────────────▶ OPEN
"""

import time
import logging
from enum import Enum
from typing import Callable, Awaitable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"       # 正常
    OPEN = "open"           # 熔断，拒绝调用
    HALF_OPEN = "half_open" # 探测恢复


class CircuitBreakerOpenError(Exception):
    """熔断器开路时抛出"""
    pass


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.total_failures = 0
        self.total_successes = 0

    async def acall(self, coro_func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """异步调用入口 — await 内部 coroutine，正确处理返回值"""
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.recovery_timeout:
                logger.info(f"[CircuitBreaker:{self.name}] {self.state.value} → HALF_OPEN (recovery timeout reached)")
                self.state = CircuitState.HALF_OPEN
            else:
                remaining = self.recovery_timeout - elapsed
                raise CircuitBreakerOpenError(
                    f"熔断器 {self.name} 已开路，{remaining:.0f}s 后重试"
                )

        try:
            result = await coro_func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        self.failure_count = 0
        self.total_successes += 1
        if self.state != CircuitState.CLOSED:
            logger.info(f"[CircuitBreaker:{self.name}] HALF_OPEN → CLOSED (recovered)")
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.warning(
                    f"[CircuitBreaker:{self.name}] {self.state.value} → OPEN "
                    f"({self.failure_count} consecutive failures)"
                )
            self.state = CircuitState.OPEN

    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def stats(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
        }
