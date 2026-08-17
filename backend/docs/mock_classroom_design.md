# 模拟课堂功能设计

## 目标

模拟课堂让用户以“老师试讲”的方式输出一个知识点，系统通过讲解内容、讲解熟练度和摄像头状态给出综合评分，帮助判断用户是否真正理解并能表达该知识。

这个功能和自习室的区别：

- 自习室偏监督：用户是否在学习。
- 模拟课堂偏输出检测：用户能否把知识讲清楚。

## MVP 流程

```text
选择/输入知识点 -> 开启摄像头和麦克风 -> 开始讲课 -> 上传音频和视频帧 -> 结束讲课 -> 生成评分报告
```

前端首屏不做宣传页，直接进入课堂准备界面。

## 前端页面设计

建议新增：

```text
frontend/src/pages/MockClassroomView.vue
```

路由：

```text
/mock-classroom
```

导航栏文案：

```text
模拟课堂
```

页面分三种状态：

### 1. 准备页

用户设置：

- 讲解主题：例如“二次函数的顶点式”
- 讲解时长：建议 3、5、8、10 分钟
- 摄像头
- 麦克风

页面元素：

- 左侧：课堂设置表单
- 右侧：黑板/讲台质感预览
- 底部：开始讲课按钮

### 2. 讲课页

页面元素：

- 摄像头画面
- 讲解倒计时/正计时
- 黑板卡片：展示本次主题、讲解要点
- 实时状态：收音中、画面稳定、检测中
- 结束讲课按钮

运行中行为：

- 前端录制音频。
- 每隔 2 秒上传一帧摄像头图片。
- 音频可以结束后一次上传，MVP 不强制分片上传。

### 3. 报告页

展示：

- 综合分
- 知识理解分
- 讲解熟练度分
- 表达状态分
- 讲解文字稿
- 讲得好的地方
- 知识漏洞
- 下一次练习建议

## 评分维度

综合分建议：

```text
综合分 = 知识理解 60% + 讲解熟练度 25% + 表达状态 15%
```

### 知识理解 60%

主要依据讲解文字稿和后台知识库检索到的参考资料。

子项：

```text
核心概念覆盖       20
知识准确性         20
逻辑结构           10
例子/类比           5
重点遗漏控制         5
```

输出：

```json
{
  "score": 82,
  "coverage_score": 18,
  "accuracy_score": 17,
  "structure_score": 8,
  "example_score": 4,
  "omission_score": 5,
  "strengths": ["能准确说明顶点式的形式"],
  "gaps": ["没有解释 a 的正负对开口方向的影响"]
}
```

### 讲解熟练度 25%

依据音频时长、文字稿和语音转写过程中的时间信息。

子项：

```text
讲解连贯性         8
停顿/卡壳控制       6
重复控制           5
语速合理性         4
时长完成度         2
```

MVP 可以先用文字稿近似判断：

- 大量重复句式 -> 熟练度降低
- 讲解过短 -> 熟练度降低
- 逻辑跳跃明显 -> 连贯性降低

后续如果 ASR 返回词级时间戳，再精细计算停顿和语速。

### 表达状态 15%

摄像头状态只做辅助，不做主观情绪判断。

允许判断：

- 是否有人脸/人像稳定
- 是否长时间离开画面
- 是否多人入镜
- 是否频繁大幅晃动
- 表情是否基本自然/可见

避免判断：

- “焦虑”
- “不自信”
- “厌学”
- “情绪异常”

建议文案保持客观：

```text
镜头中人像较稳定，讲解过程中没有明显离开画面。
```

或：

```text
讲解中途多次离开画面，表达状态分会受到影响。
```

## 后端模块位置

建议新增独立模块：

```text
backend/src/router/mock_classroom_router.py
backend/src/service/mock_classroom/service.py
backend/src/service/mock_classroom/scoring.py
backend/src/service/mock_classroom/vision_analyzer.py
backend/src/models/mock_classroom_model.py
backend/static/mock-classroom/
```

路由前缀：

```text
/mock-classroom
```

## 接口设计

### 1. 开始课堂

```http
POST /mock-classroom/sessions/start
```

请求：

```json
{
  "topic": "二次函数的顶点式",
  "planned_minutes": 5
}
```

返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "session_id": "mc_20260817_abcd1234",
    "state": "running",
    "started_at": "2026-08-17T10:30:00",
    "frame_upload_interval_seconds": 2
  }
}
```

### 2. 上传摄像头帧

```http
POST /mock-classroom/sessions/{session_id}/frame
Content-Type: multipart/form-data
```

表单字段：

```text
frame: jpg/png/webp 图片
client_elapsed_seconds: 前端计时秒数
```

返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "session_id": "mc_20260817_abcd1234",
    "camera_state": "stable",
    "signals": {
      "person_count": 1,
      "face_visible": true,
      "away": false,
      "multiple_people": false
    }
  }
}
```

### 3. 上传讲课音频

```http
POST /mock-classroom/sessions/{session_id}/audio
Content-Type: multipart/form-data
```

表单字段：

```text
audio: webm/mp3/wav
client_elapsed_seconds: 前端计时秒数
```

MVP 可以结束后一次上传完整音频。后续再扩展分片上传。

返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "audio_url": "/static/mock-classroom/mc_20260817_abcd1234/audio.webm",
    "duration_seconds": 306
  }
}
```

### 4. 结束课堂

```http
POST /mock-classroom/sessions/{session_id}/finish
```

请求：

```json
{
  "client_elapsed_seconds": 306
}
```

返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "session_id": "mc_20260817_abcd1234",
    "state": "scoring",
    "report_status": "generating"
  }
}
```

