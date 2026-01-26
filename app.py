from fastapi import FastAPI, Request, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import uuid
import os
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()

app = FastAPI(title="CEFR Level Platform - Beta")

# Create static directory if not exists
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize database on startup
@app.on_event("startup")
async def startup():
    from database import init_db, create_default_admin
    try:
        init_db()
        create_default_admin()
    except Exception as e:
        print(f"Database initialization error: {e}")
        print("Running without database - some features may not work")

# OpenAI client
openai_client = None
if os.getenv('OPENAI_API_KEY'):
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def calculate_cefr_level(reading_percent, listening_percent, writing_score):
    """Calculate overall CEFR level based on scores"""
    # writing_score is out of 10
    writing_percent = (writing_score / 10) * 100 if writing_score else 0

    # Calculate weighted average (reading and listening are more objective)
    avg_score = (reading_percent * 0.35 + listening_percent * 0.35 + writing_percent * 0.30)

    if avg_score >= 90:
        return "C2"
    elif avg_score >= 80:
        return "C1"
    elif avg_score >= 70:
        return "B2"
    elif avg_score >= 55:
        return "B1"
    elif avg_score >= 40:
        return "A2"
    else:
        return "A1"

async def evaluate_writing_with_ai(text, prompt):
    """Evaluate writing using OpenAI API"""
    if not openai_client:
        # Fallback evaluation without AI
        word_count = len(text.split())
        base_score = min(word_count / 20, 5)  # Up to 5 points for length

        # Simple quality checks
        if len(text) > 100:
            base_score += 1
        if any(word in text.lower() for word in ['because', 'however', 'therefore', 'although']):
            base_score += 1
        if text[0].isupper() and text.endswith('.'):
            base_score += 1
        if ',' in text:
            base_score += 0.5
        if any(c in text for c in ['?', '!']):
            base_score += 0.5

        return {
            'score': min(base_score, 10),
            'feedback': 'AI evaluation not available. Basic scoring applied based on length and structure.',
            'level': 'B1'
        }

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """You are a CEFR English writing evaluator. Evaluate the writing and respond in JSON format:
{
    "score": <number 1-10>,
    "level": "<CEFR level A1-C2>",
    "feedback": "<detailed feedback in Uzbek language>",
    "grammar": "<grammar assessment>",
    "vocabulary": "<vocabulary assessment>",
    "coherence": "<coherence and cohesion assessment>",
    "task_achievement": "<how well the task was completed>"
}
Evaluate based on:
1. Grammar and accuracy (25%)
2. Vocabulary range and appropriacy (25%)
3. Coherence and cohesion (25%)
4. Task achievement (25%)"""
                },
                {
                    "role": "user",
                    "content": f"Writing prompt: {prompt}\n\nStudent's response:\n{text}"
                }
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"OpenAI error: {e}")
        return {
            'score': 5,
            'feedback': 'AI evaluation failed. Default score assigned.',
            'level': 'B1'
        }

# ===== PUBLIC ROUTES =====

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """About page"""
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request):
    """Pricing page - Beta is free"""
    return templates.TemplateResponse("pricing.html", {"request": request})

@app.get("/start", response_class=HTMLResponse)
async def start_test(request: Request):
    """Start test page"""
    session_id = str(uuid.uuid4())

    # Create session in database
    try:
        from database import create_test_session
        create_test_session(session_id)
    except Exception as e:
        print(f"Database error: {e}")

    response = templates.TemplateResponse("start.html", {
        "request": request,
        "session_id": session_id
    })
    response.set_cookie(key="test_session", value=session_id, max_age=7200)  # 2 hours
    return response

# ===== TEST ROUTES =====

@app.get("/test/reading", response_class=HTMLResponse)
async def reading_test(request: Request):
    """Reading test page"""
    session_id = request.cookies.get("test_session")
    if not session_id:
        return RedirectResponse(url="/start", status_code=302)

    try:
        from database import get_reading_questions
        questions = get_reading_questions(limit=10)
    except:
        questions = []

    return templates.TemplateResponse("test_reading.html", {
        "request": request,
        "questions": questions,
        "session_id": session_id
    })

