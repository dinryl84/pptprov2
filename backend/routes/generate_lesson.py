from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import json
import os

router = APIRouter()

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


class LessonRequest(BaseModel):
    area: str
    grade: str
    quarter: str
    session: str
    duration: str
    lc: str
    teacher: Optional[str] = "Teacher"
    lang: Optional[str] = "English"
    extra: Optional[str] = ""


def get_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=500,
            detail="DEEPSEEK_API_KEY not configured on server."
        )
    return key


def clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    # Extract first JSON object if there's extra text
    start = raw.find("{")
    if start != -1:
        raw = raw[start:]
    return raw


@router.post("/generate-lesson")
async def generate_lesson(req: LessonRequest):
    api_key = get_api_key()

    lang_rule = (
        f"CRITICAL: Write ALL lesson content strictly in {req.lang}. "
        "This applies to objectives, activities, instructions, examples, problems, and all text fields."
    )

    prompt = f"""You are a DepEd Senior High School lesson plan writer for the Philippines. Generate a complete, detailed lesson plan.

LESSON DETAILS:
- Learning Area: {req.area}
- Grade Level: {req.grade}
- Term: {req.quarter}
- Session: {req.session}
- Duration: {req.duration}
- Teacher: {req.teacher}
- Learning Competency: {req.lc}
- Language: {req.lang}
{f'- Additional Instructions: {req.extra}' if req.extra else ''}

{lang_rule}

Return ONLY a valid JSON object — no markdown fences, no extra text before or after. Use this exact structure:

{{
  "lessonTitle": "string — specific, not generic",
  "learningArea": "string",
  "gradeLevel": "string",
  "quarter": "string",
  "session": "string",
  "duration": "string",
  "teacherName": "string",
  "references": ["array of reference strings"],
  "learningCompetency": "string",
  "contentStandard": "string",
  "performanceStandard": "string",
  "objectives": ["4-5 specific measurable objectives"],
  "learnerContext": "string — 2-3 sentences on differentiation and context",
  "prelesson": {{
    "duration": "string e.g. 10 minutes",
    "title": "string — activity name",
    "description": "string — what teacher does/says",
    "steps": ["array of step strings"]
  }},
  "flow": [
    {{
      "phase": "Phase 1 — Direct Instruction",
      "duration": "string",
      "title": "string",
      "activities": ["array of activity strings"],
      "workedExamples": [
        {{
          "title": "string",
          "problem": "string",
          "solution": ["array of solution step strings"],
          "answer": "string"
        }}
      ]
    }},
    {{
      "phase": "Phase 2 — Guided Practice",
      "duration": "string",
      "title": "string",
      "activities": ["array"],
      "problems": [
        {{"label": "string", "problem": "string", "answer": "string"}}
      ]
    }},
    {{
      "phase": "Phase 3 — Independent Practice",
      "duration": "string",
      "title": "string",
      "activities": ["array"],
      "problems": [
        {{"label": "string", "problem": "string", "answer": "string"}}
      ]
    }}
  ],
  "wrapup": {{
    "duration": "string",
    "consolidation": "string",
    "exitTicket": {{
      "question": "string",
      "answer": "string"
    }}
  }},
  "resources": ["array of material strings"],
  "formativeAssessment": ["array"],
  "extendedLearning": ["array"],
  "teacherReflections": ["4-5 reflective question strings"],
  "answerKey": [
    {{"activity": "string", "item": "string", "solution": "string"}}
  ],
  "aiDeclaration": "AI was used to generate this lesson plan. The teacher is responsible for accuracy, appropriateness, and final classroom use."
}}

Use Filipino context (sari-sari store, palengke, Philippine peso ₱, DepEd references). All problems must have complete numeric solutions."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                DEEPSEEK_API_URL, headers=headers, json=payload
            )
            response.raise_for_status()
            data = response.json()

        raw = data["choices"][0]["message"]["content"]
        finish_reason = data["choices"][0].get("finish_reason", "")

        if finish_reason == "length":
            raise HTTPException(
                status_code=500,
                detail="Response was truncated. Please try again."
            )

        raw = clean_json(raw)
        lesson = json.loads(raw)
        return {"success": True, "lesson": lesson}

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"DeepSeek API error: {e.response.status_code} — {e.response.text}"
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse AI response as JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
