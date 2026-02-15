from unittest.mock import AsyncMock, MagicMock

import pytest
from tech_interview.content_generator import ContentGenerator
from tech_interview.topic_selector import TopicSelector


class TestTechInterview:
    def test_topic_selector_returns_dict(self):
        selector = TopicSelector()
        topic = selector.get_random_topic()
        assert isinstance(topic, dict)
        assert "content" in topic
        assert "type" in topic
        assert topic["type"] in ["general", "coding"]

    @pytest.mark.anyio
    async def test_generator_uses_coding_prompt(self):
        zai_mock = MagicMock()
        zai_mock.chat_completion = AsyncMock(return_value="Mocked Content")
        tavily_mock = MagicMock()
        tavily_mock.get_search_context = AsyncMock(return_value="Mocked Context")

        generator = ContentGenerator(zai_mock, tavily_mock)

        await generator.generate_interview_question("Two Sum", "coding")

        # Verify ZaiClient was called with coding prompt
        call_args = zai_mock.chat_completion.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[1]["content"]
        system_content = messages[0]["content"]

        # Check for Coding specific terms
        assert "The Problem" in user_content
        assert "Model Solution" in user_content
        assert "Test Cases" in user_content
        assert "specializing in Algorithms" in system_content

    @pytest.mark.anyio
    async def test_generator_uses_general_prompt(self):
        zai_mock = MagicMock()
        zai_mock.chat_completion = AsyncMock(return_value="Mocked Content")
        tavily_mock = MagicMock()
        tavily_mock.get_search_context = AsyncMock(return_value="Mocked Context")

        generator = ContentGenerator(zai_mock, tavily_mock)

        await generator.generate_interview_question("CAP Theorem", "general")

        # Verify ZaiClient was called with general prompt
        call_args = zai_mock.chat_completion.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[1]["content"]
        system_content = messages[0]["content"]

        # Check for General specific terms
        assert "The Question" in user_content
        assert "Common Pitfalls" in user_content
        assert "expert technical interviewer" in system_content
