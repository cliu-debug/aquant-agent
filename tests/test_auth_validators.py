"""认证中间件和输入验证器测试"""

import os
import sys
from pathlib import Path
import time

import pytest
import jwt

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ==================== 认证中间件测试 ====================

class TestAuthEnabled:
    """认证启用状态测试"""

    def test_auth_disabled_when_api_key_empty(self, monkeypatch):
        """API Key未设置时，认证不启用"""
        monkeypatch.delenv("ASTOCK_API_KEY", raising=False)
        # 需要重新导入以获取新的环境变量值
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "")
        assert auth_module.is_auth_enabled() is False

    def test_auth_disabled_when_api_key_is_disabled(self, monkeypatch):
        """API Key设置为disabled时，认证不启用"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "disabled")
        assert auth_module.is_auth_enabled() is False

    def test_auth_enabled_when_api_key_set(self, monkeypatch):
        """API Key设置有效值时，认证启用"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "my-secret-key")
        assert auth_module.is_auth_enabled() is True


class TestJWTToken:
    """JWT Token生成和验证测试"""

    def test_generate_jwt_token_success(self, monkeypatch):
        """正确API Key生成JWT Token"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "test-api-key")
        monkeypatch.setattr(auth_module, "JWT_SECRET", "test-secret")
        monkeypatch.setattr(auth_module, "JWT_ALGORITHM", "HS256")

        token = auth_module.generate_jwt_token("test-api-key")
        assert isinstance(token, str)
        assert len(token) > 0

        # 解码验证
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "astock-user"
        assert "iat" in payload
        assert "exp" in payload

    def test_generate_jwt_token_invalid_key(self, monkeypatch):
        """错误API Key生成Token应抛出异常"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "correct-key")

        with pytest.raises(ValueError, match="Invalid API Key"):
            auth_module.generate_jwt_token("wrong-key")

    def test_verify_token_with_api_key(self, monkeypatch):
        """使用API Key直接验证"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "test-api-key")

        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="test-api-key"
        )
        assert auth_module.verify_token(credentials) is True

    def test_verify_token_with_jwt(self, monkeypatch):
        """使用JWT Token验证"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "test-api-key")
        monkeypatch.setattr(auth_module, "JWT_SECRET", "test-secret")

        token = auth_module.generate_jwt_token("test-api-key")

        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=token
        )
        assert auth_module.verify_token(credentials) is True

    def test_verify_token_expired_jwt(self, monkeypatch):
        """过期JWT Token验证失败"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "test-api-key")
        monkeypatch.setattr(auth_module, "JWT_SECRET", "test-secret")

        # 创建已过期的Token
        payload = {
            "sub": "astock-user",
            "iat": int(time.time()) - 3600,
            "exp": int(time.time()) - 1800,  # 半小时前过期
        }
        expired_token = jwt.encode(payload, "test-secret", algorithm="HS256")

        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=expired_token
        )
        assert auth_module.verify_token(credentials) is False

    def test_verify_token_invalid_jwt(self, monkeypatch):
        """无效JWT Token验证失败"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "test-api-key")

        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid-token-string"
        )
        assert auth_module.verify_token(credentials) is False

    def test_verify_token_no_credentials(self, monkeypatch):
        """无凭证时验证失败（认证启用时）"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "test-api-key")
        assert auth_module.verify_token(None) is False

    def test_verify_token_no_credentials_auth_disabled(self, monkeypatch):
        """无凭证时验证通过（认证未启用时）"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "")
        assert auth_module.verify_token(None) is True


# ==================== 输入验证器测试 ====================

class TestValidateStockCode:
    """股票代码验证测试"""

    def test_valid_code_with_sh_suffix(self):
        """带.SH后缀的有效代码"""
        from astock_agents.web.validators import validate_stock_code
        assert validate_stock_code("600519.SH") == "600519.SH"

    def test_valid_code_with_sz_suffix(self):
        """带.SZ后缀的有效代码"""
        from astock_agents.web.validators import validate_stock_code
        assert validate_stock_code("000858.SZ") == "000858.SZ"

    def test_valid_code_with_bj_suffix(self):
        """带.BJ后缀的有效代码"""
        from astock_agents.web.validators import validate_stock_code
        assert validate_stock_code("430047.BJ") == "430047.BJ"

    def test_code_auto_append_sh(self):
        """6开头代码自动补充.SH"""
        from astock_agents.web.validators import validate_stock_code
        assert validate_stock_code("600519") == "600519.SH"

    def test_code_auto_append_sz(self):
        """0开头代码自动补充.SZ"""
        from astock_agents.web.validators import validate_stock_code
        assert validate_stock_code("000858") == "000858.SZ"

    def test_code_auto_append_sz_for_3(self):
        """3开头代码自动补充.SZ（创业板）"""
        from astock_agents.web.validators import validate_stock_code
        assert validate_stock_code("300750") == "300750.SZ"

    def test_code_auto_append_bj(self):
        """8开头代码自动补充.BJ（北交所）"""
        from astock_agents.web.validators import validate_stock_code
        assert validate_stock_code("830799") == "830799.BJ"

    def test_code_auto_append_bj_for_4(self):
        """4开头代码自动补充.BJ（北交所）"""
        from astock_agents.web.validators import validate_stock_code
        assert validate_stock_code("430047") == "430047.BJ"

    def test_code_lowercase_auto_upper(self):
        """小写后缀自动转大写"""
        from astock_agents.web.validators import validate_stock_code
        assert validate_stock_code("600519.sh") == "600519.SH"

    def test_code_with_spaces(self):
        """带空格的代码自动去除"""
        from astock_agents.web.validators import validate_stock_code
        assert validate_stock_code(" 600519 ") == "600519.SH"

    def test_empty_code(self):
        """空代码抛出异常"""
        from astock_agents.web.validators import validate_stock_code
        with pytest.raises(ValueError, match="股票代码不能为空"):
            validate_stock_code("")

    def test_invalid_code_format(self):
        """无效格式抛出异常"""
        from astock_agents.web.validators import validate_stock_code
        with pytest.raises(ValueError, match="股票代码格式无效"):
            validate_stock_code("ABC123")

    def test_code_too_short(self):
        """代码位数不足抛出异常"""
        from astock_agents.web.validators import validate_stock_code
        with pytest.raises(ValueError, match="股票代码格式无效"):
            validate_stock_code("60051")


