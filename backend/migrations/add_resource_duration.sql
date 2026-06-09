-- resource_read_status 增加资源使用时长字段
ALTER TABLE resource_read_status
  ADD COLUMN duration_seconds INT NOT NULL DEFAULT 0 COMMENT '累计使用时长（秒）' AFTER read_at;
