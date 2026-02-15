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
CODING_QUESTION_PROMPT = """
### ROLE
You are a Senior Technical Interviewer at a FAANG company.
Your goal is to present a challenging algorithmic coding problem and then provide a comprehensive "Model Solution".

### TOPIC
**{topic}**

### CONTEXT (Real-world Interview Experiences)
{context}

### INSTRUCTIONS
1.  **Language**: Strictly **English**.
2.  **Structure**:
    *   **❓ The Problem**: Clearly state the problem statement, input format, output format, and constraints.
    *   **💡 Key Concepts**: Briefly list the algorithms or data structures needed (e.g., "Two Pointers", "Sliding Window", "Min-Heap").
    *   **✅ Model Solution**: Provide an idiomatic **Python** solution.
        *   Include time and space complexity analysis (Big O).
        *   Explain the approach step-by-step.
    *   **🧪 Test Cases**: Provide 2-3 significant test cases with expected outputs.

### FORMATTING
-   Use **Discord Markdown**.
-   Use `###` for section headers.
-   Use `> ` for blockquotes.
-   Use syntax highlighting for code blocks (e.g., ```python ... ```).
-   **Do not** output any pre-text or post-text.
"""

# General System Design / CS Concepts
GENERAL_TOPICS = [
    # System Design
    "Design a URL Shortener (TinyURL)",
    "Design a Rate Limiter",
    "Design a Notification System",
    "Design a Chat Application (WhatsApp/Slack)",
    "Design a Key-Value Store (Redis)",
    "Design Instagram/Twitter Feed",
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

# Algorithmic Coding Questions
CODING_TOPICS = [
    "Reverse a Linked List",
    "Detect Cycle in Linked List",
    "Valid Parentheses",
    "Merge K Sorted Lists",
    "Top K Frequent Elements",
    "Longest Substring Without Repeating Characters",
    "Binary Tree Level Order Traversal",
    "Lowest Common Ancestor of a Binary Tree",
    "Two Sum",
    "Best Time to Buy and Sell Stock",
    "Coin Change (Dynamic Programming)",
    "Implement Trie (Prefix Tree)",
    # Graphs
    "Number of Islands",
    "Clone Graph",
    "Course Schedule (Topological Sort)",
    "Pacific Atlantic Water Flow",
    # Dynamic Programming
    "Climbing Stairs",
    "Longest Increasing Subsequence",
    "House Robber",
    "Word Break",
    # Intervals
    "Merge Intervals",
    "Insert Interval",
    "Non-overlapping Intervals",
    # Matrix
    "Spiral Matrix",
    "Word Search",
    # Binary Search
    "Search in Rotated Sorted Array",
    "Find Minimum in Rotated Sorted Array",
    # Heap / Priority Queue
    "Find Median from Data Stream",
    "Kth Largest Element in an Array",
    # Sliding Window
    "Minimum Window Substring",
    # Backtracking
    "Subsets",
    "Permutations",
    "Combination Sum",
    "Subsets II",
    "Permutations II",
    # Advanced Data Structures
    "LRU Cache",
    "LFU Cache",
    "Design Twitter",
    "Design In-Memory File System",
    "Find Median from Data Stream",
    "Serialize and Deserialize Binary Tree",
    # Strings (Advanced)
    "Minimum Window Substring",
    "Longest Palindromic Substring",
    "Word Ladder",
    "Decode Ways",
    "Regular Expression Matching",
    # Arrays (Advanced)
    "Trapping Rain Water",
    "Product of Array Except Self",
    "Maximum Subarray (Kadane's Algorithm)",
    "K Closest Points to Origin",
    "3Sum",
    # Trees & Graphs (Advanced)
    "Validate Binary Search Tree",
    "Construct Binary Tree from Preorder and Inorder Traversal",
    "Word Search II",
    "Alien Dictionary (Topological Sort)",
    "Cheapest Flights Within K Stops",
    # Bit Manipulation
    "Single Number",
    "Counting Bits",
    "Reverse Bits",
]

INTERVIEW_TOPICS = (
    GENERAL_TOPICS + CODING_TOPICS
)  # For backwards compatibility if needed, but we will use specific lists

# Discord Embed Color (Purple)
EMBED_COLOR = "9900ff"
