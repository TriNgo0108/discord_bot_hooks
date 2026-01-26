"""Configuration for Gmail Reader."""

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GmailConfig:
    email_address: str = field(default_factory=lambda: os.getenv("GMAIL_ADDRESS", ""))
    app_password: str = field(default_factory=lambda: os.getenv("GMAIL_APP_PASSWORD", ""))
    imap_server: str = "imap.gmail.com"
    email_folder: str = "INBOX"

    def validate(self) -> bool:
        if not self.email_address or not self.app_password:
            logger.error("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set.")
            return False
        return True


@dataclass
class AIConfig:
    api_key: str = field(default_factory=lambda: os.getenv("ZAI_API_KEY", ""))
    base_url: str = field(
        default_factory=lambda: os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
    )
    model: str = field(default_factory=lambda: os.getenv("ZAI_MODEL", "glm-4.7"))


@dataclass
class DiscordConfig:
    webhook_url: str = field(default_factory=lambda: os.getenv("DISCORD_WEBHOOK_GMAIL", ""))


@dataclass
class AppConfig:
    gmail: GmailConfig = field(default_factory=GmailConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)


CONFIG = AppConfig()
