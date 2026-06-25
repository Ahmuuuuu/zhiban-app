"""外部视频搜索服务 — 搜索 B站教学视频并保存为资源"""
import json
import logging
import re
import httpx
from backend.src.models.usermodel import User
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.notification_model import Notification
from backend.src.utils.redis_client import cache_get, cache_set, _cache_key, _text_hash

logger = logging.getLogger(__name__)

_BVID_PATTERN  = re.compile(r"BV[a-zA-Z0-9]{10,}")
_BILI_EMBED_TPL = "//player.bilibili.com/player.html?bvid={bvid}&autoplay=0&high_quality=1"

# B站搜索 API（无需 key，公开接口）
_BILI_SEARCH_API = "https://api.bilibili.com/x/web-interface/search/all/v2"
_BILI_VIDEO_API  = "https://api.bilibili.com/x/web-interface/view?bvid={bvid}"

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}


async def _search_bilibili_api(keyword: str, max_results: int = 3) -> list[dict]:
    """通过 B站 search/all/v2 搜索视频"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            resp = await client.get(
                _BILI_SEARCH_API,
                headers=_DEFAULT_HEADERS,
                params={"keyword": keyword, "page": 1},
            )
            if resp.status_code != 200:
                logger.warning("B站搜索 HTTP %s", resp.status_code)
                return []

            data = resp.json()
            if data.get("code") != 0:
                logger.warning("B站搜索 code=%s msg=%s", data.get("code"), data.get("message"))
                return []

            # 从分节结果中找到 video 类型
            sections = data.get("data", {}).get("result", [])
            for section in sections:
                if section.get("result_type") == "video":
                    items = section.get("data", [])
                    return [_build_video_item(i) for i in items[:max_results] if _build_video_item(i)]
            return []
    except Exception:
        logger.exception("B站搜索失败 keyword=%s", keyword)
        return []


async def _search_bilibili_html(keyword: str, max_results: int = 3) -> list[dict]:
    """兜底：搜索页 HTML 提取视频数据（API 不可用时）"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), follow_redirects=True) as client:
            resp = await client.get(
                "https://search.bilibili.com/video",
                headers=_DEFAULT_HEADERS,
                params={"keyword": keyword, "page": 1},
            )
            if resp.status_code != 200:
                return []

            html = resp.text
            # 从 HTML 中提取所有 BVID
            bvids = re.findall(r'BV[a-zA-Z0-9]{10,}', html)
            # 去重
            seen = set()
            unique_bvids = [b for b in bvids if not (b in seen or seen.add(b))]
            if not unique_bvids:
                return []

            # 用详情 API 逐个获取信息（只取前 max_results 个）
            results = []
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as detail_client:
                for bvid in unique_bvids[:max_results]:
                    try:
                        dr = await detail_client.get(
                            _BILI_VIDEO_API.format(bvid=bvid),
                            headers=_DEFAULT_HEADERS,
                        )
                        if dr.status_code == 200:
                            dd = dr.json().get("data")
                            if dd:
                                results.append({
                                    "bvid": bvid,
                                    "title": dd.get("title", ""),
                                    "page_url": f"https://www.bilibili.com/video/{bvid}",
                                    "description": dd.get("desc", ""),
                                    "source": "bilibili",
                                    "source_label": "B站",
                                    "embed_url": _BILI_EMBED_TPL.format(bvid=bvid),
                                    "cover_url": dd.get("pic", ""),
                                    "duration": dd.get("duration"),
                                    "author": dd.get("owner", {}).get("name", ""),
                                    "view_count": (dd.get("stat") or {}).get("view", 0),
                                })
                    except Exception:
                        logger.debug("HTML兜底详情查询失败 bvid=%s", bvid)
            return results
    except Exception:
        logger.debug("B站搜索页提取失败 keyword=%s", keyword)
        return []


async def _enrich_detail(videos: list[dict]) -> list[dict]:
    """补充 B站视频封面/时长等信息"""
    enriched = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        for v in videos:
            if v.get("cover_url") and v.get("duration") is not None:
                enriched.append(v)
                continue
            try:
                resp = await client.get(
                    _BILI_VIDEO_API.format(bvid=v["bvid"]),
                    headers=_DEFAULT_HEADERS,
                )
                if resp.status_code == 200:
                    d = resp.json().get("data") or {}
                    if d:
                        v.setdefault("title", d.get("title", ""))
                        v.setdefault("cover_url", d.get("pic", ""))
                        if v.get("duration") is None:
                            v["duration"] = d.get("duration")
                        v.setdefault("author", d.get("owner", {}).get("name", ""))
                        stat = d.get("stat") or {}
                        v.setdefault("view_count", stat.get("view", 0))
                        v.setdefault("description", d.get("desc", ""))
            except Exception:
                logger.debug("B站详情查询失败 bvid=%s", v["bvid"])
            enriched.append(v)
    return enriched


# ─── 工具函数 ───

def _extract_bvid(url: str) -> str | None:
    m = _BVID_PATTERN.search(url)
    return m.group() if m else None


def _duration_to_seconds(dur: str | int | None) -> int | None:
    """将 B站时长格式转成秒数（"293:4" → 17584, 334 原样返回）"""
    if dur is None:
        return None
    if isinstance(dur, int):
        return dur
    if isinstance(dur, str) and ":" in dur:
        parts = dur.split(":")
        if len(parts) == 2:
            try:
                return int(parts[0]) * 60 + int(parts[1])
            except ValueError:
                return None
        if len(parts) == 3:
            try:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except ValueError:
                return None
    try:
        return int(dur)
    except (ValueError, TypeError):
        return None


