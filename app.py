from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, List
import uvicorn
import uuid
import json
import os
import re
import random
import httpx
from datetime import datetime
from pathlib import Path

# .env faylidan o'zgaruvchilarni yuklash (GOOGLE_CLIENT_SECRET va boshqalar)
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")  # app.py bilan bir papkada .env

app = FastAPI(title="CEFR Level - English Assessment Platform")

# Multi-language support
TRANSLATIONS = {
    "uz": {
        "site_name": "CEFR Level",
        "tagline": "Ingliz tili darajangizni aniqlang",
        "start_test": "Testni boshlash",
        "pricing": "Narxlar",
        "about": "Biz haqimizda",
        "reading": "Reading",
        "listening": "Listening",
        "writing": "Writing",
        "results": "Natijalar",
        "your_level": "Sizning CEFR darajangiz",
        "overall_score": "Umumiy ball",
        "take_another": "Yana test topshirish",
        "back_home": "Bosh sahifa",
        "feedback_title": "Bizga yordam bering!",
        "feedback_desc": "Bu Beta versiya. Fikr-mulohazalaringiz loyihamizni yaxshilashga yordam beradi.",
        "submit": "Yuborish",
        "minutes": "daqiqa",
        "words": "so'z",
        "question": "Savol",
        "instructions": "Ko'rsatmalar",
        "time_remaining": "Qolgan vaqt",
    },
    "en": {
        "site_name": "CEFR Level",
        "tagline": "Discover Your English Proficiency Level",
        "start_test": "Start Test",
        "pricing": "Pricing",
        "about": "About Us",
        "reading": "Reading",
        "listening": "Listening",
        "writing": "Writing",
        "results": "Results",
        "your_level": "Your CEFR Level",
        "overall_score": "Overall Score",
        "take_another": "Take Another Test",
        "back_home": "Back to Home",
        "feedback_title": "Help Us Improve!",
        "feedback_desc": "This is a Beta version. Your feedback helps us improve the platform.",
        "submit": "Submit",
        "minutes": "minutes",
        "words": "words",
        "question": "Question",
        "instructions": "Instructions",
        "time_remaining": "Time Remaining",
    }
}

def get_lang(request: Request) -> str:
    return request.cookies.get("lang", "uz")

def get_translations(request: Request) -> dict:
    lang = get_lang(request)
    return TRANSLATIONS.get(lang, TRANSLATIONS["uz"])

