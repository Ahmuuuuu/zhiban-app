---
name: learning-progress-driven-portrait
description: 用户学习进度驱动画像自动同步的方案设计，替代纯聊天套话
type: project
---

# 学习进度驱动画像方案

## 核心理念
用户不一定聊天，但一定会学。通过记录用户的学习进度行为来自动构建画像，比纯靠聊天套话更可靠。

## 数据流
```
上传资料 → 知识库有了（ChromaDB）
  ↓
用户自主学习 → 标记进度 → learning_progress 表
  ↓
画像自动同步 → 更新 User_picture.traits 的6个维度
  ↓
聊天界面 → UnifiedChat 读画像 + 知识库 → 个性化辅导
```

## 需要做的事（清单）

### 1. 建 learning_progress 表
- 字段：id, user_id(FK), knowledge_point(str), status(enum: 未开始/学习中/已掌握/卡住了), field(关联到traits维度), created_at, updated_at
- 表名：learning_progress

### 2. 进度更新接口
- `POST /learning/update_progress`
- Body: knowledge_point, status
- 前端打勾/标记时调

### 3. 进度→画像自动同步函数
- 用户标记"已掌握"某个知识点 → `strengths` + `knowbase` 同步提升
- 用户标记"卡住了" → `weaknesses` + `commonmis` 记录
- 连续学同方向内容 → `interest` 推测
- 学习频率 → `learning_pace` 推测

### 4. 置信度体系加 source='behavior'
- 目前有 popup(0.75) / user_stated(0.65) / agent_inferred(0.30)
- 新增 behavior(0.70) — 行为数据置信度仅次于弹窗
- 需要在 portrait_utils.py 的 CONFIDENCE_FLOOR/CEIL/BOOST 里加

### 5. UnifiedChat prompt 调整
- 对话时优先读画像再回答
- 可以结合学习进度数据做个性化辅导

## 设计决策
- 画像 80% 靠学习行为自动构建，聊天只是补充
- `knowbase` 和 `commonmis` 直接从进度数据可算
- `interest` 和 `learning_pace` 需要积累足够进度记录才能推断，初期可能靠聊天补
- 比赛评分点全覆盖：多维度画像 / 个性化学习路径 / AI答疑 / 多智能体资源生成

## 后续
- 这个完成后可以接 LangGraph 的 Planner→Executor→Reviewer 做资源生成
- 学习路线规划可以根据 learning_progress 的"卡住了"标记动态调整
