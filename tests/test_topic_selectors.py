from coding_interview.topic_selector import TopicSelector as CodingSelector
from tech_interview.topic_selector import TopicSelector as TechSelector


def test_tech_selector_always_general():
    selector = TechSelector()
    for _ in range(50):
        topic = selector.get_random_topic()
        assert topic["type"] == "general"


def test_coding_selector_always_coding():
    selector = CodingSelector()
    for _ in range(50):
        topic = selector.get_random_topic()
        assert topic["type"] == "coding"