# Static fayllar (papka mavjud bo'lsa)
if Path(__file__).resolve().parent.joinpath("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory stores
sessions: Dict[str, Dict] = {}
feedbacks: List[Dict] = []

# OPENAI: qo'llab-quvvatlanadi OPENAI_API_KEY va typo OPENAI_API_KE
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KE") or "").strip()
ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()

DATA_DIR = Path("data")
ADMIN_PASSWORD = "osco2026"

CEFR_LEVELS = {
    "C2": {"min_score": 90, "description": "Mastery"},
    "C1": {"min_score": 80, "description": "Advanced"},
    "B2": {"min_score": 70, "description": "Upper Intermediate"},
    "B1": {"min_score": 55, "description": "Intermediate"},
    "A2": {"min_score": 40, "description": "Elementary"},
    "A1": {"min_score": 0, "description": "Beginner"},
}


# ============ DATA MANAGEMENT ============

def load_json(filename: str) -> dict:
    path = DATA_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(filename: str, data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============ USERS (AUTH) ============

USERS_FILE = "users.json"
AUTH_COOKIE = "auth_token"
AUTH_MAX_AGE = 30 * 24 * 3600  # 30 days

def load_users() -> dict:
    data = load_json(USERS_FILE)
    if "users" not in data:
        data["users"] = []
    return data

def save_users(data: dict):
    save_json(USERS_FILE, data)

def hash_password(password: str) -> str:
    from passlib.hash import bcrypt
    return bcrypt.using(rounds=12).hash(password)

def verify_password(password: str, hash_str: str) -> bool:
    from passlib.hash import bcrypt
    try:
        return bcrypt.verify(password, hash_str)
    except Exception:
        return False

def get_user_by_id(uid: str):
    data = load_users()
    for u in data["users"]:
        if u.get("id") == uid:
            return u
    return None

def get_user_by_email(email: str):
    data = load_users()
    email_lower = (email or "").strip().lower()
    for u in data["users"]:
        if (u.get("email") or "").strip().lower() == email_lower:
            return u
    return None

def get_user_by_google_id(google_id: str):
    data = load_users()
    for u in data["users"]:
        if u.get("google_id") == google_id:
            return u
    return None

def create_user(email: str, password: str, name: str = "") -> dict:
    data = load_users()
    uid = str(uuid.uuid4())
    user = {
        "id": uid,
        "email": (email or "").strip().lower(),
        "password_hash": hash_password(password),
        "name": (name or "").strip() or (email or "").split("@")[0],
        "google_id": None,
        "avatar": None,
        "created_at": datetime.now().isoformat(),
        "free_tests": 10,  # Beta: 10 free tests for new users
        "purchased_tests": 0,  # Purchased tests count
    }
    data["users"].append(user)
    save_users(data)
    return user

def update_user(uid: str, **kwargs) -> dict | None:
    data = load_users()
    for u in data["users"]:
        if u.get("id") == uid:
            for key, value in kwargs.items():
                u[key] = value
            save_users(data)
            return u
    return None

def create_or_update_user_google(google_id: str, email: str, name: str, picture: str = None) -> dict:
    data = load_users()
    for u in data["users"]:
        if u.get("google_id") == google_id:
            u["email"] = (email or u.get("email", "")).strip().lower()
            u["name"] = (name or u.get("name", "")).strip()
            if picture:
                u["avatar"] = picture
            # Ensure free_tests field exists for existing users
            if "free_tests" not in u:
                u["free_tests"] = 10  # Beta bonus
            save_users(data)
            return u
    # New user – onboarding kerak (faqat ism so'raladi)
    uid = str(uuid.uuid4())
    user = {
        "id": uid,
        "email": (email or "").strip().lower(),
        "password_hash": "",
        "name": (name or "").strip() or (email or "").split("@")[0],
        "google_id": google_id,
        "avatar": picture,
        "created_at": datetime.now().isoformat(),
        "onboarding_done": False,
        "free_tests": 10,  # Beta: 10 free tests for new users
        "purchased_tests": 0,  # Purchased tests count
    }
    data["users"].append(user)
    save_users(data)
    return user

def get_current_user(request: Request):
    token = request.cookies.get(AUTH_COOKIE)
    if not token:
        return None
    try:
        from itsdangerous import URLSafeTimedSerializer
        secret = os.getenv("SECRET_KEY", "cefr-level-secret-change-in-production")
        s = URLSafeTimedSerializer(secret)
        uid = s.loads(token, max_age=AUTH_MAX_AGE)
        return get_user_by_id(uid)
    except Exception:
        return None

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "957401626494-fap468c0rveevdd6r3flt6b0ih11au49.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

def get_reading_tests() -> list:
    data = load_json("reading_tests.json")
    return data.get("tests", [])

def get_listening_tests() -> list:
    data = load_json("listening_tests.json")
    return data.get("tests", [])

def get_writing_tests() -> list:
    data = load_json("writing_tests.json")
    return data.get("tests", [])

def _build_test_from_all_tests(section: str, user: dict) -> dict:
    """Barcha testlardan har bir part turi uchun bitta part tanlab, yangi test yaratadi."""
    tests = get_reading_tests() if section == "reading" else (get_listening_tests() if section == "listening" else get_writing_tests())
    if not tests:
        return dict(DEFAULT_READING if section == "reading" else (DEFAULT_LISTENING if section == "listening" else DEFAULT_WRITING))
    
    # Har bir part_number uchun (1-5 yoki 1-6) barcha testlardan shu part_number ga ega bo'lgan partlarni yig'ish
    # Format: parts_by_number[pnum] = [(part, test_id), ...]
    parts_by_number = {}
    
    for test in tests:
        if not test.get("parts"):
            continue
        test_id = test.get("id", "")
        for part in test["parts"]:
            pnum = part.get("part_number", 0)
            if pnum > 0:
                if pnum not in parts_by_number:
                    parts_by_number[pnum] = []
                parts_by_number[pnum].append((dict(part), test_id))  # Copy part va test_id ni birga saqlash
    
    # Har bir part_number uchun random bitta part tanlash
    selected_parts = []
    max_parts = 5 if section == "reading" else (6 if section == "listening" else 2)
    seen_ids = list(user.get("seen_reading_parts" if section == "reading" else "seen_listening_parts", []) or [])
    
    for pnum in range(1, max_parts + 1):
        if pnum in parts_by_number and parts_by_number[pnum]:
            candidates = parts_by_number[pnum]  # [(part_dict, test_id), ...]
            
            # Reading uchun Part 1 har doim open_cloze bo'lishi kerak
            if section == "reading" and pnum == 1:
                candidates = [(p, tid) for p, tid in candidates if p.get("type") == "open_cloze"]
                if not candidates:
                    # Agar open_cloze topilmasa, default dan foydalanish
                    default_test = DEFAULT_READING
            # Reading uchun Part 3 har doim matching_headings bo'lishi kerak
            if section == "reading" and pnum == 3:
                candidates = [(p, tid) for p, tid in candidates if p.get("type") == "matching_headings"]
                if not candidates:
                    # Agar matching_headings topilmasa, default dan foydalanish
                    default_test = DEFAULT_READING
                    if default_test.get("parts"):
                        for dp in default_test["parts"]:
                            if dp.get("part_number") == 1 and dp.get("type") == "open_cloze":
                                candidates = [(dict(dp), default_test.get("id", "reading_default"))]
                                break
            
            if not candidates:
                continue
            
            # Avval ko'rilmaganlarni, keyin ko'rilganlarni tanlash
            unseen = []
            seen = []
            for part_dict, test_id in candidates:
                pid = test_id + "_" + str(pnum)
                if pid in seen_ids:
                    seen.append((part_dict, test_id))
                else:
                    unseen.append((part_dict, test_id))
            
            if unseen:
                selected, test_id = random.choice(unseen)
            elif seen:
                selected, test_id = random.choice(seen)
            else:
                selected, test_id = random.choice(candidates)
            
            # Partni copy qilish va part_number ni to'g'ri qo'yish
            part_copy = dict(selected)
            part_copy["part_number"] = pnum
            part_copy["_source_test_id"] = test_id  # Original test ID ni saqlash
            selected_parts.append(part_copy)
    
    # Agar hech qanday part topilmasa yoki kam partlar bo'lsa, default testdan to'ldirish
    default_test = DEFAULT_READING if section == "reading" else (DEFAULT_LISTENING if section == "listening" else DEFAULT_WRITING)
    default_parts = default_test.get("parts", [])
    
    # Har bir part_number uchun agar part topilmasa, default dan olish
    for pnum in range(1, max_parts + 1):
        # Agar bu part_number uchun part topilgan bo'lsa, o'tkazib yuborish
        if any(p.get("part_number") == pnum for p in selected_parts):
            continue
        
        # Default testdan shu part_number ga ega bo'lgan partni topish
        for dp in default_parts:
            if dp.get("part_number") == pnum:
                part_copy = dict(dp)
                part_copy["_source_test_id"] = default_test.get("id", section + "_default")
                selected_parts.append(part_copy)
                break
    
    # Agar hali ham hech qanday part bo'lmasa, default testning barcha partlarini olish
    if not selected_parts:
        selected_parts = [dict(p) for p in default_parts]
        for p in selected_parts:
            if "_source_test_id" not in p:
                p["_source_test_id"] = default_test.get("id", section + "_default")
    
    # Partlarni part_number bo'yicha tartiblash
    selected_parts.sort(key=lambda p: p.get("part_number", 0))
    
    # Yangi test yaratish
    first_test = tests[0] if tests else {}
    new_test = {
        "id": section + "_combined",
        "title": first_test.get("title", section.capitalize() + " Test"),
        "time_limit": first_test.get("time_limit", 60 if section == "reading" else (40 if section == "listening" else 80)),
        "parts": selected_parts
    }
    
    # Partlarni ko'rilmaganlar avval qilib tartiblash (lekin part_number tartibini saqlab qolish)
    new_test["parts"] = _order_parts_for_user(new_test["parts"], seen_ids, new_test["id"])
    
    return new_test

def _order_parts_for_user(parts: list, seen_ids: list, test_id: str) -> list:
    """Partlarni avval ko'rilmaganlar (part_number tartibida), keyin ko'rilganlar (part_number tartibida) qilib qaytaradi."""
    if not parts:
        return parts
    unseen = []
    seen = []
    for p in parts:
        pid = test_id + "_" + str(p.get("part_number", 0))
        if pid in seen_ids:
            seen.append(p)
        else:
            unseen.append(p)
    # Part_number bo'yicha tartiblash (random emas, tartibda)
    unseen.sort(key=lambda p: p.get("part_number", 0))
    seen.sort(key=lambda p: p.get("part_number", 0))
    return unseen + seen

def _mark_parts_seen(user_id: str, section: str, test_id: str, parts: list) -> None:
    key = "seen_reading_parts" if section == "reading" else "seen_listening_parts"
    user = get_user_by_id(user_id)
    if not user:
        return
    current = list(user.get(key, []) or [])
    for p in parts:
        pid = test_id + "_" + str(p.get("part_number", 0))
        if pid not in current:
            current.append(pid)
    update_user(user_id, **{key: current})

def get_feedbacks() -> list:
    data = load_json("feedbacks.json")
    return data.get("feedbacks", [])

def save_feedback(fb: dict):
    data = load_json("feedbacks.json")
    if "feedbacks" not in data:
        data["feedbacks"] = []
    data["feedbacks"].append(fb)
    save_json("feedbacks.json", data)

# ============ TEST HISTORY (foydalanuvchi test natijalari) ============

TEST_HISTORY_FILE = "test_history.json"

def load_test_history_data() -> dict:
    data = load_json(TEST_HISTORY_FILE)
    if "results" not in data:
        data["results"] = []
    return data

def save_test_result(session: dict):
    """Test to'liq tugagach natijani user_id bilan saqlaydi."""
    if not session.get("user_id"):
        return
    if not all([
        session.get("reading", {}).get("completed"),
        session.get("listening", {}).get("completed"),
        session.get("writing", {}).get("completed"),
    ]):
        return
    data = load_test_history_data()
    session_id = session.get("id")
    for r in data["results"]:
        if r.get("session_id") == session_id:
            return  # allaqachon saqlangan
    record = {
        "session_id": session_id,
        "user_id": session["user_id"],
        "completed_at": datetime.now().isoformat(),
        "reading_score": session.get("reading", {}).get("score", 0),
        "reading_total": session.get("reading", {}).get("total", 0),
        "reading_percentage": session.get("reading", {}).get("percentage", 0),
        "reading_details": session.get("reading", {}).get("details", []),
        "listening_score": session.get("listening", {}).get("score", 0),
        "listening_total": session.get("listening", {}).get("total", 0),
        "listening_percentage": session.get("listening", {}).get("percentage", 0),
        "listening_details": session.get("listening", {}).get("details", []),
        "writing_percentage": session.get("writing", {}).get("percentage", 0),
        "writing_evaluation": session.get("writing", {}).get("evaluation"),
        "overall_score": session.get("overall_score", 0),
        "cefr_level": session.get("cefr_level") or "—",
        "level_description": session.get("level_description") or "",
    }
    data["results"].append(record)
    save_json(TEST_HISTORY_FILE, data)

def get_test_history(user_id: str, limit: int = 50) -> list:
    data = load_test_history_data()
    user_results = [r for r in data["results"] if r.get("user_id") == user_id]
    user_results.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
    return user_results[:limit]


def get_test_result_by_session(session_id: str, user_id: str) -> dict | None:
    """Profil uchun bitta test natijasini session_id va user_id bo'yicha qaytaradi."""
    data = load_test_history_data()
    for r in data["results"]:
        if r.get("session_id") == session_id and r.get("user_id") == user_id:
            return r
    return None

def get_total_tests_taken() -> int:
    """Jami topshirilgan testlar soni (barcha foydalanuvchilar)."""
    data = load_test_history_data()
    return len(data.get("results", []))

# ============ LIKE / DISLIKE (1 user = 1 ovoz) ============

RATINGS_FILE = "ratings.json"

def load_ratings() -> dict:
    data = load_json(RATINGS_FILE)
    if "votes" not in data:
        data["votes"] = {}
    return data

def save_ratings(data: dict):
    save_json(RATINGS_FILE, data)

def get_user_rating(user_id: str) -> dict | None:
    """Foydalanuvchi ovozini qaytaradi: {"vote": "like"|"dislike", "reason": "..."} yoki None."""
    data = load_ratings()
    return data.get("votes", {}).get(user_id)

def set_rating(user_id: str, vote: str, reason: str = ""):
    """Bir foydalanuvchi faqat bitta ovoz beradi. vote: "like" yoki "dislike"."""
    data = load_ratings()
    if "votes" not in data:
        data["votes"] = {}
    data["votes"][user_id] = {"vote": vote, "reason": (reason or "").strip()}
    save_ratings(data)

def get_rating_counts() -> tuple:
    """(likes, dislikes) soni."""
    data = load_ratings()
    votes = data.get("votes", {})
    likes = sum(1 for v in votes.values() if v.get("vote") == "like")
    dislikes = sum(1 for v in votes.values() if v.get("vote") == "dislike")
    return likes, dislikes

def get_landing_stats() -> dict:
    """Landing va admin uchun: users, tests_taken, likes, dislikes."""
    users_data = load_users()
    users_count = len(users_data.get("users", []))
    tests_taken = get_total_tests_taken()
    likes, dislikes = get_rating_counts()
    return {"users": users_count, "tests_taken": tests_taken, "likes": likes, "dislikes": dislikes}

# Aloqa ma'lumotlari (profil sahifasida)
CONTACT_INFO = {
    "email": "info@cefrlevel.uz",
    "telegram": "@cefrlevel",
    "phone": "+998 71 123 45 67",
    "address_uz": "Toshkent sh., O'zbekiston",
}

def init_default_data():
    """Initialize default test data if files don't exist"""
    if not (DATA_DIR / "reading_tests.json").exists():
        save_json("reading_tests.json", {"tests": [DEFAULT_READING]})
    if not (DATA_DIR / "listening_tests.json").exists():
        save_json("listening_tests.json", {"tests": [DEFAULT_LISTENING]})
    if not (DATA_DIR / "writing_tests.json").exists():
        save_json("writing_tests.json", {"tests": [DEFAULT_WRITING]})
    if not (DATA_DIR / "feedbacks.json").exists():
        save_json("feedbacks.json", {"feedbacks": []})
    # Writing AI: kalit yuklanganligini logda ko'rsatish
    if OPENAI_API_KEY:
        print("[Writing AI] OPENAI_API_KEY yuklandi – Writing bo'limida AI baholash ishlatiladi.")
    else:
        print("[Writing AI] OPENAI_API_KEY topilmadi. .env da OPENAI_API_KEY qo'ying. Fallback baho ishlatiladi (0% dan yuqoriga).")


# ============ DEFAULT TEST DATA ============

DEFAULT_READING = {
    "id": "reading_1",
    "title": "Reading Test 1",
    "time_limit": 60,
    "parts": [
        {
            "part_number": 1,
            "title": "Part 1: Open Cloze",
            "instruction": "For questions 1-6, read the text below and think of the word which best fits each gap. Use only ONE word in each gap.",
            "type": "open_cloze",
            "text": "Climate Change and Its Impact\n\nClimate change is one of (1)_____ most pressing issues facing our planet today. Scientists agree that human activities, particularly the burning of fossil fuels, (2)_____ responsible for the rising global temperatures we are experiencing.\n\nThe effects of climate change are already (3)_____ felt around the world. Extreme weather events such (4)_____ hurricanes, floods, and droughts are becoming more frequent and severe. Sea levels are rising, threatening coastal communities and island nations.\n\n(5)_____ order to address this crisis, governments and individuals must take action. Reducing carbon emissions, investing in renewable energy, and protecting forests are all essential steps. However, time is running (6)_____. If we do not act quickly, the consequences will be catastrophic.",
            "questions": [
                {"number": 1, "correct": "the"},
                {"number": 2, "correct": "are"},
                {"number": 3, "correct": "being"},
                {"number": 4, "correct": "as"},
                {"number": 5, "correct": "In"},
                {"number": 6, "correct": "out"}
            ]
        },
        {
            "part_number": 2,
            "title": "Part 2: Multiple Choice Cloze",
            "instruction": "For questions 9-16, read the text and choose which answer (A–J) best fits each gap. Questions are listed in order on the left; choose one of the 10 variants for each.",
            "type": "multiple_choice_cloze",
            "text": "The Rise of Remote Work\n\nThe COVID-19 pandemic has (9)_____ transformed the way we work. Before 2020, working from home was (10)_____ a privilege enjoyed by a small percentage of the workforce. However, the global health crisis (11)_____ companies worldwide to rapidly adopt remote work policies.\n\nThis shift has had both positive and negative (12)_____. On the one hand, employees have gained more flexibility and eliminated lengthy commutes. Many workers report feeling more (13)_____ and having a better work-life balance. On the other hand, some people struggle with isolation and find it difficult to (14)_____ work from their personal life.\n\nCompanies are now (15)_____ hybrid models that combine remote and office work. This approach aims to offer the best of both worlds, allowing employees to enjoy flexibility while still maintaining face-to-face (16)_____ with colleagues.",
            "questions": [
                {"number": 9, "question": "The COVID-19 pandemic has _____ transformed the way we work.", "options": {"A": "deeply", "B": "hardly", "C": "rarely", "D": "slightly", "E": "fully", "F": "barely", "G": "fairly", "H": "widely", "I": "nearly", "J": "truly"}, "correct": "A"},
                {"number": 10, "question": "Before 2020, working from home was _____ a privilege enjoyed by a small percentage of the workforce.", "options": {"A": "often", "B": "commonly", "C": "mainly", "D": "usually", "E": "mostly", "F": "typically", "G": "largely", "H": "always", "I": "sometimes", "J": "rarely"}, "correct": "C"},
                {"number": 11, "question": "The global health crisis _____ companies worldwide to rapidly adopt remote work policies.", "options": {"A": "made", "B": "forced", "C": "let", "D": "allowed", "E": "led", "F": "enabled", "G": "required", "H": "caused", "I": "persuaded", "J": "encouraged"}, "correct": "B"},
                {"number": 12, "question": "This shift has had both positive and negative _____.", "options": {"A": "consequences", "B": "results", "C": "outcomes", "D": "effects", "E": "impacts", "F": "reactions", "G": "responses", "H": "changes", "I": "developments", "J": "trends"}, "correct": "A"},
                {"number": 13, "question": "Many workers report feeling more _____ and having a better work-life balance.", "options": {"A": "effective", "B": "productive", "C": "efficient", "D": "successful", "E": "focused", "F": "motivated", "G": "satisfied", "H": "relaxed", "I": "creative", "J": "confident"}, "correct": "B"},
                {"number": 14, "question": "Some people find it difficult to _____ work from their personal life.", "options": {"A": "divide", "B": "split", "C": "separate", "D": "part", "E": "distinguish", "F": "remove", "G": "keep", "H": "balance", "I": "manage", "J": "organize"}, "correct": "C"},
                {"number": 15, "question": "Companies are now _____ hybrid models that combine remote and office work.", "options": {"A": "accepting", "B": "receiving", "C": "embracing", "D": "welcoming", "E": "adopting", "F": "introducing", "G": "testing", "H": "exploring", "I": "considering", "J": "supporting"}, "correct": "C"},
                {"number": 16, "question": "Employees enjoy flexibility while still maintaining face-to-face _____ with colleagues.", "options": {"A": "interaction", "B": "communication", "C": "connection", "D": "contact", "E": "collaboration", "F": "cooperation", "G": "discussion", "H": "relationship", "I": "network", "J": "exchange"}, "correct": "A"}
            ]
        },
        {
            "part_number": 3,
            "title": "Part 3: Matching Headings to Paragraphs",
            "instruction": "Read the text and choose the correct heading for each paragraph from the list of headings below. There are more headings than paragraphs, so you will not use all of them. You cannot use any heading more than once.",
            "type": "matching_headings",
            "main_title": "HOW DOES THE BIOLOGICAL CLOCK TICK?",
            "headings": {
                "A": "The biological clock",
                "B": "Why dying is beneficial",
                "C": "The ageing process of men and women",
                "D": "Prolonging your life",
                "E": "Limitations of life span",
                "F": "Modes of development of different species",
                "G": "A stable life span despite improvements",
                "H": "Energy consumption"
            },
            "paragraphs": [
                {
                    "number": "I",
                    "text": "Our life span is restricted. Everyone accepts this as 'biologically' obvious. 'Nothing lives for ever!' However, in this statement we think of artificially produced, technical objects, products which are subjected to natural wear and tear during use. This leads to the result that at some time or other the object stops working and is unusable ('death' in the biological sense). But are the wear and tear and loss of function of technical objects and the death of living organisms really similar or comparable?"
                },
                {
                    "number": "II",
                    "text": "Thus ageing and death should not be seen as inevitable, particularly as the organism possesses many mechanisms for repair. It is not, in principle, necessary for a biological system to age and die. Nevertheless, a restricted life span, ageing, and then death are basic characteristics of life. The reason for this is easy to recognise: in nature, the existent organisms either adapt or are regularly replaced by new types. Because of changes in the genetic material (mutations) these have new characteristics and in the course of their individual lives they are tested for optimal or better adaptation to the environmental conditions. Immortality would disrupt this system—it needs room for new and better life. This is the basic problem of evolution."
                },
                {
                    "number": "III",
                    "text": "Every organism has a life span which is highly characteristic. The number of years during which something lives is highly varied. There are striking differences in life span between different species of animals, but within one species the parameter is relatively constant. For example, the average duration of human life has hardly changed in thousands of years. Although more and more people attain an advanced age as a result of developments in medical care and better nutrition, the characteristic upper limit for most remains 80 years. A further argument against the simple 'wear and tear' theory can be seen in the fact that the time within which organisms age lies between a few hours (for a unicellular organism) and several thousand years (for mammoth trees)."
                },
                {
                    "number": "IV",
                    "text": "If a life span is a genetically determined biological characteristic, it is logically necessary to propose the existence of an internal clock, which in some way measures and controls the ageing process and which finally determines death as the last step in a fixed programme. Like the life span, the metabolic rate has for different organisms a fixed mathematical relationship to the body mass. In comparison to the life span this relationship is 'inverted': the larger the organism the lower its metabolic rate. Again this relationship is valid not only for birds, but also, similarly on average within the systematic unit, for all other organisms (plants, animals, unicellular organisms)."
                },
                {
                    "number": "V",
                    "text": "Animals which behave 'frugally' with energy become particularly old, for example, crocodiles and tortoises. Parrots and birds of prey are often held chained up. Thus they are not able to 'experience life' and so they attain a high life span in captivity. Animals which save energy by hibernation or lethargy (e.g. bats or hedgehogs) live much longer than those which are always active. The metabolic rate of mice can be reduced by a very low consumption of food (hunger diet). They then live twice as long as their well-fed comrades. Women live distinctly longer than men. If you examine the metabolic rates of the two sexes you establish that the higher male metabolic rate roughly accounts for the lower male life span. That means that they live life 'energetically'—more intensively, but not for as long."
                },
                {
                    "number": "VI",
                    "text": "It follows from the above that sparing use of energy reserves should tend to extend life. Extreme high performance sports may lead to optimal cardiovascular performance, but they quite certainly do not prolong life. Relaxation lowers metabolic rate, as does adequate sleep and in general an equable and balanced personality. Each of us can develop his or her own 'energy saving programme' with a little self-observation, critical self-control and, above all, logical consistency. Experience will show that to live in this way not only increases the life span but is also very healthy. This final aspect should not be forgotten."
                }
            ],
            "questions": [
                {"number": 15, "paragraph": "I", "correct": "E"},
                {"number": 16, "paragraph": "II", "correct": "B"},
                {"number": 17, "paragraph": "III", "correct": "G"},
                {"number": 18, "paragraph": "IV", "correct": "A"},
                {"number": 19, "paragraph": "V", "correct": "H"},
                {"number": 20, "paragraph": "VI", "correct": "D"}
            ]
        },
        {
            "part_number": 4,
            "title": "Part 4: Reading Comprehension (4 MC + 5 True/False/No information)",
            "instruction": "Read the article. For questions 23–26, choose the best answer (A, B, C or D). For questions 27–31, choose A) True, B) False, or C) No information given in the text.",
            "type": "multiple_choice_comprehension",
            "text": "Artificial Intelligence: Friend or Foe?\n\nArtificial Intelligence (AI) has rapidly evolved from a concept in science fiction to a technology that permeates nearly every aspect of our daily lives. From the virtual assistants on our smartphones to the algorithms that recommend what we should watch next, AI has become an invisible but powerful force shaping our decisions and experiences.\n\nProponents of AI point to its tremendous potential for improving human life. In healthcare, AI systems can analyze medical images with greater accuracy than human doctors, potentially catching diseases at earlier, more treatable stages. In environmental science, AI helps researchers model climate patterns and develop strategies for conservation. The technology has also revolutionized industries from manufacturing to finance, increasing efficiency and reducing costs.\n\nHowever, critics raise valid concerns about the darker implications of AI advancement. One of the most pressing issues is the potential for widespread job displacement. As AI systems become capable of performing tasks previously done by humans, millions of workers may find themselves unemployed. This technological unemployment could exacerbate social inequality if the benefits of AI are not distributed fairly.\n\nAnother concern is the question of bias in AI systems. Because these systems learn from data created by humans, they can inherit and even amplify existing prejudices. There have been documented cases of AI systems discriminating against certain groups in areas such as hiring, lending, and criminal justice.\n\nPrivacy is yet another area of concern. AI systems often rely on vast amounts of personal data to function effectively. This raises questions about who has access to our information and how it might be used. The potential for surveillance and manipulation is significant, particularly when AI is combined with facial recognition technology.\n\nDespite these challenges, many experts believe that the benefits of AI outweigh the risks, provided that appropriate safeguards are put in place. This includes developing ethical guidelines for AI development, creating regulations to prevent misuse, and investing in education to prepare workers for a changing job market.",
            "questions": [
                {"number": 23, "question": "According to the first paragraph, AI has become", "options": {"A": "a visible force that shapes our decisions.", "B": "a technology that influences us without us noticing.", "C": "something that only exists in science fiction.", "D": "a technology limited to smartphone assistants."}, "correct": "B"},
                {"number": 24, "question": "What does the article say about AI in healthcare?", "options": {"A": "It has completely replaced human doctors.", "B": "It is less accurate than human analysis.", "C": "It may help detect diseases earlier.", "D": "It is only used for environmental research."}, "correct": "C"},
                {"number": 25, "question": "The article suggests that technological unemployment", "options": {"A": "is not a serious concern.", "B": "will only affect a few workers.", "C": "could increase social inequality.", "D": "has already been solved."}, "correct": "C"},
                {"number": 26, "question": "Why might AI systems show bias?", "options": {"A": "Because they are programmed to discriminate.", "B": "Because they learn from human-created data.", "C": "Because they only work in certain industries.", "D": "Because humans cannot control them."}, "correct": "B"},
                {"number": 27, "question": "AI is used in environmental science to model climate patterns.", "options": {"A": "True", "B": "False", "C": "No information"}, "correct": "A"},
                {"number": 28, "question": "All experts believe that AI should be banned.", "options": {"A": "True", "B": "False", "C": "No information"}, "correct": "B"},
                {"number": 29, "question": "Facial recognition is mentioned as a privacy concern when combined with AI.", "options": {"A": "True", "B": "False", "C": "No information"}, "correct": "A"},
                {"number": 30, "question": "AI has already replaced millions of workers worldwide.", "options": {"A": "True", "B": "False", "C": "No information"}, "correct": "C"},
                {"number": 31, "question": "The article says that ethical guidelines for AI are being developed.", "options": {"A": "True", "B": "False", "C": "No information"}, "correct": "A"}
            ]
        },
        {
            "part_number": 5,
            "title": "Part 5: Mixed (4 gap-fill + 2 multiple choice)",
            "instruction": "Read the passage. Complete the short text (questions 32–35) with ONE word in each gap. Then answer questions 36–37 by choosing A, B, C or D.",
            "type": "part5_mixed",
            "text": "The Future of Cities\n\nBy 2050, two-thirds of the world's population is expected to live in urban areas. This rapid urbanization presents both challenges and opportunities. Cities consume the majority of the world's energy and produce most of its waste, yet they are also centers of innovation, culture, and economic growth.\n\nSmart city technologies are already being deployed in many places. Sensors can monitor traffic flow and adjust signals in real time. Public transport systems use data to optimize routes and reduce waiting times. In some cities, streetlights dim when no one is nearby, saving energy. Waste collection is becoming more efficient with bins that signal when they are full.\n\nHowever, technology alone cannot solve urban problems. Affordable housing remains a critical issue in many cities, and inequality often increases as cities grow. Planners must balance economic development with social inclusion and environmental sustainability. The cities that thrive in the coming decades will be those that invest not only in digital infrastructure but also in green spaces, public transport, and affordable homes.",
            "gap_fill": {
                "text": "Smart cities use (32)_____ to monitor traffic and adjust signals. Some streetlights (33)_____ when no one is nearby. Bins can (34)_____ when they are full. Technology helps, but (35)_____ housing is still a key concern.",
                "questions": [
                    {"number": 32, "correct": "sensors"},
                    {"number": 33, "correct": "dim"},
                    {"number": 34, "correct": "signal"},
                    {"number": 35, "correct": "affordable"}
                ]
            },
            "questions": [
                {"number": 36, "question": "According to the passage, what will characterize cities that thrive in the future?", "options": {"A": "Only digital infrastructure.", "B": "Investment in green spaces, public transport, and affordable housing as well as technology.", "C": "Fewer people living in them.", "D": "No focus on sustainability."}, "correct": "B"},
                {"number": 37, "question": "What does the passage say about inequality and cities?", "options": {"A": "It usually decreases as cities grow.", "B": "Technology has solved it.", "C": "It often increases as cities grow.", "D": "It is not mentioned."}, "correct": "C"}
            ]
        }
    ]
}

DEFAULT_LISTENING = {
    "id": "listening_1",
    "title": "Listening Test 1",
    "time_limit": 40,
    "parts": [
        {
            "part_number": 1,
            "title": "Part 1: Multiple Choice",
            "instruction": "You will hear people talking in eight different situations. For questions 1-8, choose the best answer (A, B or C).",
            "type": "short_conversations",
            "questions": [
                {"number": 1, "audio_description": "A woman is talking to her colleague about a meeting.", "transcript": "Woman: Did you hear? The marketing meeting has been moved from 2pm to 4pm. The director had a last-minute conflict with the original time.\nMan: Oh, that's actually better for me. I have a client call at 2:30 that I was worried about.\nWoman: Great. See you at four then.", "options": {"A": "The director had another appointment.", "B": "The man requested a later time.", "C": "The meeting room was not available."}, "correct": "A"},
                {"number": 2, "audio_description": "You hear a weather forecast on the radio.", "transcript": "Announcer: Good morning, listeners. Today we're looking at a mostly cloudy day with temperatures around 15 degrees. There's a 60% chance of rain in the afternoon, so don't forget your umbrella if you're heading out later. Tomorrow looks much better though, with sunshine expected throughout the day.", "options": {"A": "It will be cloudy.", "B": "It will rain.", "C": "It will be sunny."}, "correct": "C"},
                {"number": 3, "audio_description": "A customer is speaking to a shop assistant.", "transcript": "Customer: Excuse me, I bought this jacket last week, but when I got home I noticed this small tear near the pocket. I'd like to exchange it for the same one, please.\nAssistant: I'm sorry about that. Do you have your receipt?\nCustomer: Yes, here it is.", "options": {"A": "The jacket is the wrong size.", "B": "The jacket is damaged.", "C": "The jacket is the wrong color."}, "correct": "B"},
                {"number": 4, "audio_description": "You hear a message on an answering machine.", "transcript": "Hello, this is Dr. Patterson's office calling to confirm your appointment for Thursday at 10am. If you need to reschedule, please call us back at 555-0123 before Wednesday afternoon.", "options": {"A": "To cancel an appointment.", "B": "To confirm an appointment.", "C": "To make a new appointment."}, "correct": "B"},
                {"number": 5, "audio_description": "Two friends are discussing weekend plans.", "transcript": "Man: So, are you still coming to the barbecue on Saturday?\nWoman: I'd love to, but I have to finish a report for Monday. I've been putting it off all week.\nMan: That's too bad. Maybe we can meet up for coffee on Sunday instead?\nWoman: That would be great. Let's say 2 o'clock at the usual place?", "options": {"A": "She has to visit family.", "B": "She has work to complete.", "C": "She is going to a coffee shop."}, "correct": "B"},
                {"number": 6, "audio_description": "A travel agent is giving information.", "transcript": "Agent: The flight departs at 7:15 in the morning and arrives in Paris at 9:30 local time. You'll have a two-hour layover in Amsterdam. The total cost including taxes is $450.", "options": {"A": "London", "B": "Amsterdam", "C": "Brussels"}, "correct": "B"},
                {"number": 7, "audio_description": "A professor is making an announcement.", "transcript": "Professor: Before we end today's class, I want to remind everyone that the deadline for the research paper has been extended by one week. It's now due on the 25th instead of the 18th. However, I still encourage you to submit early if you can.", "options": {"A": "The paper topic has changed.", "B": "The deadline has been extended.", "C": "The class will end early."}, "correct": "B"},
                {"number": 8, "audio_description": "A woman is talking about her new job.", "transcript": "Woman: I started my new job last Monday. The office is only a 10-minute walk from my apartment, which is so much better than my hour-long commute before. The work is challenging but interesting.", "options": {"A": "The high salary.", "B": "The short distance from home.", "C": "The easy work."}, "correct": "B"}
            ]
        },
        {
            "part_number": 2,
            "title": "Part 2: Gap Fill",
            "instruction": "You will hear a talk about the history of coffee. For questions 9-14, complete the sentences with ONE word.",
            "type": "sentence_completion",
            "audio_description": "A lecturer giving a talk about the history of coffee.",
            "transcript": "Good afternoon, everyone. Today I'm going to talk about the fascinating history of coffee.\n\nThe story of coffee begins in Ethiopia, where, according to legend, a goat herder named Kaldi noticed his goats becoming energetic after eating berries from a certain tree.\n\nFrom Ethiopia, coffee spread to the Arabian Peninsula. By the 15th century, coffee was being grown in Yemen. Coffee houses, known as qahveh khaneh, began to appear in cities throughout the Middle East.\n\nEuropeans first encountered coffee in the 17th century when Venetian traders brought it to Italy.\n\nThe Dutch were the first Europeans to establish coffee plantations in their colonies, starting in Java, Indonesia.\n\nToday, coffee is the second most traded commodity in the world after oil. The largest producer of coffee is Brazil.",
            "questions": [
                {"number": 9, "question": "According to legend, coffee was discovered by a _____ herder.", "correct": "goat"},
                {"number": 10, "question": "Coffee originated in the country of _____.", "correct": "Ethiopia"},
                {"number": 11, "question": "By the 15th century, coffee was being grown in _____.", "correct": "Yemen"},
                {"number": 12, "question": "Coffee was first brought to Europe by _____ traders.", "correct": "Venetian"},
                {"number": 13, "question": "The Dutch established plantations in _____, Indonesia.", "correct": "Java"},
                {"number": 14, "question": "The largest coffee producer in the world is _____.", "correct": "Brazil"}
            ]
        },
        {
            "part_number": 3,
            "title": "Part 3: Speaker Matching",
            "instruction": "You will hear four people talking about learning a foreign language. For questions 15-18, match each speaker with the correct statement (A-F).",
            "type": "speaker_matching",
            "audio_description": "Four people talking about learning a foreign language.",
            "speakers": [
                {"number": 15, "name": "Speaker 1", "transcript": "When I moved to Spain for work, I was forced to learn Spanish quickly. The best thing I did was completely immerse myself - I stopped watching English TV and only listened to Spanish radio."},
                {"number": 16, "name": "Speaker 2", "transcript": "I tried so many language apps and courses, but what really worked for me was finding a language exchange partner. We meet twice a week - one day we speak only German, the next only English."},
                {"number": 17, "name": "Speaker 3", "transcript": "Grammar books and vocabulary lists never worked for me. I learned French by watching French films with French subtitles. It was entertainment and education at the same time."},
                {"number": 18, "name": "Speaker 4", "transcript": "The biggest mistake I made was being afraid to speak. I spent years perfecting my written Japanese but couldn't hold a conversation. Now I force myself to speak, even if I make mistakes."}
            ],
            "options": {
                "A": "suggests that making mistakes is part of learning",
                "B": "recommends learning through entertainment media",
                "C": "believes total immersion is the most effective method",
                "D": "thinks traditional learning methods are best",
                "E": "values the social aspect of language learning",
                "F": "believes language learning requires expensive courses"
            },
            "answers": [
                {"number": 15, "correct": "C"},
                {"number": 16, "correct": "E"},
                {"number": 17, "correct": "B"},
                {"number": 18, "correct": "A"}
            ]
        },
        {
            "part_number": 4,
            "title": "Part 4: Map Labeling",
            "instruction": "You will hear someone giving a talk. Label the places (19-23) on the map (A-H). There are THREE extra options which you do not need to use. Mark your answers on the answer sheet.",
            "type": "map_labeling",
            "map_image_url": "",
            "audio_description": "Someone giving a talk about places on a map.",
            "transcript": "Welcome to our town center. Let me point out some important locations. As you enter from London Road, you'll see the town hall directly ahead - that's the large building in the center. To your left, on High Street, there's a supermarket. If you continue down High Street and turn right onto Sheep Street, you'll find the post office. Further along Sheep Street, near the park, is the primary school. And finally, if you walk down Church Lane from the town hall, you'll come to Wok'n'Roll restaurant.",
            "places": [
                {"number": 19, "name": "town hall", "correct": "D"},
                {"number": 20, "name": "supermarket", "correct": "A"},
                {"number": 21, "name": "post office", "correct": "B"},
                {"number": 22, "name": "primary school", "correct": "E"},
                {"number": 23, "name": "Wok'n'Roll", "correct": "G"}
            ],
            "map_labels": ["A", "B", "C", "D", "E", "F", "G", "H"]
        },
        {
            "part_number": 5,
            "title": "Part 5: Multiple Choice",
            "instruction": "You will hear an interview with a marine biologist. For questions 25-30, choose the best answer (A, B or C).",
            "type": "interview",
            "audio_description": "An interview with Dr. Sarah Chen, a marine biologist.",
            "transcript": "Interviewer: Today we're joined by Dr. Sarah Chen, a marine biologist who has spent the last fifteen years studying ocean ecosystems.\n\nDr. Chen: Thank you for having me.\n\nInterviewer: How would you describe the current state of our oceans?\n\nDr. Chen: Our oceans are in crisis. We're seeing coral bleaching events more frequent than ever. Fish populations are declining due to overfishing. And perhaps most concerning is the plastic pollution problem.\n\nInterviewer: What do you think is the biggest threat?\n\nDr. Chen: Climate change. Rising ocean temperatures cause coral bleaching, change fish migration patterns, and as oceans warm they absorb more carbon dioxide, making them more acidic.\n\nInterviewer: What can ordinary people do?\n\nDr. Chen: Support policies that protect marine areas. That's the most impactful thing.\n\nInterviewer: Are there success stories?\n\nDr. Chen: When we protect areas properly, nature can recover remarkably quickly.\n\nInterviewer: What's next for your research?\n\nDr. Chen: Mapping microplastic distribution in the Pacific Ocean.",
            "questions": [
                {"number": 25, "question": "How long has Dr. Chen been studying ocean ecosystems?", "options": {"A": "Five years", "B": "Ten years", "C": "Fifteen years"}, "correct": "C"},
                {"number": 26, "question": "What does Dr. Chen consider the biggest threat?", "options": {"A": "Overfishing", "B": "Plastic pollution", "C": "Climate change"}, "correct": "C"},
                {"number": 27, "question": "What happens when oceans absorb more CO2?", "options": {"A": "They become warmer.", "B": "They become more acidic.", "C": "They become cleaner."}, "correct": "B"},
                {"number": 28, "question": "What is the most impactful action for people?", "options": {"A": "Reducing plastic use", "B": "Buying sustainable seafood", "C": "Supporting protective policies"}, "correct": "C"},
                {"number": 29, "question": "What does Dr. Chen say about protected areas?", "options": {"A": "They cannot recover.", "B": "They can recover quickly.", "C": "They are not affected."}, "correct": "B"},
                {"number": 30, "question": "What is Dr. Chen's current research about?", "options": {"A": "Coral reef restoration", "B": "Fish population recovery", "C": "Microplastic distribution"}, "correct": "C"}
            ]
        },
        {
            "part_number": 6,
            "title": "Part 6: Note Completion",
            "instruction": "You will hear a talk about healthy eating habits. For questions 31-36, complete the notes with ONE word in each gap.",
            "type": "note_completion",
            "audio_description": "A nutritionist giving a talk about healthy eating habits.",
            "transcript": "Today I want to share some simple tips for healthier eating. First, always eat a good breakfast - studies show it improves your concentration throughout the morning. Second, try to include protein in every meal, such as chicken, fish, or beans.\n\nDrinking enough water is essential - aim for at least eight glasses per day. Many people confuse thirst with hunger.\n\nWhen it comes to snacking, choose fruit or nuts instead of processed foods. Also, try to cook at home more often rather than ordering takeaway. Home-cooked meals typically contain less salt and sugar.\n\nFinally, don't skip meals. Regular eating maintains your energy levels and prevents overeating later in the day.",
            "text": "Today I want to share some simple tips for healthier eating. First, always eat a good (31)_____ - studies show it improves your concentration throughout the morning. Second, try to include (32)_____ in every meal, such as chicken, fish, or beans.\n\nDrinking enough water is essential - aim for at least eight (33)_____ per day. Many people confuse thirst with hunger.\n\nWhen it comes to snacking, choose fruit or (34)_____ instead of processed foods. Also, try to cook at home more often rather than ordering takeaway. Home-cooked meals typically contain less salt and (35)_____.\n\nFinally, don't skip meals. Regular eating maintains your energy levels and prevents (36)_____ later in the day.",
            "questions": [
                {"number": 31, "correct": "breakfast"},
                {"number": 32, "correct": "protein"},
                {"number": 33, "correct": "glasses"},
                {"number": 34, "correct": "nuts"},
                {"number": 35, "correct": "sugar"},
                {"number": 36, "correct": "overeating"}
            ]
        }
    ]
}

DEFAULT_WRITING = {
    "id": "writing_1",
    "title": "Writing Test 1",
    "time_limit": 80,
    "parts": [
        {
            "part_number": 1,
            "title": "Part 1",
            "instruction": "Read the instructions for each task carefully. Complete Task 1 and Task 2.",
            "tasks": [
                {
                    "task_number": 1,
                    "title": "Task 1",
                    "type": "task1",
                    "instruction": "Read the situation below and write your answer.",
                    "situation": "You recently bought a laptop online, but when it arrived, you discovered several problems with it. The screen has a small crack, the keyboard is missing a key, and the battery drains very quickly.\n\nWrite to the company's customer service. In your text:\n- Explain what problems you found with the laptop\n- Say how you feel about this situation\n- Tell them what you would like them to do about it\n\nRecommended: at least 50 words. Fewer is accepted but may receive a lower score; you may write more if you wish.",
                    "min_words": 50,
                    "max_words": 500
                },
                {
                    "task_number": 2,
                    "title": "Task 2",
                    "type": "task2",
                    "instruction": "Write your answer.",
                    "situation": "Your English teacher has asked you to write a review of a book, film, or TV series that you have enjoyed recently.\n\nWrite a review that:\n- Briefly describes what it is about\n- Explains what you liked about it\n- Recommends it and says who would enjoy it most\n\nWrite between 120-150 words.",
                    "min_words": 120,
                    "max_words": 150
                }
            ]
        },
        {
            "part_number": 2,
            "title": "Part 2: Essay",
            "instruction": "Write an essay on the topic below.",
            "type": "essay",
            "prompt": "Some people believe that technology has made our lives easier and more convenient. Others argue that technology has created new problems and made life more stressful.\n\nDiscuss both views and give your own opinion.\n\nWrite between 180-200 words.\n\nYour essay will be evaluated on:\n- Task Achievement\n- Coherence & Cohesion\n- Lexical Resource\n- Grammatical Range & Accuracy",
            "min_words": 180,
            "max_words": 200
        }
    ]
}


# ============ SESSION HELPERS ============

def get_session(session_id: str) -> Dict:
    if session_id not in sessions:
        sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "reading": {"completed": False, "score": 0, "total": 0, "percentage": 0},
            "listening": {"completed": False, "score": 0, "total": 0, "percentage": 0},
            "writing": {"completed": False, "percentage": 0},
            "overall_score": 0,
            "cefr_level": None
        }
    return sessions[session_id]


# ============ SCORING ============

def calculate_reading_score(answers: Dict[str, str], test_data: dict) -> Dict:
    correct = 0
    total = 0
    details = []
    for part in test_data["parts"]:
        ptype = part["type"]
        if ptype in ["multiple_choice_cloze", "multiple_choice_comprehension"]:
            for q in part["questions"]:
                total += 1
                qn = str(q["number"])
                ua = answers.get(qn, "").strip().upper()
                ca = q["correct"].upper()
                ic = ua == ca
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
        elif ptype == "open_cloze":
            for q in part["questions"]:
                total += 1
                qn = str(q["number"])
                ua = answers.get(qn, "").strip().lower()
                ca = q["correct"].lower()
                ic = ua == ca
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
        elif ptype == "matching_headings":
            for q in part["questions"]:
                total += 1
                qn = str(q["number"])
                ua = answers.get(qn, "").strip().upper()
                ca = q["correct"].upper()
                ic = ua == ca
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
        elif ptype == "gapped_text":
            for q in part["questions"]:
                total += 1
                qn = str(q["number"])
                ua = answers.get(qn, "").strip().upper()
                ca = q["correct"].upper()
                ic = ua == ca
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
        elif ptype == "part5_mixed":
            for q in part.get("gap_fill", {}).get("questions", []):
                total += 1
                qn = str(q["number"])
                ua = answers.get(qn, "").strip().lower()
                ca = q["correct"].lower()
                ic = ua == ca
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
            for q in part["questions"]:
                total += 1
                qn = str(q["number"])
                ua = answers.get(qn, "").strip().upper()
                ca = q["correct"].upper()
                ic = ua == ca
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
    pct = (correct / total * 100) if total > 0 else 0
    return {"correct": correct, "total": total, "percentage": round(pct, 1), "details": details}


def calculate_listening_score(answers: Dict[str, str], test_data: dict) -> Dict:
    correct = 0
    total = 0
    details = []
    for part in test_data["parts"]:
        ptype = part["type"]
        if ptype in ["short_conversations", "interview"]:
            for q in part["questions"]:
                total += 1
                qn = str(q["number"])
                ua = answers.get(qn, "").strip().upper()
                ca = q["correct"].upper()
                ic = ua == ca
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
        elif ptype in ["sentence_completion", "note_completion"]:
            for q in part["questions"]:
                total += 1
                qn = str(q["number"])
                ua = answers.get(qn, "").strip().lower()
                ca = q["correct"].lower()
                ic = ua == ca or ca in ua
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
        elif ptype in ["multiple_matching", "speaker_matching"]:
            for a in part["answers"]:
                total += 1
                qn = str(a["number"])
                ua = answers.get(qn, "").strip().upper()
                ca = a["correct"].upper()
                ic = ua == ca
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
        elif ptype == "map_labeling":
            for p in part["places"]:
                total += 1
                qn = str(p["number"])
                ua = answers.get(qn, "").strip().upper()
                ca = p["correct"].upper()
                ic = ua == ca
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
    pct = (correct / total * 100) if total > 0 else 0
    return {"correct": correct, "total": total, "percentage": round(pct, 1), "details": details}


# ============ WRITING EVALUATION (ULTRA-STRICT) ============

def detect_spam_advanced(text: str) -> dict:
    """ULTRA-STRICT spam/gibberish/repetition detection - Band 0 for invalid content"""
    if not text or len(text.strip()) < 5:
        return {"is_spam": True, "score": 0, "reason": "Text is empty or nearly empty - 0%."}

    words = text.split()
    wc = len(words)

    # CRITICAL: Less than 20 words = 0% (completely invalid)
    if wc < 20:
        return {"is_spam": True, "score": 0, "reason": f"Only {wc} words - minimum 20 required for evaluation - 0%."}

    # Less than 50 words = Band 1 max
    if wc < 50:
        return {"is_spam": True, "score": 1, "reason": f"Only {wc} words - severely under minimum requirement."}

    lw = [w.lower() for w in words]
    unique = set(lw)
    diversity = len(unique) / wc

    # STRICT: Any low diversity = Band 1
    if diversity < 0.2:
        return {"is_spam": True, "score": 1, "reason": f"Extremely low vocabulary ({int(diversity*100)}% unique) - spam detected - Band 1."}
    if diversity < 0.25:
        return {"is_spam": True, "score": 1, "reason": f"Very low vocabulary diversity ({int(diversity*100)}% unique) - Band 1."}

    # Check for repeated phrases/sentences - VERY STRICT
    sentences = re.split(r'[.!?\n]+', text)
    sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 3]
    if len(sentences) >= 2:
        unique_sents = set(sentences)
        sent_diversity = len(unique_sents) / len(sentences)
        if sent_diversity < 0.5:
            return {"is_spam": True, "score": 1, "reason": "Repeated sentences detected - spam - Band 1."}
        if sent_diversity < 0.7:
            return {"is_spam": True, "score": 1, "reason": f"High sentence repetition ({int((1-sent_diversity)*100)}% repeated) - Band 1."}

    # Check for keyboard spam / random chars
    alpha = sum(1 for c in text if c.isalpha())
    if alpha < len(text) * 0.5:
        return {"is_spam": True, "score": 1, "reason": "Too many non-alphabetic characters - Band 1."}

    # Check top word frequency - STRICT
    freq = {}
    for w in lw:
        freq[w] = freq.get(w, 0) + 1
    # Exclude common words
    common = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'and', 'or', 'but', 'if', 'that', 'this', 'it', 'i', 'you', 'we', 'they', 'he', 'she'}
    non_common_freq = {w: c for w, c in freq.items() if w not in common}
    if non_common_freq:
        top_word_pct = max(non_common_freq.values()) / wc
        if top_word_pct > 0.25:
            return {"is_spam": True, "score": 1, "reason": f"One word repeated {int(top_word_pct*100)}% of text - Band 1."}

    # Check n-gram repetition (2-word, 3-word, 4-word) - VERY STRICT
    for n in [2, 3, 4]:
        if wc >= n * 3:
            ngrams = [" ".join(lw[i:i+n]) for i in range(wc - n + 1)]
            ngram_freq = {}
            for ng in ngrams:
                ngram_freq[ng] = ngram_freq.get(ng, 0) + 1
            max_ng = max(ngram_freq.values())
            threshold = 0.2 if n == 2 else 0.15 if n == 3 else 0.1
            if max_ng > len(ngrams) * threshold:
                return {"is_spam": True, "score": 1, "reason": f"Repeated {n}-word phrase detected ({max_ng} times) - Band 1."}

    # Check if text is mostly the same few sentences reordered
    if len(sentences) >= 3:
        words_per_sent = [len(s.split()) for s in sentences if s]
        if words_per_sent:
            avg_sent_len = sum(words_per_sent) / len(words_per_sent)
            if avg_sent_len < 4:
                return {"is_spam": True, "score": 1, "reason": "Sentences too short (avg < 4 words) - Band 1."}

    # Check for nonsense/gibberish - words not in basic English
    # (simplified check - very short words or very long words)
    weird_words = [w for w in lw if len(w) > 15 or (len(w) > 2 and not any(c in 'aeiou' for c in w))]
    if len(weird_words) > wc * 0.2:
        return {"is_spam": True, "score": 1, "reason": "Too many nonsense/gibberish words - Band 1."}

    # CRITICAL: Check if words are actual English words
    common_english = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
        'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
        'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
        'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well',
        'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us', 'very', 'much', 'before', 'too', 'same',
        'been', 'has', 'more', 'made', 'did', 'down', 'here', 'still', 'own', 'find', 'world', 'again', 'hand', 'part', 'place', 'during',
        'where', 'off', 'right', 'man', 'always', 'however', 'another', 'never', 'while', 'last', 'might', 'under', 'such', 'through',
        'life', 'being', 'long', 'little', 'got', 'those', 'great', 'old', 'many', 'must', 'home', 'big', 'around', 'high', 'each', 'read',
        'need', 'few', 'between', 'without', 'head', 'small', 'every', 'next', 'something', 'since', 'best', 'both', 'ask', 'house',
        'why', 'found', 'put', 'does', 'end', 'keep', 'let', 'thought', 'going', 'help', 'nothing', 'really', 'point', 'though', 'went',
        'better', 'enough', 'money', 'school', 'told', 'turn', 'water', 'three', 'face', 'thing', 'things', 'became', 'believe', 'second',
        'am', 'is', 'are', 'was', 'were', 'hello', 'dear', 'sincerely', 'regards', 'thanks', 'thank', 'please', 'sorry', 'hope', 'looking',
        'forward', 'hearing', 'soon', 'write', 'writing', 'touch', 'contact', 'happy', 'sad', 'today', 'morning', 'love', 'book', 'word'
    }
    clean_lw = [w.strip('.,!?;:"\'()[]{}') for w in lw if w.strip('.,!?;:"\'()[]{}').isalpha()]
    if clean_lw:
        english_count = sum(1 for w in clean_lw if w in common_english)
        english_ratio = english_count / len(clean_lw)
        if english_ratio < 0.2:
            return {"is_spam": True, "score": 0, "reason": f"Gibberish detected - only {int(english_ratio*100)}% recognizable English words - 0%."}
        if english_ratio < 0.3:
            return {"is_spam": True, "score": 1, "reason": f"Mostly gibberish - only {int(english_ratio*100)}% recognizable English words - Band 1."}

    return {"is_spam": False, "score": None, "reason": None}


