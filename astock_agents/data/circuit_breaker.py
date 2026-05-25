"""断路器 - 保护数据源和LLM调用"""

import time
from typing import Dict, Any, Optional
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging


class CircuitBreaker:
    """
    断路器实现

    状态机：CLOSED(正常) → OPEN(断开) → HALF_OPEN(半开) → CLOSED

    - CLOSED: 正常放行请求
    - OPEN: 拒绝请求，直接返回失败
    - HALF_OPEN: 放行一个请求测试，成功则恢复CLOSED，失败则回到OPEN
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1
    ):
        """
        初始化断路器

        Args:
            name: 断路器名称，用于日志标识
            failure_threshold: 连续失败次数阈值，超过后断路器打开
            recovery_timeout: 恢复超时时间(秒)，OPEN状态等待此时间后进入HALF_OPEN
            half_open_max_calls: 半开状态最大放行请求数
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = "CLOSED"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> str:
        """获取当前状态，自动检查是否应从OPEN转为HALF_OPEN"""
        if self._state == "OPEN":
            # 检查是否到了恢复时间
            if self._last_failure_time and time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                self._half_open_calls = 0
                logger.info(f"[断路器:{self.name}] OPEN → HALF_OPEN")
        return self._state

    @property
    def is_open(self) -> bool:
        """断路器是否断开（拒绝请求）"""
        return self.state == "OPEN"

    def record_success(self):
        """记录成功调用"""
        if self._state == "HALF_OPEN":
            self._success_count += 1
            self._state = "CLOSED"
            self._failure_count = 0
            logger.info(f"[断路器:{self.name}] HALF_OPEN → CLOSED (恢复正常)")
        else:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        """记录失败调用"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == "HALF_OPEN":
            self._state = "OPEN"
            logger.warning(f"[断路器:{self.name}] HALF_OPEN → OPEN (测试失败)")
        elif self._failure_count >= self.failure_threshold:
            self._state = "OPEN"
            logger.warning(f"[断路器:{self.name}] CLOSED → OPEN (连续{self._failure_count}次失败)")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取断路器统计信息

        Returns:
            包含名称、状态、失败次数、成功次数的字典
        """
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
        }


# 全局断路器注册表
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """
    获取或创建断路器

    Args:
        name: 断路器名称
        **kwargs: 传递给 CircuitBreaker 构造函数的参数

    Returns:
        CircuitBreaker 实例
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name=name, **kwargs)
    return _circuit_breakers[name]


def get_all_circuit_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """
    获取所有断路器状态

    Returns:
        以断路器名称为键、统计信息为值的字典
    """
    return {name: cb.get_stats() for name, cb in _circuit_breakers.items()}


def with_retry(
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    exceptions: tuple = (Exception,)
):
    """
    通用重试装饰器

    Args:
        max_attempts: 最大重试次数
        wait_min: 最小等待时间(秒)
        wait_max: 最大等待时间(秒)
        exceptions: 需要重试的异常类型

    Returns:
        装饰器函数
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
