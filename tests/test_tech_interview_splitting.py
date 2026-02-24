from unittest.mock import AsyncMock, patch

import pytest
from tech_interview.__main__ import main


@pytest.mark.anyio
async def test_main_sends_split_messages():
    # Mock Config
    with patch("tech_interview.__main__.Config") as MockConfig:
        mock_config = MockConfig.from_env.return_value
        mock_config.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/mock"
        mock_config.ZAI_API_KEY = "mock_zai_key"
        mock_config.TAVILY_API_KEY = "mock_tavily_key"

        # Mock Services
        with (
            patch("tech_interview.__main__.ZaiClient"),
            patch("tech_interview.__main__.TavilyClient"),
            patch("tech_interview.__main__.TopicSelector") as MockSelector,
            patch("tech_interview.__main__.ContentGenerator") as MockGenerator,
            patch(
                "tech_interview.__main__.send_discord_embeds", new_callable=AsyncMock
            ) as mock_send,
        ):
            # Setup Mocks
            mock_selector = MockSelector.return_value
            mock_selector.get_random_topic.return_value = {
                "content": "Long Topic",
                "type": "coding",
            }

            mock_generator = MockGenerator.return_value
            # Generate content longer than default split limit (4096 chars usually, but checking logic)
            long_content = "A" * 6000
            # Configure the AsyncMock to return the string when awaited
            mock_generator.generate_interview_question = AsyncMock(return_value=long_content)

            # Run Main
            await main()

            # Verify send_discord_embeds was called
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args.kwargs["content"] == long_content
            # We rely on send_discord_embeds to do the splitting,
            # so we just verify main passes the full content to it.
