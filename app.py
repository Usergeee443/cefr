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

app = FastAPI(title="OSCO CEFR Test Platform")

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
    """ULTRA-STRICT spam/gibberish/repetition detection - Band 1 for any low-quality content"""
    if not text or len(text.strip()) < 10:
        return {"is_spam": True, "score": 1, "reason": "Text is too short or empty - Band 1."}

    words = text.split()
    wc = len(words)
    if wc < 10:
        return {"is_spam": True, "score": 1, "reason": "Fewer than 10 words - Band 1."}

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
    """Evaluate writing - spam detection first, then AI or algorithmic"""

    # Check each part for spam FIRST
    parts_spam = {}
    for name, txt in [("task1", task1), ("task2", task2), ("essay", essay)]:
        parts_spam[name] = detect_spam_advanced(txt)

    # If ANY part is spam, give it score 1 immediately
    def make_spam_result(name, txt, reason):
        return {
            "score": 1, "band": 1, "word_count": len(txt.split()), "is_valid": False,
            "feedback": {
                "overall": "Band 1 - Non User",
                "content": reason,
                "organization": "No valid structure detected.",
                "language": "No meaningful language use.",
                "accuracy": "Cannot evaluate."
            }
        }

    results = {}
    for name, txt in [("task1", task1), ("task2", task2), ("essay", essay)]:
        if parts_spam[name]["is_spam"]:
            if name == "essay":
                results[name] = {
                    "score": 1, "band": 1, "word_count": len(txt.split()), "is_valid": False,
                    "feedback": {
                        "overall": "Band 1 - Non User",
                        "task_achievement": parts_spam[name]["reason"],
                        "coherence_cohesion": "No coherent structure.",
                        "lexical_resource": "No meaningful vocabulary.",
                        "grammatical_range": "Cannot evaluate."
                    }
                }
            else:
                results[name] = make_spam_result(name, txt, parts_spam[name]["reason"])

    # For non-spam parts, try AI evaluation
    non_spam_parts = [n for n in ["task1", "task2", "essay"] if n not in results]

    if non_spam_parts:
        ai_result = await try_ai_evaluation(task1, task2, essay, writing_test, non_spam_parts)
        if ai_result:
            for name in non_spam_parts:
                if name in ai_result:
                    results[name] = ai_result[name]

    # Fallback: algorithmic for anything still not evaluated
    part1_data = writing_test["parts"][0] if writing_test.get("parts") else {}
    part2_data = writing_test["parts"][1] if len(writing_test.get("parts", [])) > 1 else {}

    tasks = part1_data.get("tasks", [])
    t1_min = tasks[0].get("min_words", 120) if len(tasks) > 0 else 120
    t1_max = tasks[0].get("max_words", 150) if len(tasks) > 0 else 150
    t2_min = tasks[1].get("min_words", 120) if len(tasks) > 1 else 120
    t2_max = tasks[1].get("max_words", 150) if len(tasks) > 1 else 150
    e_min = part2_data.get("min_words", 250)
    e_max = part2_data.get("max_words", 300)

    if "task1" not in results:
        ev = algorithmic_score(task1, t1_min, t1_max, "email")
        results["task1"] = {
            "score": ev["score"], "band": ev["score"], "word_count": ev["wc"], "is_valid": ev["score"] > 2,
            "feedback": {"overall": f"Band {ev['score']}", "content": ev["feedback"], "organization": "Algorithmic.", "language": "Algorithmic.", "accuracy": "Algorithmic."}
        }
    if "task2" not in results:
        ev = algorithmic_score(task2, t2_min, t2_max, "review")
        results["task2"] = {
            "score": ev["score"], "band": ev["score"], "word_count": ev["wc"], "is_valid": ev["score"] > 2,
            "feedback": {"overall": f"Band {ev['score']}", "content": ev["feedback"], "organization": "Algorithmic.", "language": "Algorithmic.", "accuracy": "Algorithmic."}
        }
    if "essay" not in results:
        ev = algorithmic_score(essay, e_min, e_max, "essay")
        results["essay"] = {
            "score": ev["score"], "band": ev["score"], "word_count": ev["wc"], "is_valid": ev["score"] > 2,
            "feedback": {"overall": f"Band {ev['score']}", "task_achievement": ev["feedback"], "coherence_cohesion": "Algorithmic.", "lexical_resource": "Algorithmic.", "grammatical_range": "Algorithmic."}
        }

    # Calculate overall
    t1s = results["task1"]["score"]
    t2s = results["task2"]["score"]
    es = results["essay"]["score"]
    overall = t1s * 0.25 + t2s * 0.25 + es * 0.5
    pct = (overall / 9) * 100

    cefr = "A1"
    for lv, d in CEFR_LEVELS.items():
        if pct >= d["min_score"]:
            cefr = lv
            break

    return {
        "task1": results["task1"], "task2": results["task2"], "essay": results["essay"],
        "overall_score": round(overall, 1), "overall_band": round(overall),
        "overall_percentage": round(pct, 1), "cefr_level": cefr,
        "general_feedback": "Evaluation complete."
    }