@app.post("/test/reading/submit")
async def submit_reading(request: Request):
    """Submit reading test answers"""
    session_id = request.cookies.get("test_session")
    if not session_id:
        return JSONResponse({"error": "No session"}, status_code=400)

    form = await request.form()

    try:
        from database import get_reading_questions, save_answer, update_test_session

        # Get questions to check answers
        questions = get_reading_questions(limit=10)
        correct_count = 0

        for q in questions:
            user_answer = form.get(f"q_{q['id']}", "")
            is_correct = user_answer.upper() == q['correct_answer'].upper()
            if is_correct:
                correct_count += 1
            save_answer(session_id, 'reading', q['id'], user_answer, is_correct)

        # Update session
        update_test_session(session_id, reading_score=correct_count, reading_total=len(questions))

        return JSONResponse({
            "success": True,
            "score": correct_count,
            "total": len(questions),
            "next": "/test/listening"
        })
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/test/listening", response_class=HTMLResponse)
async def listening_test(request: Request):
    """Listening test page"""
    session_id = request.cookies.get("test_session")
    if not session_id:
        return RedirectResponse(url="/start", status_code=302)

    try:
        from database import get_listening_questions
        questions = get_listening_questions(limit=10)
    except:
        questions = []

    return templates.TemplateResponse("test_listening.html", {
        "request": request,
        "questions": questions,
        "session_id": session_id
    })

