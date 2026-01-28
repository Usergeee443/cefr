from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import uvicorn
import uuid
import json
import os
import re
import httpx
import asyncio
from datetime import datetime

# Import test data
from data.test_data import READING_TEST, LISTENING_TEST, WRITING_TEST, CEFR_LEVELS, WRITING_BAND_DESCRIPTORS

app = FastAPI(title="CEFR Mock Test Platform")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# In-memory session storage (for demo - use Redis/DB in production)
sessions: Dict[str, Dict] = {}

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


class WritingSubmission(BaseModel):
    task1_response: str
    task2_response: str
    essay_response: str


def get_session(session_id: str) -> Dict:
    """Get or create a session"""
    if session_id not in sessions:
        sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "reading": {"completed": False, "answers": {}, "score": 0, "total": 0},
            "listening": {"completed": False, "answers": {}, "score": 0, "total": 0},
            "writing": {"completed": False, "responses": {}, "scores": {}, "feedback": {}},
            "overall_score": 0,
            "cefr_level": None
        }
    return sessions[session_id]


def calculate_reading_score(answers: Dict[str, str]) -> Dict:
    """Calculate reading test score"""
    correct = 0
    total = 0
    details = []

    for part in READING_TEST["parts"]:
        part_type = part["type"]

        if part_type in ["multiple_choice_cloze", "multiple_choice_comprehension"]:
            for q in part["questions"]:
                total += 1
                q_num = str(q["number"])
                user_answer = answers.get(q_num, "").strip().upper()
                correct_answer = q["correct"].upper()
                is_correct = user_answer == correct_answer
                if is_correct:
                    correct += 1
                details.append({
                    "question": q_num,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "part": part["part_number"]
                })

        elif part_type == "open_cloze":
            for q in part["questions"]:
                total += 1
                q_num = str(q["number"])
                user_answer = answers.get(q_num, "").strip().lower()
                correct_answer = q["correct"].lower()
                # Allow some flexibility for open cloze
                is_correct = user_answer == correct_answer
                if is_correct:
                    correct += 1
                details.append({
                    "question": q_num,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "part": part["part_number"]
                })

        elif part_type == "gapped_text":
            for q in part["questions"]:
                total += 1
                q_num = str(q["number"])
                user_answer = answers.get(q_num, "").strip().upper()
                correct_answer = q["correct"].upper()
                is_correct = user_answer == correct_answer
                if is_correct:
                    correct += 1
                details.append({
                    "question": q_num,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "part": part["part_number"]
                })

    percentage = (correct / total * 100) if total > 0 else 0
    return {
        "correct": correct,
        "total": total,
        "percentage": round(percentage, 1),
        "details": details
    }


def calculate_listening_score(answers: Dict[str, str]) -> Dict:
    """Calculate listening test score"""
    correct = 0
    total = 0
    details = []

    for part in LISTENING_TEST["parts"]:
        part_type = part["type"]

        if part_type == "short_conversations":
            for q in part["questions"]:
                total += 1
                q_num = str(q["number"])
                user_answer = answers.get(q_num, "").strip().upper()
                correct_answer = q["correct"].upper()
                is_correct = user_answer == correct_answer
                if is_correct:
                    correct += 1
                details.append({
                    "question": q_num,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "part": part["part_number"]
                })

        elif part_type == "sentence_completion":
            for q in part["questions"]:
                total += 1
                q_num = str(q["number"])
                user_answer = answers.get(q_num, "").strip().lower()
                correct_answer = q["correct"].lower()
                # Be flexible with case and minor variations
                is_correct = user_answer == correct_answer or correct_answer in user_answer
                if is_correct:
                    correct += 1
                details.append({
                    "question": q_num,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "part": part["part_number"]
                })

        elif part_type == "multiple_matching":
            for answer in part["answers"]:
                total += 1
                q_num = str(answer["number"])
                user_answer = answers.get(q_num, "").strip().upper()
                correct_answer = answer["correct"].upper()
                is_correct = user_answer == correct_answer
                if is_correct:
                    correct += 1
                details.append({
                    "question": q_num,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "part": part["part_number"]
                })

        elif part_type == "interview":
            for q in part["questions"]:
                total += 1
                q_num = str(q["number"])
                user_answer = answers.get(q_num, "").strip().upper()
                correct_answer = q["correct"].upper()
                is_correct = user_answer == correct_answer
                if is_correct:
                    correct += 1
                details.append({
                    "question": q_num,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "part": part["part_number"]
                })

    percentage = (correct / total * 100) if total > 0 else 0
    return {
        "correct": correct,
        "total": total,
        "percentage": round(percentage, 1),
        "details": details
    }


