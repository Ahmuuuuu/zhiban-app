"""站内消息推送 — 双表 API"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Query
from tortoise.expressions import Q

from backend.src.utils.jwt import get_user_id_from_token
from backend.src.utils.admin_check import is_admin
from backend.src.models.notification_model import Notification, UserNotification

router = APIRouter(prefix="/notification", tags=["消息通知"])


async def _visible_qs(user_id: int):
    """用户可见的通知：is_active 且 (全员广播 或 定向给自己)"""
    return Notification.filter(
        Q(target_user_id__isnull=True) | Q(target_user_id=user_id),
        is_active=True,
    )


@router.get("/list")
async def list_notifications(
    user_id: int = Depends(get_user_id_from_token),
    page: int = Query(1, ge=1, alias="page"),
    size: int = Query(20, ge=1, le=100, alias="size"),
):
    qs = await _visible_qs(user_id)
    total = await qs.count()

    # 未读 = 可见总数 - 已读条数
    visible_ids = await qs.values_list("id", flat=True)
    read_ids = await UserNotification.filter(
        user_id=user_id, is_read=True, notification_id__in=visible_ids
    ).values_list("notification_id", flat=True)
    read_set = set(read_ids)
    unread_count = total - len(read_set)

    records = await qs.order_by("-created_at").offset((page - 1) * size).limit(size).values(
        "id", "type", "title", "content", "target_url", "created_at"
    )
    items = []
    for r in records:
        items.append({
            "id": r["id"],
            "type": r["type"],
            "title": r["title"],
            "content": r["content"],
            "target_url": r["target_url"],
            "is_read": r["id"] in read_set,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })

    return {"items": items, "total": total, "unread_count": unread_count}


@router.get("/unread-count")
async def unread_count(user_id: int = Depends(get_user_id_from_token)):
    visible_ids = await (await _visible_qs(user_id)).values_list("id", flat=True)
    if not visible_ids:
        return {"unread_count": 0}
    read_count = await UserNotification.filter(
        user_id=user_id, is_read=True, notification_id__in=visible_ids
    ).count()
    return {"unread_count": len(visible_ids) - read_count}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: int, user_id: int = Depends(get_user_id_from_token)):
    # 确保通知存在且对用户可见
    visible = await (await _visible_qs(user_id)).filter(id=notification_id).exists()
    if not visible:
        raise HTTPException(404, "消息不存在")

    from tortoise.transactions import in_transaction
    _, created = await UserNotification.update_or_create(
        user_id=user_id,
        notification_id=notification_id,
        defaults={"is_read": True, "read_at": datetime.now(timezone.utc)},
    )
    return {"ok": True, "created": created}


@router.post("/read-all")
async def mark_all_read(user_id: int = Depends(get_user_id_from_token)):
    visible_ids = await (await _visible_qs(user_id)).values_list("id", flat=True)
    count = 0
    for nid in visible_ids:
        _, created = await UserNotification.update_or_create(
            user_id=user_id,
            notification_id=nid,
            defaults={"is_read": True, "read_at": datetime.now(timezone.utc)},
        )
        count += 1
    return {"ok": True, "count": count}


@router.post("/send")
async def send_notice(
    type: str = Query("system", description="resource/reminder/system/weekly_report"),
    title: str = Query(description="通知标题"),
    content: str = Query("", description="通知正文"),
    target_url: str = Query(None, description="跳转链接"),
    target_user_id: int = Query(None, description="定向用户ID，不传则全员广播"),
    user_id: int = Depends(get_user_id_from_token),
):
    """管理员发送通知"""
    if not await is_admin(user_id):
        raise HTTPException(403, "仅管理员可操作")

    await Notification.create(
        type=type,
        title=title,
        content=content,
        target_url=target_url,
        target_user_id=target_user_id,
    )
    scope = f"用户 {target_user_id}" if target_user_id else "全员"
    return {"ok": True, "msg": f"已向 {scope} 发送"}