async def try_ai_evaluation(task1, task2, essay, writing_test, parts_to_eval) -> dict:
    """Try AI evaluation via Anthropic or OpenAI"""
    prompt = f"""You are an EXTREMELY strict CEFR English examiner. Evaluate ONLY genuine English writing. Be HARSH.

CRITICAL RULES:
- Repeated sentences/phrases = score 1-2 (SPAM)
- Random/irrelevant text = score 1
- Gibberish or non-English = score 1
- Under word count = maximum score 4
- Score 5 = barely adequate B1 attempt
- Score 7+ requires near-perfect English

TASK 1 (Email, 120-150 words): {task1}
[{len(task1.split())} words]

TASK 2 (Review, 120-150 words): {task2}
[{len(task2.split())} words]

ESSAY (250-300 words): {essay}
[{len(essay.split())} words]

Respond in EXACT JSON:
{{"task1":{{"score":0,"content":"","organization":"","language":"","accuracy":""}},"task2":{{"score":0,"content":"","organization":"","language":"","accuracy":""}},"essay":{{"score":0,"task_achievement":"","coherence_cohesion":"","lexical_resource":"","grammatical_range":""}},"general_feedback":""}}"""

    try:
        if ANTHROPIC_API_KEY:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post("https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                    json={"model": "claude-3-haiku-20240307", "max_tokens": 2000, "messages": [{"role": "user", "content": prompt}]})
                if r.status_code == 200:
                    content = r.json()["content"][0]["text"]
                    m = re.search(r'\{[\s\S]*\}', content)
                    if m:
                        ev = json.loads(m.group())
                        return format_ai_result(ev, task1, task2, essay)
        elif OPENAI_API_KEY:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post("https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "gpt-3.5-turbo", "messages": [{"role": "system", "content": "Strict CEFR examiner. JSON only."}, {"role": "user", "content": prompt}], "temperature": 0.2})
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    m = re.search(r'\{[\s\S]*\}', content)
                    if m:
                        ev = json.loads(m.group())
                        return format_ai_result(ev, task1, task2, essay)
    except Exception as e:
        print(f"AI error: {e}")
    return None


def format_ai_result(ev, task1, task2, essay):
    r = {}
    for name, txt in [("task1", task1), ("task2", task2)]:
        s = ev.get(name, {}).get("score", 3)
        s = max(1, min(9, s))
        r[name] = {
            "score": s, "band": s, "word_count": len(txt.split()), "is_valid": True,
            "feedback": {
                "overall": f"Band {s}",
                "content": ev.get(name, {}).get("content", ""),
                "organization": ev.get(name, {}).get("organization", ""),
                "language": ev.get(name, {}).get("language", ""),
                "accuracy": ev.get(name, {}).get("accuracy", "")
            }
        }
    s = ev.get("essay", {}).get("score", 3)
    s = max(1, min(9, s))
    r["essay"] = {
        "score": s, "band": s, "word_count": len(essay.split()), "is_valid": True,
        "feedback": {
            "overall": f"Band {s}",
            "task_achievement": ev.get("essay", {}).get("task_achievement", ""),
            "coherence_cohesion": ev.get("essay", {}).get("coherence_cohesion", ""),
            "lexical_resource": ev.get("essay", {}).get("lexical_resource", ""),
            "grammatical_range": ev.get("essay", {}).get("grammatical_range", "")
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

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/start", response_class=HTMLResponse)
async def start_test(request: Request):
    sid = str(uuid.uuid4())
    get_session(sid)
    resp = templates.TemplateResponse("start.html", {"request": request, "session_id": sid})
    resp.set_cookie(key="session_id", value=sid, max_age=7200)
    return resp

@app.get("/test/reading", response_class=HTMLResponse)
async def reading_test(request: Request):
    sid = request.cookies.get("session_id")
    if not sid: return RedirectResponse(url="/start", status_code=302)
    tests = get_reading_tests()
    test = tests[0] if tests else DEFAULT_READING
    return templates.TemplateResponse("test_reading.html", {"request": request, "test_data": test, "session_id": sid})

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
    return templates.TemplateResponse("test_listening.html", {"request": request, "test_data": test, "session_id": sid})

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
    return templates.TemplateResponse("test_writing.html", {"request": request, "test_data": test, "session_id": sid})

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
    return templates.TemplateResponse("results.html", {"request": request, "session": s, "cefr_levels": CEFR_LEVELS})

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
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