async def evaluate_writing_with_ai(task1: str, task2: str, essay: str) -> Dict:
    """Evaluate writing using AI with strict CEFR criteria"""

    # First, detect spam/invalid submissions
    def is_spam_or_invalid(text: str) -> tuple:
        """Check if text is spam, repeated words, or otherwise invalid"""
        if not text or len(text.strip()) < 20:
            return True, "Text is too short"

        words = text.lower().split()
        if len(words) < 10:
            return True, "Not enough words"

        # Check for repeated words (spam detection)
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        # If any single word is more than 50% of the text, it's spam
        max_count = max(word_counts.values())
        if max_count > len(words) * 0.5:
            return True, "Repetitive/spam content detected"

        # Check for very low vocabulary diversity
        unique_words = len(set(words))
        if unique_words < len(words) * 0.2:  # Less than 20% unique words
            return True, "Extremely low vocabulary diversity - spam detected"

        # Check if it's just random characters or keyboard spam
        alpha_chars = sum(1 for c in text if c.isalpha())
        if alpha_chars < len(text) * 0.5:
            return True, "Invalid characters - not proper English text"

        return False, None

    # Check each part for spam
    spam_results = {}
    for name, content in [("task1", task1), ("task2", task2), ("essay", essay)]:
        is_spam, reason = is_spam_or_invalid(content)
        spam_results[name] = {"is_spam": is_spam, "reason": reason}

    # If all are spam, return very low scores
    if all(r["is_spam"] for r in spam_results.values()):
        return {
            "task1": {
                "score": 1,
                "band": 1,
                "feedback": {
                    "overall": "Your submission appears to be spam or invalid text. Please write a genuine response addressing the task requirements.",
                    "content": "No relevant content provided.",
                    "organization": "No recognizable structure.",
                    "language": "No appropriate language use detected.",
                    "accuracy": "Cannot evaluate accuracy on invalid submission."
                },
                "word_count": len(task1.split()),
                "is_valid": False
            },
            "task2": {
                "score": 1,
                "band": 1,
                "feedback": {
                    "overall": "Your submission appears to be spam or invalid text. Please write a genuine review addressing the task requirements.",
                    "content": "No relevant content provided.",
                    "organization": "No recognizable structure.",
                    "language": "No appropriate language use detected.",
                    "accuracy": "Cannot evaluate accuracy on invalid submission."
                },
                "word_count": len(task2.split()),
                "is_valid": False
            },
            "essay": {
                "score": 1,
                "band": 1,
                "feedback": {
                    "overall": "Your submission appears to be spam or invalid text. Please write a genuine essay discussing both views.",
                    "task_achievement": "Task not addressed.",
                    "coherence_cohesion": "No coherent structure.",
                    "lexical_resource": "No meaningful vocabulary use.",
                    "grammatical_range": "Cannot evaluate grammar on invalid submission."
                },
                "word_count": len(essay.split()),
                "is_valid": False
            },
            "overall_score": 1,
            "overall_band": 1,
            "overall_percentage": 10,
            "cefr_level": "A1",
            "general_feedback": "Your submissions were detected as spam or invalid text. Please provide genuine English responses that address the task requirements."
        }

    # Prepare the evaluation prompt
    evaluation_prompt = f"""You are a strict CEFR English examiner. Evaluate the following writing submissions according to official CEFR B2/C1 examination standards.

BE VERY STRICT. Do not give high scores to:
- Repetitive text (same words repeated)
- Text that doesn't address the task
- Very short responses
- Responses with many grammar errors
- Responses with limited vocabulary

TASK 1 - Email/Letter (120-150 words required):
The task was to write a complaint email about a faulty laptop (screen crack, missing key, battery issues).
---
{task1}
---
Word count: {len(task1.split())}

TASK 2 - Review (120-150 words required):
The task was to write a book/film/TV series review with description, opinion, and recommendation.
---
{task2}
---
Word count: {len(task2.split())}

ESSAY (250-300 words required):
The task was to discuss whether technology has made life easier or more stressful, presenting both views.
---
{essay}
---
Word count: {len(essay.split())}

For each piece, evaluate STRICTLY on a scale of 1-9:
1-2: Non-existent or spam/irrelevant
3-4: Very weak, many errors, doesn't address task
5: Modest attempt, addresses task partially
6: Competent, addresses task with some weaknesses
7: Good, clear communication with minor issues
8: Very good, fluent with minimal errors
9: Expert, near-native quality

Respond in this exact JSON format:
{{
    "task1": {{
        "score": <1-9>,
        "content": "<feedback on content/task achievement>",
        "organization": "<feedback on organization>",
        "language": "<feedback on language use>",
        "accuracy": "<feedback on grammar/spelling>"
    }},
    "task2": {{
        "score": <1-9>,
        "content": "<feedback on content/task achievement>",
        "organization": "<feedback on organization>",
        "language": "<feedback on language use>",
        "accuracy": "<feedback on grammar/spelling>"
    }},
    "essay": {{
        "score": <1-9>,
        "task_achievement": "<feedback>",
        "coherence_cohesion": "<feedback>",
        "lexical_resource": "<feedback>",
        "grammatical_range": "<feedback>"
    }},
    "general_feedback": "<overall assessment and recommendations>"
}}

Remember: Be STRICT. A score of 6 means competent B2 level. Don't inflate scores. Spam or repetitive content should get 1-2."""

    # Try to call AI API
    try:
        if ANTHROPIC_API_KEY:
            # Use Anthropic Claude API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 2000,
                        "messages": [
                            {"role": "user", "content": evaluation_prompt}
                        ]
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["content"][0]["text"]
                    # Extract JSON from response
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        evaluation = json.loads(json_match.group())
                        return process_ai_evaluation(evaluation, task1, task2, essay)

        elif OPENAI_API_KEY:
            # Use OpenAI API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": "You are a strict CEFR English examiner. Always respond with valid JSON."},
                            {"role": "user", "content": evaluation_prompt}
                        ],
                        "temperature": 0.3
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        evaluation = json.loads(json_match.group())
                        return process_ai_evaluation(evaluation, task1, task2, essay)

    except Exception as e:
        print(f"AI evaluation error: {e}")

    # Fallback to algorithmic evaluation
    return algorithmic_evaluation(task1, task2, essay)


