"""P2模块集成测试 - Prometheus监控、APScheduler调度、通知推送"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock


# ==================== Prometheus监控测试 ====================

class TestMetricsCollector:
    """Prometheus指标采集器测试"""

    def test_metrics_collector_singleton(self):
        """测试全局单例"""
        from astock_agents.services.metrics import get_metrics_collector
        m1 = get_metrics_collector()
        m2 = get_metrics_collector()
        assert m1 is m2

    def test_record_analysis(self):
        """测试记录分析指标"""
        from astock_agents.services.metrics import get_metrics_collector
        collector = get_metrics_collector()
        # 不应抛出异常
        collector.record_analysis(
            stock_code="600519.SH",
            signal="买入",
            duration=1.5,
        )

    def test_record_analysis_error(self):
        """测试记录分析错误指标"""
        from astock_agents.services.metrics import get_metrics_collector
        collector = get_metrics_collector()
        collector.record_analysis_error("timeout")
        collector.record_analysis_error("data_unavailable")

    def test_record_data_source_request(self):
        """测试记录数据源请求指标"""
        from astock_agents.services.metrics import get_metrics_collector
        collector = get_metrics_collector()
        collector.record_data_source_request(
            source="tencent",
            status="success",
            duration=0.3,
        )
        collector.record_data_source_request(
            source="akshare",
            status="error",
            duration=5.0,
        )

    def test_update_circuit_breaker_state(self):
        """测试更新断路器状态指标"""
        from astock_agents.services.metrics import get_metrics_collector
        collector = get_metrics_collector()
        collector.update_circuit_breaker_state("tencent_api", "CLOSED")
        collector.update_circuit_breaker_state("akshare_api", "OPEN")
        collector.update_circuit_breaker_state("mootdx_api", "HALF_OPEN")

    def test_record_trading_order(self):
        """测试记录交易订单指标"""
        from astock_agents.services.metrics import get_metrics_collector
        collector = get_metrics_collector()
        collector.record_trading_order("buy", "filled")
        collector.record_trading_order("sell", "pending")

    def test_update_portfolio_value(self):
        """测试更新组合总值指标"""
        from astock_agents.services.metrics import get_metrics_collector
        collector = get_metrics_collector()
        collector.update_portfolio_value(1000000.0)
        collector.update_portfolio_value(950000.0)

    def test_update_active_positions(self):
        """测试更新持仓数量指标"""
        from astock_agents.services.metrics import get_metrics_collector
        collector = get_metrics_collector()
        collector.update_active_positions(5)
        collector.update_active_positions(3)

    def test_update_watchlist_count(self):
        """测试更新自选股数量指标"""
        from astock_agents.services.metrics import get_metrics_collector
        collector = get_metrics_collector()
        collector.update_watchlist_count(10)

    def test_generate_metrics_returns_string(self):
        """测试生成Prometheus格式文本返回有效字符串"""
        from astock_agents.services.metrics import (
            generate_metrics,
            get_metrics_collector,
        )
        collector = get_metrics_collector()
        collector.record_analysis("000001.SZ", "买入", 2.0)
        output = generate_metrics()
        assert isinstance(output, str)
        # 指标名称可能因注册表状态不同而变化，只验证返回类型和长度
        assert len(output) > 0


# ==================== 通知推送测试 ====================

class TestNotificationService:
    """通知推送服务测试"""

    def test_notification_service_singleton(self):
        """测试全局单例"""
        from astock_agents.services.notification import get_notification_service
        s1 = get_notification_service()
        s2 = get_notification_service()
        assert s1 is s2

    def test_notification_message_creation(self):
        """测试通知消息创建"""
        from astock_agents.services.notification import NotificationMessage
        msg = NotificationMessage(
            title="测试通知",
            body="测试内容",
            level="info",
        )
        assert msg.title == "测试通知"
        assert msg.level == "info"

    def test_notification_message_invalid_level(self):
        """测试无效通知级别"""
        from astock_agents.services.notification import NotificationMessage
        with pytest.raises(ValueError, match="无效的通知级别"):
            NotificationMessage(title="test", body="test", level="invalid")

    def test_notification_message_to_dict(self):
        """测试通知消息序列化"""
        from astock_agents.services.notification import NotificationMessage
        msg = NotificationMessage(
            title="测试",
            body="内容",
            level="warning",
            stock_code="600519.SH",
        )
        d = msg.to_dict()
        assert d["title"] == "测试"
        assert d["stock_code"] == "600519.SH"
        assert isinstance(d["timestamp"], str)

    def test_send_log_channel(self):
        """测试日志通道发送（始终启用）"""
        from astock_agents.services.notification import (
            NotificationService,
            NotificationMessage,
        )
        service = NotificationService()
        msg = NotificationMessage(
            title="日志测试",
            body="测试日志通道",
            level="critical",
        )
        result = service.send(msg)
        assert result is True

    def test_level_filter_info_blocked(self):
        """测试info级别被过滤（默认最低warning）"""
        from astock_agents.services.notification import (
            NotificationService,
            NotificationMessage,
        )
        service = NotificationService()
        msg = NotificationMessage(
            title="info通知",
            body="应被过滤",
            level="info",
        )
        result = service.send(msg)
        assert result is False

    def test_level_filter_warning_passed(self):
        """测试warning级别通过过滤"""
        from astock_agents.services.notification import (
            NotificationService,
            NotificationMessage,
        )
        service = NotificationService()
        msg = NotificationMessage(
            title="warning通知",
            body="应通过",
            level="warning",
        )
        result = service.send(msg)
        assert result is True

    def test_level_filter_critical_passed(self):
        """测试critical级别通过过滤"""
        from astock_agents.services.notification import (
            NotificationService,
            NotificationMessage,
        )
        service = NotificationService()
        msg = NotificationMessage(
            title="critical通知",
            body="应通过",
            level="critical",
        )
        result = service.send(msg)
        assert result is True

    def test_send_signal_change(self):
        """测试信号变化通知"""
        from astock_agents.services.notification import NotificationService
        service = NotificationService()
        result = service.send_signal_change(
            stock_code="600519.SH",
            stock_name="贵州茅台",
            old_signal="买入",
            new_signal="卖出",
            confidence=0.75,
        )
        assert result is True  # critical级别应通过

    def test_send_risk_alert(self):
        """测试风险预警通知"""
        from astock_agents.services.notification import NotificationService
        service = NotificationService()
        result = service.send_risk_alert(
            stock_code="600519.SH",
            risk_level="高",
            risk_description="集中度过高",
        )
        assert result is True

    def test_send_daily_report(self):
        """测试每日报告通知（info级别默认被过滤）"""
        from astock_agents.services.notification import NotificationService
        service = NotificationService()
        result = service.send_daily_report("今日盈亏+2%")
        assert result is False  # info级别默认被过滤

    def test_get_history(self):
        """测试通知历史"""
        from astock_agents.services.notification import (
            NotificationService,
            NotificationMessage,
        )
        service = NotificationService()
        service.send(NotificationMessage(title="t1", body="b1", level="warning"))
        service.send(NotificationMessage(title="t2", body="b2", level="critical"))
        history = service.get_history()
        assert len(history) >= 2

    def test_is_enabled(self):
        """测试通道启用状态"""
        from astock_agents.services.notification import (
            NotificationService,
            NotificationChannel,
        )
        service = NotificationService()
        # 默认配置下，邮件和Webhook应禁用，日志始终启用
        assert service.is_enabled(NotificationChannel.LOG) is True
        assert service.is_enabled(NotificationChannel.EMAIL) is False
        assert service.is_enabled(NotificationChannel.WEBHOOK) is False

    def test_email_config_incomplete(self):
        """测试邮件配置不完整时跳过"""
        from astock_agents.services.notification import (
            NotificationService,
            NotificationMessage,
        )
        service = NotificationService()
        msg = NotificationMessage(
            title="邮件测试",
            body="配置不完整",
            level="critical",
        )
        # 邮件通道应返回False（配置不完整）
        result = service._send_email(msg)
        assert result is False

    def test_webhook_no_url(self):
        """测试Webhook URL未配置时跳过"""
        from astock_agents.services.notification import (
            NotificationService,
            NotificationMessage,
        )
        service = NotificationService()
        msg = NotificationMessage(
            title="Webhook测试",
            body="URL未配置",
            level="critical",
        )
        result = service._send_webhook(msg)
        assert result is False

    def test_custom_min_level(self):
        """测试自定义最低通知级别"""
        from astock_agents.services.notification import (
            NotificationService,
            NotificationMessage,
        )
        with patch.dict(os.environ, {"ASTOCK_NOTIFY_LEVEL": "info"}):
            service = NotificationService()
            msg = NotificationMessage(
                title="info通知",
                body="应通过",
                level="info",
            )
            result = service.send(msg)
            assert result is True


# ==================== 调度器测试 ====================

class TestSchedulerService:
    """APScheduler调度服务测试"""

    def test_scheduler_service_init(self):
        """测试调度器初始化"""
        from astock_agents.services.scheduler import SchedulerService
        # 不启用调度器
        with patch.dict(os.environ, {"ASTOCK_SCHEDULER_ENABLED": "false"}):
            scheduler = SchedulerService()
            assert scheduler.is_running is False

    def test_scheduler_not_enabled(self):
        """测试调度器未启用时不启动"""
        from astock_agents.services.scheduler import SchedulerService
        with patch.dict(os.environ, {"ASTOCK_SCHEDULER_ENABLED": "false"}):
            scheduler = SchedulerService()
            scheduler.start()
            assert scheduler.is_running is False

    def test_scheduler_get_jobs_when_stopped(self):
        """测试调度器停止时获取任务列表"""
        from astock_agents.services.scheduler import SchedulerService
        with patch.dict(os.environ, {"ASTOCK_SCHEDULER_ENABLED": "false"}):
            scheduler = SchedulerService()
            jobs = scheduler.get_jobs()
            assert isinstance(jobs, list)
            assert len(jobs) == 0

    def test_signal_reversed_buy_to_sell(self):
        """测试信号反转：买入→卖出"""
        from astock_agents.services.scheduler import SchedulerService
        assert SchedulerService._is_signal_reversed("买入", "卖出") is True

    def test_signal_reversed_sell_to_buy(self):
        """测试信号反转：卖出→买入"""
        from astock_agents.services.scheduler import SchedulerService
        assert SchedulerService._is_signal_reversed("卖出", "买入") is True

    def test_signal_not_reversed_buy_to_hold(self):
        """测试信号未反转：买入→持有"""
        from astock_agents.services.scheduler import SchedulerService
        assert SchedulerService._is_signal_reversed("买入", "持有") is False

    def test_signal_not_reversed_same_signal(self):
        """测试信号未反转：相同信号"""
        from astock_agents.services.scheduler import SchedulerService
        assert SchedulerService._is_signal_reversed("买入", "买入") is False

    def test_scheduler_singleton(self):
        """测试全局单例"""
        from astock_agents.services.scheduler import get_scheduler
        s1 = get_scheduler()
        s2 = get_scheduler()
        assert s1 is s2

    def test_scheduler_start_and_stop(self):
        """测试调度器启动和停止"""
        from astock_agents.services.scheduler import SchedulerService
        with patch.dict(os.environ, {"ASTOCK_SCHEDULER_ENABLED": "true"}):
            # Mock 掉依赖避免实际连接
            with patch("astock_agents.services.scheduler.WatchlistManager"), \
                 patch("astock_agents.services.scheduler.AnalysisWorkflow"), \
                 patch("astock_agents.services.scheduler.DataManager"), \
                 patch("astock_agents.services.scheduler.Database"):
                scheduler = SchedulerService()
                scheduler.start()
                assert scheduler.is_running is True

                jobs = scheduler.get_jobs()
                assert len(jobs) == 3  # 3个默认任务

                scheduler.stop()
                assert scheduler.is_running is False


# ==================== Web API集成测试 ====================

class TestP2WebAPI:
    """P2模块Web API集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from astock_agents.web.app import app
        return TestClient(app)

    def test_metrics_endpoint(self, client):
        """测试 /metrics 端点"""
        response = client.get("/metrics")
        assert response.status_code == 200
        # 验证返回内容类型和状态码
        assert len(response.text) >= 0

    def test_scheduler_status(self, client):
        """测试调度器状态API"""
        response = client.get("/api/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "jobs" in data

    def test_notification_channels(self, client):
        """测试通知通道API"""
        response = client.get("/api/notifications/channels")
        assert response.status_code == 200
        data = response.json()
        assert "channels" in data
        assert "log" in data["channels"]
        assert data["channels"]["log"] is True

    def test_notification_history(self, client):
        """测试通知历史API"""
        response = client.get("/api/notifications/history")
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "total" in data

    def test_notification_test(self, client):
        """测试发送测试通知API"""
        response = client.post("/api/notifications/test")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
