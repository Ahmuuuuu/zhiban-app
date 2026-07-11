"""
外部视频搜索服务单元测试

测试目标：backend/src/service/video_service.py
覆盖范围：
- 工具函数（BVID 提取、格式化、HTML 清理）
- _build_video_item 构建逻辑
- search() 搜索编排（mock httpx）
"""
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from backend.src.service.video_service import (
    _extract_bvid,
    _clean_title,
    _strip_em,
    _format_duration,
    _format_view_count,
    _duration_to_seconds,
    _ensure_https,
    _build_video_item,
    _search_bilibili_api,
    _search_bilibili_html,
    _enrich_detail,
    ExternalVideoService,
)


# ═══════════════════════════════════════════════
#  _extract_bvid
# ═══════════════════════════════════════════════

class TestExtractBvid:
    def test_standard_bvid(self):
        """标准 B站 BV 号"""
        url = "https://www.bilibili.com/video/BV1xx411c7mD"
        assert _extract_bvid(url) == "BV1xx411c7mD"

    def test_bvid_with_params(self):
        """带查询参数的 URL"""
        url = "https://www.bilibili.com/video/BV1GJ411x7FH?p=2&spm_id_from=333.788"
        assert _extract_bvid(url) == "BV1GJ411x7FH"

    def test_short_url(self):
        """不带协议的 URL"""
        url = "//www.bilibili.com/video/BV1eY411Z7TY"
        assert _extract_bvid(url) == "BV1eY411Z7TY"

    def test_no_bvid(self):
        """不包含 BVID 的 URL"""
        url = "https://www.bilibili.com/"
        assert _extract_bvid(url) is None

    def test_empty_string(self):
        assert _extract_bvid("") is None

    def test_arcurl_format(self):
        """arcurl 格式"""
        url = "https://www.bilibili.com/video/BV1Qa4y1s7QG"
        assert _extract_bvid(url) == "BV1Qa4y1s7QG"


# ═══════════════════════════════════════════════
#  _clean_title / _strip_em
# ═══════════════════════════════════════════════

class TestCleanTitle:
    def test_remove_em_tag(self):
        """去掉 <em class=\"keyword\"> 标签"""
        raw = "线性代数<em class=\"keyword\">矩阵</em>教学"
        assert _clean_title(raw) == "线性代数矩阵教学"

    def test_no_tags(self):
        raw = "线性代数教程"
        assert _clean_title(raw) == raw

    def test_empty_string(self):
        assert _clean_title("") == ""


class TestStripEm:
    def test_remove_em(self):
        assert _strip_em("这是<em>重点</em>内容") == "这是重点内容"

    def test_no_em(self):
        text = "普通描述文本"
        assert _strip_em(text) == text


# ═══════════════════════════════════════════════
#  _duration_to_seconds
# ═══════════════════════════════════════════════

class TestDurationToSeconds:
    def test_none(self):
        assert _duration_to_seconds(None) is None

    def test_int_passthrough(self):
        """整数秒直接返回"""
        assert _duration_to_seconds(334) == 334

    def test_mmss_string(self):
        """MM:SS 格式"""
        assert _duration_to_seconds("293:4") == 293 * 60 + 4

    def test_hhmmss_string(self):
        """HH:MM:SS 格式"""
        assert _duration_to_seconds("1:01:01") == 3661

    def test_numeric_string(self):
        """纯数字字符串"""
        assert _duration_to_seconds("1200") == 1200

    def test_empty_string(self):
        assert _duration_to_seconds("") is None


# ═══════════════════════════════════════════════
#  _ensure_https
# ═══════════════════════════════════════════════

class TestEnsureHttps:
    def test_already_https(self):
        assert _ensure_https("https://example.com") == "https://example.com"

    def test_protocol_relative(self):
        assert _ensure_https("//i0.hdslb.com/pic.jpg") == "https://i0.hdslb.com/pic.jpg"

    def test_http(self):
        assert _ensure_https("http://example.com") == "http://example.com"

    def test_empty(self):
        assert _ensure_https("") == ""


# ═══════════════════════════════════════════════
#  _format_duration
# ═══════════════════════════════════════════════

class TestFormatDuration:
    def test_none(self):
        assert _format_duration(None) == ""

    def test_seconds_only(self):
        assert _format_duration(45) == "0:45"

    def test_minutes(self):
        assert _format_duration(125) == "2:05"

    def test_hours(self):
        assert _format_duration(3661) == "1:01:01"

    def test_exact_hour(self):
        assert _format_duration(3600) == "1:00:00"