def process_ai_evaluation(evaluation: Dict, task1: str, task2: str, essay: str) -> Dict:
    """Process AI evaluation results into standard format"""

    task1_score = evaluation.get("task1", {}).get("score", 5)
    task2_score = evaluation.get("task2", {}).get("score", 5)
    essay_score = evaluation.get("essay", {}).get("score", 5)

    # Calculate overall score (weighted average)
    # Task 1: 25%, Task 2: 25%, Essay: 50%
    overall_score = (task1_score * 0.25 + task2_score * 0.25 + essay_score * 0.5)
    overall_percentage = (overall_score / 9) * 100

    # Map to CEFR level
    cefr_level = "A1"
    for level, data in CEFR_LEVELS.items():
        if overall_percentage >= data["min_score"]:
            cefr_level = level
            break

    return {
        "task1": {
            "score": task1_score,
            "band": task1_score,
            "feedback": {
                "overall": f"Band {task1_score} - {WRITING_BAND_DESCRIPTORS.get(task1_score, {}).get('description', 'N/A')}",
                "content": evaluation.get("task1", {}).get("content", ""),
                "organization": evaluation.get("task1", {}).get("organization", ""),
                "language": evaluation.get("task1", {}).get("language", ""),
                "accuracy": evaluation.get("task1", {}).get("accuracy", "")
            },
            "word_count": len(task1.split()),
            "is_valid": True
        },
        "task2": {
            "score": task2_score,
            "band": task2_score,
            "feedback": {
                "overall": f"Band {task2_score} - {WRITING_BAND_DESCRIPTORS.get(task2_score, {}).get('description', 'N/A')}",
                "content": evaluation.get("task2", {}).get("content", ""),
                "organization": evaluation.get("task2", {}).get("organization", ""),
                "language": evaluation.get("task2", {}).get("language", ""),
                "accuracy": evaluation.get("task2", {}).get("accuracy", "")
            },
            "word_count": len(task2.split()),
            "is_valid": True
        },
        "essay": {
            "score": essay_score,
            "band": essay_score,
            "feedback": {
                "overall": f"Band {essay_score} - {WRITING_BAND_DESCRIPTORS.get(essay_score, {}).get('description', 'N/A')}",
                "task_achievement": evaluation.get("essay", {}).get("task_achievement", ""),
                "coherence_cohesion": evaluation.get("essay", {}).get("coherence_cohesion", ""),
                "lexical_resource": evaluation.get("essay", {}).get("lexical_resource", ""),
                "grammatical_range": evaluation.get("essay", {}).get("grammatical_range", "")
            },
            "word_count": len(essay.split()),
            "is_valid": True
        },
        "overall_score": round(overall_score, 1),
        "overall_band": round(overall_score),
        "overall_percentage": round(overall_percentage, 1),
        "cefr_level": cefr_level,
        "general_feedback": evaluation.get("general_feedback", "")
    }


