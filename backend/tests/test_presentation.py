"""测试课件管线：生成资源 → 生成 HTML 课件"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
DESKTOP = Path("C:/Users/35808/Desktop")

TOPIC = "CPU缓存架构与工作原理"


async def main():
    from backend.src.utils.database import init_db, close_db
    await init_db()

    # 1. 检查是否已有 topic 资源
    from backend.src.models.resource_model import GeneratedResource
    records = await GeneratedResource.filter(user_id=1, topic=TOPIC).all()
    has_doc = any(r.resource_type == "document" for r in records)
    has_mm = any(r.resource_type == "mindmap" for r in records)
    has_ppt = any(r.resource_type == "ppt" for r in records)
    print(f"[CHECK] document={has_doc} mindmap={has_mm} ppt={has_ppt}")

    # 2. 缺失的资源通过 LLM 快速生成
    if not has_doc or not has_mm or not has_ppt:
        print("[INFO] 生成缺失资源...")
        from backend.src.service.resource_service import ResourceService
        types = []
        if not has_doc:
            types.append("document")
        if not has_mm:
            types.append("mindmap")
        if not has_ppt:
            types.append("ppt")
        saved = await ResourceService.generate_and_save(TOPIC, 1, types)
        print(f"[OK] 生成了 {len(saved)} 个资源")
        for s in saved:
            print(f"  - {s['resource_type']}: id={s['resource_id']}")

    # 3. 生成 HTML 课件（异步后台逐章生成）
    from backend.src.service.presentation_service import generate as gen_presentation, get_presentation
    print("[WAIT] 启动课件生成（含 EdgeTTS 配音）...")
    result = await gen_presentation(TOPIC, 1)
    if "error" in result:
        print(f"[ERROR] {result['error']}")
        return
    pres_id = result["id"]
    print(f"[OK] 课件已启动: id={pres_id}, file_url={result['file_url']}")

    # 4. 轮询等待后台生成完成
    import asyncio
    while True:
        pres = await get_presentation(pres_id, 1)
        status = pres["status"]
        print(f"  └─ 状态: {status}, 章节: {pres['chapter_count']}, 时长: {pres['total_duration_ms'] // 1000}s")
        if status in ("ready", "failed"):
            if status == "failed":
                print(f"[ERROR] 课件生成失败: {pres.get('error_message')}")
            break
        await asyncio.sleep(3)

    # 5. 复制到桌面方便查看
    src = Path(__file__).parent.parent / "static" / "presentations" / result["file_url"].rsplit("/", 1)[-1]
    dst = DESKTOP / f"{TOPIC}_课件.html"
    dst.write_bytes(src.read_bytes())
    print(f"[OK] 已复制到桌面: {dst}")

    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
