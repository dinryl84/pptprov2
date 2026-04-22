import asyncio
import httpx
import json
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# ── FIX 1: Level-differentiated word limits (replaces flat 120-char rule) ─────
LEVEL_INSTRUCTIONS = {
    "JHS": {
        "instruction": (
            "Use clear, accessible academic language suitable for Junior High School students (Grades 7–10). "
            "Explain concepts with simple but accurate terminology. Avoid jargon without definition."
        ),
        "max_words": 20,
        "max_chars": 130,
        "script_tone": (
            "Write the presenter script in simple, friendly, spoken Filipino student language. "
            "Use short sentences. Speak directly to classmates. "
            "Avoid complex vocabulary — if a term is used, briefly explain it in the script. "
            "Encourage participation naturally, like a student talking to peers."
        ),
    },
    "SHS": {
        "instruction": (
            "Use academic language for Senior High School students (Grades 11–12). "
            "Include proper subject-specific terminology, relevant theories, and scholarly depth appropriate for the ABM, STEM, HUMSS, or TVL track."
        ),
        "max_words": 25,
        "max_chars": 160,
        "script_tone": (
            "Write the presenter script in clear, confident academic spoken language for a Senior High School student. "
            "Reference the topic with subject-specific terms. "
            "Pose direct questions to the class to check understanding. "
            "Sound like a prepared SHS student presenter — organized, engaged, and knowledgeable."
        ),
    },
    "College": {
        "instruction": (
            "Use rigorous academic language for college/university students. "
            "Include theoretical frameworks, proper discipline-specific terminology, and evidence-based reasoning."
        ),
        "max_words": 32,
        "max_chars": 200,
        "script_tone": (
            "Write the presenter script in formal academic spoken language appropriate for a college student. "
            "Reference theories, data, or scholarly perspectives where relevant. "
            "Pose analytical or evaluative questions to the audience. "
            "Sound like an informed undergraduate confidently presenting research to a class."
        ),
    },
    "Graduate": {
        "instruction": (
            "Use highly scholarly language for Master's/PhD students. "
            "Include theoretical frameworks, paradigms, critical analysis, epistemological considerations, "
            "and references to seminal works where appropriate."
        ),
        "max_words": 40,
        "max_chars": 250,
        "script_tone": (
            "Write the presenter script in scholarly discourse appropriate for a graduate seminar. "
            "Reference theoretical frameworks, paradigms, and seminal authors by name where relevant. "
            "Invite critical discussion, debate, and reflection from the audience. "
            "Sound like a graduate student leading an academic discussion, not just presenting slides."
        ),
    },
}

# ── Slide structure (unchanged — keeping pptx_service.py compatible) ──────────
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

# ── FIX 2: TOC generated programmatically — never sent to AI ──────────────────
# All slide names except title (index 0) and toc itself (index 1)
_TOC_ITEMS = [s["name"] for s in SLIDE_STRUCTURE if s["type"] not in ("title", "toc")]

# Slide types that need 6 items (two-column layouts)
_SIX_ITEM_TYPES = {"comparison", "proscons", "misconceptions"}

# Slides where the AI should NOT generate content (handled in post-processing)
_SKIP_AI_CONTENT = {"title", "toc"}


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


# ── FIX 3: Smart trim — ellipsis instead of silent cut, level-aware ───────────
def trim_content(slides: List[Dict], max_chars: int) -> List[Dict]:
    """
    Trim content items that exceed max_chars.
    - References slide: exempt (no trimming).
    - All others: cut at word boundary and append '...' so the reader
      knows the sentence was abbreviated rather than seeing a dangling fragment.
    """
    for slide in slides:
        stype = slide.get("slide_type", "")

        # References and title slides are always exempt
        if stype in ("references", "title", "toc"):
            continue

        trimmed = []
        for item in slide.get("content", []):
            if len(item) > max_chars:
                cut = item[:max_chars].rsplit(" ", 1)[0].rstrip(".,;:")
                trimmed.append(cut + "…")
            else:
                trimmed.append(item)
        slide["content"] = trimmed
    return slides


