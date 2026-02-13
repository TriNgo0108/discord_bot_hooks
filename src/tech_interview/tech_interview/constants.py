"""Constants for Tech Interview Hook."""

INTERVIEW_PROMPT = """
### ROLE
You are a Senior Technical Interviewer at a FAANG company.
Your goal is to present a realistic interview question and then provide a comprehensive "Model Answer".

### TOPIC
**{topic}**

### CONTEXT (Real-world Interview Experiences)
{context}

### INSTRUCTIONS
1.  **Language**: Strictly **English**.
2.  **Structure**:
    *   **❓ The Question**: Present the question clearly (e.g., "Design a URL Shortener", "Explain the difference between Process and Thread").
    *   **💡 Key Concepts**: Briefly list the core concepts tested here.
    *   **✅ Model Answer**: Provide a high-quality, depth-first answer.
        *   If it's coding: Provide idiomatic Python solution with time/space complexity analysis.
        *   If it's system design: Outline high-level architecture, key components, and trade-offs.
    *   **⚠️ Common Pitfalls**: What mistakes do candidates often make?

### FORMATTING
-   Use **Discord Markdown**.
-   Use `###` for section headers.
-   Use `> ` for blockquotes.
-   Use syntax highlighting for code blocks (e.g., ```python ... ```).
-   **Do not** output any pre-text or post-text.
"""

# Curated list of interview topics
INTERVIEW_TOPICS = [
    # System Design
    "Design a URL Shortener (TinyURL)",
    "Design a Rate Limiter",
    "Design a Notification System",
    "Design a Chat Application (WhatsApp/Slack)",
    "Design a Key-Value Store (Redis)",
    "Design Instagram/Twitter Feed",
    # Algorithms / Data Structures
    "Reverse a Linked List",
    "Detect Cycle in Linked List",
    "Valid Parentheses",
    "Merge K Sorted Lists",
    "Top K Frequent Elements",
    "Longest Substring Without Repeating Characters",
    "Binary Tree Level Order Traversal",
    "Lowest Common Ancestor of a Binary Tree",
    # Language Specific (Python)
    "Python Garbage Collection Mechanism",
    "Python Multiprocessing vs Multithreading",
    "Python Decorators and Closures",
    "Python Generator vs Iterator",
    # General CS
    "TCP vs UDP",
    "Process vs Thread",
    "HTTP vs HTTPS",
    "REST vs GraphQL",
    "ACID Properties in Databases",
    "CAP Theorem explained",
]

# Discord Embed Color (Purple)
EMBED_COLOR = "9900ff"
