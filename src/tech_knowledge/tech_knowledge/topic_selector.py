"""Selects topics for tech knowledge generation."""

import random

# Curated list of high-value technical topics
TECH_TOPICS = [
    # Python
    "Python Asyncio: Event Loops & Couroutines",
    "Python Decorators: Best Practices",
    "Python Type Hints & Mypy",
    "Python Context Managers (with statement)",
    "Python Generators & Iterators",
    "Python Global Interpreter Lock (GIL)",
    "Python Data Classes vs Pydantic",
    # React / Frontend
    "React Hooks: useEffect dependency array pitfalls",
    "React Server Components (RSC) vs Client Components",
    "React Performance: Memoization (useMemo, useCallback)",
    "React Context API vs Redux/Zustand",
    "TypeScript Generics: Advanced Patterns",
    "CSS Grid vs Flexbox: When to use which",
    # Backend / System Design
    "REST vs GraphQL vs gRPC",
    "Database Indexing Strategies (B-Tree vs Hash)",
    "CAP Theorem in Distributed Systems",
    "Caching Strategies (Write-through vs Write-back)",
    "Microservices vs Monolith: Trade-offs",
    "Event-Driven Architecture Patterns",
    # AWS / Cloud
    "AWS Lambda Cold Starts & mitigation",
    "AWS DynamoDB Single Table Design",
    "AWS S3 Consistency Model",
    "Containerization: Docker vs Podman",
    "Kubernetes: Pods, Deployments & Services",
    # Data Science / AI
    "Pandas: Vectorization vs Iteration",
    "NumPy Broadcasting Rules",
    "RAG (Retrieval-Augmented Generation) Architecture",
    "LLM Fine-tuning vs Prompt Engineering",
    "Vector Databases: HNSW Indexing",
    "AI Agents: ReAct Pattern",
]


class TopicSelector:
    """Selects a topic for the knowledge drop."""

    def get_random_topic(self) -> str:
        """Return a random topic from the curated list."""
        return random.choice(TECH_TOPICS)
