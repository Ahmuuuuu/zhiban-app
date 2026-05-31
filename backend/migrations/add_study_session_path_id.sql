-- study_sessions 增加 path_id 字段，用于分路径统计学习时长
ALTER TABLE study_sessions
  ADD COLUMN path_id INT NULL COMMENT '关联的学习路径ID' AFTER last_heartbeat_at,
  ADD KEY idx_path_id (path_id);
