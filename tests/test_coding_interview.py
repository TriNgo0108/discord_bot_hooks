from unittest.mock import AsyncMock, patch

import pytest
from coding_interview.__main__ import main


@pytest.mark.anyio
async def test_coding_interview_main():
    # Mock Config
    with patch("coding_interview.__main__.Config") as MockConfig:
        mock_config = MockConfig.from_env.return_value
        mock_config.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/mock"
        mock_config.ZAI_API_KEY = "mock_zai_key"
        mock_config.TAVILY_API_KEY = "mock_tavily_key"

        # Mock Services
        with (
            patch("coding_interview.__main__.ZaiClient"),
            patch("coding_interview.__main__.TavilyClient"),
            patch("coding_interview.__main__.TopicSelector") as MockSelector,
            patch("coding_interview.__main__.ContentGenerator") as MockGenerator,
            patch(
                "coding_interview.__main__.send_discord_embeds",
                new_callable=AsyncMock,
            ) as mock_send,
        ):
            # Setup Mocks
            mock_selector = MockSelector.return_value
            mock_selector.get_random_topic.return_value = {
                "content": "Coding Topic",
                "type": "coding",
            }

            mock_generator = MockGenerator.return_value
            mock_generator.generate_interview_question = AsyncMock(return_value="Content")

            # Run Main
            await main()

            # Verify send_discord_embeds was called
            mock_send.assert_called_once()
