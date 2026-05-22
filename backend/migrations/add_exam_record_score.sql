-- 为 exam_records 表添加 score 字段
ALTER TABLE exam_records ADD COLUMN score FLOAT NULL COMMENT '得分(0-100)，简答题为 null';
