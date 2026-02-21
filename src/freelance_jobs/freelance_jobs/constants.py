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
    # Vietnamese market
    "Lập trình viên",
    "Tuyển dụng IT",
    "Freelance Vietnam",
    # Vietnamese skill/knowledge terms
    "Kỹ sư phần mềm",
    "Kỹ sư DevOps",
    "Kỹ sư AI",
    "Kỹ sư dữ liệu",
    "Quản trị cơ sở dữ liệu",
    "Điện toán đám mây",
    "Trí tuệ nhân tạo",
]

# Target high-quality remote/freelance job boards
JOB_SITES = [
    # International
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
    # Vietnamese
    "topdev.vn",
    "itviec.com",
    "vietnamworks.com",
    "vlance.vn",
    "fastwork.vn",
    "freec.asia",
    "topcv.vn",
    "careerbuilder.vn",
    "careerviet.vn",
    "vieclam24h.vn",
]

# Prompt for filtering/formatting
# Domain filtering is handled by Tavily's include_domains parameter in job_finder.py
JOB_SEARCH_QUERY_TEMPLATE = '"{{keyword}}" (remote OR freelance OR contract) last 3 days'


# Discord Embed Color (Green)
EMBED_COLOR = "00cc66"

# Prompt for Job Analysis using Prompt Engineering Patterns
# Pattern: Instruction Hierarchy (System Context → Constraints → Task → Output Schema
#          → Field Rules → Few-Shot Examples → Self-Verification → Input Data)
JOB_ANALYSIS_PROMPT = """
## System Context
You are a senior technical recruiter with 10+ years of experience analyzing freelance and contract job postings. You specialize in accurately extracting structured data from unstructured job descriptions across international and Vietnamese job boards.

## Constraints
- Extract ONLY information explicitly stated in the job description.
- NEVER infer, assume, or hallucinate data that is not present.
- If a field cannot be determined from the text, use null.
- Return ONLY the JSON array — no explanations or commentary outside the JSON.

## Task
For each job snippet provided, extract the following structured fields by reading the description carefully, step by step:

1. First, identify the **budget/rate** mentioned.
2. Then, list all **technical skills** (specific tools, languages, frameworks).
3. Next, list all **required knowledge** (domain expertise, experience level, methodologies, certifications, education).
4. Determine the **remote policy** (Remote, Hybrid, On-site).
5. Find the **contract duration**.
6. Note the **posted date** if available.
7. Finally, write a **concise 1-sentence summary** of the core responsibility.

## Output Schema
Return a strictly valid JSON array. Each object MUST follow this exact schema:
```json
{
  "budget": "string or null",
  "skills": ["string"],
  "required_knowledge": ["string"],
  "remote_policy": "string or null",
  "duration": "string or null",
  "posted_date": "string or null",
  "summary": "string"
}
```

## Field Extraction Rules

| Field | Extract | Do NOT Extract |
|-------|---------|----------------|
| skills | Specific technologies, languages, frameworks, tools (e.g., "Python", "Docker", "React", "PostgreSQL") | Soft skills, generic terms ("team player", "fast learner") |
| required_knowledge | Experience level, domain expertise, methodologies, certifications, degrees (e.g., "5+ years backend", "CI/CD pipelines", "Agile/Scrum", "AWS Certified") | Personality traits, company culture preferences |
| budget | Exact amounts or ranges as stated (e.g., "$50/hr", "$2000-3000 fixed") | Guessed amounts |
| remote_policy | "Remote", "Hybrid", "On-site", or null | — |
| duration | Contract length as stated (e.g., "3 months", "Long-term", "6-week sprint") | — |
| summary | One sentence describing the core role and responsibility | Multi-sentence descriptions |

## Examples

### Example 1 — International Posting (complete info)
Input:
Title: Python Dev needed
Content: We need a Python expert for a 3-month project. Budget is $40-60/hr. Must know Django and deployed on AWS. 3+ years experience with REST APIs and microservices required. Familiarity with CI/CD pipelines preferred. Remote only. Posted 2 days ago.

Output:
[
  {
    "budget": "$40-60/hr",
    "skills": ["Python", "Django", "AWS"],
    "required_knowledge": ["3+ years experience", "REST API design", "Microservices architecture", "CI/CD pipelines"],
    "remote_policy": "Remote",
    "duration": "3 months",
    "posted_date": "2 days ago",
    "summary": "Python developer needed for a 3-month remote project involving Django and AWS."
  }
]

### Example 2 — Vietnamese Posting (partial info)
Input:
Title: Tuyển Lập trình viên Frontend
Content: Công ty ABC tuyển lập trình viên React. Yêu cầu: thành thạo TypeScript, có kinh nghiệm 2 năm trở lên, hiểu biết về UX/UI. Làm việc remote. Lương thỏa thuận.

Output:
[
  {
    "budget": null,
    "skills": ["React", "TypeScript"],
    "required_knowledge": ["2+ years experience", "UX/UI knowledge"],
    "remote_policy": "Remote",
    "duration": null,
    "posted_date": null,
    "summary": "Frontend developer role requiring React and TypeScript with UX/UI knowledge."
  }
]

## Self-Verification
Before returning your response, verify:
1. Is the output strictly valid JSON (no trailing commas, no comments)?
2. Does every object contain ALL 7 fields?
3. Are "skills" and "required_knowledge" properly separated (no overlap)?
4. Have you avoided hallucinating any information not in the original text?

If any check fails, fix the output before returning.

## Input Data
Analyze the following jobs:
${jobs_content}
"""