def algorithmic_evaluation(task1: str, task2: str, essay: str) -> Dict:
    """Fallback algorithmic evaluation when AI is not available - STRICT version"""

    def evaluate_text(text: str, min_words: int, max_words: int, task_type: str) -> Dict:
        words = text.split()
        word_count = len(words)
        unique_words = len(set(w.lower() for w in words if w.isalpha()))
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        score = 5  # Start at modest level
        feedback = []

        # Word count penalty - STRICT
        if word_count < min_words * 0.5:
            score -= 3
            feedback.append(f"Severely under word count ({word_count}/{min_words} minimum)")
        elif word_count < min_words:
            score -= 2
            feedback.append(f"Under word count ({word_count}/{min_words} minimum)")
        elif word_count > max_words * 1.5:
            score -= 1
            feedback.append(f"Significantly over word count ({word_count}/{max_words} maximum)")
        elif word_count >= min_words and word_count <= max_words:
            score += 1
            feedback.append("Word count is appropriate")

        # Vocabulary diversity - STRICT
        vocab_ratio = unique_words / word_count if word_count > 0 else 0
        if vocab_ratio < 0.2:
            score -= 3
            feedback.append("Extremely limited vocabulary - repetitive content")
        elif vocab_ratio < 0.3:
            score -= 2
            feedback.append("Very limited vocabulary range")
        elif vocab_ratio < 0.4:
            score -= 1
            feedback.append("Limited vocabulary diversity")
        elif vocab_ratio >= 0.5:
            score += 1
            feedback.append("Good vocabulary range")

        # Sentence structure - STRICT
        avg_sentence_length = word_count / len(sentences) if sentences else 0
        if avg_sentence_length < 5:
            score -= 2
            feedback.append("Sentences too short - lacks complexity")
        elif avg_sentence_length < 8:
            score -= 1
            feedback.append("Simple sentence structures")
        elif avg_sentence_length > 25:
            score -= 1
            feedback.append("Sentences may be too long and complex")
        elif 12 <= avg_sentence_length <= 20:
            score += 1
            feedback.append("Good sentence length variety")

        # Check for basic punctuation and capitalization
        has_proper_caps = text[0].isupper() if text else False
        has_punctuation = any(c in text for c in '.!?')

        if not has_proper_caps:
            score -= 1
            feedback.append("Missing proper capitalization")
        if not has_punctuation:
            score -= 1
            feedback.append("Missing punctuation")

        # Check for paragraph structure (only for essay)
        if task_type == "essay":
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            if len(paragraphs) < 3:
                score -= 1
                feedback.append("Essay lacks proper paragraph structure")
            elif len(paragraphs) >= 4:
                score += 1
                feedback.append("Good paragraph organization")

        # Spam detection - repeated words
        word_freq = {}
        for w in words:
            w_lower = w.lower()
            word_freq[w_lower] = word_freq.get(w_lower, 0) + 1

        max_freq = max(word_freq.values()) if word_freq else 0
        if max_freq > word_count * 0.3:
            score -= 4
            feedback.append("Spam detected - excessive word repetition")

        # Ensure score is within bounds
        score = max(1, min(9, score))

        return {
            "score": score,
            "word_count": word_count,
            "feedback": " | ".join(feedback) if feedback else "Evaluation complete"
        }

    task1_eval = evaluate_text(task1, 120, 150, "email")
    task2_eval = evaluate_text(task2, 120, 150, "review")
    essay_eval = evaluate_text(essay, 250, 300, "essay")

    # Calculate overall score
    overall_score = (task1_eval["score"] * 0.25 + task2_eval["score"] * 0.25 + essay_eval["score"] * 0.5)
    overall_percentage = (overall_score / 9) * 100

    # Map to CEFR level
    cefr_level = "A1"
    for level, data in CEFR_LEVELS.items():
        if overall_percentage >= data["min_score"]:
            cefr_level = level
            break

    return {
        "task1": {
            "score": task1_eval["score"],
            "band": task1_eval["score"],
            "feedback": {
                "overall": f"Band {task1_eval['score']} - {WRITING_BAND_DESCRIPTORS.get(task1_eval['score'], {}).get('description', 'N/A')}",
                "content": task1_eval["feedback"],
                "organization": "Evaluated algorithmically",
                "language": "Evaluated algorithmically",
                "accuracy": "Evaluated algorithmically"
            },
            "word_count": task1_eval["word_count"],
            "is_valid": task1_eval["score"] > 2
        },
        "task2": {
            "score": task2_eval["score"],
            "band": task2_eval["score"],
            "feedback": {
                "overall": f"Band {task2_eval['score']} - {WRITING_BAND_DESCRIPTORS.get(task2_eval['score'], {}).get('description', 'N/A')}",
                "content": task2_eval["feedback"],
                "organization": "Evaluated algorithmically",
                "language": "Evaluated algorithmically",
                "accuracy": "Evaluated algorithmically"
            },
            "word_count": task2_eval["word_count"],
            "is_valid": task2_eval["score"] > 2
        },
        "essay": {
            "score": essay_eval["score"],
            "band": essay_eval["score"],
            "feedback": {
                "overall": f"Band {essay_eval['score']} - {WRITING_BAND_DESCRIPTORS.get(essay_eval['score'], {}).get('description', 'N/A')}",
                "task_achievement": essay_eval["feedback"],
                "coherence_cohesion": "Evaluated algorithmically",
                "lexical_resource": "Evaluated algorithmically",
                "grammatical_range": "Evaluated algorithmically"
            },
            "word_count": essay_eval["word_count"],
            "is_valid": essay_eval["score"] > 2
        },
        "overall_score": round(overall_score, 1),
        "overall_band": round(overall_score),
        "overall_percentage": round(overall_percentage, 1),
        "cefr_level": cefr_level,
        "general_feedback": "This evaluation was performed algorithmically. For more detailed feedback, please ensure AI evaluation is enabled."
    }


