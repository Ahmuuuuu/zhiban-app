-- resource_annotations 表从单 FK 改为多态关联（source_type + source_id）
-- 全新表无数据，直接删掉让 Tortoise generate_schemas 按新模型重建
DROP TABLE IF EXISTS resource_annotations;