def algorithmic_score(text: str, min_w: int, max_w: int, task_type: str) -> dict:
    """ULTRA-STRICT algorithmic evaluation - starts at 2 (Limited User)"""
    spam = detect_spam_advanced(text)
    if spam["is_spam"]:
        return {"score": spam["score"], "feedback": spam["reason"], "wc": len(text.split())}

    words = text.split()
    wc = len(words)
    lw = [w.lower() for w in words if w.isalpha()]
    unique = len(set(lw))
    diversity = unique / wc if wc > 0 else 0

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 2]
    num_sent = len(sentences) if sentences else 1
    avg_sl = wc / num_sent

    score = 2  # Start VERY LOW (Limited User) - must earn points
    fb = []

    # Word count - STRICT requirements (0 ball ham mumkin)
    if wc < min_w * 0.3:
        score = 0
        fb.append(f"SEVERELY under word count ({wc}/{min_w}) - Band 0.")
        return {"score": 0, "feedback": " ".join(fb), "wc": wc}
    elif wc < min_w * 0.5:
        fb.append(f"Very under word count ({wc}/{min_w}) - max Band 2.")
    elif wc < min_w * 0.7:
        fb.append(f"Under word count ({wc}/{min_w}) - max Band 3.")
        score = min(score, 3)
    elif wc < min_w:
        fb.append(f"Slightly under word count ({wc}/{min_w}).")
    elif min_w <= wc <= max_w:
        score += 1
        fb.append("Word count appropriate.")
    elif wc > max_w * 1.3:
        score -= 1
        fb.append(f"Over word count ({wc}/{max_w}).")

    # Vocabulary diversity - STRICT
    if diversity < 0.3:
        fb.append("Very limited vocabulary - cannot score above Band 3.")
        score = min(score, 3)
    elif diversity < 0.4:
        fb.append("Limited vocabulary range.")
    elif diversity >= 0.5:
        score += 1
        fb.append("Adequate vocabulary range.")
    elif diversity >= 0.6:
        score += 1
        fb.append("Good vocabulary range.")

    # Sentence complexity - STRICT
    if avg_sl < 5:
        score -= 1
        fb.append("Sentences too short - simplistic writing.")
    elif avg_sl < 7:
        fb.append("Very simple sentences.")
    elif 10 <= avg_sl <= 18:
        score += 1
        fb.append("Good sentence variety.")
    elif avg_sl > 25:
        fb.append("Sentences too long - unclear.")

    # Punctuation & caps - REQUIRED
    if text and not text[0].isupper():
        score -= 1
        fb.append("No capitalization - poor presentation.")
    if not any(c in text for c in '.!?'):
        score -= 1
        fb.append("No punctuation - Band 2 max.")
        score = min(score, 2)

    # Paragraph structure for essay - REQUIRED
    if task_type == "essay":
        paras = [p.strip() for p in text.split('\n') if len(p.strip()) > 10]
        if len(paras) < 2:
            fb.append("No paragraph structure - max Band 3.")
            score = min(score, 3)
        elif len(paras) < 3:
            fb.append("Needs more paragraphs.")
        elif len(paras) >= 4:
            score += 1
            fb.append("Good structure.")

    # Sentence repetition check - STRICT
    sent_lower = [s.strip().lower() for s in sentences if len(s.strip()) > 5]
    if len(sent_lower) >= 2:
        unique_s = set(sent_lower)
        ratio = len(unique_s) / len(sent_lower)
        if ratio < 0.7:
            score = max(0, score - 2)
            fb.append(f"Sentence repetition detected ({int((1-ratio)*100)}% repeated).")
        elif ratio < 0.85:
            score -= 1
            fb.append("Some repetition in sentences.")

    # Check for real content (not just filler)
    content_words = [w for w in lw if len(w) > 3]
    if len(content_words) < wc * 0.4:
        fb.append("Too many short/filler words.")
        score -= 1

    score = max(0, min(9, score))
    return {"score": score, "feedback": " ".join(fb), "wc": wc}