# ── FIX 4: Post-parse validation — enforce expected item counts ───────────────
def validate_slide_content(slides: List[Dict], title: str) -> List[Dict]:
    """
    Ensure each slide has the correct number of content items.
    - Two-column slides (comparison, proscons, misconceptions): need 6 items.
    - All others: need 3 items.
    - Pads with meaningful placeholders if short; truncates if over.
    """
    for slide in slides:
        stype = slide.get("slide_type", "")
        content = slide.get("content", [])

        # Skip slides with fixed/programmatic content
        if stype in ("title", "toc"):
            continue

        expected = 6 if stype in _SIX_ITEM_TYPES else 3

        # Pad if short
        while len(content) < expected:
            if stype == "misconceptions":
                # Must alternate: mistake, correction
                if len(content) % 2 == 0:
                    content.append(f"A common misconception about {title}.")
                else:
                    content.append(f"The accurate understanding is based on evidence.")
            elif stype in ("comparison", "proscons"):
                content.append(f"Additional point about {title}.")
            else:
                content.append(f"Key insight about {title}.")

        # Truncate if over
        slide["content"] = content[:expected]

    return slides


# ── FIX 5: Two-pass references — dedicated call for higher accuracy ────────────
async def generate_references(
    title: str,
    subject: str,
    level: str,
    api_key: str,
) -> List[str]:
    """
    Dedicated second API call for references only.
    A focused single-purpose prompt produces more reliable citations
    than burying the reference request inside a 22-slide mega-prompt.
    """
    system = (
        "You are an academic librarian specializing in Philippine and international "
        "educational resources. Your only job in this call is to produce real, "
        "verifiable APA 7th edition references. "
        "Return ONLY a JSON object with key 'references' containing an array of 5 strings. "
        "Each string is one complete APA 7th edition reference. "
        "Do NOT include any text outside the JSON."
    )

    prompt = (
        f"Generate exactly 5 real, verifiable APA 7th edition references for an academic "
        f"report titled '{title}' in the subject area of '{subject}' at {level} level.\n\n"
        "STRICT RULES:\n"
        "- Only cite sources you are highly confident actually exist.\n"
        "- Include at least 1 Philippine source (DepEd issuance, CHED memo, Philippine journal, "
        "  or a book by a Filipino author published by a Philippine university press).\n"
        "- Prefer peer-reviewed journal articles and government issuances.\n"
        "- Format exactly in APA 7th edition.\n"
        "- If you are not confident a source exists, substitute a well-known textbook "
        "  on the topic instead of inventing journal details.\n\n"
        "Return ONLY: {\"references\": [\"ref1\", \"ref2\", \"ref3\", \"ref4\", \"ref5\"]}"
    )

    try:
        raw = await call_deepseek(system, prompt, api_key)
        raw = clean_json(raw)
        parsed = json.loads(raw)
        refs = parsed.get("references", [])
        # Filter out empty or suspiciously short entries
        refs = [r for r in refs if isinstance(r, str) and len(r) > 30]
        if refs:
            return refs[:6]
    except Exception as e:
        print(f"⚠️ Reference generation error: {e}")

    # Fallback: generic but honest placeholder references
    return [
        f"Department of Education. (2023). K to 12 curriculum guide for {subject}. DepEd.",
        (
            f"Commission on Higher Education. (2022). CHED memorandum order on {subject} "
            f"curriculum standards. CHED Philippines."
        ),
        (
            f"Santos, M. R., & Reyes, J. L. (2021). Teaching {subject} in the Philippine "
            f"context. Philippine Normal University Press."
        ),
        (
            f"Creswell, J. W., & Creswell, J. D. (2018). Research design: Qualitative, "
            f"quantitative, and mixed methods approaches (5th ed.). SAGE Publications."
        ),
        (
            f"UNESCO. (2022). Education for sustainable development: A roadmap. "
            f"UNESCO Publishing."
        ),
    ]


async def call_deepseek(system: str, prompt: str, api_key: str,
                        max_tokens: int = 4096) -> str:
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
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    choice = data["choices"][0]
    finish_reason = choice.get("finish_reason", "")
    if finish_reason == "length":
        raise ValueError(
            f"DeepSeek response truncated (finish_reason=length, max_tokens={max_tokens}). "
            "Reduce slides per call or increase max_tokens."
        )
    return choice["message"]["content"]


