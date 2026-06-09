-- generation_tasks 表 — 资源生成任务持久化
CREATE TABLE IF NOT EXISTS generation_tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  task_id VARCHAR(36) NOT NULL UNIQUE,
  user_id INT NOT NULL,
  topic VARCHAR(255) NOT NULL DEFAULT '',
  resource_types VARCHAR(255) NOT NULL DEFAULT '[]',
  chat_group_id INT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  progress INT NOT NULL DEFAULT 0,
  progress_msg VARCHAR(255) NOT NULL DEFAULT '',
  result TEXT NULL,
  error TEXT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  KEY idx_user_id (user_id),
  KEY idx_status (status),
  KEY idx_created_at (created_at),
  CONSTRAINT fk_gt_user FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