async def evaluate_writing_with_ai(task1: str, task2: str, essay: str, writing_test: dict) -> Dict:
    """100% AI evaluation - NO spam detection, direct AI evaluation only"""

    print(f"[Writing AI] === BAHOLASH BOSHLANDI ===")
    print(f"[Writing AI] task1: {len(task1.split())} so'z, task2: {len(task2.split())} so'z, essay: {len(essay.split())} so'z")
    print(f"[Writing AI] OPENAI_API_KEY mavjud: {bool(OPENAI_API_KEY)}, uzunlik: {len(OPENAI_API_KEY)}")

    # Bo'sh yoki juda qisqa matn tekshirish (faqat 5 so'zdan kam)
    results = {}
    for name, txt in [("task1", task1), ("task2", task2), ("essay", essay)]:
        wc = len(txt.split())
        if wc < 5:
            print(f"[Writing AI] {name}: faqat {wc} so'z - juda kam, score=0")
            if name == "essay":
                results[name] = {
                    "score": 0, "band": 0, "word_count": wc, "is_valid": False,
                    "feedback": {
                        "overall": "Band 0 - Bo'sh",
                        "task_achievement": f"Faqat {wc} so'z yozilgan. Minimum 20 so'z kerak.",
                        "coherence_cohesion": "", "lexical_resource": "", "grammatical_range": ""
                    }
                }
            else:
                results[name] = {
                    "score": 0, "band": 0, "word_count": wc, "is_valid": False,
                    "feedback": {
                        "overall": "Band 0 - Bo'sh",
                        "content": f"Faqat {wc} so'z yozilgan. Minimum 20 so'z kerak.",
                        "organization": "", "language": "", "accuracy": ""
                    }
                }

    # AI bilan baholash - barcha qolgan qismlar
    parts_to_eval = [n for n in ["task1", "task2", "essay"] if n not in results]
    print(f"[Writing AI] AI baholash uchun: {parts_to_eval}")

    if parts_to_eval:
        ai_result = await try_ai_evaluation(task1, task2, essay, writing_test, parts_to_eval)
        if ai_result:
            print(f"[Writing AI] AI muvaffaqiyatli baholadi! Natijalar: {list(ai_result.keys())}")
            for name in parts_to_eval:
                if name in ai_result:
                    results[name] = ai_result[name]
                    print(f"[Writing AI] {name}: score={ai_result[name].get('score', '?')}")
        else:
            print("[Writing AI] AI baholash muvaffaqiyatsiz bo'ldi!")
            for name in parts_to_eval:
                txt = task1 if name == "task1" else (task2 if name == "task2" else essay)
                wc = len(txt.split())
                if name == "essay":
                    results[name] = {
                        "score": 0, "band": 0, "word_count": wc, "is_valid": False,
                        "feedback": {
                            "overall": "AI baholash ishlamadi",
                            "task_achievement": "AI xizmati hozirda ishlamayapti. Qayta urinib ko'ring.",
                            "coherence_cohesion": "OPENAI_API_KEY tekshiring.",
                            "lexical_resource": "", "grammatical_range": ""
                        },
                        "ai_unavailable": True
                    }
                else:
                    results[name] = {
                        "score": 0, "band": 0, "word_count": wc, "is_valid": False,
                        "feedback": {
                            "overall": "AI baholash ishlamadi",
                            "content": "AI xizmati hozirda ishlamayapti. Qayta urinib ko'ring.",
                            "organization": "OPENAI_API_KEY tekshiring.",
                            "language": "", "accuracy": ""
                        },
                        "ai_unavailable": True
                    }

    # Ensure all parts have results
    for name in ["task1", "task2", "essay"]:
        if name not in results:
            results[name] = {"score": 0, "band": 0, "word_count": 0, "is_valid": False,
                             "feedback": {"overall": "Baholanmadi", "content": "", "organization": "", "language": "", "accuracy": ""}}

    # Calculate overall
    t1s = results["task1"]["score"]
    t2s = results["task2"]["score"]
    es = results["essay"]["score"]
    overall = t1s * 0.25 + t2s * 0.25 + es * 0.5
    pct = (overall / 9) * 100

    if t1s == 0 and t2s == 0 and es == 0:
        pct = 0

    print(f"[Writing AI] === NATIJA: task1={t1s}, task2={t2s}, essay={es}, overall={overall:.2f}, pct={pct:.1f}% ===")

    cefr = "A1"
    for lv, d in CEFR_LEVELS.items():
        if pct >= d["min_score"]:
            cefr = lv
            break

    return {
        "task1": results["task1"], "task2": results["task2"], "essay": results["essay"],
        "overall_score": round(overall, 1), "overall_band": round(overall),
        "overall_percentage": round(pct, 1), "cefr_level": cefr,
        "general_feedback": "AI baholash yakunlandi. Yozuvingiz barcha qismlar bo'yicha tahlil qilindi." if any(r.get("is_valid") for r in results.values()) else "Yuborilgan matn baholanmadi. Iltimos, ingliz tilida mazmunli javob yozing."
    }


