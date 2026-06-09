CREATE TABLE IF NOT EXISTS resource_annotations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  source_type VARCHAR(16) NOT NULL DEFAULT 'generated' COMMENT '资源来源: generated/knowledge',
  source_id INT NOT NULL DEFAULT 0 COMMENT '来源记录的主键ID',
  selected_text TEXT NOT NULL,
  note_text TEXT NOT NULL,
  position JSON NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  KEY idx_user_source (user_id, source_type, source_id),
  KEY idx_source (source_type, source_id),
  CONSTRAINT fk_ra_user FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
