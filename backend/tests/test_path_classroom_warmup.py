"""Learning-path warmup tests for the classroom pre-generation pipeline."""

import asyncio

import pytest

from backend.src.service.path.helpers import pre_generate_node


@pytest.mark.asyncio
async def test_warmup_generates_classroom_after_resources_and_quiz():
    events = []

    async def generate_resources(path_id, node_id, user_id):
        events.append("resources:start")
        await asyncio.sleep(0)
        events.append("resources:done")
        return {}

    async def generate_quiz(path_id, node_id, user_id, pre_generate=False):
        assert pre_generate is True
        events.append("quiz:start")
        await asyncio.sleep(0)
        events.append("quiz:done")
        return {}

    async def generate_classroom(path_id, node_id, user_id):
        assert "resources:done" in events
        assert "quiz:done" in events
        events.append("classroom:done")
        return {}

    await pre_generate_node(
        12,
        34,
        56,
        generate_resources,
        generate_quiz,
        generate_classroom,
    )
    await asyncio.sleep(0)

    assert events.index("resources:start") < events.index("resources:done")
    assert events.index("quiz:start") < events.index("quiz:done")
    assert events[-1] == "classroom:done"


@pytest.mark.asyncio
async def test_warmup_keeps_resource_and_quiz_parallel_without_classroom_callback():
    calls = []

    async def generate_resources(*_args):
        calls.append("resources")
        return {}

    async def generate_quiz(*_args, **_kwargs):
        calls.append("quiz")
        return {}

    await pre_generate_node(1, 2, 3, generate_resources, generate_quiz)

    assert set(calls) == {"resources", "quiz"}
