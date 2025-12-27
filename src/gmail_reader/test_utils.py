from gmail_reader import main


def test_clean_text_basic():
    text = "Hello&nbsp;World"
    assert main.clean_text_content(text) == "Hello World"


def test_clean_text_messy_chars():
    text = "Hello\u200bWorld"
    assert main.clean_text_content(text) == "HelloWorld"


def test_clean_text_multiline():
    text = "Line 1\n\n\nLine 2"
    assert main.clean_text_content(text) == "Line 1\n\nLine 2"


def test_split_text_smartly_no_split():
    text = "a" * 100
    chunks = main.split_text_smartly(text, max_length=200)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_text_smartly_with_split():
    text = "a" * 300
    chunks = main.split_text_smartly(text, max_length=200)
    assert len(chunks) == 2
    assert len(chunks[0]) == 200
    assert len(chunks[1]) == 100


def test_split_text_smartly_newline():
    # Only 10 chars, then newline, then 200 chars. Max 200.
    # Should split at newline if possible, but here 10+1+200 = 211 > 200.
    # The newline is conveniently early.
    # Wait, the logic tries to find LAST newline in the candidate block.
    # Candidate = text[:200].
    # We want to ensure it splits correctly.

    part1 = "a" * 150
    part2 = "b" * 150
    text = part1 + "\n" + part2
    # Total 301. Max 200.
    # Candidate = part1 + "\n" + part2[:49] (total 200 chars)
    # Last newline is at index 150.
    # Split should happen at 151.

    chunks = main.split_text_smartly(text, max_length=200)
    assert chunks[0] == part1 + "\n"
    assert chunks[1] == part2


if __name__ == "__main__":
    test_clean_text_basic()
    test_clean_text_messy_chars()
    test_clean_text_multiline()
    test_split_text_smartly_no_split()
    test_split_text_smartly_with_split()
    test_split_text_smartly_newline()
    print("All tests passed!")