COMMON_ENGLISH_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
    'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
    'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
    'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well',
    'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us', 'very', 'much', 'before', 'too', 'same',
    'been', 'has', 'more', 'made', 'did', 'down', 'here', 'still', 'own', 'find', 'world', 'again', 'hand', 'part', 'place', 'during',
    'where', 'off', 'right', 'man', 'always', 'however', 'another', 'never', 'while', 'last', 'might', 'under', 'such', 'through',
    'life', 'being', 'long', 'little', 'got', 'those', 'great', 'old', 'many', 'must', 'home', 'big', 'around', 'high', 'each', 'read',
    'need', 'few', 'between', 'without', 'head', 'small', 'every', 'next', 'something', 'still', 'since', 'best', 'both', 'ask', 'house',
    'why', 'found', 'put', 'does', 'end', 'keep', 'let', 'thought', 'going', 'help', 'nothing', 'really', 'point', 'though', 'went',
    'better', 'enough', 'money', 'school', 'told', 'turn', 'water', 'three', 'face', 'thing', 'things', 'became', 'believe', 'second',
    'person', 'state', 'night', 'away', 'having', 'room', 'should', 'number', 'yes', 'called', 'family', 'feel', 'began', 'sure', 'name',
    'become', 'important', 'business', 'looking', 'children', 'rather', 'later', 'used', 'kind', 'once', 'four', 'five', 'six', 'seven',
    'eight', 'nine', 'ten', 'today', 'morning', 'love', 'book', 'write', 'writing', 'written', 'wrote', 'word', 'words', 'english',
    'test', 'email', 'letter', 'review', 'essay', 'opinion', 'agree', 'disagree', 'think', 'believe', 'feel', 'suggest', 'recommend',
    'therefore', 'moreover', 'furthermore', 'however', 'although', 'nevertheless', 'conclusion', 'finally', 'firstly', 'secondly',
    'addition', 'example', 'instance', 'order', 'result', 'reason', 'fact', 'indeed', 'certainly', 'course', 'generally', 'usually',
    'often', 'sometimes', 'always', 'never', 'perhaps', 'probably', 'possible', 'impossible', 'necessary', 'important', 'different',
    'interesting', 'beautiful', 'wonderful', 'excellent', 'amazing', 'terrible', 'horrible', 'difficult', 'easy', 'simple', 'hard',
    'experience', 'education', 'environment', 'technology', 'information', 'communication', 'development', 'opportunity', 'community',
    'restaurant', 'hotel', 'movie', 'film', 'music', 'sport', 'travel', 'friend', 'friends', 'dear', 'sincerely', 'regards', 'best',
    'thanks', 'thank', 'please', 'sorry', 'hope', 'looking', 'forward', 'hearing', 'soon', 'write', 'writing', 'touch', 'contact',
    'happy', 'sad', 'angry', 'excited', 'worried', 'surprised', 'disappointed', 'satisfied', 'comfortable', 'uncomfortable',
    'would', 'could', 'should', 'might', 'may', 'must', 'will', 'shall', 'can', 'able', 'unable', 'doing', 'done', 'seen', 'took',
    'gave', 'came', 'knew', 'thought', 'wanted', 'needed', 'tried', 'started', 'began', 'finished', 'ended', 'continued', 'stopped'
}

async def get_strict_ai_score(text: str, task_type: str) -> int:
    """ULTRA-STRICT fallback score when AI is unavailable - properly detects gibberish"""
    words = text.split()
    wc = len(words)

    # Absolute minimums
    if wc < 20:
        return 0
    if wc < 40:
        return 1

    # Clean words (lowercase, alphabetic only)
    clean_words = [w.lower().strip('.,!?;:"\'()[]{}') for w in words]
    clean_words = [w for w in clean_words if w.isalpha() and len(w) > 1]

    if len(clean_words) < 15:
        return 0

    # Check how many words are actual English words
    english_word_count = sum(1 for w in clean_words if w in COMMON_ENGLISH_WORDS)
    english_ratio = english_word_count / len(clean_words) if clean_words else 0

    # STRICT: If less than 30% recognized English words = gibberish
    if english_ratio < 0.25:
        return 0  # Completely gibberish
    if english_ratio < 0.35:
        return 1  # Mostly gibberish
    if english_ratio < 0.45:
        return 2  # Significant gibberish

    # Check word diversity
    unique = len(set(clean_words))
    diversity = unique / len(clean_words) if clean_words else 0

    if diversity < 0.2:
        return 1  # Too repetitive
    if diversity < 0.3:
        return 2

    # Check sentence structure
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]

    if len(sentences) < 2:
        return 2  # No real sentence structure

    # Check average sentence length (too short = gibberish)
    avg_sent_len = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
    if avg_sent_len < 5:
        return 1  # Fragmented text

    # Target word counts: Task1: 50+, Task2: 120-150, Essay: 180-200
    target_min = 50 if task_type == "email" else (120 if task_type != "essay" else 180)

    # Score based on content quality
    base_score = 3  # Start at band 3

    # Adjust for word count
    if wc < target_min * 0.5:
        base_score = 2
    elif wc < target_min * 0.7:
        base_score = 3
    elif wc < target_min * 0.9:
        base_score = 4
    else:
        base_score = 4

    # Adjust for English quality
    if english_ratio > 0.6:
        base_score = min(base_score + 1, 5)
    elif english_ratio < 0.5:
        base_score = max(base_score - 1, 2)

    # Cap at 5 without proper AI evaluation
    return min(base_score, 5)


