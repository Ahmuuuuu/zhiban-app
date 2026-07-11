"""
JWT 工具函数单元测试

测试目标：backend/src/utils/jwt.py
覆盖范围：
- Token 创建与解码（正常流程）
- 过期时间验证
- 无效/篡改 Token 检测
- Role 字段正确性
"""
import time
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

from backend.src.utils.jwt import create_access_token, decode_token


class TestCreateAccessToken:
    """Token 创建测试"""

    def test_returns_string(self):
        """Token 应该是字符串类型"""
        token = create_access_token(user_id=1)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_contains_three_parts(self):
        """JWT 格式: header.payload.signature (三段用 . 分隔)"""
        token = create_access_token(user_id=42)
        parts = token.split(".")
        assert len(parts) == 3

    def test_payload_has_correct_user_id(self):
        """Payload 中的 sub 字段应该等于传入的 user_id"""
        token = create_access_token(user_id=100)
        payload = decode_token(token)
        assert payload["sub"] == "100"

    def test_default_role_is_user(self):
        """默认 role 应该是 'user'"""
        token = create_access_token(user_id=1)
        payload = decode_token(token)
        assert payload.get("role") == "user"

    def test_custom_role(self):
        """可以自定义 role"""
        token = create_access_token(user_id=1, role="admin")
        payload = decode_token(token)
        assert payload["role"] == "admin"

    def test_expiry_7_days_later(self):
        """Token 默认 7 天后过期"""
        token = create_access_token(user_id=1)
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        # 过期时间应该在 6~8 天之间（留点余量）
        diff = exp - now
        assert timedelta(days=6) < diff < timedelta(days=8)

    def test_iat_field_present(self):
        """Payload 应包含 iat (签发时间) 字段"""
        token = create_access_token(user_id=1)
        payload = decode_token(token)
        assert "iat" in payload

    def test_different_users_get_different_tokens(self):
        """不同用户应该得到不同的 Token"""
        t1 = create_access_token(user_id=1)
        t2 = create_access_token(user_id=2)
        assert t1 != t2


class TestDecodeToken:
    """Token 解码测试"""

    def test_decode_valid_token(self):
        """能解码自己生成的合法 Token"""
        token = create_access_token(user_id=99)
        payload = decode_token(token)
        assert payload["sub"] == "99"

    def test_decode_tampered_token_raises(self):
        """篡改过的 Token 应该抛出 JWTError"""
        token = create_access_token(user_id=1)
        # 修改 Payload 部分
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "xxxxx"  # 改几个字符
        tampered = ".".join(parts)

        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_decode_empty_string_raises(self):
        """空字符串应该抛出异常"""
        with pytest.raises(JWTError):
            decode_token("")

    def test_decode_random_string_raises(self):
        """随机字符串不是合法 JWT"""
        with pytest.raises(JWTError):
            decode_token("this.is.not.a.valid.token")

    def test_decode_with_wrong_key_raises(self):
        """用错误的密钥签名 → 解码失败"""
        # 用另一个密钥编码
        fake_payload = {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        wrong_key_token = jwt.encode(fake_payload, "wrong-secret-key", "HS256")

        with pytest.raises(JWTError):
            decode_token(wrong_key_token)


class TestTokenExpiry:
    """过期相关测试"""

    def test_expired_token_raises(self):
        """已过期的 Token 应该解码失败"""
        # 手工构造一个已过期的 Token
        expired_payload = {
            "sub": "1",
            "role": "user",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),  # 1秒前过期
            "iat": datetime.now(timezone.utc) - timedelta(days=7),
        }
        expired_token = jwt.encode(expired_payload, os.getenv("JWT_KEY"), "HS256")

        with pytest.raises(JWTError, match="expired"):
            decode_token(expired_token)

    def test_not_yet_valid_token(self):
        """未到生效时间的 Token（如果有 nbf 声明）"""
        future_payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            "nbf": datetime.now(timezone.utc) + timedelta(days=1),  # 明天生效
        }
        future_token = jwt.encode(future_payload, os.getenv("JWT_KEY"), "HS256")

        with pytest.raises(JWTError):
            decode_token(future_token)


# 需要在文件顶部导入 os
import os
