# 自习室后端设计

## 目标

自习室后端负责三件事：

- 管理一次自习会话：开始、持续检测、结束、统计。
- 调用 YOLO 分析前端上传的视频帧，输出学习状态。
- 在用户开启学习 Vlog 时保存抽帧，并在结束后生成延时摄影。

前端不直接理解 YOLO 标签。后端把模型结果转换成业务状态：

- `focused`：专注中
- `away`：离开座位
- `phone_detected`：疑似玩手机
- `multiple_people`：多人入镜
- `unknown`：暂时无法判断

## 后端模块位置

建议新增独立模块，避免和已有普通学习统计混在一起：

```text
backend/src/router/study_room_router.py
backend/src/service/study_room/service.py
backend/src/models/study_room_model.py
backend/static/study-room/
```

路由前缀：

```text
/study-room
```

## 接口设计

### 1. 开始自习

```http
POST /study-room/sessions/start
```

请求体：

```json
{
  "goal": "完成高数习题第 3 章",
  "planned_minutes": 45,
  "vlog_enabled": true,
  "timelapse_interval_seconds": 5,
  "timelapse_target_seconds": 30
}
```

字段说明：

- `goal`：本次目标，最多 80 字。
- `planned_minutes`：计划时长，建议限制 10-240。
- `vlog_enabled`：用户是否主动开启学习 Vlog。
- `timelapse_interval_seconds`：抽帧间隔，建议 3、5、8 秒。
- `timelapse_target_seconds`：期望成片长度，允许为空，后端自动计算。

返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "session_id": "sr_20260816_abcdef",
    "state": "running",
    "started_at": "2026-08-16T19:30:00",
    "frame_upload_interval_seconds": 2,
    "vlog_enabled": true
  }
}
```

### 2. 上传一帧并检测

```http
POST /study-room/sessions/{session_id}/frame
Content-Type: multipart/form-data
```

表单字段：

```text
frame: 图片文件，jpg/png/webp
client_elapsed_seconds: 前端计时秒数，可选
save_for_vlog: 是否保存为 Vlog 抽帧，可选
```

返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "session_id": "sr_20260816_abcdef",
    "state": "focused",
    "message": "状态很好，继续保持。",
    "confidence": 0.86,
    "reminder": null,
    "signals": {
      "person_count": 1,
      "phone_detected": false,
      "away": false,
      "multiple_people": false
    },
    "metrics": {
      "elapsed_seconds": 120,
      "focus_seconds": 110,
      "focus_rate": 92,
      "away_count": 0,
      "alert_count": 1
    }
  }
}
```

如果需要提醒，`reminder` 返回：

```json
{
  "type": "phone_detected",
  "message": "检测到手机使用，先放一放？",
  "level": "warning"
}
```

### 3. 查询会话状态

```http
GET /study-room/sessions/{session_id}
```

返回当前会话信息、统计数据、最近提醒。

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "session_id": "sr_20260816_abcdef",
    "state": "running",
    "goal": "完成高数习题第 3 章",
    "planned_minutes": 45,
    "started_at": "2026-08-16T19:30:00",
    "ended_at": null,
    "metrics": {
      "elapsed_seconds": 120,
      "focus_seconds": 110,
      "focus_rate": 92,
      "away_count": 0,
      "alert_count": 1
    },
    "recent_alerts": []
  }
}
```

### 4. 结束自习

```http
POST /study-room/sessions/{session_id}/finish
```

请求体：

```json
{
  "client_elapsed_seconds": 2700
}
```

返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "session_id": "sr_20260816_abcdef",
    "state": "finished",
    "summary": {
      "goal": "完成高数习题第 3 章",
      "elapsed_seconds": 2700,
      "focus_seconds": 2380,
      "focus_rate": 88,
      "away_count": 2,
      "alert_count": 4,
      "phone_alert_count": 1,
      "multiple_people_alert_count": 1
    },
    "timelapse": {
      "enabled": true,
      "status": "generating",
      "url": null
    }
  }
}
```

说明：

- 如果 `vlog_enabled=false`，`timelapse.status` 返回 `disabled`。
- 如果已同步生成完成，返回 `ready` 和 `url`。
- 如果后台生成，前端轮询第 5 个接口。

### 5. 查询延时摄影

```http
GET /study-room/sessions/{session_id}/timelapse
```

