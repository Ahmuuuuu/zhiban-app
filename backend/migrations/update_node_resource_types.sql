-- 将存量节点的 resource_types 从旧默认值（2种）更新为新默认值（4种）
-- 只更新恰好等于旧默认值的节点，保留可能的自定义配置
UPDATE path_nodes
SET resource_types = '["document", "ppt", "mindmap"]'
WHERE resource_types = '["document", "image"]';