async def try_ai_evaluation(task1: str, task2: str, essay: str, writing_test: dict, parts_to_eval: list) -> dict:
    """Try AI evaluation via Anthropic or OpenAI"""
    t1_instruction = ""
    t2_instruction = ""
    essay_instruction = ""
    if writing_test and writing_test.get("parts"):
        for p in writing_test["parts"]:
            if p.get("part_number") == 1 and p.get("tasks"):
                t1_instruction = (p["tasks"][0].get("situation") or "")[:300]
                if len(p["tasks"]) > 1:
                    t2_instruction = (p["tasks"][1].get("situation") or "")[:300]
            if p.get("part_number") == 2:
                essay_instruction = (p.get("prompt") or "")[:400]
    prompt = f"""You are a CEFR English writing examiner. Evaluate the candidate's writing strictly but fairly.

SCORING GUIDE (0-9 scale). IMPORTANT: Use 0 when the answer deserves no credit.
- Score 0: Empty, nearly empty (e.g. under 10 words), gibberish, nonsense, completely off-topic, non-English, or no meaningful content. Give 0 whenever the writing does not deserve any credit.
- Score 1: Only if there is at least minimal relevant content but very poor (e.g. a few relevant words or one short relevant sentence). Otherwise use 0.
- Score 2: Very limited English, mostly incomprehensible
- Score 3: Limited user - frequent errors, hard to follow
- Score 4: Below average - many errors, partially addresses task
- Score 5: Modest - adequate attempt, some errors, addresses task
- Score 6: Competent - generally effective, minor errors
- Score 7: Good - well-written, few errors, good task achievement
- Score 8: Very good - fluent, rare errors, excellent structure
- Score 9: Expert - near-perfect English

RULES:
- Gibberish / nonsense / empty / irrelevant = score 0 (not 1)
- Repeated sentences or spam = score 0 or 1
- Off-topic = score 0 (write "Off-topic" or "Irrelevant" in feedback)
- Under word count = max score 4
- Each score must be a NUMBER from 0 to 9 (use 0 when appropriate)

TASK 1 instruction: {t1_instruction}
TASK 2 instruction: {t2_instruction}
ESSAY topic: {essay_instruction}

=== CANDIDATE TASK 1 ({len(task1.split())} words) ===
{task1[:2000]}

=== CANDIDATE TASK 2 ({len(task2.split())} words) ===
{task2[:2000]}

=== CANDIDATE ESSAY ({len(essay.split())} words) ===
{essay[:3000]}

IMPORTANT: general_feedback must be written in Uzbek (Latin script): 2-3 sentences overall summary and 1-2 short recommendations for the candidate. Other feedback fields can be in English.

Return ONLY valid JSON (no markdown, no code blocks):
{{"task1":{{"score":5,"content":"feedback","organization":"feedback","language":"feedback","accuracy":"feedback"}},"task2":{{"score":5,"content":"feedback","organization":"feedback","language":"feedback","accuracy":"feedback"}},"essay":{{"score":5,"task_achievement":"feedback","coherence_cohesion":"feedback","lexical_resource":"feedback","grammatical_range":"feedback"}},"general_feedback":"umumiy xulosa va tavsiyalar o'zbekchada"}}"""

    def extract_json(text: str):
        """AI javobidan JSON ni ajratib olish - bir necha usul bilan sinab ko'radi"""
        if not text or not text.strip():
            print("[Writing AI] extract_json: bo'sh matn")
            return None
        raw = text.strip()

        def try_parse(s: str):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                return None

        # 1) To'g'ridan-to'g'ri parse
        out = try_parse(raw)
        if out and isinstance(out, dict):
            return out

        # 2) ```json ... ``` blokini olib tashlash
        if "```" in raw:
            code_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw)
            if code_match:
                out = try_parse(code_match.group(1).strip())
                if out and isinstance(out, dict):
                    return out
            # Greedy variant
            code_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw)
            if code_match:
                out = try_parse(code_match.group(1).strip())
                if out and isinstance(out, dict):
                    return out

        # 3) Trailing vergul bo'lsa olib tashlash
        cleaned = re.sub(r",\s*}", "}", raw)
        cleaned = re.sub(r",\s*]", "]", cleaned)
        out = try_parse(cleaned)
        if out and isinstance(out, dict):
            return out

        # 4) { ... } blokini topish
        # Eng katta blokdan boshlab sinash
        brace_start = raw.find('{')
        brace_end = raw.rfind('}')
        if brace_start >= 0 and brace_end > brace_start:
            candidate = raw[brace_start:brace_end+1]
            out = try_parse(candidate)
            if out and isinstance(out, dict):
                return out
            # Trailing vergul bilan
            candidate_clean = re.sub(r",\s*}", "}", candidate)
            candidate_clean = re.sub(r",\s*]", "]", candidate_clean)
            out = try_parse(candidate_clean)
            if out and isinstance(out, dict):
                return out

        print(f"[Writing AI] extract_json: parse qilib bo'lmadi. Matn uzunligi: {len(raw)}, boshi: {raw[:150]}")
        return None

    def normalize_ev(ev):
        """API turli kalit nomlari (Task1, task 1, task_1) ni task1, task2, essay ga aylantiradi."""
        if not ev or not isinstance(ev, dict):
            return ev
        normalized = {}
        for k, v in ev.items():
            if not isinstance(k, str):
                continue
            key_clean = k.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
            if key_clean in ("task1",):
                normalized["task1"] = v
            elif key_clean in ("task2",):
                normalized["task2"] = v
            elif key_clean in ("essay",):
                normalized["essay"] = v
            elif key_clean in ("generalfeedback", "feedback", "overall"):
                normalized["general_feedback"] = v
        return normalized

    def validate_ev(ev):
        """AI javobida task1, task2, essay borligini tekshirish."""
        if not ev or not isinstance(ev, dict):
            print(f"[Writing AI] validate_ev: dict emas - {type(ev)}")
            return False
        missing = []
        for key in ("task1", "task2", "essay"):
            if key not in ev:
                missing.append(key)
            elif not isinstance(ev.get(key), dict):
                missing.append(f"{key}(not dict)")
        if missing:
            print(f"[Writing AI] validate_ev: yetishmayotgan kalitlar: {missing}, mavjud: {list(ev.keys())}")
            return False
        return True

    try:
        # ========== 1) OpenAI ==========
        if OPENAI_API_KEY:
            print(f"[Writing AI] OpenAI ga so'rov yuborilmoqda... (kalit: {OPENAI_API_KEY[:8]}...)")
            for model in ("gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"):
                try:
                    print(f"[Writing AI] Model: {model} sinab ko'rilmoqda...")
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        r = await client.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                            json={
                                "model": model,
                                "messages": [
                                    {"role": "system", "content": "You are a CEFR writing examiner. Reply ONLY with a valid JSON object. Do NOT use markdown code blocks. Do NOT add any text before or after the JSON. The JSON must have keys: task1, task2, essay, general_feedback. Each of task1, task2, essay must have a \"score\" field (integer 0-9) and feedback fields."},
                                    {"role": "user", "content": prompt}
                                ],
                                "temperature": 0.3,
                                "max_tokens": 2000,
                            },
                        )
                        print(f"[Writing AI] OpenAI ({model}) status: {r.status_code}")

                        if r.status_code == 200:
                            data = r.json()
                            choices = data.get("choices") or []
                            if choices:
                                msg = choices[0].get("message") or {}
                                content = (msg.get("content") or "").strip()
                                print(f"[Writing AI] OpenAI ({model}) javob uzunligi: {len(content)}")
                                if content:
                                    print(f"[Writing AI] Javob boshi: {content[:200]}")
                                    ev = extract_json(content)
                                    if ev:
                                        print(f"[Writing AI] JSON parse muvaffaqiyatli. Kalitlar: {list(ev.keys())}")
                                        ev = normalize_ev(ev)
                                        print(f"[Writing AI] Normalize keyin: {list(ev.keys())}")
                                    if ev and validate_ev(ev):
                                        # Score larni tekshirish
                                        for k in ("task1", "task2", "essay"):
                                            s = ev.get(k, {}).get("score", "YO'Q")
                                            print(f"[Writing AI] {k} score = {s}")
                                        print(f"[Writing AI] OpenAI ({model}) MUVAFFAQIYATLI!")
                                        return format_ai_result(ev, task1, task2, essay)
                                    else:
                                        print(f"[Writing AI] OpenAI ({model}) javob yaroqsiz.")
                                        if ev:
                                            # score kaliti bor/yo'qligini tekshirish
                                            for k in ("task1", "task2", "essay"):
                                                d = ev.get(k, "YO'Q")
                                                if isinstance(d, dict):
                                                    print(f"[Writing AI]   {k}: keys={list(d.keys())}, score={d.get('score', 'YOQ')}")
                                                else:
                                                    print(f"[Writing AI]   {k}: {type(d)} = {str(d)[:100]}")
                            else:
                                print(f"[Writing AI] OpenAI ({model}) - choices bo'sh!")
                        elif r.status_code == 401:
                            print(f"[Writing AI] OpenAI 401 - KALIT NOTO'G'RI! Body: {r.text[:300]}")
                            break  # Kalit noto'g'ri - boshqa model sinash kerak emas
                        elif r.status_code == 429:
                            print(f"[Writing AI] OpenAI ({model}) 429 - Rate limit. Keyingi modelga o'tish...")
                        elif r.status_code == 404:
                            print(f"[Writing AI] OpenAI ({model}) 404 - Model topilmadi. Keyingi modelga...")
                        else:
                            print(f"[Writing AI] OpenAI ({model}) xato: status={r.status_code}, body={r.text[:300]}")
                except httpx.TimeoutException:
                    print(f"[Writing AI] OpenAI ({model}) TIMEOUT (120s)")
                except Exception as e:
                    print(f"[Writing AI] OpenAI ({model}) Exception: {type(e).__name__}: {e}")
        else:
            print("[Writing AI] OPENAI_API_KEY o'rnatilmagan!")

        # ========== 2) Anthropic (fallback) ==========
        if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.strip():
            print("[Writing AI] Anthropic ga so'rov yuborilmoqda...")
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": ANTHROPIC_API_KEY.strip(), "anthropic-version": "2023-06-01", "content-type": "application/json"},
                        json={"model": "claude-3-haiku-20240307", "max_tokens": 2000, "messages": [{"role": "user", "content": prompt}]},
                    )
                    print(f"[Writing AI] Anthropic status: {r.status_code}")
                    if r.status_code == 200:
                        data = r.json()
                        content = ""
                        for block in data.get("content", []):
                            if block.get("type") == "text":
                                content += block.get("text", "")
                        if not content and data.get("content"):
                            content = str(data["content"][0].get("text", ""))
                        content = (content or "").strip()
                        if content:
                            print(f"[Writing AI] Anthropic javob uzunligi: {len(content)}")
                            ev = extract_json(content)
                            if ev:
                                ev = normalize_ev(ev)
                            if ev and validate_ev(ev):
                                print("[Writing AI] Anthropic MUVAFFAQIYATLI!")
                                return format_ai_result(ev, task1, task2, essay)
                            else:
                                print(f"[Writing AI] Anthropic javob yaroqsiz: {content[:200]}")
                    else:
                        print(f"[Writing AI] Anthropic xato: status={r.status_code}, body={r.text[:300]}")
            except Exception as e:
                print(f"[Writing AI] Anthropic Exception: {type(e).__name__}: {e}")
        else:
            print("[Writing AI] ANTHROPIC_API_KEY ham o'rnatilmagan!")

    except Exception as e:
        print(f"[Writing AI] Umumiy xato: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print("[Writing AI] Hech bir AI ishlamadi! None qaytarilmoqda.")
    return None


def _score_float(val):
    """Parse score from AI (string, float, or int). Returns float 0-9. O'nli ball bemani yozuvda 0.1, 1, 2, 3% kabi past foizlarni berish uchun."""
    if val is None:
        return 3.0
    if isinstance(val, (int, float)):
        return max(0.0, min(9.0, float(val)))
    if isinstance(val, str):
        # "7/9", "7.5" kabi formatlar
        s = str(val).strip()
        m = re.match(r'(\d+\.?\d*)', s.replace(',', '.'))
        if m:
            return max(0.0, min(9.0, float(m.group(1))))
    try:
        return max(0.0, min(9.0, float(val)))
    except (TypeError, ValueError):
        return 3.0


def format_ai_result(ev, task1, task2, essay):
    """AI javobidan natijalarni formatlash"""
    def part_score(d):
        if not d or not isinstance(d, dict):
            return 3.0
        v = d.get("score") or d.get("Score") or d.get("band") or d.get("Band")
        s = _score_float(v)
        print(f"[Writing AI] part_score: raw={v}, parsed={s}")
        return s

    def get_feedback(d, key, default="Evaluated."):
        """Feedback matnini olish - turli kalit nomlarini sinash"""
        if not d or not isinstance(d, dict):
            return default
        return str(d.get(key, "") or d.get(key.replace("_", " "), "") or default)

    # Bemani / bo'sh / gibberish bo'lsa 0 ball (11.1% oldini olish)
    def force_zero_if_worthless(fb_text: str, current_score: float) -> float:
        if not fb_text:
            return current_score
        low = fb_text.lower()
        if any(w in low for w in ("gibberish", "nonsense", "empty", "no content", "no relevant", "completely irrelevant", "non-english", "not english", "no meaningful", "does not address", "off-topic", "off topic", "irrelevant")):
            return 0.0
        return current_score

    r = {}
    for name, txt in [("task1", task1), ("task2", task2)]:
        d = ev.get(name, {})
        s = part_score(d)
        fb_content = get_feedback(d, "content")
        s = force_zero_if_worthless(fb_content, s)
        if fb_content and any(w in fb_content.lower() for w in ("off-topic", "does not address", "irrelevant", "off topic")) and s > 0:
            s = 0.0
        s = max(0.0, min(9.0, s))
        r[name] = {
            "score": s, "band": round(s), "word_count": len(txt.split()), "is_valid": s >= 3,
            "feedback": {
                "overall": f"Band {s}",
                "content": fb_content,
                "organization": get_feedback(d, "organization"),
                "language": get_feedback(d, "language"),
                "accuracy": get_feedback(d, "accuracy")
            }
        }

    # Essay
    d_essay = ev.get("essay", {})
    s = part_score(d_essay)
    fb_ta = get_feedback(d_essay, "task_achievement")
    s = force_zero_if_worthless(fb_ta or "", s)
    if fb_ta and any(w in fb_ta.lower() for w in ("off-topic", "does not address", "irrelevant", "off topic")) and s > 0:
        s = 0.0
    s = max(0.0, min(9.0, s))

    r["essay"] = {
        "score": s, "band": round(s), "word_count": len(essay.split()), "is_valid": s >= 3,
        "feedback": {
            "overall": f"Band {s}",
            "task_achievement": fb_ta,
            "coherence_cohesion": get_feedback(d_essay, "coherence_cohesion"),
            "lexical_resource": get_feedback(d_essay, "lexical_resource"),
            "grammatical_range": get_feedback(d_essay, "grammatical_range")
        }
    }
    print(f"[Writing AI] format_ai_result: task1={r['task1']['score']}, task2={r['task2']['score']}, essay={r['essay']['score']}")
    return r


def calc_final(reading_pct, listening_pct, writing_pct):
    overall = reading_pct * 0.30 + listening_pct * 0.30 + writing_pct * 0.40
    cefr = "A1"
    desc = "Beginner"
    for lv, d in CEFR_LEVELS.items():
        if overall >= d["min_score"]:
            cefr = lv
            desc = d["description"]
            break
    return {"overall_percentage": round(overall, 1), "cefr_level": cefr, "level_description": desc}


# ============ ROUTES ============

@app.on_event("startup")
async def startup():
    init_default_data()

@app.get("/lang/{lang}")
async def set_language(lang: str):
    """Switch language"""
    if lang not in ["uz", "en"]:
        lang = "uz"
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie(key="lang", value=lang, max_age=86400*365)
    return resp

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("index.html", {"request": request, "t": t, "lang": lang, "user": None})

@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("pricing.html", {"request": request, "t": t, "lang": lang, "user": get_current_user(request)})

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("about.html", {"request": request, "t": t, "lang": lang, "user": get_current_user(request)})

@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request):
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("faq.html", {"request": request, "t": t, "lang": lang, "user": get_current_user(request)})