# ═══════════════════════════════════════════════
#  _format_view_count
# ═══════════════════════════════════════════════

class TestFormatViewCount:
    def test_none(self):
        assert _format_view_count(None) == ""

    def test_small_number(self):
        assert _format_view_count(999) == "999"

    def test_wan(self):
        assert _format_view_count(10000) == "1.0万"

    def test_wan_with_decimals(self):
        assert _format_view_count(1234567) == "123.5万"

    def test_zero(self):
        assert _format_view_count(0) == "0"


# ═══════════════════════════════════════════════
#  _build_video_item
# ═══════════════════════════════════════════════

class TestBuildVideoItem:
    def test_full_item(self):
        """标准 API 响应条目（search/all/v2 格式）"""
        item = {
            "bvid": "BV1xx411c7mD",
            "title": "线性代数<em class=\"keyword\">矩阵</em>",
            "arcurl": "https://www.bilibili.com/video/BV1xx411c7mD",
            "description": "详细讲解<em>矩阵乘法</em>",
            "pic": "//i0.hdslb.com/bfs/archive/abc.jpg",
            "duration": "3661",
            "author": "宋浩老师",
            "play": 1234567,
        }
        result = _build_video_item(item)
        assert result is not None
        assert result["bvid"] == "BV1xx411c7mD"
        assert result["title"] == "线性代数矩阵"
        assert result["source"] == "bilibili"
        assert result["source_label"] == "B站"
        assert result["embed_url"] == "//player.bilibili.com/player.html?bvid=BV1xx411c7mD&autoplay=0&high_quality=1"
        assert result["cover_url"] == "https://i0.hdslb.com/bfs/archive/abc.jpg"
        assert result["duration"] == 3661
        assert result["author"] == "宋浩老师"
        assert result["view_count"] == 1234567

    def test_missing_arcurl_fallback(self):
        """arcurl 缺失时用 bvid 拼 page_url"""
        item = {"bvid": "BV1GJ411x7FH"}
        result = _build_video_item(item)
        assert result is not None
        assert result["page_url"] == "https://www.bilibili.com/video/BV1GJ411x7FH"

    def test_no_bvid(self):
        """没有 bvid 时返回 None"""
        assert _build_video_item({"title": "no bvid"}) is None

    def test_arcurl_with_bvid(self):
        """从 arcurl 提取 bvid"""
        item = {"arcurl": "https://www.bilibili.com/video/BV1Qa4y1s7QG"}
        result = _build_video_item(item)
        assert result is not None
        assert result["bvid"] == "BV1Qa4y1s7QG"


# ═══════════════════════════════════════════════
#  _search_bilibili_api（mock httpx）
# ═══════════════════════════════════════════════

class TestSearchBilibiliApi:
    """mock httpx.AsyncClient 测试 B站 search/all/v2"""

    @patch("backend.src.service.video_service.httpx.AsyncClient")
    async def test_success(self, mock_client_cls):
        """API 返回正常数据（search/all/v2 分节格式）"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": 0,
            "data": {
                "result": [
                    {
                        "result_type": "video",
                        "data": [
                            {
                                "bvid": "BV1xx411c7mD",
                                "title": "线性代数教程",
                                "arcurl": "https://www.bilibili.com/video/BV1xx411c7mD",
                                "description": "优质教学视频",
                                "pic": "//i0.hdslb.com/bfs/archive/a.jpg",
                                "duration": "1200",
                                "author": "宋浩老师",
                                "play": 50000,
                            }
                        ],
                    }
                ]
            },
        }
        mock_client.get.return_value = mock_resp

        result = await _search_bilibili_api("线性代数", max_results=3)
        assert len(result) == 1
        assert result[0]["bvid"] == "BV1xx411c7mD"
        assert result[0]["title"] == "线性代数教程"

    @patch("backend.src.service.video_service.httpx.AsyncClient")
    async def test_api_error_code(self, mock_client_cls):
        """API 返回错误 code"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": -1, "message": "请求太频繁"}
        mock_client.get.return_value = mock_resp

        result = await _search_bilibili_api("线性代数")
        assert result == []

    @patch("backend.src.service.video_service.httpx.AsyncClient")
    async def test_http_error(self, mock_client_cls):
        """HTTP 非 200"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_client.get.return_value = mock_resp

        result = await _search_bilibili_api("线性代数")
        assert result == []

    @patch("backend.src.service.video_service.httpx.AsyncClient")
    async def test_request_exception(self, mock_client_cls):
        """网络异常"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("连接超时")

        result = await _search_bilibili_api("线性代数")
        assert result == []