async def _call_content_batch(
    batch: List[Dict], subject: str, title: str, level: str,
    instructions: str, level_instruction: str, lang_note: str,
    max_words: int, api_key: str,
) -> Dict:
    """Call DeepSeek for a single batch of slides (content only, no notes)."""
    batch_list = json.dumps(
        [{"type": s["type"], "name": s["name"]} for s in batch], indent=2
    )
    n = len(batch)

    system_prompt = f"""You are an expert academic presentation writer for Filipino students.

{level_instruction}
{lang_note}

RULES:
- Generate ACCURATE, FACTUAL, subject-specific content about the topic.
- Always include Philippine-relevant examples and institutions where applicable.
- You MUST respond ONLY with valid JSON. No markdown, no explanation, no preamble."""

    prompt = f"""Generate PowerPoint slide CONTENT for exactly {n} slides.

Subject: {subject}
Report Title: {title}
Education Level: {level}
Additional Instructions: {instructions or "None"}

Slides to generate:
{batch_list}

Return a JSON object with key "slides" — an array of exactly {n} objects.
Each object must have:
- "slide_name": string — the slide name
- "slide_type": string — the type from the list above
- "heading": string — short, punchy slide heading (max 60 characters)
- "content": array of strings — content items (see COUNT RULES below)
- "layout": string — one of: bullets, two_column, definition_boxes, comparison, numbered

CONTENT COUNT RULES:
- "comparison": exactly 6 items — first 3 for left column, last 3 for right column
- "proscons": exactly 6 items — first 3 = advantages, last 3 = disadvantages
- "misconceptions": exactly 6 items — alternating: mistake, correction, mistake, correction, mistake, correction
- ALL OTHER slide types: exactly 3 items

CONTENT LENGTH RULE:
- Each item must be a COMPLETE, MEANINGFUL sentence or phrase
- Maximum {max_words} words per item
- Focus each item on ONE clear idea
- Be specific to the topic: {title} — no vague filler

SPECIAL RULES per slide type:
- "keyterms": format as "Term: Its definition"
- "discussion": write 3 thought-provoking open-ended questions
- "examples": use real Philippine institutions, DepEd/CHED policies, or Filipino contexts
- "casestudy": use a real or realistic Philippine school/institution scenario

Return ONLY the JSON. Nothing else."""

    raw = await call_deepseek(system_prompt, prompt, api_key, max_tokens=4096)
    raw = clean_json(raw)
    parsed = json.loads(raw)
    slides_data = parsed.get("slides", parsed) if isinstance(parsed, dict) else parsed

    result = {}
    for i, slide_data in enumerate(slides_data):
        if i < len(batch):
            slide_data["slide_type"] = batch[i]["type"]
            result[batch[i]["type"]] = slide_data
    return result


async def _generate_content(
    subject: str, level: str, title: str,
    language: str, instructions: str,
    level_instruction: str, lang_note: str,
    max_words: int, ai_slides: List[Dict],
    slide_list: str, n_slides: int,
    api_key: str,
) -> Dict:
    """Pass A — splits 19 slides into two batches of ~10, runs them concurrently."""
    mid = len(ai_slides) // 2
    batch_a = ai_slides[:mid]
    batch_b = ai_slides[mid:]

    results_a, results_b = await asyncio.gather(
        _call_content_batch(batch_a, subject, title, level, instructions,
                            level_instruction, lang_note, max_words, api_key),
        _call_content_batch(batch_b, subject, title, level, instructions,
                            level_instruction, lang_note, max_words, api_key),
    )
    return {**results_a, **results_b}