@app.get("/api/landing-stats", response_class=JSONResponse)
async def api_landing_stats(request: Request):
    """Landing 'Bizni natijalar' uchun: users, tests_taken, likes, dislikes."""
    return JSONResponse(get_landing_stats())

@app.post("/api/rate", response_class=JSONResponse)
async def api_rate(request: Request):
    """Like yoki Dislike — 1 user 1 ovoz. Dislike bo'lsa reason so'raladi."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"success": False, "error": "login_required"}, status_code=401)
    try:
        body = await request.json()
        vote = (body.get("vote") or "").strip().lower()
        if vote not in ("like", "dislike"):
            return JSONResponse({"success": False, "error": "invalid_vote"}, status_code=400)
        reason = (body.get("reason") or "").strip() or "—"
        set_rating(user["id"], vote, reason)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

# ============ AUTH ROUTES ============

LOGIN_ERROR_MESSAGES = {
    "token_failed": "Google token olinmadi. .env faylida GOOGLE_CLIENT_SECRET o'rnating (Google Cloud Console → Credentials → OAuth 2.0 Client ID → Client secret).",
    "missing_client_secret": "Google bilan kirish uchun .env da GOOGLE_CLIENT_SECRET o'rnating.",
    "no_code": "Google javob bermadi. Qaytadan urinib ko'ring.",
    "no_token": "Token olinmadi.",
    "userinfo_failed": "Foydalanuvchi ma'lumotlari olinmadi.",
    "no_google_id": "Google ID topilmadi.",
}

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = "", next_url: str = ""):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url=next_url or "/dashboard", status_code=302)
    t = get_translations(request)
    lang = get_lang(request)
    error_message = LOGIN_ERROR_MESSAGES.get(error, error) if error else ""
    return templates.TemplateResponse("login.html", {
        "request": request, "t": t, "lang": lang, "user": get_current_user(request),
        "error": error_message, "next_url": next_url or "/dashboard", "google_client_id": GOOGLE_CLIENT_ID
    })

@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(""), password: str = Form(""), next_url: str = Form("/dashboard")):
    email = (email or "").strip().lower()
    if not email or not password:
        return templates.TemplateResponse("login.html", {
            "request": request, "t": get_translations(request), "lang": get_lang(request), "user": get_current_user(request),
            "error": "Email va parol kiriting.", "next_url": next_url, "google_client_id": GOOGLE_CLIENT_ID
        })
    user = get_user_by_email(email)
    if not user or not user.get("password_hash") or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse("login.html", {
            "request": request, "t": get_translations(request), "lang": get_lang(request), "user": get_current_user(request),
            "error": "Email yoki parol noto'g'ri.", "next_url": next_url, "google_client_id": GOOGLE_CLIENT_ID
        })
    from itsdangerous import URLSafeTimedSerializer
    secret = os.getenv("SECRET_KEY", "cefr-level-secret-change-in-production")
    s = URLSafeTimedSerializer(secret)
    token = s.dumps(user["id"])
    resp = RedirectResponse(url=next_url or "/dashboard", status_code=302)
    resp.set_cookie(key=AUTH_COOKIE, value=token, max_age=AUTH_MAX_AGE, httponly=True, samesite="lax")
    return resp

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = ""):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("register.html", {
        "request": request, "t": t, "lang": lang, "user": get_current_user(request),
        "error": error, "google_client_id": GOOGLE_CLIENT_ID
    })

@app.post("/register", response_class=HTMLResponse)
async def register_submit(request: Request, email: str = Form(""), password: str = Form(""), name: str = Form("")):
    email = (email or "").strip().lower()
    if not email or not password:
        return templates.TemplateResponse("register.html", {
            "request": request, "t": get_translations(request), "lang": get_lang(request), "user": get_current_user(request),
            "error": "Email va parol kiriting.", "google_client_id": GOOGLE_CLIENT_ID
        })
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {
            "request": request, "t": get_translations(request), "lang": get_lang(request), "user": get_current_user(request),
            "error": "Parol kamida 6 belgidan iborat bo'lishi kerak.", "google_client_id": GOOGLE_CLIENT_ID
        })
    if get_user_by_email(email):
        return templates.TemplateResponse("register.html", {
            "request": request, "t": get_translations(request), "lang": get_lang(request), "user": get_current_user(request),
            "error": "Bu email allaqachon ro'yxatdan o'tgan.", "google_client_id": GOOGLE_CLIENT_ID
        })
    user = create_user(email, password, name)
    from itsdangerous import URLSafeTimedSerializer
    secret = os.getenv("SECRET_KEY", "cefr-level-secret-change-in-production")
    ser = URLSafeTimedSerializer(secret)
    token = ser.dumps(user["id"])
    resp = RedirectResponse(url="/dashboard", status_code=302)
    resp.set_cookie(key=AUTH_COOKIE, value=token, max_age=AUTH_MAX_AGE, httponly=True, samesite="lax")
    return resp

@app.get("/logout")
async def logout_route():
    resp = RedirectResponse(url="/", status_code=302)
    resp.delete_cookie(AUTH_COOKIE)
    return resp

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/profile", status_code=302)
    t = get_translations(request)
    lang = get_lang(request)
    test_history = get_test_history(user["id"])
    return templates.TemplateResponse("profile.html", {
        "request": request, "t": t, "lang": lang, "user": user,
        "test_history": test_history, "contact": CONTACT_INFO
    })

@app.get("/profile/result/{session_id}", response_class=HTMLResponse)
async def profile_result_detail(request: Request, session_id: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/profile", status_code=302)
    record = get_test_result_by_session(session_id, user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="Natija topilmadi")
    t = get_translations(request)
    lang = get_lang(request)
    # result_detail uchun session o'rniga record dan session-ga o'xshash obyekt yasaymiz
    session_like = {
        "cefr_level": record.get("cefr_level"),
        "level_description": CEFR_LEVELS.get(record.get("cefr_level", ""), {}).get("description", ""),
        "overall_score": record.get("overall_score", 0),
        "reading": {
            "percentage": record.get("reading_percentage", 0),
            "score": record.get("reading_score", 0),
            "total": record.get("reading_total", 0),
            "details": record.get("reading_details") or [],
        },
        "listening": {
            "percentage": record.get("listening_percentage", 0),
            "score": record.get("listening_score", 0),
            "total": record.get("listening_total", 0),
            "details": record.get("listening_details") or [],
        },
        "writing": {
            "percentage": record.get("writing_percentage", 0),
            "evaluation": record.get("writing_evaluation") or {},
        },
        "completed_at": record.get("completed_at"),
    }
    return templates.TemplateResponse("result_detail.html", {
        "request": request, "session": session_like, "cefr_levels": CEFR_LEVELS,
        "t": t, "lang": lang, "record": record
    })


@app.post("/profile/feedback")
async def profile_feedback_submit(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"success": False, "error": "login_required"}, status_code=401)
    fd = await request.form()
    fb = {
        "user_id": user["id"],
        "user_email": user.get("email", ""),
        "user_name": user.get("name", ""),
        "session_id": request.cookies.get("session_id") or "profile",
        "submitted_at": datetime.now().isoformat(),
        "rating": fd.get("rating", ""),
        "difficulty": fd.get("difficulty", ""),
        "accuracy": fd.get("accuracy", ""),
        "recommend": fd.get("recommend", ""),
        "best_part": fd.get("best_part", ""),
        "worst_part": fd.get("worst_part", ""),
        "suggestions": fd.get("suggestions", ""),
        "message": fd.get("message", ""),
    }
    save_feedback(fb)
    return JSONResponse({"success": True})

def _build_redirect_uri(request: Request) -> str:
    """Redirect URI ni so'rov hostiga qarab yasaymiz (localhost yoki 127.0.0.1)."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/auth/google/callback"

@app.get("/auth/google")
async def auth_google(request: Request, next_url: str = ""):
    from urllib.parse import quote
    redirect_uri = _build_redirect_uri(request)
    state = next_url or "/start"
    import base64
    state_b64 = base64.urlsafe_b64encode(state.encode()).decode()
    redirect_encoded = quote(redirect_uri, safe="")
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_encoded}"
        "&response_type=code"
        "&scope=openid email profile"
        f"&state={state_b64}"
        "&access_type=offline"
        "&prompt=consent"
    )
    return RedirectResponse(url=url, status_code=302)

@app.get("/auth/google/callback")
async def auth_google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(url=f"/login?error={error}", status_code=302)
    if not code:
        return RedirectResponse(url="/login?error=no_code", status_code=302)
    if not (GOOGLE_CLIENT_SECRET or "").strip():
        return RedirectResponse(url="/login?error=missing_client_secret", status_code=302)
    redirect_uri = _build_redirect_uri(request)  # auth so'rovida yuborilgan bilan bir xil bo'lishi kerak
    import base64
    next_url = "/start"
    if state:
        try:
            pad = 4 - len(state) % 4
            if pad != 4:
                state = state + ("=" * pad)
            next_url = base64.urlsafe_b64decode(state.encode()).decode()
        except Exception:
            pass
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET.strip(),
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if token_resp.status_code != 200:
        try:
            err_body = token_resp.text
            print(f"[Google OAuth] token exchange failed: status={token_resp.status_code}, body={err_body}")
        except Exception:
            print(f"[Google OAuth] token exchange failed: status={token_resp.status_code}")
        return RedirectResponse(url="/login?error=token_failed", status_code=302)
    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(url="/login?error=no_token", status_code=302)
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if user_resp.status_code != 200:
        return RedirectResponse(url="/login?error=userinfo_failed", status_code=302)
    info = user_resp.json()
    google_id = info.get("id")
    email = (info.get("email") or "").strip().lower()
    name = (info.get("name") or "").strip()
    picture = info.get("picture")
    if not google_id:
        return RedirectResponse(url="/login?error=no_google_id", status_code=302)
    user = create_or_update_user_google(google_id, email, name, picture)
    from itsdangerous import URLSafeTimedSerializer
    secret = os.getenv("SECRET_KEY", "cefr-level-secret-change-in-production")
    ser = URLSafeTimedSerializer(secret)
    token = ser.dumps(user["id"])
    # Yangi foydalanuvchi: onboarding (ism) → keyin platforma
    if user.get("onboarding_done") is False:
        resp = RedirectResponse(url="/onboarding", status_code=302)
    else:
        resp = RedirectResponse(url=next_url or "/dashboard", status_code=302)
    resp.set_cookie(key=AUTH_COOKIE, value=token, max_age=AUTH_MAX_AGE, httponly=True, samesite="lax")
    return resp

# ============ ONBOARDING (faqat ism – yangi Google user) ============

@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/dashboard", status_code=302)
    if user.get("onboarding_done") is True:
        return RedirectResponse(url="/dashboard", status_code=302)
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("onboarding.html", {"request": request, "t": t, "lang": lang, "user": user})

@app.post("/onboarding", response_class=HTMLResponse)
async def onboarding_submit(request: Request, name: str = Form("")):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/dashboard", status_code=302)
    name = (name or "").strip()
    if name:
        update_user(user["id"], name=name, onboarding_done=True)
    else:
        update_user(user["id"], onboarding_done=True)
    return RedirectResponse(url="/dashboard", status_code=302)

# ============ PROTECTED: TEST (require login) ============

@app.get("/start", response_class=HTMLResponse)
async def start_test(request: Request):
    # Redirect /start to /dashboard - /start is deprecated
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/dashboard", status_code=302)
    t = get_translations(request)
    lang = get_lang(request)
    test_history = get_test_history(user["id"])
    user_rating = get_user_rating(user["id"])
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "t": t, "lang": lang, "user": user,
        "test_history": test_history, "user_rating": user_rating
    })