class TestValidateQuantity:
    """交易数量验证测试"""

    def test_valid_quantity(self):
        """有效的交易数量"""
        from astock_agents.web.validators import validate_quantity
        assert validate_quantity(100) == 100
        assert validate_quantity(1000) == 1000

    def test_quantity_not_multiple_of_100(self):
        """非100整数倍抛出异常"""
        from astock_agents.web.validators import validate_quantity
        with pytest.raises(ValueError, match="100的整数倍"):
            validate_quantity(150)

    def test_quantity_zero(self):
        """数量为0抛出异常"""
        from astock_agents.web.validators import validate_quantity
        with pytest.raises(ValueError, match="必须大于0"):
            validate_quantity(0)

    def test_quantity_negative(self):
        """负数抛出异常"""
        from astock_agents.web.validators import validate_quantity
        with pytest.raises(ValueError, match="必须大于0"):
            validate_quantity(-100)


class TestValidatePrice:
    """价格验证测试"""

    def test_valid_price(self):
        """有效价格"""
        from astock_agents.web.validators import validate_price
        assert validate_price(100.0) == 100.0

    def test_price_round_to_2_decimals(self):
        """价格保留2位小数"""
        from astock_agents.web.validators import validate_price
        assert validate_price(100.456) == 100.46

    def test_price_none(self):
        """None表示市价单，直接返回"""
        from astock_agents.web.validators import validate_price
        assert validate_price(None) is None

    def test_price_zero(self):
        """价格为0抛出异常"""
        from astock_agents.web.validators import validate_price
        with pytest.raises(ValueError, match="价格必须大于0"):
            validate_price(0)

    def test_price_negative(self):
        """负数价格抛出异常"""
        from astock_agents.web.validators import validate_price
        with pytest.raises(ValueError, match="价格必须大于0"):
            validate_price(-10.5)


# ==================== API集成测试 ====================

class TestAuthAPI:
    """认证API集成测试"""

    @pytest.fixture
    def client(self, monkeypatch):
        """创建测试客户端"""
        # 确保认证启用
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "test-api-key-123")
        monkeypatch.setattr(auth_module, "JWT_SECRET", "test-jwt-secret")

        from fastapi.testclient import TestClient
        from astock_agents.web.app import app
        return TestClient(app)

    @pytest.fixture
    def client_no_auth(self, monkeypatch):
        """创建无认证的测试客户端"""
        from astock_agents.web import auth as auth_module
        monkeypatch.setattr(auth_module, "API_KEY", "")

        from fastapi.testclient import TestClient
        from astock_agents.web.app import app
        return TestClient(app)

    def test_health_check_no_auth_required(self, client):
        """健康检查不需要认证"""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_unauthorized_without_credentials(self, client):
        """未提供凭证时返回401"""
        response = client.get("/api/stocks/popular")
        assert response.status_code == 401

    def test_authorized_with_api_key_header(self, client):
        """使用X-API-Key请求头认证成功"""
        response = client.get(
            "/api/stocks/popular",
            headers={"X-API-Key": "test-api-key-123"},
        )
        assert response.status_code == 200

    def test_authorized_with_bearer_api_key(self, client):
        """使用Bearer Token方式传入API Key认证成功"""
        response = client.get(
            "/api/stocks/popular",
            headers={"Authorization": "Bearer test-api-key-123"},
        )
        assert response.status_code == 200

    def test_authorized_with_jwt_token(self, client):
        """使用JWT Token认证成功"""
        from astock_agents.web import auth as auth_module
        token = auth_module.generate_jwt_token("test-api-key-123")

        response = client.get(
            "/api/stocks/popular",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_get_token_success(self, client):
        """获取JWT Token成功"""
        response = client.post(
            "/api/auth/token",
            json={"api_key": "test-api-key-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "expires_in" in data
        assert data["expires_in"] == 86400

    def test_get_token_invalid_key(self, client):
        """使用错误API Key获取Token失败"""
        response = client.post(
            "/api/auth/token",
            json={"api_key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_no_auth_all_requests(self, client_no_auth):
        """认证未启用时所有请求直接通过"""
        response = client_no_auth.get("/api/stocks/popular")
        assert response.status_code == 200

    def test_static_files_no_auth_required(self, client):
        """静态文件不需要认证"""
        response = client.get("/static/index.html")
        # 可能返回404（文件不存在），但不应该是401
        assert response.status_code != 401
