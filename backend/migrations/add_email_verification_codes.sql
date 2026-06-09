-- 邮箱验证码表
CREATE TABLE IF NOT EXISTS email_verification_codes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(128) NOT NULL,
  code VARCHAR(6) NOT NULL,
  purpose VARCHAR(16) NOT NULL DEFAULT 'login',
  used TINYINT(1) NOT NULL DEFAULT 0,
  expires_at DATETIME(6) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  KEY idx_email (email),
  KEY idx_email_code (email, code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