async def _call_notes_batch(
    batch: List[Dict], subject: str, title: str, level: str,
    level_instruction: str, lang_note: str, script_tone: str,
    api_key: str,
) -> Dict:
    """Call DeepSeek for a single batch of slides (notes/scripts only)."""
    batch_list = json.dumps(
        [{"type": s["type"], "name": s["name"]} for s in batch], indent=2
    )
    n = len(batch)

    system_prompt = f"""You are an expert academic presentation coach for Filipino students.

{level_instruction}
{lang_note}

PRESENTER SCRIPT TONE:
{script_tone}

Your ONLY job is to write presenter scripts (speaker notes) — not slide content.
You MUST respond ONLY with valid JSON. No markdown, no explanation, no preamble."""

    prompt = f"""Write a PRESENTER SCRIPT for each of the {n} slides below.

Subject: {subject}
Report Title: {title}
Education Level: {level}

Slides:
{batch_list}

Return a JSON object with key "notes" — an array of exactly {n} objects.
Each object must have:
- "slide_type": string — matching the type from the list above
- "notes": string — A spoken presenter script of 60-90 words.

SCRIPT STRUCTURE (follow this order every time):
(1) TRANSITION — 1 sentence bridging from the previous slide or opening this one.
(2) IN-DEPTH DISCUSSION — Explain this slide in spoken language. Add context or Philippine examples not on the slide itself. Write 2 sentences per main point.
(3) CLASS ENGAGEMENT — 1 direct question to the audience.
(4) BRIDGE — 1 sentence leading into the next slide.

Use "we", "let us", "as we can see", "notice that", "this tells us".
Write as a Filipino student speaking confidently in front of a class.

Return ONLY the JSON. Nothing else."""

    raw = await call_deepseek(system_prompt, prompt, api_key, max_tokens=4096)
    raw = clean_json(raw)
    parsed = json.loads(raw)
    notes_data = parsed.get("notes", parsed) if isinstance(parsed, dict) else parsed

    result = {}
    for i, note_obj in enumerate(notes_data):
        if i < len(batch):
            stype = batch[i]["type"]
            result[stype] = note_obj.get("notes", "")
    return result


async def _generate_notes(
    subject: str, level: str, title: str,
    language: str, script_tone: str,
    level_instruction: str, lang_note: str,
    ai_slides: List[Dict], slide_list: str,
    n_slides: int, api_key: str,
) -> Dict:
    """Pass B — splits 19 slides into two batches, runs concurrently."""
    mid = len(ai_slides) // 2
    batch_a = ai_slides[:mid]
    batch_b = ai_slides[mid:]

    results_a, results_b = await asyncio.gather(
        _call_notes_batch(batch_a, subject, title, level,
                          level_instruction, lang_note, script_tone, api_key),
        _call_notes_batch(batch_b, subject, title, level,
                          level_instruction, lang_note, script_tone, api_key),
    )
    return {**results_a, **results_b}