### 5. 查询报告

```http
GET /mock-classroom/sessions/{session_id}/report
```

返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "status": "ready",
    "overall_score": 84,
    "knowledge_score": 86,
    "fluency_score": 80,
    "presentation_score": 82,
    "transcript": "今天我要讲的是二次函数的顶点式...",
    "strengths": ["能够说明顶点坐标的含义"],
    "gaps": ["没有讲清楚参数 a 对图像开口的影响"],
    "suggestions": ["下次讲解时补充一个具体函数图像例子"]
  }
}
```

### 6. 删除课堂媒体

```http
DELETE /mock-classroom/sessions/{session_id}/media
```

用于删除音频、视频帧等原始媒体。

## 数据库表设计

### MockClassroomSession

表名：

```text
mock_classroom_sessions
```

字段：

```text
id                    Int PK
session_key           CharField unique
topic                 CharField
reference_text        Text null，后台知识库检索到的评分参考资料
planned_minutes       Int
state                 CharField
report_status         CharField
audio_url             CharField null
transcript            Text null
elapsed_seconds       Int
overall_score         Int
knowledge_score       Int
fluency_score         Int
presentation_score    Int
started_at            Datetime
ended_at              Datetime null
created_at            Datetime auto_now_add
updated_at            Datetime auto_now
user                  ForeignKey User
```

### MockClassroomFrameLog

表名：

```text
mock_classroom_frame_logs
```

字段：

```text
id                    Int PK
session               ForeignKey MockClassroomSession
captured_at           Datetime
client_elapsed_seconds Int
camera_state          CharField
person_count          Int
face_visible          Boolean
away                  Boolean
multiple_people       Boolean
raw_result            Text null
```

### MockClassroomReport

表名：

```text
mock_classroom_reports
```

字段：

```text
id                    Int PK
session               ForeignKey MockClassroomSession
overall_score         Int
knowledge_score       Int
fluency_score         Int
presentation_score    Int
strengths             Text
gaps                  Text
suggestions           Text
rubric_json           Text
created_at            Datetime auto_now_add
```

## 后端评分流水线

结束课堂后执行：

```text
1. 保存最后一次会话状态
2. 读取音频文件
3. 调用 ASR 生成 transcript
4. 用 topic 从知识库检索参考资料，再结合 transcript 做知识理解评分
5. 用 transcript + 时长信息做熟练度评分
6. 汇总摄像头帧日志做表达状态评分
7. 计算综合分
8. 保存 MockClassroomReport
```

## 摄像头分析策略

MVP 先复用自习室 YOLO 能力：

```text
person_count == 0 -> away
person_count > 1 -> multiple_people
person_count == 1 -> stable
```

表情分析后续再加。第一版可以只把“人脸/人像是否稳定”计入表达状态分，避免因为表情模型不准影响主评分。

后续可选增强：

- 人脸可见度
- 视线大致方向
- 画面晃动幅度
- 表情自然度

## 隐私和清理

默认只为评分保存必要文件：

- 音频文件
- 少量摄像头分析日志
- 可选调试帧

建议：

- 默认不长期保存原始视频帧。
- 用户可以删除课堂媒体。
- 报告和文字稿可以保留，用于学习记录。
- 后续加定时任务清理 7 天前的原始音频/帧。

## 第 1 版实现边界

第一版先做可闭环的 MVP：

- 页面可开始/结束模拟课堂。
- 前端能录音和上传摄像头帧。
- 后端能保存 session、音频、帧日志。
- 能生成文字稿。
- 能返回三项评分和综合报告。

暂不做：

- 直播式实时评分。
- 完整视频录制。
- 复杂情绪识别。
- 多知识点自动拆分评分。

## 第 5 步实现范围

当前后端已经完成模拟课堂的基础闭环接口：

- 创建模拟课堂 session。
- 接收并保存摄像头抽帧。
- 接收并保存讲课音频。
- 结束模拟课堂 session。
- 返回报告占位结构。
- 删除本次课堂的原始媒体文件。

暂未接入：

- ASR 语音转文字。
- 知识理解评分。
- 讲解熟练度评分。
- 表达状态/表情综合评分。

## 第 7 步实现范围

当前已接入报告生成流水线：

- 讲课结束后后台生成报告。
- 音频转写走 OpenAI 兼容 ASR 接口；未配置 ASR 时不阻塞报告，会降级为无文字稿评分。
- 摄像头帧复用自习室 YOLO 能力，统计人像是否稳定、是否离开画面、是否多人入镜。
- 知识理解和讲解熟练度优先用 LLM 结合文字稿与后台知识库参考资料评分。
- LLM 或 ASR 不可用时，使用启发式评分，并在建议里说明限制。
- 前端结束讲课后自动轮询报告状态，展示综合分、知识理解、讲解熟练度、表达状态。

ASR 环境变量：

```text
MOCK_CLASSROOM_ASR_ENABLED=true
MOCK_CLASSROOM_ASR_URL=https://api.openai.com/v1/audio/transcriptions
MOCK_CLASSROOM_ASR_API_KEY=你的 ASR key
MOCK_CLASSROOM_ASR_MODEL=whisper-1
MOCK_CLASSROOM_ASR_TIMEOUT_SECONDS=120
```

如果只配置 `OPENAI_API_KEY`，且没有配置 `MOCK_CLASSROOM_ASR_URL`，系统会默认使用 OpenAI 兼容的 `/v1/audio/transcriptions` 地址。
