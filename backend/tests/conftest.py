"""
测试配置 & 公共 Fixture

pytest 运行时会自动加载这个文件，里面定义的 fixture 可以被所有测试文件使用。
"""
import asyncio
import os
import sys
import pytest
from pathlib import Path

# 确保能 import backend.src.xxx
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# 设置测试环境变量（避免读取真实 .env）
os.environ["JWT_KEY"] = "test-jwt-secret-key-for-testing-only"
os.environ["ALGORITHM"] = "HS256"


@pytest.fixture(scope="session")
def event_loop():
    """整个测试 session 共享一个事件循环（async 测试需要）"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_audio_dir(tmp_path):
    """临时音频目录 fixture，每次测试自动清理"""
    d = tmp_path / "audio"
    d.mkdir()
    return d