@app.post("/test/listening/submit")
async def submit_listening(request: Request):
    """Submit listening test answers"""
    session_id = request.cookies.get("test_session")
    if not session_id:
        return JSONResponse({"error": "No session"}, status_code=400)

    form = await request.form()

    try:
        from database import get_listening_questions, save_answer, update_test_session

        questions = get_listening_questions(limit=10)
        correct_count = 0

        for q in questions:
            user_answer = form.get(f"q_{q['id']}", "")
            is_correct = user_answer.upper() == q['correct_answer'].upper()
            if is_correct:
                correct_count += 1
            save_answer(session_id, 'listening', q['id'], user_answer, is_correct)

        update_test_session(session_id, listening_score=correct_count, listening_total=len(questions))

        return JSONResponse({
            "success": True,
            "score": correct_count,
            "total": len(questions),
            "next": "/test/writing"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/test/writing", response_class=HTMLResponse)
async def writing_test(request: Request):
    """Writing test page"""
    session_id = request.cookies.get("test_session")
    if not session_id:
        return RedirectResponse(url="/start", status_code=302)

    try:
        from database import get_writing_prompts
        prompts = get_writing_prompts(limit=1)
        prompt = prompts[0] if prompts else {
            'id': 0,
            'prompt_text': 'Write about your favorite hobby and why you enjoy it. Describe how you started this hobby and how it has affected your life.',
            'min_words': 150,
            'max_words': 300
        }
    except:
        prompt = {
            'id': 0,
            'prompt_text': 'Write about your favorite hobby and why you enjoy it. Describe how you started this hobby and how it has affected your life.',
            'min_words': 150,
            'max_words': 300
        }

    return templates.TemplateResponse("test_writing.html", {
        "request": request,
        "prompt": prompt,
        "session_id": session_id
    })

@app.post("/test/writing/submit")
async def submit_writing(request: Request):
    """Submit writing test for AI evaluation"""
    session_id = request.cookies.get("test_session")
    if not session_id:
        return JSONResponse({"error": "No session"}, status_code=400)

    form = await request.form()
    text = form.get("writing_text", "")
    prompt_text = form.get("prompt_text", "")

    if len(text.strip()) < 50:
        return JSONResponse({"error": "Writing too short. Minimum 50 characters required."}, status_code=400)

    # Evaluate with AI
    evaluation = await evaluate_writing_with_ai(text, prompt_text)

    try:
        from database import update_test_session, get_test_session
        import json

        update_test_session(
            session_id,
            writing_score=evaluation.get('score', 5),
            writing_feedback=json.dumps(evaluation, ensure_ascii=False)
        )

        # Calculate final CEFR level
        session = get_test_session(session_id)
        if session:
            reading_percent = (session['reading_score'] / session['reading_total'] * 100) if session['reading_total'] > 0 else 50
            listening_percent = (session['listening_score'] / session['listening_total'] * 100) if session['listening_total'] > 0 else 50

            overall_level = calculate_cefr_level(reading_percent, listening_percent, evaluation.get('score', 5))

            from datetime import datetime
            update_test_session(session_id, overall_level=overall_level, completed_at=datetime.now())

        return JSONResponse({
            "success": True,
            "evaluation": evaluation,
            "next": "/survey"
        })
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse({
            "success": True,
            "evaluation": evaluation,
            "next": "/survey"
        })

@app.get("/survey", response_class=HTMLResponse)
async def survey_page(request: Request):
    """Survey page before showing results"""
    session_id = request.cookies.get("test_session")
    if not session_id:
        return RedirectResponse(url="/start", status_code=302)

    return templates.TemplateResponse("survey.html", {
        "request": request,
        "session_id": session_id
    })

@app.post("/survey/submit")
async def submit_survey(request: Request):
    """Submit survey and redirect to results"""
    session_id = request.cookies.get("test_session")
    if not session_id:
        return JSONResponse({"error": "No session"}, status_code=400)

    form = await request.form()

    try:
        from database import save_survey

        survey_data = {
            'overall_experience': int(form.get('overall_experience', 5)),
            'difficulty_rating': int(form.get('difficulty_rating', 3)),
            'would_recommend': form.get('would_recommend') == 'yes',
            'feedback': form.get('feedback', ''),
            'improvement_suggestions': form.get('improvement_suggestions', ''),
            'age_group': form.get('age_group', ''),
            'english_purpose': form.get('english_purpose', '')
        }

        save_survey(session_id, survey_data)
    except Exception as e:
        print(f"Survey error: {e}")

    return JSONResponse({"success": True, "redirect": "/results"})

@app.get("/survey/skip")
async def skip_survey(request: Request):
    """Skip survey and go to results"""
    return RedirectResponse(url="/results", status_code=302)

@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    """Results page with CEFR level"""
    session_id = request.cookies.get("test_session")
    if not session_id:
        return RedirectResponse(url="/start", status_code=302)

    try:
        from database import get_test_session
        session = get_test_session(session_id)

        if not session:
            session = {
                'reading_score': 0,
                'reading_total': 10,
                'listening_score': 0,
                'listening_total': 10,
                'writing_score': 5,
                'writing_feedback': '{}',
                'overall_level': 'B1'
            }

        writing_feedback = {}
        if session.get('writing_feedback'):
            try:
                writing_feedback = json.loads(session['writing_feedback'])
            except:
                writing_feedback = {'feedback': session['writing_feedback']}

        return templates.TemplateResponse("results.html", {
            "request": request,
            "session": session,
            "writing_feedback": writing_feedback
        })
    except Exception as e:
        print(f"Results error: {e}")
        return templates.TemplateResponse("results.html", {
            "request": request,
            "session": {
                'reading_score': 0,
                'reading_total': 10,
                'listening_score': 0,
                'listening_total': 10,
                'writing_score': 5,
                'overall_level': 'B1'
            },
            "writing_feedback": {}
        })

# ===== ADMIN ROUTES =====

@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page"""
    admin_token = request.cookies.get("admin_token")
    if admin_token == "authenticated":
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login")
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Admin login handler"""
    try:
        from database import verify_admin
        admin = verify_admin(username, password)

        if admin:
            response = RedirectResponse(url="/admin/dashboard", status_code=302)
            response.set_cookie(key="admin_token", value="authenticated", max_age=3600)
            return response
    except Exception as e:
        print(f"Login error: {e}")

    return templates.TemplateResponse("admin_login.html", {
        "request": request,
        "error": "Login yoki parol noto'g'ri"
    })

@app.get("/admin/logout")
async def admin_logout():
    """Admin logout"""
    response = RedirectResponse(url="/admin", status_code=302)
    response.delete_cookie("admin_token")
    return response

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return RedirectResponse(url="/admin", status_code=302)

    try:
        from database import get_statistics
        stats = get_statistics()
    except:
        stats = {
            'total_tests': 0,
            'avg_reading': 0,
            'avg_listening': 0,
            'avg_writing': 0,
            'level_distribution': {},
            'total_surveys': 0,
            'avg_experience': 0
        }

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "stats": stats
    })

