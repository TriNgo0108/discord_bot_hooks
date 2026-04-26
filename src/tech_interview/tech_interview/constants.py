"""Constants for English Grammar Hook."""

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — Role identity & behavioral constraints
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are **GrammarCoach**, an experienced English language instructor \
specializing in teaching grammar to non-native speakers. You have 10+ years \
of experience helping intermediate-to-advanced learners master English \
grammar through clear explanations, memorable examples, and practical exercises.

## Behavioral Constraints
- **Language**: English only.
- **Tone**: Friendly, patient, and encouraging — like a supportive tutor \
in a one-on-one session. Avoid being overly academic or dry.
- **Depth**: Target intermediate-to-advanced learners (B1–C1 level). \
Skip absolute beginner concepts (e.g., what a noun is). \
Focus on *nuance*, *common mistakes*, and *natural-sounding usage*.
- **Accuracy**: All grammar rules, examples, and explanations must be \
linguistically correct. When a rule has exceptions, mention them.
- **Examples**: Use realistic, everyday sentences — not textbook-style \
artificial examples. Show both correct and incorrect usage side by side.
- **Formatting**: Use Discord Markdown exclusively. \
Use `###` for section headers, `> ` for blockquotes, and \
bold/italic for emphasis.
- **No Preamble**: Do not include greetings, disclaimers, or sign-offs. \
Start directly with the first section header.
"""

# ─────────────────────────────────────────────────────────────────────────────
# USER PROMPT — Task instructions, context, and output structure
# ─────────────────────────────────────────────────────────────────────────────

GRAMMAR_PROMPT = """\
## Task
Create an engaging **Grammar Drop** on the topic below. \
This will be read by non-native English speakers who want to improve \
their grammar during a 3-minute study session.

## Topic
**{topic}**

## Reference Context (web search results — use as grounding, not as outline)
<context>
{context}
</context>

## Chain-of-Thought (internal reasoning — do NOT include in output)
Before writing, silently reason through:
1. What is the core rule that learners must understand?
2. What mistake do non-native speakers make most often with this topic?
3. What is the simplest way to explain this so it clicks instantly?

## Required Sections (preserve this order)

### 📖 The Rule
> State the grammar rule clearly in 2–3 sentences. \
Use simple, direct language. If there are multiple forms, \
present them in a clean table or list.

### 🔍 How It Works
- Explain *when* and *why* this rule applies.
- If there are multiple cases or forms, walk through each one \
with a brief explanation.
- Use a comparison table if it helps clarify differences \
(e.g., Present Perfect vs Past Simple).

### ✅ Correct vs ❌ Incorrect
- Provide 3–4 pairs of sentences showing correct and incorrect usage.
- Format each pair like this:
  - ❌ *She have been to Paris.* → ✅ *She has been to Paris.*
- Briefly explain *why* the incorrect version is wrong.

### 💡 Pro Tips
- Share 2–3 practical tips or memory tricks that help learners \
remember this rule.
- Include any common exceptions or edge cases.

### 🎯 Quick Quiz
- Provide 3 fill-in-the-blank or choose-the-correct-option exercises.
- Put the answers in a spoiler tag using Discord format: `||answer||`.

## Quality Guardrails
After generating everything, silently self-verify:
- [ ] Every section is present and non-empty.
- [ ] All example sentences sound natural (not textbook-artificial).
- [ ] Correct vs Incorrect pairs clearly show the mistake and fix.
- [ ] Quiz answers are accurate and placed in spoiler tags.
- [ ] Total length fits within ~1500 words (Discord embed friendly).
If any check fails, revise the relevant section before outputting.

## Output
Write the grammar drop now. Start with `### 📖 The Rule`.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Topic Lists
# ─────────────────────────────────────────────────────────────────────────────

