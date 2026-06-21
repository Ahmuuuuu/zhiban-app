"""
ServiceError 异常类测试

测试目标：backend/src/utils/exceptions.py
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestServiceError:
    def test_init_with_detail(self):
        from backend.src.utils.exceptions import ServiceError
        err = ServiceError("资源不存在")
        assert err.detail == "资源不存在"

    def test_is_exception_subclass(self):
        from backend.src.utils.exceptions import ServiceError
        assert issubclass(ServiceError, Exception)

    def test_can_be_raised_and_caught(self):
        from backend.src.utils.exceptions import ServiceError
        with pytest.raises(ServiceError) as ctx:
            raise ServiceError("测试错误")
        assert ctx.value.detail == "测试错误"

    def test_str_representation(self):
        from backend.src.utils.exceptions import ServiceError
        err = ServiceError("参数错误")
        assert "参数错误" in str(err)

    def test_catch_as_generic_exception(self):
        """ServiceError 能被通用 except Exception 捕获"""
        from backend.src.utils.exceptions import ServiceError
        try:
            raise ServiceError("test")
        except Exception as e:
            assert isinstance(e, ServiceError)
            assert e.detail == "test"
