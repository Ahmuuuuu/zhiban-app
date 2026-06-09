ALTER TABLE exam_questions MODIFY COLUMN point_value FLOAT NULL COMMENT '题目分值(null则按难度自动计算)';