GRAMMAR_TOPICS = [
    # Tenses
    "Present Simple vs Present Continuous",
    "Past Simple vs Present Perfect",
    "Present Perfect vs Present Perfect Continuous",
    "Past Simple vs Past Continuous",
    "Past Perfect: When and How to Use It",
    "Future Tenses: Will vs Going To vs Present Continuous",
    "The Difference Between 'Used To' and 'Would'",
    # Articles & Determiners
    "Articles: A, An, and The — When to Use Each",
    "Zero Article: When to Drop 'The'",
    "Some vs Any: Rules and Exceptions",
    "Much, Many, A Lot Of: Countable vs Uncountable Nouns",
    "Each vs Every: Subtle Differences",
    "This, That, These, Those: Demonstratives",
    # Prepositions
    "Prepositions of Time: In, On, At",
    "Prepositions of Place: In, On, At",
    "Prepositions After Adjectives (e.g., Good At, Interested In)",
    "Prepositions After Verbs (e.g., Depend On, Agree With)",
    "By, Until, and By the Time",
    # Conditionals
    "Zero and First Conditional",
    "Second Conditional: Unreal Present Situations",
    "Third Conditional: Unreal Past Situations",
    "Mixed Conditionals: Combining Second and Third",
    "Wish and If Only: Expressing Regret",
    # Modal Verbs
    "Can, Could, and Be Able To",
    "Must vs Have To vs Need To",
    "Should, Ought To, and Had Better",
    "May vs Might: Degrees of Probability",
    "Modal Verbs for Deduction: Must, Can't, Might",
    # Passive Voice
    "Active vs Passive Voice: When to Use Each",
    "Passive Voice in Different Tenses",
    "Get + Past Participle (e.g., Get Fired, Get Married)",
    "Causative: Have/Get Something Done",
    # Reported Speech
    "Reported Speech: Statements",
    "Reported Speech: Questions and Commands",
    "Reporting Verbs: Say, Tell, Ask, Suggest, Recommend",
    # Clauses & Sentence Structure
    "Relative Clauses: Who, Which, That, Whose",
    "Defining vs Non-Defining Relative Clauses",
    "Noun Clauses: That-Clauses and Wh-Clauses",
    "Adverbial Clauses: Because, Although, While, If",
    "Participle Clauses: Replacing Relative Clauses",
    # Gerunds & Infinitives
    "Gerund vs Infinitive: Which Verbs Take Which?",
    "Verbs Followed by Gerund (e.g., Enjoy, Avoid, Consider)",
    "Verbs Followed by Infinitive (e.g., Want, Decide, Hope)",
    "Verbs That Change Meaning: Stop, Remember, Try, Forget",
    # Confusing Words
    "Make vs Do: Usage Differences",
    "Say vs Tell: When to Use Each",
    "Bring vs Take: Direction Matters",
    "Borrow vs Lend: Who Gives and Who Gets?",
    "Like vs As: Comparison vs Role",
    "So vs Such: Intensifiers",
    "Still, Yet, Already, and Just",
    "Too vs Enough: Position and Meaning",
    "Even, Even If, and Even Though",
    # Word Order & Inversion
    "Adjective Order in English (Opinion-Size-Age-Shape-Color)",
    "Adverb Placement: Where to Put Adverbs in a Sentence",
    "Inversion After Negative Adverbs (e.g., Never Have I Seen)",
    # Punctuation & Writing
    "Commas: The Essential Rules",
    "Semicolons vs Colons: When to Use Each",
    "Apostrophes: Possession and Contractions",
    "Direct and Indirect Questions",
    # Common Mistake Areas
    "Subject-Verb Agreement: Tricky Cases",
    "Pronoun Reference: Avoiding Ambiguity",
    "Parallel Structure in Lists and Comparisons",
    "Double Negatives: Why to Avoid Them",
    "Dangling Modifiers: How to Fix Them",
    "Run-On Sentences and Comma Splices",
    # Idiomatic & Advanced
    "Phrasal Verbs: Separable vs Inseparable",
    "Collocations: Natural Word Combinations",
    "Linking Words and Connectors for Writing",
    "Emphasis with Cleft Sentences (It Is... That/Who)",
    "Inversion for Emphasis in Formal English",
]

# Discord Embed Color (Green — learning/growth)
EMBED_COLOR = "2ecc71"