@app.get("/practice", response_class=HTMLResponse)
async def practice_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/practice", status_code=302)
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("practice.html", {
        "request": request, "t": t, "lang": lang, "user": user
    })

@app.get("/info", response_class=HTMLResponse)
async def info_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/info", status_code=302)
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("info.html", {
        "request": request, "t": t, "lang": lang, "user": user
    })

@app.get("/test/reading", response_class=HTMLResponse)
async def reading_test(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/test/reading", status_code=302)

    sid = request.cookies.get("session_id")
    # Create new session if none exists
    if not sid:
        # Check if user has test credits
        total_tests = (user.get("free_tests") or 0) + (user.get("purchased_tests") or 0)
        if total_tests <= 0:
            return RedirectResponse(url="/dashboard?error=no_tests", status_code=302)

        # Deduct one test credit
        if user.get("free_tests", 0) > 0:
            update_user(user["id"], free_tests=user["free_tests"] - 1)
        elif user.get("purchased_tests", 0) > 0:
            update_user(user["id"], purchased_tests=user["purchased_tests"] - 1)

        # Create new session
        sid = str(uuid.uuid4())
        s = get_session(sid)
        s["user_id"] = user["id"]

    test = _build_test_from_all_tests("reading", user)
    s = get_session(sid)
    s["reading_test_id"] = test.get("id", "reading_combined")
    t = get_translations(request)
    lang = get_lang(request)
    resp = templates.TemplateResponse("test_reading.html", {"request": request, "test_data": test, "session_id": sid, "t": t, "lang": lang, "user": user})
    resp.set_cookie(key="session_id", value=sid, max_age=7200)
    return resp

@app.post("/test/reading/submit")
async def submit_reading(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return JSONResponse({"error": "No session"}, status_code=400)
    s = get_session(sid)
    user_id = s.get("user_id")
    user = get_user_by_id(user_id) if user_id else None
    fd = await request.form()
    answers = {k: v for k, v in fd.items() if k != "session_id"}
    # Rebuild test from all tests (same as when showing)
    test = _build_test_from_all_tests("reading", user or {})
    result = calculate_reading_score(answers, test)
    s["reading"] = {"completed": True, "score": result["correct"], "total": result["total"], "percentage": result["percentage"], "details": result["details"]}
    if user_id:
        # Mark parts as seen - use _source_test_id if available
        for part in test["parts"]:
            pnum = part.get("part_number", 0)
            source_test_id = part.get("_source_test_id")
            if source_test_id:
                _mark_parts_seen(user_id, "reading", source_test_id, [part])
            else:
                # Fallback: find original test
                tests = get_reading_tests()
                for t in tests:
                    if t.get("parts"):
                        for orig_part in t["parts"]:
                            if orig_part.get("part_number") == pnum and orig_part.get("type") == part.get("type"):
                                _mark_parts_seen(user_id, "reading", t.get("id", "reading_1"), [orig_part])
                                break
    return JSONResponse({"success": True, "score": result["correct"], "total": result["total"], "percentage": result["percentage"], "redirect": "/test/listening"})

@app.get("/test/listening", response_class=HTMLResponse)
async def listening_test(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return RedirectResponse(url="/dashboard", status_code=302)
    s = get_session(sid)
    user_id = s.get("user_id")
    user = get_user_by_id(user_id) if user_id else None
    test = _build_test_from_all_tests("listening", user or {})
    s["listening_test_id"] = test.get("id", "listening_combined")
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("test_listening.html", {"request": request, "test_data": test, "session_id": sid, "t": t, "lang": lang})

# ============ TTS AUDIO GENERATION FOR LISTENING ============
import hashlib
import base64

# Cache for generated audio (in-memory, for demo; use Redis/disk in production)
audio_cache: Dict[str, bytes] = {}

@app.post("/api/tts")
async def generate_tts(request: Request):
    """Generate audio from transcript text using OpenAI TTS API"""
    if not OPENAI_API_KEY:
        return JSONResponse({"error": "TTS not available - OPENAI_API_KEY not set"}, status_code=503)
    
    try:
        body = await request.json()
        text = body.get("text", "").strip()
        voice = body.get("voice", "alloy")  # alloy, echo, fable, onyx, nova, shimmer
        
        if not text:
            return JSONResponse({"error": "Text is required"}, status_code=400)
        
        if len(text) > 4000:
            return JSONResponse({"error": "Text too long (max 4000 chars)"}, status_code=400)
        
        # Check cache
        cache_key = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
        if cache_key in audio_cache:
            audio_b64 = base64.b64encode(audio_cache[cache_key]).decode()
            return JSONResponse({"audio": audio_b64, "cached": True})
        
        # Call OpenAI TTS API
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": voice,
                    "response_format": "mp3"
                }
            )
            
            if r.status_code == 200:
                audio_data = r.content
                # Cache the audio
                audio_cache[cache_key] = audio_data
                audio_b64 = base64.b64encode(audio_data).decode()
                return JSONResponse({"audio": audio_b64, "cached": False})
            else:
                print(f"[TTS] OpenAI error: {r.status_code} - {r.text[:200]}")
                return JSONResponse({"error": f"TTS API error: {r.status_code}"}, status_code=500)
                
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/test/listening/submit")
async def submit_listening(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return JSONResponse({"error": "No session"}, status_code=400)
    s = get_session(sid)
    user_id = s.get("user_id")
    user = get_user_by_id(user_id) if user_id else None
    fd = await request.form()
    answers = {k: v for k, v in fd.items() if k != "session_id"}
    # Rebuild test from all tests (same as when showing)
    test = _build_test_from_all_tests("listening", user or {})
    result = calculate_listening_score(answers, test)
    s["listening"] = {"completed": True, "score": result["correct"], "total": result["total"], "percentage": result["percentage"], "details": result["details"]}
    if user_id:
        # Mark parts as seen - use _source_test_id if available
        for part in test["parts"]:
            pnum = part.get("part_number", 0)
            source_test_id = part.get("_source_test_id")
            if source_test_id:
                _mark_parts_seen(user_id, "listening", source_test_id, [part])
            else:
                # Fallback: find original test
                tests = get_listening_tests()
                for t in tests:
                    if t.get("parts"):
                        for orig_part in t["parts"]:
                            if orig_part.get("part_number") == pnum and orig_part.get("type") == part.get("type"):
                                _mark_parts_seen(user_id, "listening", t.get("id", "listening_1"), [orig_part])
                                break
    return JSONResponse({"success": True, "score": result["correct"], "total": result["total"], "percentage": result["percentage"], "redirect": "/test/writing"})

def _writing_test_for_display(test: dict) -> dict:
    """Writing testdan partlarni Part 1 (tasks) va Part 2 (essay) tartibida qaytaradi — admin paneldan kelgan ma'lumot to'g'ri ko'rinsin."""
    test = dict(test)
    parts = list(test.get("parts") or [])
    p1 = next((p for p in parts if p.get("type") == "tasks" or p.get("part_number") == 1), None)
    p2 = next((p for p in parts if p.get("type") == "essay" or p.get("part_number") == 2), None)
    if p1 is not None or p2 is not None:
        test["parts"] = [p1 or _default_writing_part(1), p2 or _default_writing_part(2)]
    elif parts:
        parts.sort(key=lambda p: p.get("part_number", 99))
        test["parts"] = parts
    else:
        test["parts"] = [DEFAULT_WRITING["parts"][0], DEFAULT_WRITING["parts"][1]]
    return test


def _default_writing_part(part_number: int) -> dict:
    """DEFAULT_WRITING dan bitta part nusxasi."""
    for p in DEFAULT_WRITING.get("parts", []):
        if p.get("part_number") == part_number:
            return dict(p)
    return {}


@app.get("/test/writing", response_class=HTMLResponse)
async def writing_test(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return RedirectResponse(url="/dashboard", status_code=302)
    tests = get_writing_tests()
    test = tests[0] if tests else DEFAULT_WRITING
    test = _writing_test_for_display(test)
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("test_writing.html", {"request": request, "test_data": test, "session_id": sid, "t": t, "lang": lang})

@app.post("/test/writing/submit")
async def submit_writing(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return JSONResponse({"error": "No session"}, status_code=400)
    fd = await request.form()
    t1 = fd.get("task1", "")
    t2 = fd.get("task2", "")
    essay = fd.get("essay", "")
    tests = get_writing_tests()
    test = tests[0] if tests else DEFAULT_WRITING
    test = _writing_test_for_display(test)
    ev = await evaluate_writing_with_ai(t1, t2, essay, test)
    s = get_session(sid)
    s["writing"] = {"completed": True, "responses": {"task1": t1, "task2": t2, "essay": essay}, "evaluation": ev, "percentage": ev["overall_percentage"]}
    r_pct = s.get("reading", {}).get("percentage", 0)
    l_pct = s.get("listening", {}).get("percentage", 0)
    final = calc_final(r_pct, l_pct, ev["overall_percentage"])
    s["overall_score"] = final["overall_percentage"]
    s["cefr_level"] = final["cefr_level"]
    s["level_description"] = final["level_description"]
    return JSONResponse({"success": True, "evaluation": ev, "redirect": "/results"})

@app.get("/results", response_class=HTMLResponse)
async def results(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return RedirectResponse(url="/dashboard", status_code=302)
    s = get_session(sid)
    if not all([s.get("reading", {}).get("completed"), s.get("listening", {}).get("completed"), s.get("writing", {}).get("completed")]):
        return RedirectResponse(url="/dashboard", status_code=302)
    save_test_result(s)  # profil tarixiga saqlash
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("results.html", {"request": request, "session": s, "cefr_levels": CEFR_LEVELS, "t": t, "lang": lang, "user": get_current_user(request), "hide_nav": True})

@app.post("/feedback/submit")
async def submit_feedback(request: Request):
    sid = request.cookies.get("session_id")
    fd = await request.form()
    fb = {
        "session_id": sid or "unknown",
        "submitted_at": datetime.now().isoformat(),
        "rating": fd.get("rating", ""),
        "difficulty": fd.get("difficulty", ""),
        "accuracy": fd.get("accuracy", ""),
        "recommend": fd.get("recommend", ""),
        "best_part": fd.get("best_part", ""),
        "worst_part": fd.get("worst_part", ""),
        "suggestions": fd.get("suggestions", ""),
        "name": fd.get("name", ""),
        "email": fd.get("email", "")
    }
    save_feedback(fb)
    return JSONResponse({"success": True})


# ============ ADMIN ROUTES ============

def check_admin(request: Request) -> bool:
    return request.cookies.get("admin_auth") == "osco_admin_ok"

@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    if check_admin(request):
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login")
async def admin_login(request: Request):
    fd = await request.form()
    if fd.get("password") == ADMIN_PASSWORD:
        resp = RedirectResponse(url="/admin/dashboard", status_code=302)
        resp.set_cookie(key="admin_auth", value="osco_admin_ok", max_age=86400)
        return resp
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Noto'g'ri parol"})

@app.get("/admin/logout")
async def admin_logout():
    resp = RedirectResponse(url="/admin", status_code=302)
    resp.delete_cookie("admin_auth")
    return resp

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not check_admin(request): return RedirectResponse(url="/admin", status_code=302)
    reading = get_reading_tests()
    listening = get_listening_tests()
    writing = get_writing_tests()
    fbs = get_feedbacks()
    users_data = load_users()
    users_list = list(users_data.get("users", []))
    stats = get_landing_stats()
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "reading_count": len(reading),
        "listening_count": len(listening),
        "writing_count": len(writing),
        "feedback_count": len(fbs),
        "user_count": stats["users"],
        "tests_taken": stats["tests_taken"],
        "likes_count": stats["likes"],
        "dislikes_count": stats["dislikes"],
        "feedbacks": fbs[-20:],
        "reading_tests": reading,
        "listening_tests": listening,
        "writing_tests": writing,
        "users": users_list
    })

@app.get("/admin/data/{section}", response_class=JSONResponse)
async def admin_get_data(request: Request, section: str):
    if not check_admin(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if section == "reading": return JSONResponse({"tests": get_reading_tests()})
    if section == "listening": return JSONResponse({"tests": get_listening_tests()})
    if section == "writing": return JSONResponse({"tests": get_writing_tests()})
    if section == "feedbacks": return JSONResponse({"feedbacks": get_feedbacks()})
    return JSONResponse({"error": "Unknown section"}, status_code=400)

@app.post("/admin/data/{section}")
async def admin_save_data(request: Request, section: str):
    if not check_admin(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    body = await request.json()
    if section == "reading":
        save_json("reading_tests.json", {"tests": body.get("tests", [])})
    elif section == "listening":
        save_json("listening_tests.json", {"tests": body.get("tests", [])})
    elif section == "writing":
        save_json("writing_tests.json", {"tests": body.get("tests", [])})
    else:
        return JSONResponse({"error": "Unknown section"}, status_code=400)
    return JSONResponse({"success": True})


# Admin: Listening Part 4 xarita rasm yuklash
UPLOAD_MAPS_DIR = Path(__file__).resolve().parent / "static" / "uploads" / "listening_maps"
ALLOWED_MAP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


@app.post("/admin/upload-listening-map", response_class=JSONResponse)
async def admin_upload_listening_map(request: Request, file: UploadFile = File(...)):
    if not check_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if not file.filename:
        return JSONResponse({"error": "Fayl tanlanmagan"}, status_code=400)
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_MAP_EXTENSIONS:
        return JSONResponse({"error": "Faqat rasm fayllari (png, jpg, gif, webp)"}, status_code=400)
    UPLOAD_MAPS_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_MAPS_DIR / name
    try:
        content = await file.read()
        path.write_bytes(content)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    url = f"/static/uploads/listening_maps/{name}"
    return JSONResponse({"url": url})

@app.post("/admin/user/{user_id}")
async def admin_update_user(request: Request, user_id: str):
    if not check_admin(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    body = await request.json()
    free_tests = body.get("free_tests", 0)
    purchased_tests = body.get("purchased_tests", 0)
    updated = update_user(user_id, free_tests=free_tests, purchased_tests=purchased_tests)
    if updated:
        return JSONResponse({"success": True})
    return JSONResponse({"error": "User not found"}, status_code=404)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "OSCO CEFR"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    # Render va boshqa cloud'da PORT beriladi, reload o'chiq
    use_reload = not os.getenv("PORT")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=use_reload)
