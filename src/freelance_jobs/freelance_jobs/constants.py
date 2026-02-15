"""Constants for Freelance Jobs Hook."""

# Curated list of high-value tech keywords
JOB_KEYWORDS = [
    # Frontend / Mobile
    "TypeScript",
    "Flutter",
    "React",
    # Backend / Systems
    "Python",
    "FastAPI",
    "Node.js",
    "C#",
    ".NET",
    # AI / Data
    "LangChain",
    "OpenAI API",
    "Data Engineering",
    "Machine Learning",
    # DevOps / Cloud
    "Kubernetes",
    "Terraform",
    "AWS Lambda",
    "AWS",
    # Web3
    "Solidity",
    "Smart Contract",
]

# Target high-quality remote/freelance job boards
JOB_SITES = [
    "weworkremotely.com",
    "remoteok.com",
    "wellfound.com",
    "remotive.com",
    "workingnomads.com",
    "dynamitejobs.com",
    "flexjobs.com",
    "crossover.com",
    "builtin.com",
    "himalayas.app",
    "justremote.co",
    "pangian.com",
    "linkedin.com",
    "indeed.com",
]

_SITES_QUERY = " OR ".join([f"site:{site}" for site in JOB_SITES])

# Prompt for filtering/formatting
# Uses OR to capture both "freelance" and "contract" terms along with specific sites
JOB_SEARCH_QUERY_TEMPLATE = (
    f'"{{keyword}}" (remote OR freelance OR contract) ({_SITES_QUERY}) last 3 days'
)

# Discord Embed Color (Green)
EMBED_COLOR = "00cc66"