# Reading questions management
@app.get("/admin/reading", response_class=HTMLResponse)
async def admin_reading(request: Request):
    """Admin reading questions page"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return RedirectResponse(url="/admin", status_code=302)

    try:
        from database import get_all_reading_questions
        questions = get_all_reading_questions()
    except:
        questions = []

    return templates.TemplateResponse("admin_reading.html", {
        "request": request,
        "questions": questions
    })

@app.post("/admin/reading/add")
async def add_reading_question_route(request: Request):
    """Add new reading question"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    form = await request.form()

    try:
        from database import add_reading_question

        add_reading_question(
            passage=form.get('passage'),
            question=form.get('question'),
            options=[
                form.get('option_a'),
                form.get('option_b'),
                form.get('option_c'),
                form.get('option_d')
            ],
            correct=form.get('correct_answer'),
            difficulty=form.get('difficulty', 'B1')
        )

        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/admin/reading/{question_id}")
async def delete_reading_question_route(request: Request, question_id: int):
    """Delete reading question"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        from database import delete_reading_question
        delete_reading_question(question_id)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Listening questions management
@app.get("/admin/listening", response_class=HTMLResponse)
async def admin_listening(request: Request):
    """Admin listening questions page"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return RedirectResponse(url="/admin", status_code=302)

    try:
        from database import get_all_listening_questions
        questions = get_all_listening_questions()
    except:
        questions = []

    return templates.TemplateResponse("admin_listening.html", {
        "request": request,
        "questions": questions
    })

@app.post("/admin/listening/add")
async def add_listening_question_route(request: Request):
    """Add new listening question"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    form = await request.form()

    try:
        from database import add_listening_question

        add_listening_question(
            audio_url=form.get('audio_url'),
            transcript=form.get('transcript', ''),
            question=form.get('question'),
            options=[
                form.get('option_a'),
                form.get('option_b'),
                form.get('option_c'),
                form.get('option_d')
            ],
            correct=form.get('correct_answer'),
            difficulty=form.get('difficulty', 'B1')
        )

        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/admin/listening/{question_id}")
async def delete_listening_question_route(request: Request, question_id: int):
    """Delete listening question"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        from database import delete_listening_question
        delete_listening_question(question_id)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Writing prompts management
@app.get("/admin/writing", response_class=HTMLResponse)
async def admin_writing(request: Request):
    """Admin writing prompts page"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return RedirectResponse(url="/admin", status_code=302)

    try:
        from database import get_all_writing_prompts
        prompts = get_all_writing_prompts()
    except:
        prompts = []

    return templates.TemplateResponse("admin_writing.html", {
        "request": request,
        "prompts": prompts
    })

@app.post("/admin/writing/add")
async def add_writing_prompt_route(request: Request):
    """Add new writing prompt"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    form = await request.form()

    try:
        from database import add_writing_prompt

        add_writing_prompt(
            prompt_text=form.get('prompt_text'),
            min_words=int(form.get('min_words', 150)),
            max_words=int(form.get('max_words', 300)),
            difficulty=form.get('difficulty', 'B1')
        )

        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/admin/writing/{prompt_id}")
async def delete_writing_prompt_route(request: Request, prompt_id: int):
    """Delete writing prompt"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        from database import delete_writing_prompt
        delete_writing_prompt(prompt_id)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Survey responses
@app.get("/admin/surveys", response_class=HTMLResponse)
async def admin_surveys(request: Request):
    """Admin survey responses page"""
    admin_token = request.cookies.get("admin_token")
    if admin_token != "authenticated":
        return RedirectResponse(url="/admin", status_code=302)

    try:
        from database import get_all_surveys
        surveys = get_all_surveys()
    except:
        surveys = []

    return templates.TemplateResponse("admin_surveys.html", {
        "request": request,
        "surveys": surveys
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "CEFR Level Platform Beta"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
