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

# Prompt for Job Analysis using Prompt Engineering Patterns
# Pattern: System Context -> Task Instruction -> Output Format -> Error Recovery -> Few-Shot Examples
JOB_ANALYSIS_PROMPT = """
You are an expert technical recruiter and data analyst. Your goal is to extract structured data from freelance job descriptions.

Task:
Analyze the provided job snippets and extract the following fields for each job:
- budget: The budget or rate mentioned (e.g., "$50/hr", "$2000 fixed"). If a range is given, keep the range.
- skills: A list of specific technical skills, languages, or frameworks mentioned (e.g., ["Python", "React", "AWS"]).
- remote_policy: The remote work policy (e.g., "Remote", "Hybrid", "On-site").
- duration: The duration of the contract (e.g., "3 months", "Long-term").
- posted_date: When the job was posted (e.g., "2 hours ago", "2023-10-27").
- summary: A concise 1-sentence summary of the role.

Output Format:
Return a strictly valid JSON list of objects. Each object must strictly follow this schema:
{
  "budget": "string or null",
  "skills": ["string"],
  "remote_policy": "string or null",
  "duration": "string or null",
  "posted_date": "string or null",
  "summary": "string"
}

Guide:
- If a field is not found, use null or "Unknown". Do NOT hallucinate.
- For 'skills', extract specific technologies, not generic terms like "Good communication".
- For 'summary', focus on the core responsibility (e.g., "Build a React dashboard for a fintech startup").

Examples:

Input:
Title: Python Dev needed
Content: We need a Python expert for a 3-month project. Budget is $40-60/hr. Must know Django and deployed on AWS. Remote.

Output:
[
  {
    "budget": "$40-60/hr",
    "skills": ["Python", "Django", "AWS"],
    "remote_policy": "Remote",
    "duration": "3 months",
    "posted_date": null,
    "summary": "Python developer needed for a 3-month project involving Django and AWS."
  }
]

Now, analyze the following jobs:
${jobs_content}
"""
