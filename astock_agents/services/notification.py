"""通知推送模块 - 邮件、Webhook、日志多通道通知服务

支持的通知通道：
1. EMAIL - SMTP SSL 邮件推送
2. WEBHOOK - HTTP POST Webhook 推送（含 HMAC-SHA256 签名）
3. LOG - loguru 日志记录

环境变量配置：
- ASTOCK_NOTIFY_EMAIL_ENABLED: 是否启用邮件（默认 false）
- ASTOCK_NOTIFY_EMAIL_SMTP_HOST: SMTP 服务器地址
- ASTOCK_NOTIFY_EMAIL_SMTP_PORT: SMTP 端口（默认 465）
- ASTOCK_NOTIFY_EMAIL_USER: 发件邮箱
- ASTOCK_NOTIFY_EMAIL_PASSWORD: 邮箱密码/授权码
- ASTOCK_NOTIFY_EMAIL_TO: 收件人（逗号分隔）
- ASTOCK_NOTIFY_WEBHOOK_ENABLED: 是否启用 Webhook（默认 false）
- ASTOCK_NOTIFY_WEBHOOK_URL: Webhook URL
- ASTOCK_NOTIFY_WEBHOOK_SECRET: Webhook 签名密钥
- ASTOCK_NOTIFY_LEVEL: 最低通知级别（默认 warning）
"""

import hmac
import json
import os
import smtplib
import hashlib
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from typing import Dict, List, Optional

import requests
from loguru import logger


# ---------------------------------------------------------------------------
# 通知级别优先级映射（数值越大优先级越高）
# ---------------------------------------------------------------------------
_LEVEL_PRIORITY: Dict[str, int] = {
    "info": 1,
    "warning": 2,
    "critical": 3,
}


