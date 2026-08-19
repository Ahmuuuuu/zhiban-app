from backend.src.service.resource.persistence import is_failed_generation_content


def test_failed_generation_markers_are_not_treated_as_resource_content():
    assert is_failed_generation_content("[生成失败: The read operation timed out]")
    assert is_failed_generation_content("The read operation timed out")
    assert is_failed_generation_content("[generation failed: upstream timeout]")
    assert not is_failed_generation_content("ASCII、BCD 和奇偶校验的思维导图")