# ═══════════════════════════════════════════════
#  _search_bilibili_html（mock httpx）
# ═══════════════════════════════════════════════

class TestSearchBilibiliHtml:
    """mock httpx 测试兜底 HTML 搜索"""

    @patch("backend.src.service.video_service.httpx.AsyncClient")
    async def test_success(self, mock_client_cls):
        """HTML 提取 BVID + 详情 API 补充信息"""
        # 两次 AsyncClient() 调用：搜索页 → 详情 API
        search_client = AsyncMock()
        detail_client = AsyncMock()

        instances = [
            MagicMock(__aenter__=AsyncMock(return_value=search_client)),
            MagicMock(__aenter__=AsyncMock(return_value=detail_client)),
        ]
        mock_client_cls.side_effect = iter(instances)

        # 搜索页返回含 BVID 的 HTML
        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.text = "<html>BV1eY411Z7TY BV1xx411c7mD</html>"
        search_client.get.return_value = search_resp

        # 详情 API 响应
        detail_resp = MagicMock()
        detail_resp.status_code = 200
        detail_resp.json.return_value = {
            "code": 0,
            "data": {
                "bvid": "BV1eY411Z7TY",
                "title": "高等数学",
                "pic": "https://i0.hdslb.com/bfs/archive/b.jpg",
                "duration": 1800,
                "owner": {"name": "张宇老师"},
                "stat": {"view": 200000},
                "desc": "高等数学教学",
            },
        }
        detail_client.get.return_value = detail_resp

        result = await _search_bilibili_html("高等数学", max_results=3)
        # HTML 中有 2 个 BVID，各返回一个结果
        assert len(result) == 2
        assert result[0]["bvid"] == "BV1eY411Z7TY"
        assert result[0]["title"] == "高等数学"
        assert result[0]["author"] == "张宇老师"

    @patch("backend.src.service.video_service.httpx.AsyncClient")
    async def test_no_bvid_in_html(self, mock_client_cls):
        """HTML 中没有 BVID"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><div>no video here</div></html>"
        mock_client.get.return_value = mock_resp

        result = await _search_bilibili_html("高等数学")
        assert result == []

    @patch("backend.src.service.video_service.httpx.AsyncClient")
    async def test_http_error(self, mock_client_cls):
        """搜索页 404"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client.get.return_value = mock_resp

        result = await _search_bilibili_html("高等数学")
        assert result == []


# ═══════════════════════════════════════════════
#  _enrich_detail（mock httpx）
# ═══════════════════════════════════════════════

class TestEnrichDetail:
    @patch("backend.src.service.video_service.httpx.AsyncClient")
    async def test_skip_if_already_complete(self, mock_client_cls):
        """已有封面和时长时跳过 API 调用"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        video = {
            "bvid": "BV1xx411c7mD",
            "cover_url": "https://example.com/cover.jpg",
            "duration": 1200,
        }
        result = await _enrich_detail([video])
        mock_client.get.assert_not_called()
        assert result[0]["cover_url"] == "https://example.com/cover.jpg"
        assert result[0]["duration"] == 1200

    @patch("backend.src.service.video_service.httpx.AsyncClient")
    async def test_enrich_missing_fields(self, mock_client_cls):
        """补充缺失的字段"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": 0,
            "data": {
                "pic": "https://i0.hdslb.com/bfs/archive/c.jpg",
                "duration": 900,
                "owner": {"name": "李永乐老师"},
                "stat": {"view": 888888},
                "desc": "详细讲解",
                "title": "概率论",
            },
        }
        mock_client.get.return_value = mock_resp

        video = {"bvid": "BV1xx411c7mD"}
        result = await _enrich_detail([video])
        assert result[0]["cover_url"] == "https://i0.hdslb.com/bfs/archive/c.jpg"
        assert result[0]["duration"] == 900
        assert result[0]["author"] == "李永乐老师"
        assert result[0]["view_count"] == 888888


# ═══════════════════════════════════════════════
#  ExternalVideoService.search（完整编排）
# ═══════════════════════════════════════════════

