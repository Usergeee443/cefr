# CEFR Test Data - Authentic Format
# Based on Cambridge English and CEFR official exam structures

READING_TEST = {
    "time_limit": 60,  # minutes
    "parts": [
        {
            "part_number": 1,
            "title": "Part 1: Multiple Choice Cloze",
            "instruction": "For questions 1-8, read the text below and decide which answer (A, B, C or D) best fits each gap.",
            "type": "multiple_choice_cloze",
            "text": """The Rise of Remote Work

The COVID-19 pandemic has (1)_____ transformed the way we work. Before 2020, working from home was (2)_____ a privilege enjoyed by a small percentage of the workforce. However, the global health crisis (3)_____ companies worldwide to rapidly adopt remote work policies.

This shift has had both positive and negative (4)_____. On the one hand, employees have gained more flexibility and eliminated lengthy commutes. Many workers report feeling more (5)_____ and having a better work-life balance. On the other hand, some people struggle with isolation and find it difficult to (6)_____ work from their personal life.

Companies are now (7)_____ hybrid models that combine remote and office work. This approach aims to offer the best of both worlds, allowing employees to enjoy flexibility while still maintaining face-to-face (8)_____ with colleagues.""",
            "questions": [
                {
                    "number": 1,
                    "options": {"A": "deeply", "B": "hardly", "C": "rarely", "D": "slightly"},
                    "correct": "A"
                },
                {
                    "number": 2,
                    "options": {"A": "often", "B": "commonly", "C": "mainly", "D": "usually"},
                    "correct": "C"
                },
                {
                    "number": 3,
                    "options": {"A": "made", "B": "forced", "C": "let", "D": "allowed"},
                    "correct": "B"
                },
                {
                    "number": 4,
                    "options": {"A": "consequences", "B": "results", "C": "outcomes", "D": "effects"},
                    "correct": "A"
                },
                {
                    "number": 5,
                    "options": {"A": "effective", "B": "productive", "C": "efficient", "D": "successful"},
                    "correct": "B"
                },
                {
                    "number": 6,
                    "options": {"A": "divide", "B": "split", "C": "separate", "D": "part"},
                    "correct": "C"
                },
                {
                    "number": 7,
                    "options": {"A": "accepting", "B": "receiving", "C": "embracing", "D": "welcoming"},
                    "correct": "C"
                },
                {
                    "number": 8,
                    "options": {"A": "interaction", "B": "communication", "C": "connection", "D": "contact"},
                    "correct": "A"
                }
            ]
        },
        {
            "part_number": 2,
            "title": "Part 2: Open Cloze",
            "instruction": "For questions 9-16, read the text below and think of the word which best fits each gap. Use only ONE word in each gap.",
            "type": "open_cloze",
            "text": """Climate Change and Its Impact

Climate change is one of (9)_____ most pressing issues facing our planet today. Scientists agree that human activities, particularly the burning of fossil fuels, (10)_____ responsible for the rising global temperatures we are experiencing.

The effects of climate change are already (11)_____ felt around the world. Extreme weather events such (12)_____ hurricanes, floods, and droughts are becoming more frequent and severe. Sea levels are rising, threatening coastal communities and island nations.

(13)_____ order to address this crisis, governments and individuals must take action. Reducing carbon emissions, investing in renewable energy, and protecting forests are all essential steps. However, time is running (14)_____. If we do not act quickly, the consequences (15)_____ be catastrophic.

Each of us has a role to play. Simple changes in (16)_____ daily lives, such as using public transportation, reducing waste, and conserving energy, can make a difference.""",
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
            "title": "Part 3: Multiple Choice Comprehension",
            "instruction": "You are going to read a magazine article about artificial intelligence. For questions 17-22, choose the answer (A, B, C or D) which you think fits best according to the text.",
            "type": "multiple_choice_comprehension",
            "text": """Artificial Intelligence: Friend or Foe?

Artificial Intelligence (AI) has rapidly evolved from a concept in science fiction to a technology that permeates nearly every aspect of our daily lives. From the virtual assistants on our smartphones to the algorithms that recommend what we should watch next, AI has become an invisible but powerful force shaping our decisions and experiences.

Proponents of AI point to its tremendous potential for improving human life. In healthcare, AI systems can analyze medical images with greater accuracy than human doctors, potentially catching diseases at earlier, more treatable stages. In environmental science, AI helps researchers model climate patterns and develop strategies for conservation. The technology has also revolutionized industries from manufacturing to finance, increasing efficiency and reducing costs.

However, critics raise valid concerns about the darker implications of AI advancement. One of the most pressing issues is the potential for widespread job displacement. As AI systems become capable of performing tasks previously done by humans, millions of workers may find themselves unemployed. This technological unemployment could exacerbate social inequality if the benefits of AI are not distributed fairly.

Another concern is the question of bias in AI systems. Because these systems learn from data created by humans, they can inherit and even amplify existing prejudices. There have been documented cases of AI systems discriminating against certain groups in areas such as hiring, lending, and criminal justice. Addressing these biases requires careful attention to the data used to train AI and the algorithms themselves.

Privacy is yet another area of concern. AI systems often rely on vast amounts of personal data to function effectively. This raises questions about who has access to our information and how it might be used. The potential for surveillance and manipulation is significant, particularly when AI is combined with facial recognition technology and social media analysis.

Despite these challenges, many experts believe that the benefits of AI outweigh the risks, provided that appropriate safeguards are put in place. This includes developing ethical guidelines for AI development, creating regulations to prevent misuse, and investing in education to prepare workers for a changing job market. The key is to ensure that humans remain in control of these powerful systems and that the technology serves humanity's best interests.

The debate over AI is far from settled, but one thing is clear: the technology is here to stay. How we choose to develop and deploy AI will shape the future of our society for generations to come. The choices we make today will determine whether AI becomes a tool for human flourishing or a source of new challenges and inequalities.""",
            "questions": [
                {
                    "number": 17,
                    "question": "According to the first paragraph, AI has become",
                    "options": {
                        "A": "a visible force that shapes our decisions.",
                        "B": "a technology that influences us without us noticing.",
                        "C": "something that only exists in science fiction.",
                        "D": "a technology limited to smartphone assistants."
                    },
                    "correct": "B"
                },
                {
                    "number": 18,
                    "question": "What does the article say about AI in healthcare?",
                    "options": {
                        "A": "It has completely replaced human doctors.",
                        "B": "It is less accurate than human analysis.",
                        "C": "It may help detect diseases earlier.",
                        "D": "It is only used for environmental research."
                    },
                    "correct": "C"
                },
                {
                    "number": 19,
                    "question": "The article suggests that technological unemployment",
                    "options": {
                        "A": "is not a serious concern.",
                        "B": "will only affect a few workers.",
                        "C": "could increase social inequality.",
                        "D": "has already been solved."
                    },
                    "correct": "C"
                },
                {
                    "number": 20,
                    "question": "Why might AI systems show bias?",
                    "options": {
                        "A": "Because they are programmed to discriminate.",
                        "B": "Because they learn from human-created data.",
                        "C": "Because they only work in certain industries.",
                        "D": "Because humans cannot control them."
                    },
                    "correct": "B"
                },
                {
                    "number": 21,
                    "question": "What does the article say about privacy and AI?",
                    "options": {
                        "A": "AI does not require any personal data.",
                        "B": "Privacy concerns are exaggerated.",
                        "C": "AI combined with facial recognition raises surveillance concerns.",
                        "D": "Social media is safe from AI analysis."
                    },
                    "correct": "C"
                },
                {
                    "number": 22,
                    "question": "According to the experts mentioned in the article,",
                    "options": {
                        "A": "AI should be banned completely.",
                        "B": "the risks of AI are greater than the benefits.",
                        "C": "AI can be beneficial if proper safeguards are implemented.",
                        "D": "humans have already lost control of AI."
                    },
                    "correct": "C"
                }
            ]
        },
        {
            "part_number": 4,
            "title": "Part 4: Gapped Text",
            "instruction": "You are going to read an article about sustainable living. Six sentences have been removed from the article. Choose from the sentences A-G the one which fits each gap (23-28). There is one extra sentence which you do not need to use.",
            "type": "gapped_text",
            "text": """Living Sustainably in the Modern World

Sustainable living is no longer just a trend but a necessity in our rapidly changing world. With climate change accelerating and natural resources depleting, individuals are looking for ways to reduce their environmental impact. (23)_____

One of the most effective ways to live more sustainably is to reduce consumption. (24)_____ By being mindful of what we purchase and choosing quality over quantity, we can significantly decrease our environmental footprint.

Food choices also play a crucial role in sustainable living. The production of meat, particularly beef, generates significant greenhouse gas emissions. (25)_____ Even small changes, like participating in "Meatless Mondays," can make a difference.

Transportation is another area where individuals can make impactful changes. (26)_____ For those who need to drive, choosing fuel-efficient or electric vehicles is a step in the right direction.

Energy consumption at home offers numerous opportunities for sustainability. (27)_____ Additionally, unplugging devices when not in use and using natural light whenever possible can reduce energy bills and environmental impact.

Water conservation is equally important. Simple practices such as fixing leaky faucets, taking shorter showers, and collecting rainwater for gardens can save thousands of liters annually. (28)_____ With these small but consistent efforts, each of us can contribute to a more sustainable future.""",
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

LISTENING_TEST = {
    "time_limit": 40,  # minutes
    "parts": [
        {
            "part_number": 1,
            "title": "Part 1: Short Conversations",
            "instruction": "You will hear people talking in eight different situations. For questions 1-8, choose the best answer (A, B or C).",
            "type": "short_conversations",
            "questions": [
                {
                    "number": 1,
                    "audio_description": "A woman is talking to her colleague about a meeting.",
                    "transcript": "Woman: Did you hear? The marketing meeting has been moved from 2pm to 4pm. The director had a last-minute conflict with the original time.\nMan: Oh, that's actually better for me. I have a client call at 2:30 that I was worried about.\nWoman: Great. See you at four then.",
                    "question": "Why was the meeting time changed?",
                    "options": {
                        "A": "The director had another appointment.",
                        "B": "The man requested a later time.",
                        "C": "The meeting room was not available."
                    },
                    "correct": "A"
                },
                {
                    "number": 2,
                    "audio_description": "You hear a weather forecast on the radio.",
                    "transcript": "Announcer: Good morning, listeners. Today we're looking at a mostly cloudy day with temperatures around 15 degrees. There's a 60% chance of rain in the afternoon, so don't forget your umbrella if you're heading out later. Tomorrow looks much better though, with sunshine expected throughout the day.",
                    "question": "What does the forecast say about tomorrow?",
                    "options": {
                        "A": "It will be cloudy.",
                        "B": "It will rain.",
                        "C": "It will be sunny."
                    },
                    "correct": "C"
                },
                {
                    "number": 3,
                    "audio_description": "A customer is speaking to a shop assistant.",
                    "transcript": "Customer: Excuse me, I bought this jacket last week, but when I got home I noticed this small tear near the pocket. I'd like to exchange it for the same one, please.\nAssistant: I'm sorry about that. Do you have your receipt?\nCustomer: Yes, here it is.\nAssistant: Thank you. Let me check if we have the same size in stock.",
                    "question": "What is the customer's problem?",
                    "options": {
                        "A": "The jacket is the wrong size.",
                        "B": "The jacket is damaged.",
                        "C": "The jacket is the wrong color."
                    },
                    "correct": "B"
                },
                {
                    "number": 4,
                    "audio_description": "You hear a message on an answering machine.",
                    "transcript": "Hello, this is Dr. Patterson's office calling to confirm your appointment for Thursday at 10am. If you need to reschedule, please call us back at 555-0123 before Wednesday afternoon. We look forward to seeing you.",
                    "question": "What is the purpose of this call?",
                    "options": {
                        "A": "To cancel an appointment.",
                        "B": "To confirm an appointment.",
                        "C": "To make a new appointment."
                    },
                    "correct": "B"
                },
                {
                    "number": 5,
                    "audio_description": "Two friends are discussing weekend plans.",
                    "transcript": "Man: So, are you still coming to the barbecue on Saturday?\nWoman: I'd love to, but I have to finish a report for Monday. I've been putting it off all week.\nMan: That's too bad. Maybe we can meet up for coffee on Sunday instead?\nWoman: That would be great. Let's say 2 o'clock at the usual place?",
                    "question": "Why can't the woman go to the barbecue?",
                    "options": {
                        "A": "She has to visit family.",
                        "B": "She has work to complete.",
                        "C": "She is going to a coffee shop."
                    },
                    "correct": "B"
                },
                {
                    "number": 6,
                    "audio_description": "A travel agent is giving information to a customer.",
                    "transcript": "Agent: The flight departs at 7:15 in the morning and arrives in Paris at 9:30 local time. You'll have a two-hour layover in Amsterdam. The total cost including taxes is $450. Should I book it for you?\nCustomer: Yes, please. Can I pay by credit card?",
                    "question": "Where will the plane stop before Paris?",
                    "options": {
                        "A": "London",
                        "B": "Amsterdam",
                        "C": "Brussels"
                    },
                    "correct": "B"
                },
                {
                    "number": 7,
                    "audio_description": "A professor is making an announcement to students.",
                    "transcript": "Professor: Before we end today's class, I want to remind everyone that the deadline for the research paper has been extended by one week. It's now due on the 25th instead of the 18th. However, I still encourage you to submit early if you can, as I'll provide feedback more quickly on early submissions.",
                    "question": "What has the professor announced?",
                    "options": {
                        "A": "The paper topic has changed.",
                        "B": "The deadline has been extended.",
                        "C": "The class will end early."
                    },
                    "correct": "B"
                },
                {
                    "number": 8,
                    "audio_description": "A woman is talking about her new job.",
                    "transcript": "Woman: I started my new job last Monday. The office is only a 10-minute walk from my apartment, which is so much better than my hour-long commute before. The work is challenging but interesting, and my colleagues have been very welcoming.",
                    "question": "What does the woman like about her new job?",
                    "options": {
                        "A": "The high salary.",
                        "B": "The short distance from home.",
                        "C": "The easy work."
                    },
                    "correct": "B"
                }
            ]
        },
        {
            "part_number": 2,
            "title": "Part 2: Long Monologue",
            "instruction": "You will hear a talk about the history of coffee. For questions 9-18, complete the sentences with a word or short phrase.",
            "type": "sentence_completion",
            "audio_description": "A lecturer giving a talk about the history of coffee.",
            "transcript": """Good afternoon, everyone. Today I'm going to talk about the fascinating history of coffee, one of the world's most popular beverages.

The story of coffee begins in Ethiopia, where, according to legend, a goat herder named Kaldi noticed his goats becoming energetic after eating berries from a certain tree. This discovery dates back to approximately the 9th century.

From Ethiopia, coffee spread to the Arabian Peninsula, where it was first cultivated and traded. By the 15th century, coffee was being grown in Yemen, and it had become an important part of social and religious life. Coffee houses, known as qahveh khaneh, began to appear in cities throughout the Middle East.

Europeans first encountered coffee in the 17th century when Venetian traders brought it to Italy. Initially, some people were suspicious of the dark beverage and called it "the bitter invention of Satan." However, Pope Clement the Eighth gave coffee his approval, and its popularity quickly spread across Europe.

The Dutch were the first Europeans to establish coffee plantations in their colonies, starting in Java, Indonesia, in the late 1600s. This is why we sometimes call coffee "java" today.

Coffee reached the Americas in the 18th century. Interestingly, it wasn't always popular in North America. In fact, tea was the preferred drink until the Boston Tea Party in 1773, when Americans switched to coffee as a patriotic gesture against British tea taxes.

Today, coffee is the second most traded commodity in the world after oil. Over 2.25 billion cups of coffee are consumed every day worldwide. The largest producer of coffee is Brazil, which accounts for about one-third of global production.

The coffee industry has evolved significantly in recent years, with consumers increasingly interested in specialty coffee, fair trade practices, and sustainable farming methods. From its humble origins in Ethiopia to the sophisticated coffee culture we see today, coffee has truly become a global phenomenon.""",
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
            "title": "Part 3: Multiple Speakers Discussion",
            "instruction": "You will hear five different people talking about their experiences learning a foreign language. For questions 19-23, choose from the list (A-H) what each speaker says. Use the letters only once. There are three extra letters which you do not need to use.",
            "type": "multiple_matching",
            "audio_description": "Five people talking about learning a foreign language.",
            "speakers": [
                {
                    "number": 19,
                    "name": "Speaker 1",
                    "transcript": "When I moved to Spain for work, I was forced to learn Spanish quickly. The best thing I did was completely immerse myself - I stopped watching English TV and only listened to Spanish radio. Within six months, I was dreaming in Spanish!"
                },
                {
                    "number": 20,
                    "name": "Speaker 2",
                    "transcript": "I tried so many language apps and courses, but what really worked for me was finding a language exchange partner. We meet twice a week - one day we speak only German, the next only English. It's free, and I've made a great friend."
                },
                {
                    "number": 21,
                    "name": "Speaker 3",
                    "transcript": "Grammar books and vocabulary lists never worked for me. I learned French by watching French films with French subtitles. It was entertainment and education at the same time. Now I can understand almost everything in French cinema."
                },
                {
                    "number": 22,
                    "name": "Speaker 4",
                    "transcript": "The biggest mistake I made was being afraid to speak. I spent years perfecting my written Japanese but couldn't hold a conversation. Now I force myself to speak, even if I make mistakes. That's when I really started improving."
                },
                {
                    "number": 23,
                    "name": "Speaker 5",
                    "transcript": "I've been learning Mandarin for five years, and what kept me motivated was setting clear goals. First it was ordering food, then having a simple conversation, then reading news articles. Each goal gave me a sense of achievement."
                }
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
            "instruction": "You will hear an interview with a marine biologist about ocean conservation. For questions 24-30, choose the best answer (A, B or C).",
            "type": "interview",
            "audio_description": "An interview with Dr. Sarah Chen, a marine biologist.",
            "transcript": """Interviewer: Today we're joined by Dr. Sarah Chen, a marine biologist who has spent the last fifteen years studying ocean ecosystems. Dr. Chen, thank you for being here.

Dr. Chen: Thank you for having me.

Interviewer: Let's start with the big picture. How would you describe the current state of our oceans?

Dr. Chen: Well, I wish I could give you good news, but honestly, our oceans are in crisis. We're seeing coral bleaching events that are more frequent and more severe than ever before. Fish populations are declining in many areas due to overfishing. And perhaps most concerning is the plastic pollution problem - there's now plastic in every part of the ocean, from the surface to the deepest trenches.

Interviewer: What do you think is the biggest threat to ocean health right now?

Dr. Chen: That's a difficult question because all these threats are interconnected. But if I had to choose one, I'd say climate change. Rising ocean temperatures affect everything - they cause coral bleaching, they change fish migration patterns, they affect the entire food chain. And as the oceans warm, they absorb more carbon dioxide, which makes them more acidic, threatening shellfish and coral even further.

Interviewer: What can ordinary people do to help protect the oceans?

Dr. Chen: There's quite a lot, actually. Reducing plastic use is important - bring your own bags, avoid single-use plastics, choose products with less packaging. Being careful about what seafood you buy matters too - look for sustainably sourced fish. But perhaps the most impactful thing is using your voice - support policies that protect marine areas, vote for leaders who take climate change seriously.

Interviewer: Are there any success stories that give you hope?

Dr. Chen: Absolutely. When we protect areas properly, nature can recover remarkably quickly. I've seen damaged coral reefs begin to recover within a few years when we reduce local stressors. Some fish populations have bounced back when overfishing is controlled. And there's growing public awareness about ocean issues, which is encouraging.

Interviewer: What's next for your research?

Dr. Chen: I'm currently leading a project to map microplastic distribution in the Pacific Ocean. We want to understand exactly where the plastic goes and how it affects marine life at every level of the food chain. It's depressing work sometimes, but it's important for developing solutions.

Interviewer: Dr. Chen, thank you for your time and your important work.

Dr. Chen: Thank you.""",
            "questions": [
                {
                    "number": 24,
                    "question": "How long has Dr. Chen been studying ocean ecosystems?",
                    "options": {
                        "A": "Five years",
                        "B": "Ten years",
                        "C": "Fifteen years"
                    },
                    "correct": "C"
                },
                {
                    "number": 25,
                    "question": "According to Dr. Chen, what is now found everywhere in the ocean?",
                    "options": {
                        "A": "Fish",
                        "B": "Plastic",
                        "C": "Coral"
                    },
                    "correct": "B"
                },
                {
                    "number": 26,
                    "question": "What does Dr. Chen consider the biggest threat to ocean health?",
                    "options": {
                        "A": "Overfishing",
                        "B": "Plastic pollution",
                        "C": "Climate change"
                    },
                    "correct": "C"
                },
                {
                    "number": 27,
                    "question": "What happens when oceans absorb more carbon dioxide?",
                    "options": {
                        "A": "They become warmer.",
                        "B": "They become more acidic.",
                        "C": "They become cleaner."
                    },
                    "correct": "B"
                },
                {
                    "number": 28,
                    "question": "According to Dr. Chen, what is the most impactful action for ordinary people?",
                    "options": {
                        "A": "Reducing plastic use",
                        "B": "Buying sustainable seafood",
                        "C": "Supporting protective policies"
                    },
                    "correct": "C"
                },
                {
                    "number": 29,
                    "question": "What does Dr. Chen say about coral reefs?",
                    "options": {
                        "A": "They cannot recover once damaged.",
                        "B": "They can recover relatively quickly when protected.",
                        "C": "They are not affected by climate change."
                    },
                    "correct": "B"
                },
                {
                    "number": 30,
                    "question": "What is Dr. Chen's current research project about?",
                    "options": {
                        "A": "Coral reef restoration",
                        "B": "Fish population recovery",
                        "C": "Microplastic distribution"
                    },
                    "correct": "C"
                }
            ]
        }
    ]
}

WRITING_TEST = {
    "time_limit": 80,  # minutes
    "parts": [
        {
            "part_number": 1,
            "title": "Part 1: Writing Tasks",
            "instruction": "Complete BOTH Task 1 and Task 2 in Part 1.",
            "tasks": [
                {
                    "task_number": 1,
                    "title": "Task 1: Email/Letter Writing",
                    "type": "email",
                    "instruction": "Read the situation below and write an appropriate email or letter.",
                    "situation": """You recently bought a laptop online, but when it arrived, you discovered several problems with it. The screen has a small crack, the keyboard is missing a key, and the battery drains very quickly.

Write an email to the company's customer service department. In your email:
- Explain what problems you found with the laptop
- Say how you feel about this situation
- Tell them what you would like them to do about it

Write between 120-150 words.""",
                    "min_words": 120,
                    "max_words": 150,
                    "criteria": {
                        "content": "Addresses all three bullet points clearly",
                        "organization": "Clear paragraph structure with appropriate greeting and closing",
                        "language": "Formal/semi-formal register appropriate for customer complaint",
                        "accuracy": "Grammar, spelling, and punctuation are accurate"
                    }
                },
                {
                    "task_number": 2,
                    "title": "Task 2: Short Report/Review",
                    "type": "report",
                    "instruction": "Read the situation below and write an appropriate report or review.",
                    "situation": """Your English teacher has asked you to write a review of a book, film, or TV series that you have enjoyed recently.

Write a review that:
- Briefly describes what the book/film/TV series is about
- Explains what you liked about it
- Recommends it to other students and says who would enjoy it most

Write between 120-150 words.""",
                    "min_words": 120,
                    "max_words": 150,
                    "criteria": {
                        "content": "Includes description, opinion, and recommendation",
                        "organization": "Logical structure with clear sections",
                        "language": "Engaging and appropriate for a review",
                        "accuracy": "Grammar, spelling, and punctuation are accurate"
                    }
                }
            ]
        },
        {
            "part_number": 2,
            "title": "Part 2: Essay",
            "instruction": "Write an essay on the topic below.",
            "type": "essay",
            "topics": [
                {
                    "topic_number": 1,
                    "title": "Essay Topic",
                    "prompt": """Some people believe that technology has made our lives easier and more convenient. Others argue that technology has created new problems and made life more stressful.

Discuss both views and give your own opinion.

Write between 250-300 words.

In your essay, you should:
- Introduce the topic and state your position
- Discuss arguments for technology making life easier
- Discuss arguments for technology creating problems
- Give your own conclusion based on the evidence

Your essay will be evaluated on:
- Task Achievement: How well you address the question
- Coherence & Cohesion: How well organized and connected your ideas are
- Lexical Resource: Range and accuracy of vocabulary
- Grammatical Range & Accuracy: Variety and correctness of grammar""",
                    "min_words": 250,
                    "max_words": 300,
                    "criteria": {
                        "task_achievement": "Addresses all parts of the task with relevant ideas",
                        "coherence_cohesion": "Information and ideas are logically organized with clear progression",
                        "lexical_resource": "Wide range of vocabulary used accurately and appropriately",
                        "grammatical_range": "Wide range of structures with good control and few errors"
                    }
                }
            ]
        }
    ]
}

# Band Score Descriptors for Writing Assessment
WRITING_BAND_DESCRIPTORS = {
    9: {
        "description": "Expert User",
        "characteristics": [
            "Fully addresses all parts of the task",
            "Uses a wide range of structures with full flexibility and accuracy",
            "Uses vocabulary with full flexibility and precision",
            "Uses cohesion in such a way that it attracts no attention"
        ]
    },
    8: {
        "description": "Very Good User",
        "characteristics": [
            "Covers all requirements sufficiently",
            "Uses a wide range of structures with majority error-free",
            "Uses a wide range of vocabulary fluently and flexibly",
            "Sequences information and ideas logically"
        ]
    },
    7: {
        "description": "Good User",
        "characteristics": [
            "Addresses all parts of the task",
            "Uses a variety of complex structures",
            "Uses sufficient range of vocabulary for clear communication",
            "Presents clear progression throughout"
        ]
    },
    6: {
        "description": "Competent User",
        "characteristics": [
            "Addresses the task, though some parts may be inadequately covered",
            "Uses a mix of simple and complex sentence forms",
            "Uses an adequate range of vocabulary for the task",
            "Arranges information coherently with clear overall progression"
        ]
    },
    5: {
        "description": "Modest User",
        "characteristics": [
            "Addresses the task only partially",
            "Uses only a limited range of structures",
            "Uses a limited range of vocabulary",
            "Presents information with some organization but may lack overall progression"
        ]
    },
    4: {
        "description": "Limited User",
        "characteristics": [
            "Responds to the task only in a minimal way",
            "Uses only a very limited range of structures",
            "Uses only basic vocabulary",
            "May not write in paragraphs"
        ]
    },
    3: {
        "description": "Extremely Limited User",
        "characteristics": [
            "Does not adequately address any part of the task",
            "Attempts sentence forms but errors dominate",
            "Uses only a very limited range of words and expressions",
            "Does not organize ideas logically"
        ]
    },
    2: {
        "description": "Intermittent User",
        "characteristics": [
            "Answer is barely related to the task",
            "Cannot use sentence forms except in memorized phrases",
            "Uses an extremely limited range of vocabulary",
            "Fails to communicate any message"
        ]
    },
    1: {
        "description": "Non User",
        "characteristics": [
            "Answer is completely unrelated to the task",
            "Cannot use sentence forms at all",
            "Can only use a few isolated words",
            "Fails to communicate"
        ]
    }
}

CEFR_LEVELS = {
    "C2": {"min_score": 90, "description": "Mastery - Near-native proficiency"},
    "C1": {"min_score": 80, "description": "Advanced - Effective operational proficiency"},
    "B2": {"min_score": 70, "description": "Upper Intermediate - Independent user"},
    "B1": {"min_score": 55, "description": "Intermediate - Threshold level"},
    "A2": {"min_score": 40, "description": "Elementary - Basic user"},
    "A1": {"min_score": 0, "description": "Beginner - Breakthrough level"}
}
