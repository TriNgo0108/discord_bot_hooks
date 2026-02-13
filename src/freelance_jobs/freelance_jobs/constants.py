"""Constants for Freelance Jobs Hook."""

# Curated list of high-value tech keywords
JOB_KEYWORDS = [
    # Frontend / Mobile
    "React Native",
    "Next.js",
    "TypeScript",
    "Flutter",
    # Backend / Systems
    "Python",
    "FastAPI",
    "Node.js",
    # AI / Data
    "LangChain",
    "OpenAI API",
    "Data Engineering",
    "Machine Learning",
    # DevOps / Cloud
    "Kubernetes",
    "Terraform",
    "AWS Lambda",
    # Web3
    "Solidity",
    "Smart Contract",
]

# Prompt for filtering/formatting
# Uses OR to capture both "freelance" and "contract" terms
JOB_SEARCH_QUERY_TEMPLATE = (
    '"{keyword}" (freelance OR contract) remote job last 3 days -upwork -fiverr'
)

# Discord Embed Color (Green)
EMBED_COLOR = "00cc66"