class TestExternalVideoServiceSearch:
    @patch("backend.src.service.video_service._search_bilibili_api")
    @patch("backend.src.service.video_service._enrich_detail")
    async def test_api_success(self, mock_enrich, mock_api):
        """API 命中 → 不走 HTML 兜底"""
        mock_api.return_value = [{"bvid": "BV1xx411c7mD", "source": "bilibili"}]
        mock_enrich.return_value = [{"bvid": "BV1xx411c7mD", "source": "bilibili", "cover_url": "x.jpg"}]

        result = await ExternalVideoService.search("线性代数")
        assert len(result) == 1
        mock_api.assert_called_once()
        mock_enrich.assert_called_once()

    @patch("backend.src.service.video_service._search_bilibili_api")
    @patch("backend.src.service.video_service._search_bilibili_html")
    @patch("backend.src.service.video_service._enrich_detail")
    async def test_api_empty_fallback_html(self, mock_enrich, mock_html, mock_api):
        """API 无结果 → 走 HTML 兜底"""
        mock_api.return_value = []
        mock_html.return_value = [{"bvid": "BV1eY411Z7TY", "source": "bilibili"}]
        mock_enrich.return_value = [{"bvid": "BV1eY411Z7TY", "source": "bilibili", "cover_url": "y.jpg"}]

        result = await ExternalVideoService.search("高等数学")
        assert len(result) == 1
        mock_api.assert_called_once()
        mock_html.assert_called_once()

    @patch("backend.src.service.video_service._search_bilibili_api")
    @patch("backend.src.service.video_service._search_bilibili_html")
    async def test_both_empty(self, mock_html, mock_api):
        """两个来源都空"""
        mock_api.return_value = []
        mock_html.return_value = []

        result = await ExternalVideoService.search("不存在的内容")
        assert result == []

    @patch("backend.src.service.video_service._search_bilibili_api")
    @patch("backend.src.service.video_service._search_bilibili_html")
    async def test_max_results_respected(self, mock_html, mock_api):
        """返回数量不超过 max_results"""
        mock_api.return_value = [{"bvid": f"BV1{i:010d}", "source": "bilibili"} for i in range(5)]

        result = await ExternalVideoService.search("python", max_results=2)
        assert len(result) == 2


# ═══════════════════════════════════════════════
#  ExternalVideoService.search_and_save（mock DB）
# ═══════════════════════════════════════════════

class TestExternalVideoServiceSearchAndSave:
    @patch("backend.src.service.video_service.User.filter")
    @patch("backend.src.service.video_service.ExternalVideoService.search")
    @patch("backend.src.service.video_service.GeneratedResource.create")
    async def test_success(self, mock_create, mock_search, mock_user_filter):
        """搜索并保存"""
        qs = AsyncMock()
        qs.first = AsyncMock(return_value=AsyncMock())
        mock_user_filter.return_value = qs

        mock_search.return_value = [
            {
                "bvid": "BV1xx411c7mD",
                "title": "线性代数",
                "page_url": "https://www.bilibili.com/video/BV1xx411c7mD",
                "description": "教学视频",
                "source": "bilibili",
                "source_label": "B站",
                "embed_url": "//player.bilibili.com/player.html?bvid=BV1xx411c7mD",
                "cover_url": "https://example.com/cover.jpg",
                "duration": 1200,
                "author": "宋浩老师",
                "view_count": 50000,
            }
        ]

        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.topic = "线性代数"
        mock_record.resource_type = "external_video"
        mock_record.file_url = "https://www.bilibili.com/video/BV1xx411c7mD"
        mock_record.cover_url = "https://example.com/cover.jpg"
        mock_record.created_at = "2026-06-23 12:00:00"
        mock_create.return_value = mock_record

        result = await ExternalVideoService.search_and_save("线性代数", 1)
        assert len(result) == 1
        assert result[0]["resource_id"] == 1
        assert result[0]["title"] == "线性代数"
        assert result[0]["source"] == "B站"
        mock_create.assert_called_once()

    @patch("backend.src.service.video_service.User.filter")
    @patch("backend.src.service.video_service.ExternalVideoService.search")
    async def test_no_results(self, mock_search, mock_user_filter):
        """搜索无结果"""
        qs = AsyncMock()
        qs.first = AsyncMock(return_value=AsyncMock())
        mock_user_filter.return_value = qs
        mock_search.return_value = []

        result = await ExternalVideoService.search_and_save("不存在的内容", 1)
        assert result == []

    @patch("backend.src.service.video_service.User.filter")
    async def test_user_not_found(self, mock_user_filter):
        """用户不存在"""
        qs = AsyncMock()
        qs.first = AsyncMock(return_value=None)
        mock_user_filter.return_value = qs

        with pytest.raises(ValueError, match="用户不存在"):
            await ExternalVideoService.search_and_save("线性代数", 999)