class NotificationChannel(Enum):
    """通知通道枚举"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"


@dataclass
class NotificationMessage:
    """通知消息数据模型

    Attributes:
        title: 通知标题
        body: 通知正文
        level: 通知级别（info / warning / critical）
        stock_code: 关联股票代码（可选）
        data: 附加数据（可选）
        timestamp: 创建时间
    """
    title: str
    body: str
    level: str = "info"
    stock_code: Optional[str] = None
    data: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """校验 level 字段合法性"""
        if self.level not in _LEVEL_PRIORITY:
            raise ValueError(
                f"无效的通知级别: {self.level}，"
                f"可选值: {list(_LEVEL_PRIORITY.keys())}"
            )

    def to_dict(self) -> Dict:
        """转换为可序列化字典

        Returns:
            包含所有字段的字典，datetime 转为 ISO 格式字符串
        """
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


class NotificationService:
    """通知推送服务

    通过环境变量配置，支持邮件、Webhook、日志三种通道。
    每个通道发送失败不影响其他通道，错误记录到日志。
    仅转发级别 >= ASTOCK_NOTIFY_LEVEL 的通知。
    """

    def __init__(self) -> None:
        """从环境变量加载配置并初始化服务"""
        # 邮件配置
        self._email_enabled: bool = (
            os.getenv("ASTOCK_NOTIFY_EMAIL_ENABLED", "false").lower() == "true"
        )
        self._smtp_host: str = os.getenv("ASTOCK_NOTIFY_EMAIL_SMTP_HOST", "")
        self._smtp_port: int = int(
            os.getenv("ASTOCK_NOTIFY_EMAIL_SMTP_PORT", "465")
        )
        self._email_user: str = os.getenv("ASTOCK_NOTIFY_EMAIL_USER", "")
        self._email_password: str = os.getenv("ASTOCK_NOTIFY_EMAIL_PASSWORD", "")
        self._email_to: List[str] = [
            addr.strip()
            for addr in os.getenv("ASTOCK_NOTIFY_EMAIL_TO", "").split(",")
            if addr.strip()
        ]

        # Webhook 配置
        self._webhook_enabled: bool = (
            os.getenv("ASTOCK_NOTIFY_WEBHOOK_ENABLED", "false").lower() == "true"
        )
        self._webhook_url: str = os.getenv("ASTOCK_NOTIFY_WEBHOOK_URL", "")
        self._webhook_secret: str = os.getenv("ASTOCK_NOTIFY_WEBHOOK_SECRET", "")

        # 最低通知级别
        self._min_level: str = os.getenv("ASTOCK_NOTIFY_LEVEL", "warning")

        # 通知历史（内存缓存，最多保留 50 条）
        self._history: deque = deque(maxlen=50)

        logger.info(
            f"[通知服务] 初始化完成 | "
            f"邮件={'启用' if self._email_enabled else '禁用'} | "
            f"Webhook={'启用' if self._webhook_enabled else '禁用'} | "
            f"最低级别={self._min_level}"
        )

    # ------------------------------------------------------------------
    # 公共方法
    # ------------------------------------------------------------------

    def send(self, message: NotificationMessage) -> bool:
        """发送通知（根据级别过滤后，遍历所有启用的通道发送）

        Args:
            message: 通知消息

        Returns:
            是否至少有一个通道成功发送
        """
        # 级别过滤
        if not self._should_send(message.level):
            logger.debug(
                f"[通知服务] 通知被过滤: level={message.level}, "
                f"最低级别={self._min_level}, 标题={message.title}"
            )
            return False

        # 记录到历史
        self._history.append(message)

        success = False

        # 日志通道（始终启用）
        if self._send_log(message):
            success = True

        # 邮件通道
        if self._email_enabled and self._send_email(message):
            success = True

        # Webhook 通道
        if self._webhook_enabled and self._send_webhook(message):
            success = True

        return success

    def send_signal_change(
        self,
        stock_code: str,
        stock_name: str,
        old_signal: str,
        new_signal: str,
        confidence: float,
    ) -> bool:
        """发送信号变化通知

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            old_signal: 原信号
            new_signal: 新信号
            confidence: 置信度（0.0 ~ 1.0）

        Returns:
            是否发送成功
        """
        level = "critical" if new_signal in ("强烈买入", "强烈卖出") else "warning"
        message = NotificationMessage(
            title=f"信号变化: {stock_name}({stock_code})",
            body=(
                f"股票 {stock_name}({stock_code}) 信号发生变化\n"
                f"原信号: {old_signal} → 新信号: {new_signal}\n"
                f"置信度: {confidence:.1%}"
            ),
            level=level,
            stock_code=stock_code,
            data={
                "old_signal": old_signal,
                "new_signal": new_signal,
                "confidence": confidence,
            },
        )
        return self.send(message)

    def send_risk_alert(
        self,
        stock_code: str,
        risk_level: str,
        risk_description: str,
    ) -> bool:
        """发送风险预警通知

        Args:
            stock_code: 股票代码
            risk_level: 风险等级（如 高/中/低）
            risk_description: 风险描述

        Returns:
            是否发送成功
        """
        notify_level = "critical" if risk_level == "高" else "warning"
        message = NotificationMessage(
            title=f"风险预警: {stock_code}",
            body=(
                f"股票 {stock_code} 触发风险预警\n"
                f"风险等级: {risk_level}\n"
                f"风险描述: {risk_description}"
            ),
            level=notify_level,
            stock_code=stock_code,
            data={
                "risk_level": risk_level,
                "risk_description": risk_description,
            },
        )
        return self.send(message)

    def send_daily_report(self, report_summary: str) -> bool:
        """发送每日报告通知

        Args:
            report_summary: 报告摘要文本

        Returns:
            是否发送成功
        """
        message = NotificationMessage(
            title="每日投资报告",
            body=report_summary,
            level="info",
        )
        return self.send(message)

    def get_history(self, limit: int = 50) -> List[NotificationMessage]:
        """获取通知历史（内存缓存最近条目）

        Args:
            limit: 返回的最大条目数，默认 50

        Returns:
            按时间倒序排列的通知消息列表
        """
        items = list(self._history)
        items.reverse()
        return items[:limit]

    def is_enabled(self, channel: NotificationChannel) -> bool:
        """检查指定通道是否启用

        Args:
            channel: 通知通道枚举值

        Returns:
            该通道是否启用
        """
        if channel == NotificationChannel.EMAIL:
            return self._email_enabled
        if channel == NotificationChannel.WEBHOOK:
            return self._webhook_enabled
        if channel == NotificationChannel.LOG:
            return True
        return False

    # ------------------------------------------------------------------
    # 私有方法 - 通道发送
    # ------------------------------------------------------------------

    def _send_email(self, message: NotificationMessage) -> bool:
        """通过 SMTP SSL 发送邮件通知

        Args:
            message: 通知消息

        Returns:
            是否发送成功
        """
        if not self._smtp_host or not self._email_user or not self._email_to:
            logger.warning("[通知服务] 邮件配置不完整，跳过邮件发送")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[AStock] {message.title}"
            msg["From"] = self._email_user
            msg["To"] = ", ".join(self._email_to)

            # 构建邮件正文
            body_lines = [
                f"通知级别: {message.level.upper()}",
                f"时间: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                message.body,
            ]
            if message.stock_code:
                body_lines.insert(0, f"股票代码: {message.stock_code}")
            if message.data:
                body_lines.append("")
                body_lines.append(f"附加数据: {json.dumps(message.data, ensure_ascii=False)}")

            text_body = "\n".join(body_lines)
            msg.attach(MIMEText(text_body, "plain", "utf-8"))

            with smtplib.SMTP_SSL(self._smtp_host, self._smtp_port, timeout=10) as smtp:
                smtp.login(self._email_user, self._email_password)
                smtp.sendmail(self._email_user, self._email_to, msg.as_string())

            logger.info(f"[通知服务] 邮件发送成功: {message.title}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("[通知服务] 邮件发送失败: SMTP 认证错误，请检查邮箱/授权码")
        except smtplib.SMTPConnectError:
            logger.error(f"[通知服务] 邮件发送失败: 无法连接 SMTP 服务器 {self._smtp_host}:{self._smtp_port}")
        except smtplib.SMTPException as exc:
            logger.error(f"[通知服务] 邮件发送失败: {exc}")
        except Exception as exc:
            logger.error(f"[通知服务] 邮件发送异常: {exc}")

        return False

    def _send_webhook(self, message: NotificationMessage) -> bool:
        """通过 HTTP POST 发送 Webhook 通知（含 HMAC-SHA256 签名）

        Args:
            message: 通知消息

        Returns:
            是否发送成功
        """
        if not self._webhook_url:
            logger.warning("[通知服务] Webhook URL 未配置，跳过发送")
            return False

        try:
            payload = message.to_dict()
            payload_json = json.dumps(payload, ensure_ascii=False)

            # 计算 HMAC-SHA256 签名
            headers = {"Content-Type": "application/json"}
            if self._webhook_secret:
                signature = hmac.new(
                    self._webhook_secret.encode("utf-8"),
                    payload_json.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                headers["X-AStock-Signature"] = signature

            response = requests.post(
                self._webhook_url,
                data=payload_json.encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()

            logger.info(f"[通知服务] Webhook 发送成功: {message.title} (HTTP {response.status_code})")
            return True

        except requests.Timeout:
            logger.error("[通知服务] Webhook 发送失败: 请求超时")
        except requests.ConnectionError:
            logger.error(f"[通知服务] Webhook 发送失败: 无法连接 {self._webhook_url}")
        except requests.HTTPError as exc:
            logger.error(f"[通知服务] Webhook 发送失败: HTTP 错误 {exc}")
        except Exception as exc:
            logger.error(f"[通知服务] Webhook 发送异常: {exc}")

        return False

    def _send_log(self, message: NotificationMessage) -> bool:
        """将通知记录到 loguru 日志

        Args:
            message: 通知消息

        Returns:
            是否记录成功（始终返回 True）
        """
        log_map = {
            "info": logger.info,
            "warning": logger.warning,
            "critical": logger.critical,
        }
        log_fn = log_map.get(message.level, logger.info)

        stock_info = f" | 股票: {message.stock_code}" if message.stock_code else ""
        log_fn(f"[通知] {message.title}{stock_info} - {message.body}")

        return True

    # ------------------------------------------------------------------
    # 私有方法 - 辅助
    # ------------------------------------------------------------------

    def _should_send(self, level: str) -> bool:
        """判断通知级别是否达到最低发送级别

        Args:
            level: 待发送通知的级别

        Returns:
            是否应该发送
        """
        msg_priority = _LEVEL_PRIORITY.get(level, 0)
        min_priority = _LEVEL_PRIORITY.get(self._min_level, 0)
        return msg_priority >= min_priority


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """获取通知服务全局单例

    Returns:
        NotificationService 实例
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
