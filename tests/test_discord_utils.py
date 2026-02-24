import unittest

from bot_common.discord_utils import split_message


class TestDiscordUtils(unittest.TestCase):
    def test_split_message_simple(self):
        message = "a" * 50
        chunks = split_message(message, limit=10)
        # Should be split into 5 chunks of size 10
        self.assertEqual(len(chunks), 5)
        self.assertEqual(chunks[0], "aaaaaaaaaa")

    def test_split_message_newline(self):
        message = "hello\nworld"
        # If limit is small enough, it should split at newline if possible?
        # The logic tries to find last newline in range [limit-1000, limit]

        # Test case where limit allows split
        # "hello\n" is 6 chars. "world" is 5 chars.
        # If limit is 6, it should split "hello\n" and "world"
        chunks = split_message(message, limit=6)
        self.assertEqual(len(chunks), 2)
        # Check actual split behavior - implementation dependent
        # implementation: search_range_start = max(0, 6-1000) = 0. search_range_end = 6.
        # last_newline = message.rfind("\n", 0, 6) -> index 5
        # split_index = 5 + 1 = 6
        # chunks[0] = message[:6] -> "hello\n"
        # message becomes "world"
        self.assertEqual(chunks[0], "hello\n")
        self.assertEqual(chunks[1], "world")

    def test_split_message_no_newline(self):
        message = "helloworld"
        chunks = split_message(message, limit=5)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], "hello")
        self.assertEqual(chunks[1], "world")

    def test_split_message_exact_limit(self):
        message = "12345"
        chunks = split_message(message, limit=5)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "12345")
