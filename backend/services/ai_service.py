import httpx
import json
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

LEVEL_INSTRUCTIONS = {
    "JHS":      "Use academic language for Junior High School students. Include proper terminology, theories, and scholarly depth.",
    "SHS":      "Use academic language for Senior High School students. Include proper terminology, theories, and scholarly depth.",
    "College":  "Use academic language for college/university students. Include proper terminology, theories, and scholarly depth.",
    "Graduate": "Use highly academic, scholarly language for Master's/PhD students. Include theoretical frameworks, citations, and critical analysis.",
}

SLIDE_STRUCTURE = [
    {"type": "title",           "name": "Title Slide"},
    {"type": "toc",             "name": "Table of Contents"},
    {"type": "intro",           "name": "Introduction"},
    {"type": "background",      "name": "Background & Context"},
    {"type": "keyterms",        "name": "Key Terms & Definitions"},
    {"type": "concept1",        "name": "Core Concept 1"},
    {"type": "concept2",        "name": "Core Concept 2"},
    {"type": "concept3",        "name": "Core Concept 3"},
    {"type": "deepdive",        "name": "In-Depth Discussion"},
    {"type": "types",           "name": "Types & Classifications"},
    {"type": "examples",        "name": "Real-World Examples (Philippine Context)"},
    {"type": "comparison",      "name": "Comparison & Analysis"},
    {"type": "proscons",        "name": "Advantages & Disadvantages"},
    {"type": "misconceptions",  "name": "Common Misconceptions"},
    {"type": "casestudy",       "name": "Case Study"},
    {"type": "trends",          "name": "Current Trends"},
    {"type": "challenges",      "name": "Challenges & Issues"},
    {"type": "recommendations", "name": "Recommendations"},
    {"type": "discussion",      "name": "Discussion Questions"},
    {"type": "takeaways",       "name": "Key Takeaways"},
    {"type": "conclusion",      "name": "Conclusion"},
    {"type": "references",      "name": "References"},
]


def get_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "DEEPSEEK_API_KEY environment variable is not set. "
            "Please add it to your .env file or Render environment variables."
        )
    return key


def clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def trim_content(slides: List[Dict]) -> List[Dict]:
    """Trim bullets > 150 chars at word boundary. References exempt."""
    for slide in slides:
        if slide.get("slide_type") == "references":
            continue
        trimmed = []
        for item in slide.get("content", []):
            if len(item) > 150:
                cut = item[:150].rsplit(" ", 1)[0]
                trimmed.append(cut)
            else:
                trimmed.append(item)
        slide["content"] = trimmed
    return slides


async def call_deepseek(system: str, prompt: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 8192,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def generate_slide_content(
    subject: str,
    level: str,
    title: str,
    language: str,
    instructions: str,
) -> List[Dict]:
    api_key = get_api_key()
    level_instruction = LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS["College"])
    lang_note = (
        "Write ALL content in Filipino (Tagalog). Use formal Filipino academic language."
        if language == "Filipino"
        else "Write ALL content in English."
    )

    slide_list = json.dumps(
        [{"type": s["type"], "name": s["name"]} for s in SLIDE_STRUCTURE],
        indent=2,
    )

    system_prompt = f"""You are an expert academic presentation writer for Filipino students with deep knowledge across all academic subjects.

{level_instruction}
{lang_note}

IMPORTANT RULES:
- Draw from your trained knowledge to generate ACCURATE, FACTUAL content about the topic.
- For the References slide: generate 5-6 REAL, VERIFIABLE academic references. Use authors, journals, and publishers you are confident about. Format in APA 7th edition. Include at least 1-2 Philippine sources (DepEd, CHED, Philippine journals) where relevant.
- Do NOT hallucinate or invent fake references. Only cite sources you are certain exist.
- Always include Philippine-relevant examples and context.
- Generate comprehensive content that will impress Filipino teachers.
- You MUST respond ONLY with valid JSON. No markdown, no explanation, no preamble."""

    prompt = f"""Generate complete PowerPoint slide content for ALL 22 slides in ONE response.

Subject: {subject}
Report Title: {title}
Education Level: {level}
Additional Instructions: {instructions or "None"}

Slides to generate:
{slide_list}

Return a JSON object with key "slides" — an array of exactly 22 objects.
Each object must have:
- "slide_name": string — the slide name
- "slide_type": string — the type from the list
- "heading": string — short, punchy, engaging slide heading (max 60 characters)
- "content": array of strings — exactly 3 content items per slide (see rules below)
- "notes": string — 2-3 sentences of speaker notes for the student presenter
- "layout": string — one of: bullets, two_column, definition_boxes, comparison, numbered

CONTENT LENGTH RULE (critical for slide layout):
- Each content item must be a COMPLETE, MEANINGFUL sentence or phrase
- Maximum 120 characters per item — if longer, split the idea into two items
- Write with academic depth but keep each point focused on ONE idea only
- Do NOT combine multiple ideas into one long run-on bullet point

SPECIAL RULES per slide type:
- "title": content = ["{subject}", "{level} Level Report", "Prepared for Class Discussion"]
- "toc": content = list of all 20 other slide names as navigation items
- "keyterms": content = term: definition format, e.g. "Research Methodology: The systematic study of methods used in research"
- "comparison": content = first half for left column, second half for right column (3 items each = 6 total)
- "proscons": content = first half = advantages, second half = disadvantages (3 items each = 6 total)
- "misconceptions": content = alternating mistake then correction pairs (3 pairs = 6 total)
- "discussion": content = 3 thought-provoking questions
- "references": content = 5-6 REAL APA 7th edition references about {title}. Only cite sources you are 100% certain exist.
- "examples": Always use real Philippine institutions, DepEd/CHED policies, or Filipino contexts
- "casestudy": Use a real or realistic Philippine school/institution scenario

Return ONLY the JSON. Nothing else."""

    try:
        raw = await call_deepseek(system_prompt, prompt, api_key)
        raw = clean_json(raw)
        parsed = json.loads(raw)
        slides_data = parsed.get("slides", parsed) if isinstance(parsed, dict) else parsed

        slides = []
        for i, slide_data in enumerate(slides_data):
            if i < len(SLIDE_STRUCTURE):
                slide_data["slide_type"] = SLIDE_STRUCTURE[i]["type"]
            slides.append(slide_data)

        slides = trim_content(slides)
        return slides

    except Exception as e:
        print(f"AI generation error: {e}")
        # Return fallback slides
        return [
            {
                "slide_name": s["name"],
                "slide_type": s["type"],
                "heading": s["name"],
                "content": [
                    f"Key information about {title}",
                    "Important concepts and ideas",
                    "Philippine context and examples",
                ],
                "notes": f"Discuss the {s['name']} section in detail with your class.",
                "layout": "bullets",
            }
            for s in SLIDE_STRUCTURE
        ]