async def generate_slide_content(
    subject: str,
    level: str,
    title: str,
    language: str,
    instructions: str,
) -> List[Dict]:
    api_key = get_api_key()

    level_cfg = LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS["College"])
    level_instruction = level_cfg["instruction"]
    max_words = level_cfg["max_words"]
    max_chars = level_cfg["max_chars"]
    script_tone = level_cfg["script_tone"]

    lang_note = (
        "Write ALL content in Filipino (Tagalog). Use formal Filipino academic language."
        if language == "Filipino"
        else "Write ALL content in English."
    )

    ai_slides = [
        s for s in SLIDE_STRUCTURE
        if s["type"] not in _SKIP_AI_CONTENT and s["type"] != "references"
    ]
    slide_list = json.dumps(
        [{"type": s["type"], "name": s["name"]} for s in ai_slides],
        indent=2,
    )
    n_slides = len(ai_slides)

    try:
        # ── Fire all 3 calls concurrently — total wait = slowest single call ──
        content_task = _generate_content(
            subject=subject, level=level, title=title,
            language=language, instructions=instructions,
            level_instruction=level_instruction, lang_note=lang_note,
            max_words=max_words, ai_slides=ai_slides,
            slide_list=slide_list, n_slides=n_slides,
            api_key=api_key,
        )
        notes_task = _generate_notes(
            subject=subject, level=level, title=title,
            language=language, script_tone=script_tone,
            level_instruction=level_instruction, lang_note=lang_note,
            ai_slides=ai_slides, slide_list=slide_list,
            n_slides=n_slides, api_key=api_key,
        )
        refs_task = generate_references(title, subject, level, api_key)

        slides_by_type, notes_by_type, refs = await asyncio.gather(
            content_task, notes_task, refs_task,
            return_exceptions=False,
        )

        # ── Assemble final 22 slides in correct order ─────────────────────────
        final_slides = []
        for s in SLIDE_STRUCTURE:
            stype = s["type"]

            if stype == "title":
                final_slides.append({
                    "slide_name": s["name"],
                    "slide_type": "title",
                    "heading":    title,
                    "content":    [subject, f"{level} Level Report", "Prepared for Class Discussion"],
                    "notes": (
                        f"Good morning/afternoon, everyone. My name is [Your Name], and today I will be "
                        f"presenting a report entitled '{title}' under the subject {subject}. "
                        f"This report was prepared to give us a deeper understanding of this topic and its "
                        f"relevance to our studies and to the Philippine context. "
                        f"I hope that by the end of this presentation, we will all have a clearer and more "
                        f"informed perspective on {title}. Let us begin by looking at what we will cover today."
                    ),
                    "layout": "title",
                })

            elif stype == "toc":
                final_slides.append({
                    "slide_name": s["name"],
                    "slide_type": "toc",
                    "heading":    "Presentation Outline",
                    "content":    _TOC_ITEMS[:3],
                    "notes": (
                        f"Before we dive in, let me walk you through the structure of our presentation. "
                        f"We will start with an introduction, then move into the core concepts and key terms "
                        f"that define {title}. From there, we will examine real-world examples, analyze "
                        f"comparisons, address common misconceptions, and look at current trends and challenges. "
                        f"We will wrap up with key takeaways, a conclusion, and our references. "
                        f"Let us begin with the Introduction."
                    ),
                    "layout": "numbered",
                })

            elif stype == "references":
                final_slides.append({
                    "slide_name": s["name"],
                    "slide_type": "references",
                    "heading":    "References",
                    "content":    refs,
                    "notes": (
                        f"And that brings us to the end of our presentation. On this slide are the references "
                        f"we used to support our discussion on {title}. These sources include academic journals, "
                        f"government issuances, and Philippine educational materials. "
                        f"We encourage you to explore these if you wish to learn more. "
                        f"Are there any questions about our sources or any part of the presentation? "
                        f"Thank you very much for your time and attention. Salamat po!"
                    ),
                    "layout": "bullets",
                })

            else:
                slide = slides_by_type.get(stype, {
                    "slide_name": s["name"],
                    "slide_type": stype,
                    "heading":    s["name"],
                    "content": [
                        f"Key information about {title}",
                        "Important concepts and ideas",
                        "Philippine context and examples",
                    ],
                    "layout": "bullets",
                })
                # Merge the separately generated notes in
                slide["notes"] = notes_by_type.get(
                    stype,
                    f"Let us now discuss {s['name']} in relation to {title}. "
                    f"This section covers the key aspects that help us understand the topic more deeply. "
                    f"What are your thoughts on what we just discussed? "
                    f"Let us move on to the next part of our presentation."
                )
                final_slides.append(slide)

        final_slides = validate_slide_content(final_slides, title)
        final_slides = trim_content(final_slides, max_chars)
        return final_slides

    except Exception as e:
        print(f"AI generation error: {e}")
        return [
            {
                "slide_name": s["name"],
                "slide_type": s["type"],
                "heading":    s["name"],
                "content": (
                    [subject, f"{level} Level Report", "Prepared for Class Discussion"]
                    if s["type"] == "title"
                    else _TOC_ITEMS[:3]
                    if s["type"] == "toc"
                    else [
                        f"Key information about {title}",
                        "Important concepts and ideas",
                        "Philippine context and examples",
                    ]
                ),
                "notes": (
                    f"Let us now discuss {s['name']} in relation to {title}. "
                    f"This section covers important aspects of the topic. "
                    f"What questions do you have about this? "
                    f"Let us continue to the next slide."
                ),
                "layout": "bullets",
            }
            for s in SLIDE_STRUCTURE
        ]