def _ensure_https(url: str) -> str:
    """补全协议相对 URL"""
    if url.startswith("//"):
        return "https:" + url
    return url


def _build_video_item(item: dict) -> dict | None:
    bvid = item.get("bvid") or _extract_bvid(item.get("arcurl", ""))
    if not bvid:
        return None
    return {
        "bvid": bvid,
        "title": _clean_title(item.get("title", "")),
        "page_url": item.get("arcurl", f"https://www.bilibili.com/video/{bvid}"),
        "description": _strip_em(item.get("description", "")),
        "source": "bilibili",
        "source_label": "B站",
        "embed_url": _BILI_EMBED_TPL.format(bvid=bvid),
        "cover_url": _ensure_https(item.get("pic", "")),
        "duration": _duration_to_seconds(item.get("duration")),
        "author": item.get("author", ""),
        "view_count": item.get("play", 0),
    }


def _clean_title(title: str) -> str:
    return title.replace("<em class=\"keyword\">", "").replace("</em>", "").strip()


def _strip_em(text: str) -> str:
    return text.replace("<em>", "").replace("</em>", "").strip()


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return ""
    m, s = divmod(int(seconds), 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_view_count(count: int | None) -> str:
    if count is None:
        return ""
    if count >= 10000:
        return f"{count / 10000:.1f}万"
    return str(count)


# ═══════════════════════════════════════════════
#  主服务
# ═══════════════════════════════════════════════

class ExternalVideoService:

    @staticmethod
    async def search(topic: str, max_results: int = 3) -> list[dict]:
        """搜索在线教学视频（B站），结果缓存 6 小时

        Returns:
            list[dict]: 每项含 title, page_url, embed_url, cover_url,
                        duration(秒), author, view_count, source, source_label, description
        """
        _ck = None
        if topic and len(topic.strip()) > 1:
            _ck = _cache_key("video:search", _text_hash(topic.strip().lower()))
            cached = await cache_get(_ck)
            if cached is not None and isinstance(cached, list):
                return cached[:max_results]

        videos = await _search_bilibili_api(topic, max_results)
        if not videos:
            videos = await _search_bilibili_html(topic, max_results)
        if videos:
            videos = await _enrich_detail(videos)

        result = videos[:max_results]
        # 非空结果才缓存（空结果可能只是临时网络问题）
        if result and _ck:
            await cache_set(_ck, result, 21600)  # 6 小时

        return result

    @staticmethod
    async def search_and_save(
        topic: str,
        user_id: int,
        max_results: int = 3,
        chat_group_id: int = 0,
    ) -> list[dict]:
        """搜索视频并保存为 GeneratedResource，同时写入聊天记录和通知"""
        user = await User.filter(id=user_id).first()
        if not user:
            raise ValueError("用户不存在")

        videos = await ExternalVideoService.search(topic, max_results)
        if not videos:
            return []

        saved = []
        for v in videos:
            record = await GeneratedResource.create(
                topic=topic,
                resource_type="external_video",
                content=json.dumps(v, ensure_ascii=False),
                file_url=v.get("page_url", ""),
                cover_url=v.get("cover_url"),
                review_passed=True,
                retry_count=0,
                user=user,
            )
            saved.append({
                "resource_id": record.id,
                "topic": record.topic,
                "resource_type": "external_video",
                "file_url": record.file_url,
                "cover_url": record.cover_url or "",
                "title": v.get("title", ""),
                "source": v.get("source_label", ""),
                "embed_url": v.get("embed_url", ""),
                "duration": v.get("duration"),
                "duration_text": _format_duration(v.get("duration")),
                "author": v.get("author", ""),
                "view_count": v.get("view_count", 0),
                "view_count_text": _format_view_count(v.get("view_count")),
                "description": v.get("description", ""),
                "created_at": str(record.created_at),
            })

        # 写入聊天历史（让对话中能看到结果）
        if chat_group_id and saved:
            lines = [f"已找到 {len(saved)} 个相关教学视频："]
            for v in saved:
                meta = "  ".join(filter(None, [
                    f"来源：{v['source']}",
                    f"UP主：{v['author']}" if v.get("author") else "",
                    f"时长：{v['duration_text']}" if v.get("duration_text") else "",
                    f"播放：{v['view_count_text']}" if v.get("view_count_text") else "",
                ]))
                lines.append(f"- {v['title']}  (资源ID: {v['resource_id']})")
                if meta:
                    lines.append(f"  {meta}")

            try:
                await ChatHistory.create(
                    user=user,
                    chat_group_id=chat_group_id,
                    req=f"搜索视频：{topic}",
                    res="\n".join(lines),
                )
            except Exception:
                logger.exception("保存聊天记录失败")

            try:
                await Notification.create(
                    type="resource",
                    title="视频推荐已找到",
                    content=f"「{topic}」共找到 {len(saved)} 个相关教学视频",
                    target_url=f"/chat?chat_group_id={chat_group_id}",
                    target_user_id=user_id,
                )
            except Exception:
                logger.exception("创建通知失败")

        return saved