返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "enabled": true,
    "status": "ready",
    "url": "/static/study-room/sr_20260816_abcdef/timelapse.mp4",
    "frame_count": 540
  }
}
```

状态：

- `disabled`：未开启 Vlog
- `capturing`：自习中仍在抽帧
- `generating`：正在生成
- `ready`：已生成
- `failed`：生成失败

### 6. 删除延时摄影

```http
DELETE /study-room/sessions/{session_id}/timelapse
```

删除成片和原始抽帧，返回：

```json
{
  "code": 200,
  "msg": "已删除"
}
```

## 数据库表设计

### StudyRoomSession

表名：

```text
study_room_sessions
```

字段：

```text
id                    Int PK
session_key           CharField unique
goal                  CharField
planned_minutes       Int
state                 CharField
vlog_enabled          Boolean
timelapse_interval    Int
timelapse_target      Int null
timelapse_status      CharField
timelapse_url         CharField null
frame_count           Int
elapsed_seconds       Int
focus_seconds         Int
away_seconds          Int
focus_rate            Int
away_count            Int
alert_count           Int
phone_alert_count     Int
multiple_people_alert_count Int
started_at            Datetime
ended_at              Datetime null
created_at            Datetime auto_now_add
updated_at            Datetime auto_now
user                  ForeignKey User
```

建议 `state`：

```text
running / paused / finished / cancelled
```

### StudyRoomFrameLog

表名：

```text
study_room_frame_logs
```

字段：

```text
id                    Int PK
session               ForeignKey StudyRoomSession
captured_at           Datetime
client_elapsed_seconds Int
state                 CharField
confidence            Float
person_count          Int
phone_detected        Boolean
away                  Boolean
multiple_people       Boolean
saved_for_vlog        Boolean
frame_path            CharField null
raw_result            Text null
```

作用：

- 记录 YOLO 每次推理结果。
- 后续可以回放分析，或者调试误判。
- 原始图片不一定每帧都保存，只有 Vlog 或调试需要才保存。

### StudyRoomAlert

表名：

```text
study_room_alerts
```

字段：

```text
id                    Int PK
session               ForeignKey StudyRoomSession
alert_type            CharField
level                 CharField
message               CharField
triggered_at          Datetime
client_elapsed_seconds Int
```

建议 `alert_type`：

```text
away / phone_detected / multiple_people / camera_invalid
```

建议 `level`：

```text
info / warning / danger
```

## 文件存储设计

根目录：

```text
backend/static/study-room/{session_key}/
```

开启 Vlog 后：

```text
backend/static/study-room/{session_key}/frames/frame_000001.jpg
backend/static/study-room/{session_key}/frames/frame_000002.jpg
backend/static/study-room/{session_key}/timelapse.mp4
```

返回给前端的 URL：

```text
/static/study-room/{session_key}/timelapse.mp4
```

## 状态判断规则

YOLO 单帧只给信号，不直接下业务结论。后端使用滑动窗口做稳定判断。

MVP 规则：

```text
最近约 6 秒连续没有检测到 person -> away
最近 4 帧中 2 帧以上检测到 cell phone -> phone_detected
person_count > 1 连续持续约 6 秒 -> multiple_people
有人 + 无手机 + 无多人告警 -> focused
```

当前实现会要求离席/多人窗口有足够样本覆盖时间段，单帧误检不会立刻触发提醒。

提醒去抖：

```text
同一 alert_type 30 秒内最多提醒一次
```

专注时间统计：

```text
focused 累计为 focus_seconds
away 累计为 away_seconds
phone_detected / multiple_people 不算专注，但也不算离席
```

## YOLO 输入输出约定

后端 service 内部建议统一成这个结构：

```python
{
    "person_count": 1,
    "phone_detected": False,
    "multiple_people": False,
    "confidence": 0.86,
    "raw": {}
}
```

之后无论换 YOLO 模型、ONNX、TensorRT，都不影响 router 和前端。

## YOLO 检测配置

第 4 步开始，`/study-room/sessions/{session_id}/frame` 会优先调用 YOLO 检测。

默认模型：

```text
yolo26n.pt
```

可以通过环境变量调整：

```text
STUDY_ROOM_YOLO_ENABLED=true
STUDY_ROOM_YOLO_MODEL=yolo26n.pt
STUDY_ROOM_YOLO_DEVICE=
STUDY_ROOM_YOLO_IMG_SIZE=640
STUDY_ROOM_YOLO_CONF=0.35
STUDY_ROOM_PERSON_CONF=0.45
STUDY_ROOM_PHONE_CONF=0.35
```

当前只解析两个 COCO 标签：

```text
person
cell phone
```

YOLO 输出会被标准化为：

```python
{
    "person_count": 1,
    "phone_detected": False,
    "away": False,
    "multiple_people": False,
    "confidence": 0.92,
    "source": "yolo",
    "raw": {
        "model": "yolo26n.pt",
        "detections": []
    }
}
```

如果后端依赖未安装、模型文件不存在、首次下载失败，接口不会直接崩溃，会退回 mock 检测，方便先跑通后续流程。

## 延时摄影生成

第 6 步开始，用户开启 `vlog_enabled=true` 后，后端会在上传帧时按 `save_for_vlog=true` 保存抽帧。结束自习时：

```text
POST /study-room/sessions/{session_id}/finish
```

如果本次会话保存过 Vlog 帧，接口会先返回：

```json
{
  "timelapse": {
    "enabled": true,
    "status": "generating",
    "url": null,
    "frame_count": 120
  }
}
```

随后 FastAPI `BackgroundTasks` 会在后台调用 FFmpeg，把 `frames/` 里的图片生成：

```text
backend/static/study-room/{session_key}/timelapse.mp4
```

前端继续轮询：

```http
GET /study-room/sessions/{session_id}/timelapse
```

当 `status=ready` 时，使用返回的 `url` 播放或下载成片。生成失败时返回 `failed`，一般原因是没有抽帧、FFmpeg 不存在或 FFmpeg 执行失败。

FFmpeg 路径配置：

```text
STUDY_ROOM_FFMPEG_BIN=/usr/bin/ffmpeg
FFMPEG_BIN=/usr/bin/ffmpeg
```

如果不配置，后端会自动查找 PATH 里的 `ffmpeg`。Docker 镜像已在 `backend/Dockerfile` 安装 `ffmpeg`。

## 隐私和清理

默认不保存原始帧。

只有满足下面情况才保存图片：

- 用户开启 `vlog_enabled`
- 或后端调试开关允许保存检测帧

删除策略：

- 用户点击删除延时摄影时，删除 `timelapse.mp4` 和 `frames/`。
- 可以后续加定时任务，自动清理 7 天前的原始帧。

## 第 3 步实现范围

下一步只实现骨架，不接 YOLO：

- 新增模型文件。
- 新增 service 目录和会话管理方法。
- 新增 router。
- 接入 `main.py` 和 `database.py`。
- 用 mock 检测结果跑通 `start/frame/finish/timelapse`。

YOLO 依赖和模型加载放到第 4 步。
