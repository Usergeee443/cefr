from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, List
import uvicorn
import uuid
import json
import os
import re
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

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


# ============ DEFAULT TEST DATA ============

DEFAULT_READING = {
    "id": "reading_1",
    "title": "Reading Test 1",
    "time_limit": 60,
    "parts": [
        {
            "part_number": 1,
            "title": "Part 1: Multiple Choice Cloze",
            "instruction": "For questions 1-8, read the text below and decide which answer (A, B, C or D) best fits each gap.",
            "type": "multiple_choice_cloze",
            "text": "The Rise of Remote Work\n\nThe COVID-19 pandemic has (1)_____ transformed the way we work. Before 2020, working from home was (2)_____ a privilege enjoyed by a small percentage of the workforce. However, the global health crisis (3)_____ companies worldwide to rapidly adopt remote work policies.\n\nThis shift has had both positive and negative (4)_____. On the one hand, employees have gained more flexibility and eliminated lengthy commutes. Many workers report feeling more (5)_____ and having a better work-life balance. On the other hand, some people struggle with isolation and find it difficult to (6)_____ work from their personal life.\n\nCompanies are now (7)_____ hybrid models that combine remote and office work. This approach aims to offer the best of both worlds, allowing employees to enjoy flexibility while still maintaining face-to-face (8)_____ with colleagues.",
            "questions": [
                {"number": 1, "options": {"A": "deeply", "B": "hardly", "C": "rarely", "D": "slightly"}, "correct": "A"},
                {"number": 2, "options": {"A": "often", "B": "commonly", "C": "mainly", "D": "usually"}, "correct": "C"},
                {"number": 3, "options": {"A": "made", "B": "forced", "C": "let", "D": "allowed"}, "correct": "B"},
                {"number": 4, "options": {"A": "consequences", "B": "results", "C": "outcomes", "D": "effects"}, "correct": "A"},
                {"number": 5, "options": {"A": "effective", "B": "productive", "C": "efficient", "D": "successful"}, "correct": "B"},
                {"number": 6, "options": {"A": "divide", "B": "split", "C": "separate", "D": "part"}, "correct": "C"},
                {"number": 7, "options": {"A": "accepting", "B": "receiving", "C": "embracing", "D": "welcoming"}, "correct": "C"},
                {"number": 8, "options": {"A": "interaction", "B": "communication", "C": "connection", "D": "contact"}, "correct": "A"}
            ]
        },
        {
            "part_number": 2,
            "title": "Part 2: Open Cloze",
            "instruction": "For questions 9-16, read the text below and think of the word which best fits each gap. Use only ONE word in each gap.",
            "type": "open_cloze",
            "text": "Climate Change and Its Impact\n\nClimate change is one of (9)_____ most pressing issues facing our planet today. Scientists agree that human activities, particularly the burning of fossil fuels, (10)_____ responsible for the rising global temperatures we are experiencing.\n\nThe effects of climate change are already (11)_____ felt around the world. Extreme weather events such (12)_____ hurricanes, floods, and droughts are becoming more frequent and severe. Sea levels are rising, threatening coastal communities and island nations.\n\n(13)_____ order to address this crisis, governments and individuals must take action. Reducing carbon emissions, investing in renewable energy, and protecting forests are all essential steps. However, time is running (14)_____. If we do not act quickly, the consequences (15)_____ be catastrophic.\n\nEach of us has a role to play. Simple changes in (16)_____ daily lives, such as using public transportation, reducing waste, and conserving energy, can make a difference.",
            "questions": [
                {"number": 9, "correct": "the"},
                {"number": 10, "correct": "are"},
                {"number": 11, "correct": "being"},
                {"number": 12, "correct": "as"},
                {"number": 13, "correct": "In"},
                {"number": 14, "correct": "out"},
                {"number": 15, "correct": "will"},
                {"number": 16, "correct": "our"}
            ]
        },
        {
            "part_number": 3,
            "title": "Part 3: Reading Comprehension",
            "instruction": "Read the article and choose the best answer (A, B, C or D) for questions 17-22.",
            "type": "multiple_choice_comprehension",
            "text": "Artificial Intelligence: Friend or Foe?\n\nArtificial Intelligence (AI) has rapidly evolved from a concept in science fiction to a technology that permeates nearly every aspect of our daily lives. From the virtual assistants on our smartphones to the algorithms that recommend what we should watch next, AI has become an invisible but powerful force shaping our decisions and experiences.\n\nProponents of AI point to its tremendous potential for improving human life. In healthcare, AI systems can analyze medical images with greater accuracy than human doctors, potentially catching diseases at earlier, more treatable stages. In environmental science, AI helps researchers model climate patterns and develop strategies for conservation. The technology has also revolutionized industries from manufacturing to finance, increasing efficiency and reducing costs.\n\nHowever, critics raise valid concerns about the darker implications of AI advancement. One of the most pressing issues is the potential for widespread job displacement. As AI systems become capable of performing tasks previously done by humans, millions of workers may find themselves unemployed. This technological unemployment could exacerbate social inequality if the benefits of AI are not distributed fairly.\n\nAnother concern is the question of bias in AI systems. Because these systems learn from data created by humans, they can inherit and even amplify existing prejudices. There have been documented cases of AI systems discriminating against certain groups in areas such as hiring, lending, and criminal justice.\n\nPrivacy is yet another area of concern. AI systems often rely on vast amounts of personal data to function effectively. This raises questions about who has access to our information and how it might be used. The potential for surveillance and manipulation is significant, particularly when AI is combined with facial recognition technology.\n\nDespite these challenges, many experts believe that the benefits of AI outweigh the risks, provided that appropriate safeguards are put in place. This includes developing ethical guidelines for AI development, creating regulations to prevent misuse, and investing in education to prepare workers for a changing job market.",
            "questions": [
                {"number": 17, "question": "According to the first paragraph, AI has become", "options": {"A": "a visible force that shapes our decisions.", "B": "a technology that influences us without us noticing.", "C": "something that only exists in science fiction.", "D": "a technology limited to smartphone assistants."}, "correct": "B"},
                {"number": 18, "question": "What does the article say about AI in healthcare?", "options": {"A": "It has completely replaced human doctors.", "B": "It is less accurate than human analysis.", "C": "It may help detect diseases earlier.", "D": "It is only used for environmental research."}, "correct": "C"},
                {"number": 19, "question": "The article suggests that technological unemployment", "options": {"A": "is not a serious concern.", "B": "will only affect a few workers.", "C": "could increase social inequality.", "D": "has already been solved."}, "correct": "C"},
                {"number": 20, "question": "Why might AI systems show bias?", "options": {"A": "Because they are programmed to discriminate.", "B": "Because they learn from human-created data.", "C": "Because they only work in certain industries.", "D": "Because humans cannot control them."}, "correct": "B"},
                {"number": 21, "question": "What does the article say about privacy and AI?", "options": {"A": "AI does not require any personal data.", "B": "Privacy concerns are exaggerated.", "C": "AI combined with facial recognition raises surveillance concerns.", "D": "Social media is safe from AI analysis."}, "correct": "C"},
                {"number": 22, "question": "According to the experts mentioned in the article,", "options": {"A": "AI should be banned completely.", "B": "the risks of AI are greater than the benefits.", "C": "AI can be beneficial if proper safeguards are implemented.", "D": "humans have already lost control of AI."}, "correct": "C"}
            ]
        },
        {
            "part_number": 4,
            "title": "Part 4: Gapped Text",
            "instruction": "Six sentences have been removed from the article. Choose from the sentences A-G the one which fits each gap (23-28). There is one extra sentence.",
            "type": "gapped_text",
            "text": "Living Sustainably in the Modern World\n\nSustainable living is no longer just a trend but a necessity in our rapidly changing world. With climate change accelerating and natural resources depleting, individuals are looking for ways to reduce their environmental impact. (23)_____\n\nOne of the most effective ways to live more sustainably is to reduce consumption. (24)_____ By being mindful of what we purchase and choosing quality over quantity, we can significantly decrease our environmental footprint.\n\nFood choices also play a crucial role in sustainable living. The production of meat, particularly beef, generates significant greenhouse gas emissions. (25)_____ Even small changes, like participating in \"Meatless Mondays,\" can make a difference.\n\nTransportation is another area where individuals can make impactful changes. (26)_____ For those who need to drive, choosing fuel-efficient or electric vehicles is a step in the right direction.\n\nEnergy consumption at home offers numerous opportunities for sustainability. (27)_____ Additionally, unplugging devices when not in use and using natural light whenever possible can reduce energy bills and environmental impact.\n\nWater conservation is equally important. Simple practices such as fixing leaky faucets, taking shorter showers, and collecting rainwater for gardens can save thousands of liters annually. (28)_____ With these small but consistent efforts, each of us can contribute to a more sustainable future.",
            "removed_sentences": {
                "A": "Walking, cycling, or using public transportation can dramatically reduce carbon emissions from daily commutes.",
                "B": "This is especially important in regions experiencing water scarcity due to climate change.",
                "C": "Fortunately, there are many practical steps that anyone can take to live more sustainably.",
                "D": "Installing solar panels, using LED bulbs, and choosing energy-efficient appliances can all reduce household energy consumption.",
                "E": "Many companies are now adopting sustainable practices in their operations.",
                "F": "We live in a consumer society where buying more is often seen as a sign of success.",
                "G": "Reducing meat consumption or switching to a plant-based diet can lower an individual's carbon footprint significantly."
            },
            "questions": [
                {"number": 23, "correct": "C"},
                {"number": 24, "correct": "F"},
                {"number": 25, "correct": "G"},
                {"number": 26, "correct": "A"},
                {"number": 27, "correct": "D"},
                {"number": 28, "correct": "B"}
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
            "title": "Part 1: Short Conversations",
            "instruction": "You will hear people talking in eight different situations. For questions 1-8, choose the best answer (A, B or C).",
            "type": "short_conversations",
            "questions": [
                {"number": 1, "audio_description": "A woman is talking to her colleague about a meeting.", "transcript": "Woman: Did you hear? The marketing meeting has been moved from 2pm to 4pm. The director had a last-minute conflict with the original time.\nMan: Oh, that's actually better for me. I have a client call at 2:30 that I was worried about.\nWoman: Great. See you at four then.", "question": "Why was the meeting time changed?", "options": {"A": "The director had another appointment.", "B": "The man requested a later time.", "C": "The meeting room was not available."}, "correct": "A"},
                {"number": 2, "audio_description": "You hear a weather forecast on the radio.", "transcript": "Announcer: Good morning, listeners. Today we're looking at a mostly cloudy day with temperatures around 15 degrees. There's a 60% chance of rain in the afternoon, so don't forget your umbrella if you're heading out later. Tomorrow looks much better though, with sunshine expected throughout the day.", "question": "What does the forecast say about tomorrow?", "options": {"A": "It will be cloudy.", "B": "It will rain.", "C": "It will be sunny."}, "correct": "C"},
                {"number": 3, "audio_description": "A customer is speaking to a shop assistant.", "transcript": "Customer: Excuse me, I bought this jacket last week, but when I got home I noticed this small tear near the pocket. I'd like to exchange it for the same one, please.\nAssistant: I'm sorry about that. Do you have your receipt?\nCustomer: Yes, here it is.", "question": "What is the customer's problem?", "options": {"A": "The jacket is the wrong size.", "B": "The jacket is damaged.", "C": "The jacket is the wrong color."}, "correct": "B"},
                {"number": 4, "audio_description": "You hear a message on an answering machine.", "transcript": "Hello, this is Dr. Patterson's office calling to confirm your appointment for Thursday at 10am. If you need to reschedule, please call us back at 555-0123 before Wednesday afternoon.", "question": "What is the purpose of this call?", "options": {"A": "To cancel an appointment.", "B": "To confirm an appointment.", "C": "To make a new appointment."}, "correct": "B"},
                {"number": 5, "audio_description": "Two friends are discussing weekend plans.", "transcript": "Man: So, are you still coming to the barbecue on Saturday?\nWoman: I'd love to, but I have to finish a report for Monday. I've been putting it off all week.\nMan: That's too bad. Maybe we can meet up for coffee on Sunday instead?\nWoman: That would be great. Let's say 2 o'clock at the usual place?", "question": "Why can't the woman go to the barbecue?", "options": {"A": "She has to visit family.", "B": "She has work to complete.", "C": "She is going to a coffee shop."}, "correct": "B"},
                {"number": 6, "audio_description": "A travel agent is giving information.", "transcript": "Agent: The flight departs at 7:15 in the morning and arrives in Paris at 9:30 local time. You'll have a two-hour layover in Amsterdam. The total cost including taxes is $450.", "question": "Where will the plane stop before Paris?", "options": {"A": "London", "B": "Amsterdam", "C": "Brussels"}, "correct": "B"},
                {"number": 7, "audio_description": "A professor is making an announcement.", "transcript": "Professor: Before we end today's class, I want to remind everyone that the deadline for the research paper has been extended by one week. It's now due on the 25th instead of the 18th. However, I still encourage you to submit early if you can.", "question": "What has the professor announced?", "options": {"A": "The paper topic has changed.", "B": "The deadline has been extended.", "C": "The class will end early."}, "correct": "B"},
                {"number": 8, "audio_description": "A woman is talking about her new job.", "transcript": "Woman: I started my new job last Monday. The office is only a 10-minute walk from my apartment, which is so much better than my hour-long commute before. The work is challenging but interesting.", "question": "What does the woman like about her new job?", "options": {"A": "The high salary.", "B": "The short distance from home.", "C": "The easy work."}, "correct": "B"}
            ]
        },
        {
            "part_number": 2,
            "title": "Part 2: Sentence Completion",
            "instruction": "You will hear a talk about the history of coffee. For questions 9-18, complete the sentences.",
            "type": "sentence_completion",
            "audio_description": "A lecturer giving a talk about the history of coffee.",
            "transcript": "Good afternoon, everyone. Today I'm going to talk about the fascinating history of coffee.\n\nThe story of coffee begins in Ethiopia, where, according to legend, a goat herder named Kaldi noticed his goats becoming energetic after eating berries from a certain tree. This discovery dates back to approximately the 9th century.\n\nFrom Ethiopia, coffee spread to the Arabian Peninsula. By the 15th century, coffee was being grown in Yemen, and it had become an important part of social and religious life. Coffee houses, known as qahveh khaneh, began to appear in cities throughout the Middle East.\n\nEuropeans first encountered coffee in the 17th century when Venetian traders brought it to Italy. Initially, some people were suspicious and called it 'the bitter invention of Satan.' However, Pope Clement the Eighth gave coffee his approval.\n\nThe Dutch were the first Europeans to establish coffee plantations in their colonies, starting in Java, Indonesia, in the late 1600s.\n\nCoffee reached the Americas in the 18th century. Americans switched from tea to coffee after the Boston Tea Party in 1773 as a patriotic gesture.\n\nToday, coffee is the second most traded commodity in the world after oil. Over 2.25 billion cups are consumed every day. The largest producer of coffee is Brazil.",
            "questions": [
                {"number": 9, "question": "According to legend, coffee was discovered by a _____ herder.", "correct": "goat"},
                {"number": 10, "question": "Coffee originated in the country of _____.", "correct": "Ethiopia"},
                {"number": 11, "question": "By the 15th century, coffee was being grown in _____.", "correct": "Yemen"},
                {"number": 12, "question": "Coffee houses in the Middle East were called qahveh _____.", "correct": "khaneh"},
                {"number": 13, "question": "Coffee was first brought to Europe by _____ traders.", "correct": "Venetian"},
                {"number": 14, "question": "The Pope who approved coffee was Clement the _____.", "correct": "Eighth"},
                {"number": 15, "question": "The Dutch established coffee plantations in _____, Indonesia.", "correct": "Java"},
                {"number": 16, "question": "Americans switched from tea to coffee after the Boston Tea _____.", "correct": "Party"},
                {"number": 17, "question": "Coffee is the second most traded commodity after _____.", "correct": "oil"},
                {"number": 18, "question": "The largest coffee producer in the world is _____.", "correct": "Brazil"}
            ]
        },
        {
            "part_number": 3,
            "title": "Part 3: Multiple Matching",
            "instruction": "You will hear five people talking about learning a foreign language. For questions 19-23, choose from the list (A-H).",
            "type": "multiple_matching",
            "audio_description": "Five people talking about learning a foreign language.",
            "speakers": [
                {"number": 19, "name": "Speaker 1", "transcript": "When I moved to Spain for work, I was forced to learn Spanish quickly. The best thing I did was completely immerse myself - I stopped watching English TV and only listened to Spanish radio. Within six months, I was dreaming in Spanish!"},
                {"number": 20, "name": "Speaker 2", "transcript": "I tried so many language apps and courses, but what really worked for me was finding a language exchange partner. We meet twice a week - one day we speak only German, the next only English. It's free, and I've made a great friend."},
                {"number": 21, "name": "Speaker 3", "transcript": "Grammar books and vocabulary lists never worked for me. I learned French by watching French films with French subtitles. It was entertainment and education at the same time."},
                {"number": 22, "name": "Speaker 4", "transcript": "The biggest mistake I made was being afraid to speak. I spent years perfecting my written Japanese but couldn't hold a conversation. Now I force myself to speak, even if I make mistakes. That's when I really started improving."},
                {"number": 23, "name": "Speaker 5", "transcript": "I've been learning Mandarin for five years, and what kept me motivated was setting clear goals. First it was ordering food, then having a simple conversation, then reading news articles."}
            ],
            "options": {
                "A": "suggests that making mistakes is part of the learning process",
                "B": "recommends learning through entertainment media",
                "C": "believes total immersion is the most effective method",
                "D": "emphasizes the importance of setting achievable targets",
                "E": "thinks traditional learning methods are best",
                "F": "values the social aspect of language learning",
                "G": "suggests learning is easier for children",
                "H": "believes language learning requires expensive courses"
            },
            "answers": [
                {"number": 19, "correct": "C"},
                {"number": 20, "correct": "F"},
                {"number": 21, "correct": "B"},
                {"number": 22, "correct": "A"},
                {"number": 23, "correct": "D"}
            ]
        },
        {
            "part_number": 4,
            "title": "Part 4: Interview",
            "instruction": "You will hear an interview with a marine biologist. For questions 24-30, choose the best answer (A, B or C).",
            "type": "interview",
            "audio_description": "An interview with Dr. Sarah Chen, a marine biologist.",
            "transcript": "Interviewer: Today we're joined by Dr. Sarah Chen, a marine biologist who has spent the last fifteen years studying ocean ecosystems.\n\nDr. Chen: Thank you for having me.\n\nInterviewer: How would you describe the current state of our oceans?\n\nDr. Chen: Our oceans are in crisis. We're seeing coral bleaching events more frequent than ever. Fish populations are declining due to overfishing. And perhaps most concerning is the plastic pollution problem - there's now plastic in every part of the ocean.\n\nInterviewer: What do you think is the biggest threat?\n\nDr. Chen: If I had to choose one, I'd say climate change. Rising ocean temperatures affect everything - they cause coral bleaching, change fish migration patterns, affect the entire food chain. And as the oceans warm, they absorb more carbon dioxide, which makes them more acidic.\n\nInterviewer: What can ordinary people do?\n\nDr. Chen: Reducing plastic use is important. Being careful about what seafood you buy matters too. But perhaps the most impactful thing is using your voice - support policies that protect marine areas, vote for leaders who take climate change seriously.\n\nInterviewer: Are there success stories?\n\nDr. Chen: Absolutely. When we protect areas properly, nature can recover remarkably quickly. I've seen damaged coral reefs begin to recover within a few years.\n\nInterviewer: What's next for your research?\n\nDr. Chen: I'm currently leading a project to map microplastic distribution in the Pacific Ocean.",
            "questions": [
                {"number": 24, "question": "How long has Dr. Chen been studying ocean ecosystems?", "options": {"A": "Five years", "B": "Ten years", "C": "Fifteen years"}, "correct": "C"},
                {"number": 25, "question": "According to Dr. Chen, what is now found everywhere in the ocean?", "options": {"A": "Fish", "B": "Plastic", "C": "Coral"}, "correct": "B"},
                {"number": 26, "question": "What does Dr. Chen consider the biggest threat to ocean health?", "options": {"A": "Overfishing", "B": "Plastic pollution", "C": "Climate change"}, "correct": "C"},
                {"number": 27, "question": "What happens when oceans absorb more carbon dioxide?", "options": {"A": "They become warmer.", "B": "They become more acidic.", "C": "They become cleaner."}, "correct": "B"},
                {"number": 28, "question": "What is the most impactful action for ordinary people?", "options": {"A": "Reducing plastic use", "B": "Buying sustainable seafood", "C": "Supporting protective policies"}, "correct": "C"},
                {"number": 29, "question": "What does Dr. Chen say about coral reefs?", "options": {"A": "They cannot recover once damaged.", "B": "They can recover quickly when protected.", "C": "They are not affected by climate change."}, "correct": "B"},
                {"number": 30, "question": "What is Dr. Chen's current research about?", "options": {"A": "Coral reef restoration", "B": "Fish population recovery", "C": "Microplastic distribution"}, "correct": "C"}
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
            "instruction": "Complete BOTH Task 1 and Task 2.",
            "tasks": [
                {
                    "task_number": 1,
                    "title": "Task 1: Email/Letter",
                    "type": "email",
                    "instruction": "Read the situation below and write an appropriate email.",
                    "situation": "You recently bought a laptop online, but when it arrived, you discovered several problems with it. The screen has a small crack, the keyboard is missing a key, and the battery drains very quickly.\n\nWrite an email to the company's customer service department. In your email:\n- Explain what problems you found with the laptop\n- Say how you feel about this situation\n- Tell them what you would like them to do about it\n\nWrite between 120-150 words.",
                    "min_words": 120,
                    "max_words": 150
                },
                {
                    "task_number": 2,
                    "title": "Task 2: Review",
                    "type": "review",
                    "instruction": "Write a review.",
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
            "prompt": "Some people believe that technology has made our lives easier and more convenient. Others argue that technology has created new problems and made life more stressful.\n\nDiscuss both views and give your own opinion.\n\nWrite between 250-300 words.\n\nYour essay will be evaluated on:\n- Task Achievement\n- Coherence & Cohesion\n- Lexical Resource\n- Grammatical Range & Accuracy",
            "min_words": 250,
            "max_words": 300
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
        elif ptype == "gapped_text":
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
        elif ptype == "sentence_completion":
            for q in part["questions"]:
                total += 1
                qn = str(q["number"])
                ua = answers.get(qn, "").strip().lower()
                ca = q["correct"].lower()
                ic = ua == ca or ca in ua
                if ic: correct += 1
                details.append({"q": qn, "ua": ua, "ca": ca, "ok": ic, "part": part["part_number"]})
        elif ptype == "multiple_matching":
            for a in part["answers"]:
                total += 1
                qn = str(a["number"])
                ua = answers.get(qn, "").strip().upper()
                ca = a["correct"].upper()
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

    # Word count - STRICT requirements
    if wc < min_w * 0.3:
        score = 1
        fb.append(f"SEVERELY under word count ({wc}/{min_w}) - Band 1.")
        return {"score": 1, "feedback": " ".join(fb), "wc": wc}
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
            score = max(1, score - 2)
            fb.append(f"Sentence repetition detected ({int((1-ratio)*100)}% repeated).")
        elif ratio < 0.85:
            score -= 1
            fb.append("Some repetition in sentences.")

    # Check for real content (not just filler)
    content_words = [w for w in lw if len(w) > 3]
    if len(content_words) < wc * 0.4:
        fb.append("Too many short/filler words.")
        score -= 1

    score = max(1, min(9, score))
    return {"score": score, "feedback": " ".join(fb), "wc": wc}


async def evaluate_writing_with_ai(task1: str, task2: str, essay: str, writing_test: dict) -> Dict:
    """100% AI evaluation - spam detection first, then ONLY AI evaluation"""

    # Check each part for spam FIRST
    parts_spam = {}
    for name, txt in [("task1", task1), ("task2", task2), ("essay", essay)]:
        parts_spam[name] = detect_spam_advanced(txt)

    # Make spam result with score 0 or 1
    def make_spam_result(name, txt, spam_info):
        score = spam_info["score"]  # Can be 0 or 1
        band_text = "Band 0 - Invalid" if score == 0 else "Band 1 - Non User"
        return {
            "score": score, "band": score, "word_count": len(txt.split()), "is_valid": False,
            "feedback": {
                "overall": band_text,
                "content": spam_info["reason"],
                "organization": "No valid structure detected.",
                "language": "No meaningful language use.",
                "accuracy": "Cannot evaluate - insufficient content."
            }
        }

    results = {}
    for name, txt in [("task1", task1), ("task2", task2), ("essay", essay)]:
        if parts_spam[name]["is_spam"]:
            score = parts_spam[name]["score"]
            band_text = "Band 0 - Invalid" if score == 0 else "Band 1 - Non User"
            if name == "essay":
                results[name] = {
                    "score": score, "band": score, "word_count": len(txt.split()), "is_valid": False,
                    "feedback": {
                        "overall": band_text,
                        "task_achievement": parts_spam[name]["reason"],
                        "coherence_cohesion": "No coherent structure.",
                        "lexical_resource": "No meaningful vocabulary.",
                        "grammatical_range": "Cannot evaluate - insufficient content."
                    }
                }
            else:
                results[name] = make_spam_result(name, txt, parts_spam[name])

    # For non-spam parts, use AI evaluation ONLY
    non_spam_parts = [n for n in ["task1", "task2", "essay"] if n not in results]

    if non_spam_parts:
        ai_result = await try_ai_evaluation(task1, task2, essay, writing_test, non_spam_parts)
        if ai_result:
            for name in non_spam_parts:
                if name in ai_result:
                    results[name] = ai_result[name]
        else:
            # No AI available - still evaluate strictly via AI prompt simulation
            # Give strict scores based on content analysis
            for name in non_spam_parts:
                txt = task1 if name == "task1" else (task2 if name == "task2" else essay)
                strict_score = await get_strict_ai_score(txt, name)
                if name == "essay":
                    results[name] = {
                        "score": strict_score, "band": strict_score, "word_count": len(txt.split()), "is_valid": strict_score >= 3,
                        "feedback": {
                            "overall": f"Band {strict_score}",
                            "task_achievement": "AI evaluation required for detailed feedback.",
                            "coherence_cohesion": "AI evaluation required.",
                            "lexical_resource": "AI evaluation required.",
                            "grammatical_range": "AI evaluation required."
                        }
                    }
                else:
                    results[name] = {
                        "score": strict_score, "band": strict_score, "word_count": len(txt.split()), "is_valid": strict_score >= 3,
                        "feedback": {
                            "overall": f"Band {strict_score}",
                            "content": "AI evaluation required for detailed feedback.",
                            "organization": "AI evaluation required.",
                            "language": "AI evaluation required.",
                            "accuracy": "AI evaluation required."
                        }
                    }

    # Calculate overall (allow 0)
    t1s = results["task1"]["score"]
    t2s = results["task2"]["score"]
    es = results["essay"]["score"]
    overall = t1s * 0.25 + t2s * 0.25 + es * 0.5
    pct = (overall / 9) * 100

    # If all parts are 0, percentage is 0
    if t1s == 0 and t2s == 0 and es == 0:
        pct = 0

    cefr = "A1"
    for lv, d in CEFR_LEVELS.items():
        if pct >= d["min_score"]:
            cefr = lv
            break

    return {
        "task1": results["task1"], "task2": results["task2"], "essay": results["essay"],
        "overall_score": round(overall, 1), "overall_band": round(overall),
        "overall_percentage": round(pct, 1), "cefr_level": cefr,
        "general_feedback": "AI Evaluation complete." if any(r.get("is_valid") for r in results.values()) else "Invalid submission - please write genuine English content."
    }


async def get_strict_ai_score(text: str, task_type: str) -> int:
    """Fallback score when AI is unavailable - fair band by word count and diversity"""
    words = text.split()
    wc = len(words)
    # Task1/Task2: 120–150 words; Essay: 250–300
    target_min = 120 if task_type != "essay" else 250
    target_ok = wc >= target_min * 0.8  # 80% of target = reasonable attempt

    if wc < 30:
        return 1
    if wc < 60:
        return 2
    if wc < 90:
        return 3

    unique = len(set(w.lower() for w in words))
    diversity = unique / wc if wc else 0
    if diversity < 0.25:
        return 2
    if diversity < 0.35:
        return 3
    if diversity < 0.5:
        return 4
    # Adequate length and diversity: band 4–5 so user sees ~44–55% when AI is off
    return 5 if target_ok else 4


async def try_ai_evaluation(task1, task2, essay, writing_test, parts_to_eval) -> dict:
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
    prompt = f"""You are an EXTREMELY strict CEFR English examiner. Evaluate ONLY genuine English writing that ADDRESSES THE TASK. Be HARSH.

CRITICAL RULES:
- OFF-TOPIC / IRRELEVANT: If the text does NOT address the given task (random content, different topic, or clearly ignoring the prompt), you MUST give score 0 or 1 only. In feedback write: "Off-topic - does not address the task." Never give more than 1 for off-topic content.
- Repeated sentences/phrases = score 1-2 (SPAM)
- Random/irrelevant text = score 1
- Gibberish or non-English = score 1
- Under word count = maximum score 4
- Score 5 = barely adequate B1 attempt that clearly addresses the task
- Score 7+ requires near-perfect English and full task achievement

TASK 1 was: {t1_instruction}
TASK 2 was: {t2_instruction}
ESSAY topic was: {essay_instruction}

CANDIDATE TASK 1 (Email, 120-150 words): {task1}
[{len(task1.split())} words]

CANDIDATE TASK 2 (Review, 120-150 words): {task2}
[{len(task2.split())} words]

CANDIDATE ESSAY (250-300 words): {essay}
[{len(essay.split())} words]

Respond in EXACT JSON:
{{"task1":{{"score":0,"content":"","organization":"","language":"","accuracy":""}},"task2":{{"score":0,"content":"","organization":"","language":"","accuracy":""}},"essay":{{"score":0,"task_achievement":"","coherence_cohesion":"","lexical_resource":"","grammatical_range":""}},"general_feedback":""}}"""

    def extract_json(text: str):
        if not text or not text.strip():
            return None
        raw = text.strip()
        # Strip markdown code block if present
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        # Try parse as-is
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # Try to find first {...} block
        for pattern in [r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", r"(\{[\s\S]*\})"]:
            m = re.search(pattern, text)
            if m:
                try:
                    return json.loads(m.group(1).strip())
                except json.JSONDecodeError:
                    continue
        # Greedy: take the longest {...} that parses
        for m in re.finditer(r"\{[\s\S]*\}", text):
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                continue
        return None

    def validate_ev(ev):
        """Ensure AI response has task1, task2, essay with score."""
        if not ev or not isinstance(ev, dict):
            return False
        for key in ("task1", "task2", "essay"):
            if key not in ev or not isinstance(ev.get(key), dict):
                return False
        return True

    try:
        # 1) OpenAI birinchi (OPENAI_API_KEY bo'lsa)
        if OPENAI_API_KEY.strip():
            async with httpx.AsyncClient(timeout=90.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY.strip()}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "You are a strict CEFR writing examiner. Reply ONLY with valid JSON. No markdown, no code block, no explanation. Output must be a single JSON object with keys task1, task2, essay, general_feedback."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    choices = data.get("choices") or []
                    if choices:
                        msg = choices[0].get("message") or {}
                        content = (msg.get("content") or "").strip()
                        if content:
                            ev = extract_json(content)
                            if ev and validate_ev(ev):
                                return format_ai_result(ev, task1, task2, essay)
                else:
                    print(f"OpenAI Writing AI: status={r.status_code}, body={r.text[:500]}")
        # 2) Anthropic
        if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.strip():
            async with httpx.AsyncClient(timeout=90.0) as client:
                r = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": ANTHROPIC_API_KEY.strip(), "anthropic-version": "2023-06-01", "content-type": "application/json"},
                    json={"model": "claude-3-haiku-20240307", "max_tokens": 2000, "messages": [{"role": "user", "content": prompt}]},
                )
                if r.status_code == 200:
                    data = r.json()
                    content = ""
                    for block in data.get("content", []):
                        if block.get("type") == "text":
                            content += block.get("text", "")
                    if not content and data.get("content"):
                        content = (data["content"][0].get("text") or "")
                    content = (content or "").strip()
                    if content:
                        ev = extract_json(content)
                        if ev and validate_ev(ev):
                            return format_ai_result(ev, task1, task2, essay)
                else:
                    print(f"Anthropic Writing AI: status={r.status_code}, body={r.text[:500]}")
    except Exception as e:
        print(f"Writing AI error: {e}")
        import traceback
        traceback.print_exc()
    return None


def _score_int(val) -> int:
    """Parse score from AI (may be string or float)."""
    if val is None:
        return 3
    if isinstance(val, int):
        return max(1, min(9, val))
    try:
        return max(1, min(9, int(float(val))))
    except (TypeError, ValueError):
        return 3


def format_ai_result(ev, task1, task2, essay):
    def cap_off_topic(name):
        d = ev.get(name, {})
        s = _score_int(d.get("score"))
        fb = (d.get("content") or d.get("task_achievement") or "").lower()
        if fb and ("off-topic" in fb or "does not address" in fb or "irrelevant" in fb):
            s = min(s, 1)
        return max(1, min(9, s))
    r = {}
    for name, txt in [("task1", task1), ("task2", task2)]:
        s = cap_off_topic(name) if name in ev else _score_int(ev.get(name, {}).get("score"))
        r[name] = {
            "score": s, "band": s, "word_count": len(txt.split()), "is_valid": s >= 3,
            "feedback": {
                "overall": f"Band {s}",
                "content": ev.get(name, {}).get("content", "") or "Evaluated.",
                "organization": ev.get(name, {}).get("organization", "") or "Evaluated.",
                "language": ev.get(name, {}).get("language", "") or "Evaluated.",
                "accuracy": ev.get(name, {}).get("accuracy", "") or "Evaluated."
            }
        }
    s = cap_off_topic("essay") if "essay" in ev else _score_int(ev.get("essay", {}).get("score"))
    r["essay"] = {
        "score": s, "band": s, "word_count": len(essay.split()), "is_valid": s >= 3,
        "feedback": {
            "overall": f"Band {s}",
            "task_achievement": ev.get("essay", {}).get("task_achievement", "") or "Evaluated.",
            "coherence_cohesion": ev.get("essay", {}).get("coherence_cohesion", "") or "Evaluated.",
            "lexical_resource": ev.get("essay", {}).get("lexical_resource", "") or "Evaluated.",
            "grammatical_range": ev.get("essay", {}).get("grammatical_range", "") or "Evaluated."
        }
    }
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
        return RedirectResponse(url="/start", status_code=302)
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
        return RedirectResponse(url=next_url or "/start", status_code=302)
    t = get_translations(request)
    lang = get_lang(request)
    error_message = LOGIN_ERROR_MESSAGES.get(error, error) if error else ""
    return templates.TemplateResponse("login.html", {
        "request": request, "t": t, "lang": lang, "user": get_current_user(request),
        "error": error_message, "next_url": next_url or "/start", "google_client_id": GOOGLE_CLIENT_ID
    })

@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(""), password: str = Form(""), next_url: str = Form("/start")):
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
    resp = RedirectResponse(url=next_url or "/start", status_code=302)
    resp.set_cookie(key=AUTH_COOKIE, value=token, max_age=AUTH_MAX_AGE, httponly=True, samesite="lax")
    return resp

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = ""):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/start", status_code=302)
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
    resp = RedirectResponse(url="/start", status_code=302)
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
        resp = RedirectResponse(url=next_url or "/start", status_code=302)
    resp.set_cookie(key=AUTH_COOKIE, value=token, max_age=AUTH_MAX_AGE, httponly=True, samesite="lax")
    return resp

# ============ ONBOARDING (faqat ism – yangi Google user) ============

@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/start", status_code=302)
    if user.get("onboarding_done") is True:
        return RedirectResponse(url="/start", status_code=302)
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("onboarding.html", {"request": request, "t": t, "lang": lang, "user": user})

@app.post("/onboarding", response_class=HTMLResponse)
async def onboarding_submit(request: Request, name: str = Form("")):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/start", status_code=302)
    name = (name or "").strip()
    if name:
        update_user(user["id"], name=name, onboarding_done=True)
    else:
        update_user(user["id"], onboarding_done=True)
    return RedirectResponse(url="/start", status_code=302)

# ============ PROTECTED: TEST (require login) ============

@app.get("/start", response_class=HTMLResponse)
async def start_test(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next_url=/start", status_code=302)
    sid = str(uuid.uuid4())
    s = get_session(sid)
    s["user_id"] = user["id"]
    t = get_translations(request)
    lang = get_lang(request)
    resp = templates.TemplateResponse("start.html", {"request": request, "session_id": sid, "t": t, "lang": lang, "user": user})
    resp.set_cookie(key="session_id", value=sid, max_age=7200)
    return resp

@app.get("/test/reading", response_class=HTMLResponse)
async def reading_test(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return RedirectResponse(url="/start", status_code=302)
    tests = get_reading_tests()
    test = tests[0] if tests else DEFAULT_READING
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("test_reading.html", {"request": request, "test_data": test, "session_id": sid, "t": t, "lang": lang})

@app.post("/test/reading/submit")
async def submit_reading(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return JSONResponse({"error": "No session"}, status_code=400)
    fd = await request.form()
    answers = {k: v for k, v in fd.items() if k != "session_id"}
    tests = get_reading_tests()
    test = tests[0] if tests else DEFAULT_READING
    result = calculate_reading_score(answers, test)
    s = get_session(sid)
    s["reading"] = {"completed": True, "score": result["correct"], "total": result["total"], "percentage": result["percentage"], "details": result["details"]}
    return JSONResponse({"success": True, "score": result["correct"], "total": result["total"], "percentage": result["percentage"], "redirect": "/test/listening"})

@app.get("/test/listening", response_class=HTMLResponse)
async def listening_test(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return RedirectResponse(url="/start", status_code=302)
    tests = get_listening_tests()
    test = tests[0] if tests else DEFAULT_LISTENING
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("test_listening.html", {"request": request, "test_data": test, "session_id": sid, "t": t, "lang": lang})

@app.post("/test/listening/submit")
async def submit_listening(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return JSONResponse({"error": "No session"}, status_code=400)
    fd = await request.form()
    answers = {k: v for k, v in fd.items() if k != "session_id"}
    tests = get_listening_tests()
    test = tests[0] if tests else DEFAULT_LISTENING
    result = calculate_listening_score(answers, test)
    s = get_session(sid)
    s["listening"] = {"completed": True, "score": result["correct"], "total": result["total"], "percentage": result["percentage"], "details": result["details"]}
    return JSONResponse({"success": True, "score": result["correct"], "total": result["total"], "percentage": result["percentage"], "redirect": "/test/writing"})

@app.get("/test/writing", response_class=HTMLResponse)
async def writing_test(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return RedirectResponse(url="/start", status_code=302)
    tests = get_writing_tests()
    test = tests[0] if tests else DEFAULT_WRITING
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
    if not sid: return RedirectResponse(url="/start", status_code=302)
    s = get_session(sid)
    if not all([s.get("reading", {}).get("completed"), s.get("listening", {}).get("completed"), s.get("writing", {}).get("completed")]):
        return RedirectResponse(url="/start", status_code=302)
    save_test_result(s)  # profil tarixiga saqlash
    t = get_translations(request)
    lang = get_lang(request)
    return templates.TemplateResponse("results.html", {"request": request, "session": s, "cefr_levels": CEFR_LEVELS, "t": t, "lang": lang, "user": get_current_user(request)})

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
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "reading_count": len(reading),
        "listening_count": len(listening),
        "writing_count": len(writing),
        "feedback_count": len(fbs),
        "feedbacks": fbs[-20:],
        "reading_tests": reading,
        "listening_tests": listening,
        "writing_tests": writing
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

@app.get("/health")
async def health():
    return {"status": "ok", "service": "OSCO CEFR"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    # Render va boshqa cloud'da PORT beriladi, reload o'chiq
    use_reload = not os.getenv("PORT")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=use_reload)