def calculate_final_cefr_level(reading_score: float, listening_score: float, writing_score: float) -> Dict:
    """Calculate final CEFR level from all sections"""
    # Weighted average: Reading 30%, Listening 30%, Writing 40%
    overall_percentage = (
        reading_score * 0.30 +
        listening_score * 0.30 +
        writing_score * 0.40
    )

    # Determine CEFR level
    cefr_level = "A1"
    level_description = CEFR_LEVELS["A1"]["description"]

    for level, data in CEFR_LEVELS.items():
        if overall_percentage >= data["min_score"]:
            cefr_level = level
            level_description = data["description"]
            break

    return {
        "overall_percentage": round(overall_percentage, 1),
        "cefr_level": cefr_level,
        "level_description": level_description
    }


# ============ ROUTES ============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/start", response_class=HTMLResponse)
async def start_test(request: Request):
    """Start a new test session"""
    session_id = str(uuid.uuid4())
    get_session(session_id)  # Initialize session
    response = templates.TemplateResponse("start.html", {
        "request": request,
        "session_id": session_id
    })
    response.set_cookie(key="session_id", value=session_id, max_age=7200)  # 2 hours
    return response


@app.get("/test/reading", response_class=HTMLResponse)
async def reading_test(request: Request):
    """Reading test page"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/start", status_code=302)

    return templates.TemplateResponse("test_reading.html", {
        "request": request,
        "test_data": READING_TEST,
        "session_id": session_id
    })


@app.post("/test/reading/submit")
async def submit_reading(request: Request):
    """Submit reading test answers"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return JSONResponse({"error": "Session not found"}, status_code=400)

    form_data = await request.form()
    answers = {key: value for key, value in form_data.items() if key != "session_id"}

    # Calculate score
    result = calculate_reading_score(answers)

    # Update session
    session = get_session(session_id)
    session["reading"] = {
        "completed": True,
        "answers": answers,
        "score": result["correct"],
        "total": result["total"],
        "percentage": result["percentage"],
        "details": result["details"]
    }

    return JSONResponse({
        "success": True,
        "score": result["correct"],
        "total": result["total"],
        "percentage": result["percentage"],
        "redirect": "/test/listening"
    })


