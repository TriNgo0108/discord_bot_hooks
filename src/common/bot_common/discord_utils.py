"""Utilities for Discord interactions."""


def split_message(message: str, limit: int = 4000) -> list[str]:
    """
    Split a message into chunks within the character limit.
    Tries to split at newlines to preserve formatting.
    """
    if limit <= 0:
        raise ValueError("Limit must be greater than 0")

    if len(message) <= limit:
        return [message]

    chunks = []
    while message:
        if len(message) <= limit:
            chunks.append(message)
            break

        # Find the best split point
        # Try to find a newline within the last 1000 characters of the limit
        search_range_start = max(0, limit - 1000)
        search_range_end = limit

        # Look for the last newline in the safe zone
        last_newline = message.rfind("\n", search_range_start, search_range_end)

        split_index = last_newline + 1 if last_newline != -1 else limit

        # Append chunk and remove from message
        chunks.append(message[:split_index])
        message = message[split_index:]

    return chunks
