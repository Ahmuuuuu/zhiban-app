-- 为 generated_resources 表添加 like_count / favorite_count 字段
ALTER TABLE generated_resources
  ADD COLUMN like_count INT NOT NULL DEFAULT 0 COMMENT '点赞数',
  ADD COLUMN favorite_count INT NOT NULL DEFAULT 0 COMMENT '收藏数';

-- 创建资源点赞表
CREATE TABLE IF NOT EXISTS resource_likes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  user_id INT NOT NULL,
  resource_id INT NOT NULL,
  UNIQUE KEY uk_user_resource (user_id, resource_id),
  KEY idx_resource_id (resource_id),
  CONSTRAINT fk_rl_user FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE CASCADE,
  CONSTRAINT fk_rl_resource FOREIGN KEY (resource_id) REFERENCES generated_resources(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