@app.get("/test/listening", response_class=HTMLResponse)
async def listening_test(request: Request):
    """Listening test page"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/start", status_code=302)

    return templates.TemplateResponse("test_listening.html", {
        "request": request,
        "test_data": LISTENING_TEST,
        "session_id": session_id
    })


@app.post("/test/listening/submit")
async def submit_listening(request: Request):
    """Submit listening test answers"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return JSONResponse({"error": "Session not found"}, status_code=400)

    form_data = await request.form()
    answers = {key: value for key, value in form_data.items() if key != "session_id"}

    # Calculate score
    result = calculate_listening_score(answers)

    # Update session
    session = get_session(session_id)
    session["listening"] = {
        "completed": True,
        "answers": answers,
        "score": result["correct"],
        "total": result["total"],
        "percentage": result["percentage"],
        "details": result["details"]
    }

    return JSONResponse({
        "success": True,
        "score": result["correct"],
        "total": result["total"],
        "percentage": result["percentage"],
        "redirect": "/test/writing"
    })


@app.get("/test/writing", response_class=HTMLResponse)
async def writing_test(request: Request):
    """Writing test page"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/start", status_code=302)

    return templates.TemplateResponse("test_writing.html", {
        "request": request,
        "test_data": WRITING_TEST,
        "session_id": session_id
    })


@app.post("/test/writing/submit")
async def submit_writing(request: Request):
    """Submit writing test - with AI evaluation"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return JSONResponse({"error": "Session not found"}, status_code=400)

    form_data = await request.form()
    task1_response = form_data.get("task1", "")
    task2_response = form_data.get("task2", "")
    essay_response = form_data.get("essay", "")

    # Evaluate with AI
    evaluation = await evaluate_writing_with_ai(task1_response, task2_response, essay_response)

    # Update session
    session = get_session(session_id)
    session["writing"] = {
        "completed": True,
        "responses": {
            "task1": task1_response,
            "task2": task2_response,
            "essay": essay_response
        },
        "evaluation": evaluation,
        "percentage": evaluation["overall_percentage"]
    }

    # Calculate final CEFR level
    reading_pct = session.get("reading", {}).get("percentage", 0)
    listening_pct = session.get("listening", {}).get("percentage", 0)
    writing_pct = evaluation["overall_percentage"]

    final_result = calculate_final_cefr_level(reading_pct, listening_pct, writing_pct)
    session["overall_score"] = final_result["overall_percentage"]
    session["cefr_level"] = final_result["cefr_level"]
    session["level_description"] = final_result["level_description"]

    return JSONResponse({
        "success": True,
        "evaluation": evaluation,
        "redirect": "/results"
    })


@app.get("/results", response_class=HTMLResponse)
async def results(request: Request):
    """Results page"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/start", status_code=302)

    session = get_session(session_id)

    # Check if all tests are completed
    if not all([
        session.get("reading", {}).get("completed"),
        session.get("listening", {}).get("completed"),
        session.get("writing", {}).get("completed")
    ]):
        return RedirectResponse(url="/start", status_code=302)

    return templates.TemplateResponse("results.html", {
        "request": request,
        "session": session,
        "cefr_levels": CEFR_LEVELS,
        "band_descriptors": WRITING_BAND_DESCRIPTORS
    })


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "CEFR Mock Test Platform"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
