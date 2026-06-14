"""
Extrai a sequência de aulas (lesson plans) a partir do Teacher's Guide.
Por enquanto cobre apenas o Starter (AEF 0). O syllabus vem do sumário
do TG (páginas 4-7) e as páginas iniciais de cada plano no TG foram
descobertas via PyMuPDF + script de localização.

Também extrai o parágrafo "Lesson plan" do TG (resumo do que a aula cobre).

Saída: data/lessons/<course_id>.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import fitz  # pymupdf

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "lessons"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# Each entry corresponds to one lesson in the order the student studies it.
# - sb_page: book page (atenção: viewer do PDF pode exigir offset; ver UI).
# - tg_page: página do PDF do Teacher's Guide onde o lesson plan começa.
# - file: arquivo (File 1..12). Lessons A/B + PE ou R&C que fecham cada arquivo.
STARTER = [
    # File 1
    {"file": 1, "code": "1A", "type": "lesson",
     "title": "A cappuccino, please",
     "sb_page": 6, "tg_page": 12,
     "topics": {
         "grammar": "verb be (singular): I and you",
         "vocabulary": "numbers 0–10, days of the week, saying goodbye",
         "pronunciation": "/h/, /aɪ/, and /i/",
         "speaking": "introducing yourself; meeting people",
         "listening": "people introducing themselves",
         "reading": ""
     }},
    {"file": 1, "code": "1B", "type": "lesson",
     "title": "World music",
     "sb_page": 8, "tg_page": 16,
     "topics": {
         "grammar": "verb be (singular): he, she, it",
         "vocabulary": "countries",
         "pronunciation": "/ɪ/, /oʊ/, /s/, and /ʃ/",
         "speaking": "talking about where people and things are from",
         "listening": "distinguishing between he and she",
         "reading": ""
     }},
    {"file": 1, "code": "PE1", "type": "practical_english", "episode": 1,
     "title": "Checking into a hotel",
     "sb_page": 10, "tg_page": 20,
     "topics": {
         "function": "checking into a hotel, booking a table",
         "vocabulary": "the classroom",
         "pronunciation": "the alphabet",
         "speaking": "people meeting for the first time"
     }},

    # File 2
    {"file": 2, "code": "2A", "type": "lesson",
     "title": "Are you on vacation?",
     "sb_page": 12, "tg_page": 25,
     "topics": {
         "grammar": "verb be (plural): we, you, they",
         "vocabulary": "nationalities",
         "pronunciation": "/dʒ/, /tʃ/, and /ʃ/",
         "speaking": "talking about nationalities",
         "listening": "understanding short conversations",
         "reading": ""
     }},
    {"file": 2, "code": "2B", "type": "lesson",
     "title": "That's my bus!",
     "sb_page": 14, "tg_page": 29,
     "topics": {
         "grammar": "Wh- and How questions with be",
         "vocabulary": "phone numbers, numbers 11–100",
         "pronunciation": "understanding numbers",
         "speaking": "giving personal information",
         "listening": "understanding numbers; asking for and giving personal information",
         "reading": ""
     }},
    {"file": 2, "code": "R&C 1&2", "type": "review", "covers_files": [1, 2],
     "title": "Review and Check 1 & 2",
     "sb_page": 16, "tg_page": 34,
     "topics": {}},

    # File 3
    {"file": 3, "code": "3A", "type": "lesson",
     "title": "Where are my keys?",
     "sb_page": 18, "tg_page": 35,
     "topics": {
         "grammar": "singular and plural nouns, a / an",
         "vocabulary": "small things",
         "pronunciation": "/z/ and /s/, plural endings",
         "speaking": "things in your bag",
         "listening": "understanding short conversations",
         "reading": ""
     }},
    {"file": 3, "code": "3B", "type": "lesson",
     "title": "Souvenirs",
     "sb_page": 20, "tg_page": 39,
     "topics": {
         "grammar": "this / that / these / those",
         "vocabulary": "souvenirs",
         "pronunciation": "/ð/, sentence rhythm",
         "speaking": "roleplay buying and selling souvenirs",
         "listening": "",
         "reading": "At a souvenir stand"
     }},
    {"file": 3, "code": "PE2", "type": "practical_english", "episode": 2,
     "title": "Buying a coffee",
     "sb_page": 22, "tg_page": 42,
     "topics": {
         "function": "understanding prices, buying lunch",
         "pronunciation": "/ʊr/, /s/, and /k/",
     }},

    # File 4
    {"file": 4, "code": "4A", "type": "lesson",
     "title": "Meet the family",
     "sb_page": 24, "tg_page": 45,
     "topics": {
         "grammar": "possessive adjectives, possessive 's",
         "vocabulary": "people and family",
         "pronunciation": "/ʌ/, /æ/, and /ə/",
         "speaking": "talking about your family and friends",
         "listening": "understanding a conversation",
         "reading": ""
     }},
    {"file": 4, "code": "4B", "type": "lesson",
     "title": "The perfect car",
     "sb_page": 26, "tg_page": 49,
     "topics": {
         "grammar": "adjectives",
         "vocabulary": "colors and common adjectives",
         "pronunciation": "/ɑr/ and /ɔr/, linking",
         "speaking": "talking about cars; discussing preferences",
         "listening": "understanding a conversation",
         "reading": ""
     }},
    {"file": 4, "code": "R&C 3&4", "type": "review", "covers_files": [3, 4],
     "title": "Review and Check 3 & 4",
     "sb_page": 28, "tg_page": 53,
     "topics": {}},

    # File 5
    {"file": 5, "code": "5A", "type": "lesson",
     "title": "A big breakfast",
     "sb_page": 30, "tg_page": 54,
     "topics": {
         "grammar": "simple present + and –: I, you, we, they",
         "vocabulary": "food and drink",
         "pronunciation": "/dʒ/ and /g/",
         "speaking": "talking about meals and food",
         "listening": "people talking about their favorite meal",
         "reading": "Breakfast around the world"
     }},
    {"file": 5, "code": "5B", "type": "lesson",
     "title": "A very long flight",
     "sb_page": 32, "tg_page": 60,
     "topics": {
         "grammar": "simple present ?: I, you, we, they",
         "vocabulary": "common verb phrases 1",
         "pronunciation": "/w/ and /v/, sentence rhythm and linking",
         "speaking": "talking about habits",
         "listening": "understanding a longer conversation",
         "reading": "On the plane"
     }},
    {"file": 5, "code": "PE3", "type": "practical_english", "episode": 3,
     "title": "Telling the time",
     "sb_page": 34, "tg_page": 62,
     "topics": {
         "function": "telling the time",
         "vocabulary": "the time, saying how you feel",
         "pronunciation": "/ɑ/, silent consonants",
     }},

    # File 6
    {"file": 6, "code": "6A", "type": "lesson",
     "title": "A school reunion",
     "sb_page": 36, "tg_page": 65,
     "topics": {
         "grammar": "simple present: he, she, it",
         "vocabulary": "jobs and places of work",
         "pronunciation": "third person -es, sentence rhythm",
         "speaking": "talking about jobs and work",
         "listening": "understanding a longer conversation",
         "reading": "English at work?"
     }},
    {"file": 6, "code": "6B", "type": "lesson",
     "title": "Good morning, goodnight",
     "sb_page": 38, "tg_page": 69,
     "topics": {
         "grammar": "adverbs of frequency",
         "vocabulary": "a typical day",
         "pronunciation": "/y/ and /yu/, sentence rhythm",
         "speaking": "Are you a morning person?; a typical evening",
         "listening": "an interview",
         "reading": ""
     }},
    {"file": 6, "code": "R&C 5&6", "type": "review", "covers_files": [5, 6],
     "title": "Review and Check 5 & 6",
     "sb_page": 40, "tg_page": 74,
     "topics": {}},

    # File 7
    {"file": 7, "code": "7A", "type": "lesson",
     "title": "Have a nice weekend!",
     "sb_page": 42, "tg_page": 75,
     "topics": {
         "grammar": "word order in questions: be and simple present",
         "vocabulary": "common verb phrases 2: free time",
         "pronunciation": "/w/, /h/, /ɛr/, and /aʊ/",
         "speaking": "your weekend",
         "listening": "an interview",
         "reading": "a short newspaper article"
     }},
    {"file": 7, "code": "7B", "type": "lesson",
     "title": "Lights, camera, action!",
     "sb_page": 44, "tg_page": 79,
     "topics": {
         "grammar": "imperatives, object pronouns: me, him, etc.",
         "vocabulary": "kinds of movies",
         "pronunciation": "sentence rhythm",
         "speaking": "talking about movies",
         "listening": "understanding a conversation; people talking about movies",
         "reading": ""
     }},
    {"file": 7, "code": "PE4", "type": "practical_english", "episode": 4,
     "title": "Saying the date, talking on the phone",
     "sb_page": 46, "tg_page": 83,
     "topics": {
         "function": "saying the date, talking on the phone",
         "vocabulary": "months, ordinal numbers",
         "pronunciation": "/θ/",
     }},

    # File 8
    {"file": 8, "code": "8A", "type": "lesson",
     "title": "Can I park here?",
     "sb_page": 48, "tg_page": 87,
     "topics": {
         "grammar": "can / can't",
         "vocabulary": "more verb phrases",
         "pronunciation": "can / can't, /ə/ and /æ/, sentence rhythm",
         "speaking": "talking about what you can and can't do in a town",
         "listening": "taking a driver's test",
         "reading": ""
     }},
    {"file": 8, "code": "8B", "type": "lesson",
     "title": "I ♥ cooking",
     "sb_page": 50, "tg_page": 92,
     "topics": {
         "grammar": "like / love / hate + verb + -ing",
         "vocabulary": "activities",
         "pronunciation": "/ʊ/, /u/, and /ŋ/, sentence rhythm",
         "speaking": "What do you like doing?",
         "listening": "",
         "reading": "tweets about what people like doing alone or with friends"
     }},
    {"file": 8, "code": "R&C 7&8", "type": "review", "covers_files": [7, 8],
     "title": "Review and Check 7 & 8",
     "sb_page": 52, "tg_page": 96,
     "topics": {}},

    # File 9
    {"file": 9, "code": "9A", "type": "lesson",
     "title": "Everything's fine!",
     "sb_page": 54, "tg_page": 97,
     "topics": {
         "grammar": "present continuous",
         "vocabulary": "common verb phrases 2: traveling",
         "pronunciation": "sentence rhythm",
         "speaking": "talking about what people are doing",
         "listening": "understanding a short conversation",
         "reading": "text messages"
     }},
    {"file": 9, "code": "9B", "type": "lesson",
     "title": "Working undercover",
     "sb_page": 56, "tg_page": 101,
     "topics": {
         "grammar": "present continuous or simple present?",
         "vocabulary": "clothes",
         "pronunciation": "/ər/, other vowel sounds",
         "speaking": "talking about clothes",
         "listening": "an interview",
         "reading": "Undercover Boss"
     }},
    {"file": 9, "code": "PE5", "type": "practical_english", "episode": 5,
     "title": "Inviting and offering",
     "sb_page": 58, "tg_page": 105,
     "topics": {
         "function": "inviting and offering",
         "pronunciation": "sentence rhythm",
     }},

    # File 10
    {"file": 10, "code": "10A", "type": "lesson",
     "title": "A room with a view",
     "sb_page": 60, "tg_page": 108,
     "topics": {
         "grammar": "there's a… / there are some…",
         "vocabulary": "hotels, in, on, under",
         "pronunciation": "/ɪr/ and /ɛr/",
         "speaking": "describing rooms",
         "listening": "hotel facilities",
         "reading": "Vermont, US and \"Champ\" the monster"
     }},
    {"file": 10, "code": "10B", "type": "lesson",
     "title": "Where were you?",
     "sb_page": 62, "tg_page": 112,
     "topics": {
         "grammar": "simple past: be",
         "vocabulary": "in, on, at",
         "pronunciation": "was and were, sentence rhythm",
         "speaking": "Where were you yesterday?",
         "listening": "a police interview",
         "reading": ""
     }},
    {"file": 10, "code": "R&C 9&10", "type": "review", "covers_files": [9, 10],
     "title": "Review and Check 9 & 10",
     "sb_page": 64, "tg_page": 116,
     "topics": {}},

    # File 11
    {"file": 11, "code": "11A", "type": "lesson",
     "title": "A new life in the US",
     "sb_page": 66, "tg_page": 117,
     "topics": {
         "grammar": "simple past: regular verbs",
         "vocabulary": "regular verbs",
         "pronunciation": "regular simple past endings",
         "speaking": "talking about past activities and events",
         "listening": "We followed our dream",
         "reading": "We followed our dream"
     }},
    {"file": 11, "code": "11B", "type": "lesson",
     "title": "How was your day?",
     "sb_page": 68, "tg_page": 121,
     "topics": {
         "grammar": "simple past irregular verbs: get, go, have, do",
         "vocabulary": "verb phrases with get, go, have, do",
         "pronunciation": "sentence rhythm",
         "speaking": "talking about yesterday",
         "listening": "understanding a conversation",
         "reading": "Life in a day"
     }},
    {"file": 11, "code": "PE6", "type": "practical_english", "episode": 6,
     "title": "Asking for and giving directions",
     "sb_page": 70, "tg_page": 125,
     "topics": {
         "function": "asking for and giving directions",
         "vocabulary": "prepositions of place",
         "pronunciation": "sentence rhythm and polite intonation",
     }},

    # File 12
    {"file": 12, "code": "12A", "type": "lesson",
     "title": "Strangers on a train",
     "sb_page": 72, "tg_page": 128,
     "topics": {
         "grammar": "simple past: regular and irregular verbs",
         "vocabulary": "regular and irregular verbs",
         "pronunciation": "irregular verbs",
         "speaking": "re-telling a story",
         "listening": "Strangers on a train",
         "reading": "Strangers on a train"
     }},
    {"file": 12, "code": "12B", "type": "lesson",
     "title": "Review the past",
     "sb_page": 74, "tg_page": 131,
     "topics": {
         "grammar": "simple past review",
         "vocabulary": "review of past verb forms",
         "pronunciation": "review of vowel sounds",
         "speaking": "oral review of the simple past",
         "listening": "",
         "reading": ""
     }},
    {"file": 12, "code": "R&C 11&12", "type": "review", "covers_files": [11, 12],
     "title": "Review and Check 11 & 12",
     "sb_page": 76, "tg_page": 132,
     "topics": {}},
]


from build_syllabus import parse_syllabus
from build_wb_index import build_all as build_all_wb
from music_suggestions import MUSIC

# WB page mappings parsed from each course's WB.pdf TOC.
WB_PAGES = build_all_wb()

OTHER_COURSES = [
    ("elementary",         "Elementary",         "A1/A2",  "AEF 1 elementary"),
    ("pre-intermediate",   "Pre-Intermediate",   "A2/B1",  "AEF 2 pre-intermediate"),
    ("intermediate",       "Intermediate",       "B1",     "AEF 3 intermediate"),
    ("upper-intermediate", "Upper-Intermediate", "B2",     "AEF 4 upper-intermediate"),
    ("advanced",           "Advanced",           "C1",     "AEF 5 advanced"),
]


def _build_course_dict(cid: str, title: str, cefr: str, folder: str) -> dict:
    base = ROOT / folder
    sb = base / "SB.pdf"
    tg = base / "TG.pdf"
    if not tg.exists():
        tg = base / "TB.pdf"   # Upper-Int / Advanced
    wb = base / "WB.pdf"
    lessons = parse_syllabus(tg, cid)
    wb_pages = WB_PAGES.get(cid, {})
    for l in lessons:
        l.setdefault("tg_page", 0)
        l.setdefault("topics", {})
        if l["code"] in wb_pages:
            l["wb_page"] = wb_pages[l["code"]]
    return {
        "id": cid,
        "title": title,
        "cefr": cefr,
        "sb_pdf_path": f"{folder}/{sb.name}",
        "tg_pdf_path": f"{folder}/{tg.name}",
        "wb_pdf_path": f"{folder}/{wb.name}",
        "lessons": lessons,
        "sb_pdf_offset": 1,
        "tg_pdf_offset": 0,
        "wb_pdf_offset": 0,
    }


COURSES = {
    "starter": {
        "id": "starter",
        "title": "Starter",
        "cefr": "A1",
        "sb_pdf_path": "AEF 0 starter/SB.pdf",
        "tg_pdf_path": "AEF 0 starter/TG.pdf",
        "wb_pdf_path": "AEF 0 starter/WB.pdf",
        "lessons": STARTER,
        "sb_pdf_offset": 1,
        "tg_pdf_offset": 0,
        "wb_pdf_offset": 0,
    }
}

# Plug the WB page mapping into the hardcoded Starter syllabus too.
_starter_wb = WB_PAGES.get("starter", {})
for l in STARTER:
    if l["code"] in _starter_wb:
        l["wb_page"] = _starter_wb[l["code"]]

for cid, title, cefr, folder in OTHER_COURSES:
    COURSES[cid] = _build_course_dict(cid, title, cefr, folder)


# ---- Summary extraction from TG --------------------------------------

LESSON_PLAN_RE = re.compile(r"\bLesson\s*plan\b", re.IGNORECASE)
END_RE = re.compile(
    r"\bMore\s+materials\b|\bOPTIONAL\s+LEAD-?IN\b|"
    r"^\s*\d+\s*\t?[A-Z][A-Z &]{2,}|"
    r"^\s*[123456]\s+[A-Z]",
    re.MULTILINE,
)


def clean_paragraph(text: str) -> str:
    """Collapse soft line breaks within paragraphs; keep paragraph breaks."""
    parts = re.split(r"\n\s*\n", text)
    out: list[str] = []
    for part in parts:
        joined = re.sub(r"\s+", " ", part).strip()
        if joined:
            out.append(joined)
    return "\n\n".join(out)


STUDENT_VOICE_SUMMARIES: dict[str, dict[str, str]] = {
    "starter": {
        "1A": "In this first lesson, you'll learn how to introduce yourself, give basic greetings, and use the I and you forms of the verb be in positive and negative sentences, questions, and short answers. The context is a coffee shop where people are asked their names — which then get written on their cups — and where two strangers meet for the first time. The lesson opens with a dialogue that leads into the grammar presentation. You then learn the numbers 0–10, and in Pronunciation you're introduced to the American English File system of teaching English sounds, starting with three: /h/, /aɪ/, and /i/. Everything comes together in a Speaking activity where you practice introducing yourself. The lesson wraps up with the days of the week and ways of saying goodbye.",
        "1B": "The topic of this lesson is world music, which sets the context for learning the names of countries and the grammar of he, she, and it with the verb be. You first meet the vocabulary through music, then expand your country words in the Vocabulary Bank and practice asking where people are from and where places are. He is, she is, and it is are presented in Grammar through a conversation about where different musicians are from. In Pronunciation, you're introduced to four new sounds: /ɪ/, /oʊ/, /s/, and /ʃ/. The lesson closes with practice distinguishing the pronunciation of he vs. she, and identifying the nationality of different people and things connected to music.",
        "PE1": "This is the first of six Practical English lessons (one every other File) that teach you the basic functional language you need to \"survive\" in an English-speaking environment. Everything in these lessons is built around video. Here you learn the alphabet and how to spell your name. In Vocabulary, you pick up the words for things in the classroom and useful classroom language. You then learn how to check into a hotel and how to book a table at a restaurant — two contexts that also practice spelling your name. The lesson closes with a focus on all the useful phrases you've just seen. The functional conversations follow two recurring characters: Rob Walker, a British journalist based in London, and Jenny Zielinski, an American living in New York who works at the same company as Rob. They'll reappear throughout the American English File series.",
        "2A": "The lesson centers on a dialogue where an American couple meets a British couple at an outdoor restaurant. You'll complete your knowledge of the verb be by studying the positive, negative, and question forms for we, you, and they. You start by learning the nationality adjectives for the countries you saw in 1B. The pronunciation focus is on three new sounds (/dʒ/, /tʃ/, and /ʃ/) that come up in those nationality words. The grammar is then presented through the dialogue, which continues into the Reading and Listening, reinforcing the new language and a few useful phrases. Finally, in Speaking, you practice asking about the nationality of different people and things.",
        "2B": "The topic of this lesson is personal information, set in a language school. You start by listening to two conversations that frame how to ask for and give personal information, introduce people, and ask how someone is. This is followed by a grammar focus on question words and word order in questions. In Vocabulary, you learn how to say phone numbers and numbers from 11–100. Pronunciation then drills the difference between pairs of numbers that sound similar (e.g., 13 vs. 30), and a listening reinforces your understanding. In Writing, you focus on words related to personal information (address, zip code, married, etc.) and practice filling out a form with your own data. Other questions like How old are you? and Are you married? are practiced in a speaking exercise where you take on a role. The lesson ends with a video about a language school.",
        "3A": "This lesson is about things people normally carry around, and how to form and use singular and plural nouns. You start in Vocabulary with the words for common small objects. In Grammar, real information about things people lose every day sets the context for learning plural nouns. You also learn the difference between a and an (articles were briefly introduced back in Practical English 1's Vocabulary Bank). The pronunciation focus is first on the /z/ sound, then on the plural endings /z/, /s/, and /ɪz/. In a listening activity, you hear short announcements and conversations where the objects mentioned help you figure out what's happening. The lesson ends with a speaking activity: you try to identify things from the Vocabulary Bank photographed from strange angles, and then talk about what's in your pocket or bag.",
        "3B": "The topic is buying souvenirs. A photo of a souvenir stall in New York teaches you the vocabulary for typical souvenirs. A conversation between a tourist and the vendor introduces the grammar of demonstrative pronouns: this, that, these, and those. In Pronunciation, you practice the voiced th sound /ð/ used in those pronouns, plus sentence rhythm. Everything comes together in a final speaking activity where you role-play buying and selling souvenirs.",
        "PE2": "In this lesson, you learn how to ask for food and drink in a restaurant or café, and how to say prices in pounds, dollars, and euros. You also review asking how much something is, from the previous lesson. The pronunciation focus is on /ʊr/, /s/, and /k/ — sounds you need to get right to pronounce the currencies correctly. The language for ordering food and drink is presented through Rob buying lunch in a London pub. You then practice buying a drink and something to eat from the same menu. The language is reinforced through listening to Jenny and her friend buying lunch in a New York deli. The lesson closes with a focus on the useful phrases you've seen.",
        "4A": "The topic is the family. You start by learning the words for people and family members in the Vocabulary Bank, plus a few irregular plurals. The new vocabulary is reinforced by the pronunciation section, which highlights common sounds in the new words. In Grammar, possessive adjectives and the possessive 's are presented through a conversation where Sarah, a babysitter, arrives at a couple's house and is introduced to the family. In the second half of the lesson, you listen to an American woman showing her birthday card to a Mexican friend and explaining who signed it. The lesson ends with you talking and writing about your own family.",
        "4B": "This lesson uses the context of a son and his elderly mother buying a car to teach you common adjectives and how to use them. The vocabulary load up front is quite high — both colors and adjectives — though as a beginner you may already know some of these words. From there you move on to the grammar of adjectives, which is fairly straightforward. Pronunciation focuses on the sounds /ɑr/ and /ɔr/ and on how words are linked in English, which will help you understand fluent speech where words run together. You then use adjectives in a speaking activity to talk about your preferences. The lesson ends with a video about the Beaulieu Motor Museum.",
        "5A": "The context is what people have for breakfast and how important the meal is. You start by reviewing food and drink words you've already met, then go to the Vocabulary Bank to expand them. You read an article where different people talk about their breakfasts, and that article is used to present the I, you, we, and they forms of verbs in the simple present. You then listen to three people talking about their favorite meal of the day — where they have it and what's on the plate. In Pronunciation, you get more practice with word stress and consonant sounds. The lesson builds to a speaking activity where you talk about your eating habits and what people eat in your country. You wrap up by writing a paragraph about your own typical breakfast.",
        "5B": "The focus is on forming questions in the simple present using I / you / we / they with some common verb phrases. A conversation between a British woman and an American woman traveling on a plane provides the context: you first review positive and negative forms of I, we, you, and they in the simple present, then meet the grammar of question formation. After the grammar presentation and practice, you go to the Vocabulary Bank to learn a group of common verb phrases, which are then recycled in the listening (the two women from earlier meet again on the return flight). In Pronunciation, you focus on the consonant sounds /w/ and /v/, and practice sentence rhythm and linking. Finally, everything comes together in a speaking activity where you ask and answer questions about lifestyle, before writing a few sentences about yourself.",
        "PE3": "In this lesson, you'll learn how to tell the time. In most languages there are two ways: digital (hour + minutes), e.g., seven forty, six twenty, and analog (minutes before/after the hour), e.g., twenty to six, twenty past six. You'll hear both if you travel to an English-speaking country, but the focus here is on the more common analog form. (It's worth knowing the digital form too, so you can recognize it when you hear it.) After learning and practicing telling the time, you focus on words with silent consonants such as half and Wednesday. The next vocabulary focus is on a few adjectives describing how you feel. After listening to Jenny and her friend Amy on a night out, you practice some useful phrases.",
        "6A": "This lesson introduces the third person singular (he, she, it) of the simple present. It's the only verb form in the present tense that's different: the verb ending changes (+ -s or -es, e.g., works, teaches), and questions and negatives use a different auxiliary (does / doesn't). For that reason, a whole lesson is devoted to this point — as a beginner you'll need time to assimilate it. The context is a school reunion. The new grammar is presented through a conversation between two old school friends gossiping (not always sympathetically) about classmates they haven't seen for years. This leads into Pronunciation, where you practice the three possible third-person -s sounds: /s/, /z/, and /ɪz/. In Vocabulary, you learn the words for some common jobs and places of work (e.g., in an office). You then read about people who use English in their work, like a Spanish waiter serving tourists in Madrid. A second pronunciation focus covers sentence rhythm, and then you talk about the jobs of two people you know and whether they use English at work. The lesson ends with you writing a couple of paragraphs about those two people.",
        "6B": "The context is daily routine. The lesson opens with a questionnaire, Are you a morning person?, about typical morning activities. This leads into the vocabulary for talking about daily routines and a grammar focus on adverbs of frequency. You'll work with the four most common ones — always, never, usually, and sometimes — and learn their position with the simple present (other frequency adverbs, and their position after be, come in Level 1). Pronunciation focuses on the /y/ sound (e.g., usually) and on sentence rhythm. You then reinforce the grammar and vocabulary in a speaking and writing activity: first you talk about your typical evening, then you write about your typical morning. The lesson ends with a video about a day in the life of a tour guide in New York.",
        "7A": "The topic is sports and other free-time activities. The lesson opens with an article about what Americans do on the weekend, followed by an interview with an American woman talking about her typical weekend. In Vocabulary, you learn more common verb phrases to describe free-time activities. In Grammar, the focus is on word order in questions (both with the verb be and with the simple present of other verbs). Pronunciation covers four more sounds: /w/, /h/, /ɛr/, and /aʊ/. The lesson ends with a speaking activity where you use the new grammar and vocabulary to talk about what you do on the weekend.",
        "7B": "Actors on a movie set provide the context for introducing imperatives and object pronouns. The lesson opens with a conversation where two actors play a scene and the director gives them instructions — letting you see the new grammar in context before going to the Grammar Bank to practice it. In Vocabulary, you learn words for different movie genres (comedy, drama, etc.). You then listen to five people talking about the Alien movies and their actors, with more practice of object pronouns. This leads into Pronunciation, where you practice sentence rhythm in conversations similar to the listening. The lesson ends with you giving your own opinions about actors, actresses, and movies.",
        "PE4": "In this lesson, you learn how to say the date in English. You start with the months of the year, then move on to ordinal numbers (presented through a general-knowledge quiz), and finally how to say the date itself. Since this is the Starter level, you're taught just one form — May first (rather than the first of May). Saying the year is left for Level 1. You then listen to a phone conversation between Rob and Jenny that involves understanding various dates, and you pick up some useful phrases along the way.",
        "8A": "Can is a very versatile verb in English: it expresses ability, possibility, and permission, and it makes requests. This lesson focuses on two of its most common uses: permission and possibility. Can for ability is mentioned briefly in the Grammar Bank, but you'll work on it properly in Level 1. The lesson opens with a text about driver's tests and licenses in different countries. The grammar is presented through a series of tweets and a conversation about a young woman learning to drive. Pronunciation focuses on sentence rhythm and on can / can't — especially the tricky difference between the positive and negative forms. The vocabulary focus is on more verb phrases, especially those used in permission / possibility contexts (e.g., pay, park). You finish by role-playing conversations between tourists and locals about what people can or can't do in your town, then writing a few sentences with useful information for tourists.",
        "8B": "This lesson focuses on free-time activities. After learning common free-time activities in Vocabulary (swimming, traveling, and so on), the grammar (like / love / hate + verb + -ing) is presented through a dating website. In Pronunciation & Speaking, you practice the short and long vowel sounds /ʊ/ and /u/, the /ŋ/ sound, and sentence rhythm. You then say whether you like the activities from the Vocabulary section. You read tweets in which people around the world say what they like doing alone and with friends, and write your own tweet. The lesson ends with a video about a gospel choir.",
        "9A": "In this lesson, you learn a new verb form — the present continuous, used to talk about actions happening now. The lesson opens with the new grammar presented through a phone call between a woman on a business trip and her husband at home. In Pronunciation, you practice sentence rhythm in present continuous sentences. In Vocabulary, you learn common verb phrases related to travel, then listen to some short travel-related conversations. In Reading, you read and match messages sent between two people trying to meet at the movie theater. The lesson ends with a Communication activity in which you describe pictures.",
        "9B": "This lesson helps you understand the difference between the present continuous and the simple present. It opens with a reading activity based on an episode of the TV show Undercover Boss (where a boss works \"undercover\" to check on his workers), which leads into the grammar presentation. In Vocabulary & Pronunciation, you learn some common items of clothing and practice the /ər/ sound. You then listen to a student who is doing an internship in a clothing store. Finally, the new grammar and vocabulary come together in a speaking activity where you talk about the clothes you're wearing right now and the clothes you wear in different seasons or for particular occasions.",
        "PE5": "In this Practical English lesson, you learn to make invitations and offers using Would you like…? and to accept or decline them politely. These skills are presented through informal social conversations: Rob invites a friend to a soccer game, and once there offers to buy food and a drink. In Pronunciation, you practice making invitations and offers using Would you like…?, focusing on sentence rhythm. Continuing the invitation theme, you then watch or listen to Jenny meeting her ex-boyfriend in the street. In Speaking & Writing, you practice inviting people to a party and accepting or declining an invitation — first orally, then in writing.",
        "10A": "The topic is hotels. The lesson opens with tourist information about Burlington, Vermont and Lake Champlain. You then learn vocabulary related to hotel rooms and hotels. The new grammar (there's a… / there are some…) is presented through a conversation between a couple on vacation and a hotel receptionist. The receptionist shows the couple their room in a real hotel next to Lake Champlain (whose website you can visit), and they talk about what is and isn't in the hotel and the surrounding area. In Pronunciation, you practice the sounds /ɪr/ and /ɛr/. In Vocabulary & Speaking, you learn the prepositions in, on, and under. The lesson ends with a speaking activity where you use prepositions to describe the location of objects in hotel rooms.",
        "10B": "The grammar (was / were) is presented through an interview between a detective and a suspected bank robber. You then listen to the same detective interviewing the suspect's friend, and you find out whether the suspect is guilty or not. The vocabulary focus is on prepositions with places — in, on, at (e.g., in bed, on a bus, at school). In Pronunciation & Speaking, you practice the strong and weak forms of was and were, plus sentence rhythm. Grammar, pronunciation, and vocabulary come together when you ask and answer questions about where you were at various times the day before. The lesson ends with a video about buildings with an interesting history.",
        "11A": "The context is a family that moves from London to North Carolina for a year. The grammar is presented through a short text and listening about their move. You then focus closely on the different pronunciations of the -ed ending and practice the grammar and pronunciation in a speaking activity. The lesson closes with a reading and a listening about the family's year in the US, and you talk about people you know who have lived or studied abroad.",
        "11B": "This lesson introduces the simple past of the four most common irregular verbs in English: get, go, have, and do. It opens by reviewing verb phrases with those four verbs. You then listen to a conversation between a father who arrives back early from a work trip and his teenage daughter, whom he's surprised to find at home. The grammar is presented using extracts from that conversation. In Pronunciation & Speaking, you focus on sentence rhythm in past questions and answers, and use it to talk about what you did yesterday. You then read an article about a movie, A Life in a Day, made from videos showing life around the world on one particular day. The lesson ends with you writing a blog post about what you did yesterday, using then, after that, and after.",
        "PE6": "In this Practical English lesson, you learn how to understand and give simple directions in the street. You start with six new prepositions of place and some very basic language for directions, practiced through a role play. The focus is more on asking for and understanding directions than on giving them, since giving directions is quite challenging at this level. You watch or listen to Rob asking for directions, and then to a conversation with Jenny where she explains where her hotel is and how to get there.",
        "12A": "In this lesson, you review the simple past (regular and irregular verbs) and learn some more irregular verbs in the context of a short story with a surprise ending about two strangers who meet on a train. In Vocabulary & Pronunciation, you learn some new high-frequency irregular verbs. You then read and listen to the first two parts of the story. In Grammar, you review the simple past of regular and irregular verbs (including the past of the verb be) and retell Parts 1 and 2 of the story. You then watch a video of Parts 3, 4, and 5 — the final section of the story is on video.",
        "12B": "This final lesson is a board game that reviews the simple past out loud. You answer 30 questions covering the grammar of the simple past plus related vocabulary and pronunciation.",
    },
    "elementary": {
        "1A": "The context of this first lesson is a young man who meets a woman at a salsa class. He then introduces her to his friend, who clearly likes her and joins the class. The lesson opens with five conversations where you practice basic greetings and asking names. You then focus on the grammar of the verb be in positive sentences and on subject pronouns. In Pronunciation, you're introduced to word stress and the American English File system of teaching English sounds, starting with six vowel sounds. A vocabulary focus covers the days of the week and the numbers 0–20, and the lesson closes with a listening and speaking activity that pulls all the strands together.",
        "1B": "The context of this lesson is the Olympics, a time when people from many nationalities gather in one place. You complete your study of the verb be and learn how to say where you and other people are from. You start by learning vocabulary for countries and nationalities, and practice that language in a world quiz. Pronunciation then covers the schwa /ə/ — a sound that shows up in many English words — and three consonant sounds that can be tricky depending on your native language. The Grammar section (be in negative sentences and questions) is presented through three interviews between a journalist and sports fans from different countries. You then practice asking where people are from. A second Vocabulary section introduces numbers 21–100, and a Pronunciation and Listening section focuses on word stress in numbers and practices them through listening and playing Bingo.",
        "1C": "The context for this lesson is the classroom and signing up for an English course. The lesson opens with classroom language, which helps you understand and respond to common classroom instructions and ask the teacher for information and clarification in English. You then learn the pronunciation of the alphabet and practice it with common abbreviations. You listen to a Skype interview with a student and a teacher at a language school in the United States and learn how to give personal information and spell. This leads into the grammar focus on possessive adjectives. Everything comes together in the final activities: a communication task where you discover the real names of some actors and singers, and a writing focus where you complete an application form for a visa.",
        "PE1": "This is the first of six Practical English lessons (one every other File) that teach you functional language for travel and social situations. The content is built around video, with an audio version available too. There's a storyline with two recurring characters: Rob Walker, a British journalist for a magazine called London 24seven, and Jenny Zielinski, who works in the New York office of the same magazine and is on a work trip to London. You meet them for the first time in this lesson, when Jenny arrives in the UK and checks into a hotel. The focus is on hotel vocabulary and the language of checking in. In the You say sections, you'll watch or listen and then repeat what the speakers say.",
        "2A": "Two rooms — one very neat, one very messy — where the well-known authors Virginia Woolf and Ian Rankin wrote their books provide the context for both vocabulary and grammar. You start by looking at photos of these rooms, full of objects, and then learn more words for everyday things. You then learn the grammar of singular and plural nouns and focus on the pronunciation of final -s or -es in plurals. A second vocabulary focus covers how to use in, on, and under, and everything is practiced in Speaking and Listening.",
        "2B": "Iconic aspects of the US introduce common adjectives and their grammatical position, and you learn to give simple descriptions. You start with a vocabulary focus on common adjectives. The grammar of adjectives is presented through a quiz about American icons that includes familiar adjective + noun phrases such as the White House and New York. After grammar practice, you move on to a pronunciation focus on long and short vowel sounds, which also recycles the adjectives. You then do a picture-difference activity, before reading an article about the differences between British and American English.",
        "2C": "You start by learning adjectives that describe states and feelings (e.g., hungry, happy). You then listen to a series of conversations between a couple with a baby driving on vacation — the husband gets increasingly irritated, the child tired and hungry, as the trip goes on. This sets the context for more imperatives (you've already met some in Classroom language) and for making suggestions starting with Let's…. A speaking activity has you role-play different situations and ask each other what's wrong. A pronunciation focus on connected speech helps you understand native speakers, and the lesson ends with a video listening about safe car trips.",
        "3A": "Different aspects of life in the United States provide the context for meeting the simple present for the first time. You start by learning a group of common verb phrases, then read a short text where an engineer writes what she likes about the United States — that's where you see how verb forms change for positive and negative sentences and in the third person singular (question forms come separately in 3B). You then practice the pronunciation of verb + -s or -es, plus the vocabulary and grammar, talking about yourself and about a partner. The lesson ends with Reading and Speaking: you read a text adapted from an American newspaper in which Americans who live abroad say what they think about other countries, and you compare it with what you think about your own country.",
        "3B": "The topic is jobs and work. You start by reading an interview that presents simple-present questions in both second and third person singular (Do you…? Does he…?). You then learn the vocabulary for common jobs and how to say what you do. A pronunciation focus covers the /ər/ sound. You listen to a radio program where competitors try to guess first a man's job, then his wife's. You then practice by asking simple-present questions about imaginary jobs, and the lesson finishes with asking third-person questions to guess someone's job.",
        "3C": "The lesson opens with a listening in which two characters, Becca and Dave, meet for the first time — a context for asking lots of questions to get to know someone. You then look at the grammar of word order in questions, especially those starting with question words. A vocabulary stage reviews and expands your knowledge of question words, and in Pronunciation you practice the rhythm of questions. A Speaking activity has you ask a variety of questions, and the lesson ends with Writing as you learn to write a personal profile.",
        "PE2": "In this lesson, you learn to tell the time and how to order a coffee (or other drink) in a coffee shop or bar. The Rob and Jenny story develops: they meet at the hotel and go to buy take-out coffee. They then go to the office, where Jenny meets Karen, the administrator, and Daniel, the boss.",
        "4A": "The main context is pictures of people in the public eye photographed with a family member or partner who isn't well known — a natural setup for the grammar of the possessive 's (e.g., Who is he? He's Brad Pitt's brother.) and the question word Whose…?. You then learn the vocabulary of family members, which leads into a focus on the /ʌ/ sound and the most common pronunciations of the letter o. The lesson ends with you listening to a woman showing her friend photos of her family, and then doing the same yourself.",
        "4B": "This lesson is based on the daily routine of two real people with busy lives: Marjan Jahangiri, a professor of cardiac surgery in London (the article about her appeared in The Sunday Times), and her son Darius, who is in his last year of high school. You start by learning verb phrases for talking about daily routines. A pronunciation focus on linking helps you understand spoken English. You then read about Marjan's day and listen to an interview with her son, and decide whose day is more tiring. A grammar focus covers prepositions of time and place, which are common when describing a typical day. The lesson ends with a Speaking activity where you talk about your typical weekdays, then write a description of your favorite day of the week. This lesson also reviews telling the time (covered in Practical English Episode 2).",
        "4C": "The topic is lifestyle choices that may determine whether you have a longer or shorter life. You start by learning the vocabulary for months and adverbs and expressions of frequency. A recent study investigating why American teenagers may not live as long as their parents provides the context for learning the word order with adverbs and expressions of frequency. Pronunciation focuses on the letter h. In the second half, you read about the so-called \"Blue Zones\" — five places in the world with very high proportions of centenarians — and about the lifestyles in two of them, comparing them to your own country. The lesson ends with a video listening about a third Blue Zone, Okinawa, in Japan.",
        "5A": "This lesson is based on TV shows like The X Factor, where amateur musicians compete in the hope of winning and becoming famous. You start with more verb phrases. Then a picture story of a contestant waiting for her first audition (based on a real participant's blog) introduces sentences with can. Can is a very versatile verb in English, used to express ability, possibility, permission, and to make requests. You've already met can for requests and permission in Practical English 1, so you should be familiar with it. In the second half, special attention goes to the pronunciation of can and can't when stressed and unstressed. You then practice orally with a questionnaire.",
        "5B": "The first part of this lesson is based on an online forum about noisy family members and neighbors. You start by learning new verbs and verb phrases, and talk about noise problems in your family or with your neighbors. The present continuous (used for what is happening now or for temporary actions/situations) is presented through conversations between family members and noisy neighbors. Pronunciation focuses on the /ŋ/ sound, which appears in all present continuous endings. You then do a \"spot the differences\" Speaking activity that practices the new grammar. The lesson ends with you listening to six conversations and guessing what the people are doing.",
        "5C": "The main context is Chicago — first its weather, then some unusual tourist attractions. If you haven't visited the US, you might think of Chicago as a windy city; here you learn the real facts about its climate. You start by learning basic vocabulary for talking about the weather and listen to a travel guide describing typical Chicago weather. The Grammar (simple present or present continuous) is presented through messages between friends in different places around the world. You then read an online guide that recommends what to do in Chicago in different seasons. Pronunciation helps you pronounce and recognize famous place names in Chicago, and the lesson finishes with writing — how to write posts about your vacation on a social-networking site.",
        "PE3": "In this third Practical English lesson, you learn some basic clothes vocabulary and key phrases for buying clothes in English. The story develops: Jenny spills Rob's coffee over his shirt, so he has to buy a new one. While he's looking for a shirt, Jenny gets a call from someone named Eddie. Rob comes out of the store, hears the end of her conversation, and wonders who Eddie is. When Jenny sees the shirt he's chosen, she insists he goes back to change it.",
        "6A": "Beyond its grammar and vocabulary goals, this lesson encourages you to start reading in English — a great way to consolidate and expand what you know. We recommend \"Graded Readers,\" books simplified by level. You first look at people's different reading habits and talk about your own. Object pronouns (me, you, him, etc.) are then presented through Part 1 of a traditional North African story. You then read and listen to Part 2, and listen to the final part, getting more practice with pronouns and possessive adjectives. Vocabulary focuses on learning words through reading. In Pronunciation, you work on three sounds (/aɪ/, /ɪ/, and /i/), which sets up the speaking activity. Finally, you retell the story playing one of the two main characters.",
        "6B": "The main vocabulary focus is how to say the date. You start by reviewing the months, then learn ordinal numbers, followed by a Listening on identifying ordinal numbers. You then read an online forum where readers answer questions about their favorite month, day of the week, and time of day. The grammar focus is like, love, etc. + the -ing form, and you talk about which free-time activities you like and dislike. The lesson ends with you interviewing a partner about their favorite or least favorite month/day/week, then writing about your own favorite times.",
        "6C": "This lesson, the last of the first half of the book, uses the topic of music to review the uses of be and do. You start with the vocabulary of musical instruments and musicians. You then use a music questionnaire to interview a partner about their musical tastes and habits. After reviewing the grammar, Pronunciation focuses on the /y/ sound, including the \"hidden\" /y/ in words like music, plus stress on words used to give opinions. You listen to a program about a street performer in London. The lesson finishes with a visit to the Writing section to learn how to write an informal email.",
        "7A": "This lesson uses self-portraits and selfies to introduce and practice the simple past of the verb be (was / were). The Grammar is presented through an audio guide about Vincent van Gogh. Pronunciation focuses on sentence stress in simple-past statements and questions with was and were. The Reading continues with self-portraits of famous people and then moves into word formation (e.g., music → musician). In Speaking, you discuss whether you take selfies and talk about the selfies and photos on your phone.",
        "7B": "Simple-past regular verbs are introduced through two true stories about flight problems. The lesson opens with a Reading about someone needing to change the last name on their ticket, and then you listen to a story about two people having a problem on the plane. These set up the simple past of regular verbs. A pronunciation focus covers -ed endings. Vocabulary introduces past time expressions, and Grammar, Vocabulary, and Pronunciation come together in the final Speaking activity.",
        "7C": "The topic is New Year's Eve. Three blogs about memorable New Year's Eves (good and bad!) provide the context for introducing simple-past irregular verbs. The vocabulary focus is on common collocations with go, have, and get (e.g., go out, get home). You then listen to a fourth person describing a memorable New Year's Eve in Brazil. Next you work on the stress pattern in Wh- questions in the simple past, which prepares you for the final Speaking and Writing activity: asking about a memorable New Year's Eve and then writing about it.",
        "PE4": "In this lesson, you practice directions. The focus is more on asking for and understanding directions than on giving them, since giving directions is a difficult skill at this level. Rob and Jenny have a free morning, and Rob plans to rent bikes and show Jenny some of London. But then Daniel calls and asks Rob to interview an artist at the Tate Modern. Jenny agrees to meet Rob at the gallery, ventures into London on her own — and gets lost.",
        "8A": "The goal is to review all forms of the simple past — regular and irregular — through a murder story. The lesson opens with a description of the story, introducing the characters and several new past forms of irregular verbs. A pronunciation focus reviews irregular and regular past forms. You then hear more of the story on audio (as a TV adaptation) when the inspector interviews the suspects. You decide who you think the murderer was before hearing what actually happened. After the murder story, a grammar focus pulls together and reviews the simple past. The lesson finishes with an extended Speaking activity where you role-play trying to break down the alibi of a robbery suspect.",
        "8B": "This lesson links back to the murder story in 8A. Many years later, a young couple looking for a house to rent are shown around Jeremy Travers's house by Barbara, his now-elderly daughter. Only after deciding to rent it do they discover the house has a dark secret: someone was murdered there. You start with a vocabulary focus on house and furniture. You then listen to Barbara showing the young couple around the old Travers house, now for rent. You hear how Kim is reluctant to rent the house but is talked into it by her husband, and how when they go to celebrate at the local restaurant they hear the true story. You focus on the grammar in the conversations — the use of there is and there are. The pronunciation focus is on /ɛr/ and /ɪr/, which prepares you for a Speaking activity describing where you live. Finally, in the Writing section you write a description of your house or apartment.",
        "8C": "This lesson is based on real information about a hotel in Los Angeles said to be haunted. An article about the hotel provides the context for practicing there was / there were and prepositions of place and movement. You start by reading the article and listening to two guests describing their experiences of staying near room 924, where the ghosts are said to appear — that's the context for the grammar of there was / there were. The lesson then moves into a vocabulary focus on more prepositions of place and movement (you've already done simple ones like in, on, under, to). Pronunciation focuses on silent letters in words like ghost and guest. You then do a Speaking activity that practices the Grammar and Vocabulary. The lesson finishes with a video listening about Portchester Castle.",
        "9A": "Food and drink provide the context for the grammar of countable and uncountable nouns, plus the related use of a, an, some, and any. You start with a quiz on food and drink words you've already met in Level 1, then go to the Vocabulary Bank to learn more. You read part of a blog where a man describes why he eats the same thing every day; that Reading leads into the grammar focus, which you then practice. You listen to four people describing their dinner the previous night. Pronunciation looks at the vowel combination ea, which can be pronounced in several different ways and shows up in many common food words (e.g., bread, meat, steak). In Speaking, you tell a partner what you ate and drank yesterday, and discuss whether your eating habits are similar.",
        "9B": "This lesson continues the food theme and focuses on sugar and salt — both known at different times in history as \"white gold.\" You start with a vocabulary focus on containers (package, can, etc.). The grammar context is the amount of sugar and salt in some common foods. You learn quantifiers (much, a lot of) and how to ask about quantity (e.g., How much sugar is there in dark chocolate?). Pronunciation covers /ʃ/ and /s/. The reading text Fascinating facts about sugar and salt is based on several recent articles and studies. The lesson ends with you interviewing a partner using a questionnaire to find out how much salt and sugar you eat every day.",
        "9C": "The context is general-knowledge quizzes, which introduce and practice comparative adjectives and high numbers. You start with a vocabulary focus on numbers greater than 100. In Listening, you decide whether some statements are true or false, then listen to a contestant answering the questions on a quiz show. The quiz questions lead into the grammar of comparative adjectives. A pronunciation focus covers stress in comparative sentences and the /ər/ sound in -er endings. In Speaking, you put the grammar and high numbers into practice with a quiz-show role-play. The lesson finishes with a reading text about trivia nights in the UK and US.",
        "PE5": "In this lesson, you learn common vocabulary for menus and practice ordering a meal in a restaurant. In the storyline, Jenny and Rob are chatting in the office when Jenny gets a call from Eddie. Eddie sings \"Happy Birthday\" to Jenny; Rob overhears and takes the chance to invite Jenny out for dinner. But before she can reply, Daniel comes out of his office and invites Jenny to a working dinner that evening.",
        "10A": "A reading text about the most dangerous place in the world to cross the street, plus other geographical superlatives, provides the context for superlative adjectives and the vocabulary of places and buildings. You start with Vocabulary, learning words for buildings and landmarks in a town or city. In Grammar, you make the logical progression from comparatives to superlatives and look at \"extreme\" places in the world (the biggest station, the oldest bridge, etc.). Pronunciation focuses on the consonant groups that turn up in superlatives (e.g., the most expensive), and you then do a role-play about your town using superlatives. An article tells you about the most dangerous place in the world to cross the street. Writing brings the topic home: you write about your own town or city.",
        "10B": "The context is travel and city vacations. The lesson opens with Grammar: be going to for future plans, presented and practiced by listening to and reading about two people who plan to travel to five continents in one day. Pronunciation focuses on sentence stress in going-to sentences. In Listening, you hear an expert from a website called Responsible Travel give advice about how to plan a vacation. In Vocabulary and Speaking, you look at common vacation phrases and then plan your own dream trip. Finally, in Writing you write a formal email booking some accommodations.",
        "10C": "This lesson covers another use of be going to: predictions (what we think or are sure is going to happen). The context is a short story about a fortune-teller, also dramatized on video. You start by discussing fortune-telling and related verb phrases. In Pronunciation, you look at stress in two-syllable words. You read and listen to a short story with a twist at the end, making a series of predictions about the outcome as you go. After the first four parts on audio, you can watch them on video and finally discover what happens. After the story, you look at the grammar of using going to for predictions, and the lesson ends with a fortune-telling activity.",
        "11A": "People's first impressions of a new country provide the context for learning common adverbs of manner and modifiers. The lesson opens with you reading forum posts written by people about what surprised them when they first arrived in the US. This leads into the grammar of forming and positioning adverbs. In Listening, an American man talks about living in Costa Rica, which leads into Pronunciation, focused on understanding connected speech. You then discuss habits and behavior in your own country or city. Finally, you write three short posts about habits in your country that might surprise a visitor.",
        "11B": "This lesson is based on a blog written by a German girl who is passionate about travel and new experiences. In the first half, you read and talk about people's dreams or \"bucket lists.\" In Grammar, you focus on the structure verb + infinitive, common when talking about dreams (e.g., I want to climb a mountain), and learn some common verbs followed by the infinitive. In the second half, you work on the weak pronunciation of to in verb phrases and on sentence stress, and talk about your dreams and plans for the future. The Writing task links back to the reading: you write your own bucket list and compare it with a partner's.",
        "11C": "The topic is phones and the internet. The lesson opens with useful phone- and internet-related language. You then listen to three people saying what they use their phones for, and you do the same. Reading focuses on life before the internet — something you may not have experienced. The grammar focus covers the uses of the definite article, with special attention to the non-use of articles when generalizing (talking about things or people in general). The lesson ends with a Speaking activity reviewing the different uses of articles.",
        "PE6": "In this final Practical English lesson, you learn vocabulary related to transportation and functional language for using public transportation. It's Jenny's final morning in London, and Rob goes to the hotel to say goodbye. Jenny tells him she's shown some of his articles to Barbara, her boss in New York, and that they'd like him to go to New York for a month to write a column for New York 24seven and a daily blog. Rob is excited but asks for time to think. Jenny takes a taxi and then a train to Heathrow but discovers on arrival that she's left her phone in the hotel. Just then, Rob arrives with the phone and tells her he wants to accept Barbara's offer and go to New York. He finally discovers who Eddie is. The story continues in American English File Level 3.",
        "12A": "The topic of movies and TV shows based on books provides the context for introducing the present perfect. The lesson opens with the grammar presented through a conversation about movies, TV shows, and books. Pronunciation focuses on sentence stress, and Vocabulary looks at common irregular past participles. The final Listening and Speaking activity uses a survey about movie, TV, and book experiences, where you learn how to ask present-perfect questions with ever. (In 12B you'll meet other regular and irregular past participles and contrast the present perfect with the simple past.)",
        "12B": "The main context is a conversation between a group of friends about where to go for dinner. One of them has already tried every restaurant the others suggest. Their conversation contrasts the present perfect and the simple past in a natural way: Have you been to…? When did you go? Why did you go there?. The lesson opens with a Listening activity exposing you to both the present perfect (for past experiences) and the simple past, which leads into the grammar focus. In Vocabulary and Pronunciation, you get more practice forming and pronouncing irregular past participles. The lesson ends with a Speaking activity where you ask opening questions in the present perfect with recently and ever, and then simple follow-up questions in the simple past.",
        "12C": "In this final lesson, you review Grammar, Vocabulary, and Pronunciation from the whole course, with a special focus on question formation. The lesson is based on an interview Sir Ian McKellen kindly gave to the American English File authors. You first read the interview and do some comprehension exercises. In Grammar and Speaking, you review question formation before interviewing a partner. Finally, you watch or listen to a show about Judi Dench, an actress who has worked in famous productions with Ian McKellen.",
    },
    "pre-intermediate": {
        "1A": "This first lesson has two main goals: a quick, efficient review of some Level 1 language points, and getting you started with the course routine. The opening exercise sets up an important grammar review: word order in questions. The vocabulary focus is on common verb phrases, which you use to complete questions you'll then ask a partner. You focus on the word order and practice it in the Grammar Bank. The pronunciation of the alphabet is reviewed, and a listening activity gives you the chance to review spelling. You bring everything together by interviewing a partner and completing a form.",
        "1B": "In this lesson, all forms of the simple present are reviewed in detail through a newspaper article: a daughter tries to find a suitable partner for her divorced father. The lesson opens with Vocabulary and Reading. Basic language for physical description is reviewed, and the Vocabulary Bank introduces new language and adjectives of personality. You then read the article about Charlotte's dad, Clint, and focus on the grammar of the simple present. A pronunciation focus covers final -s and -es endings in verbs and nouns. You then read about two possible dates for Clint and decide who you think is the better match. In Listening, you hear Elspbeth, a journalist, talking about a dating experiment in which her mother picked dates for her from a dating app. The lesson ends with you describing a single person in your life — a family member or friend — in detail, and writing a short description.",
        "1C": "The context is a project called Remake, in which modern photographers recreate famous paintings. The images from one example — Vermeer's The Milkmaid and its photographic remake — introduce clothes vocabulary, followed by a pronunciation focus on two common vowel sounds, /ə/ and /ər/. You focus again on the images and answer questions, which leads into the Grammar section: the present continuous for things happening now or around now, and for describing what's happening in a picture. The present continuous is contrasted with the simple present for habitual actions and permanent situations. After the Grammar Bank, a listening activity has you hear an art expert talking about Vermeer and the painting. You then review prepositions of place, and everything comes together in a final speaking activity where you describe two more pairs of paintings and remakes to find the similarities and differences.",
        "PE1": "This is the first of six Practical English lessons (one every other File) that teach you functional language to help you \"survive\" in English in travel and social situations. There's a storyline with two characters: Jenny Zielinski, an American journalist who works in the New York office of a magazine called NewYork 24seven, and Rob Walker, a British journalist who works in London for the same magazine but is now in New York for a month. If you did Level 1, you'll already know them. In the You Say sections, you'll watch or listen and then repeat what the speakers say. If the speaker is Rob, you'll hear a British accent, but you don't need to copy the accent when you repeat his phrases. The main focus of this lesson is describing problems and asking for help.",
        "2A": "The simple past (regular and irregular verbs) is reviewed in detail through the context of vacations, with three stories about trips where people lose something important. You start by reading about Sam, who went on vacation with friends and misplaced his phone. You then listen to a similar story. After that, you thoroughly review the simple past of both regular and irregular verbs, with a pronunciation focus on -ed endings in regular verbs. After learning new vacation vocabulary, you listen to four conversations focusing on showing interest and using \"interested\" intonation. Finally, you interview a partner about your last vacation using a short questionnaire.",
        "2B": "The lesson opens with a photo from a feature in the Guardian called \"That's me in the picture.\" The photo, by the well-known French photographer Henri Cartier-Bresson, shows a couple in a park in Paris. You read an article in which the woman in the photo tells the story behind it. You then focus on vocabulary and the correct use of the prepositions at, in, and on, both for time (review) and place. The story behind the photo also sets up a new structure: the past continuous. You then focus on the weak forms of was and were in the past continuous. This helps you when you listen to a woman describing six photos on her Instagram page. The lesson ends with you talking about your own favorite photos, then writing about one of them.",
        "2C": "You learn to use time sequencers (after that, later, etc.) and the connectors so, because, but, and although, and you review the simple past and past continuous along the way. The context is a short story with a twist. After you've read most of the story and worked on the grammar, a pronunciation focus covers word stress in two-syllable words, and Vocabulary expands your knowledge of verb phrases. In the video listening, the language comes together — you use picture prompts to retell the story so far. You then choose whether to watch or hear a happy or sad ending and find out what happens. Finally, in Speaking, you answer some questions about the ending you chose.",
        "3A": "You review going to (which you met in Level 1) to talk about plans and predictions. The context is a reading and listening based on TripAside, a company that helps travelers make the most of stopovers at airports. The lesson opens with vocabulary related to airports, then a pronunciation focus on the letter g. You read an article about TripAside and listen to a traveler meeting his guide at the airport in Rome. This leads into the grammar review and practice. You then ask and answer questions about your own plans. The lesson ends with a speaking activity where you imagine you work for TripAside and plan a tour for travelers on a stopover at your nearest airport.",
        "3B": "You learn a new use of the present continuous: talking about fixed arrangements. The context continues the story of Jake — the man who went on a guided tour in 3A and was on his way to a conference, hoping to meet up with an ex-girlfriend. The lesson opens with a quiz that tests how organized you are: you answer the questions, calculate your score, and discuss the results. Next comes a vocabulary focus on verbs that are normally followed by prepositions, and a pronunciation focus on linking, to help you understand fast speech. You listen to a conversation between Jake and his ex-girlfriend Sarah in which they make contact — you complete a calendar with Jake's appointments — and arrange to see each other. Finally, you listen to how the meeting went. After focusing on the grammar, you practice making arrangements in a speaking activity. The lesson ends with Writing: you use the grammar and vocabulary to write an email about travel arrangements.",
        "3C": "The topic is word games. First, simple defining relative clauses are introduced through a TV game show where contestants complete an alphabet wheel by saying the right word for each letter. This context shows you how relative clauses help with the essential skill of paraphrasing. After practicing the grammar, you learn other useful phrases for keeping a conversation going when you don't know the exact word. You then play the alphabet game with letters A–E only. The pronunciation focus is on how the silent e at the end of words (site, fate, etc.) changes the preceding vowel sound. Finally, you define words to a partner to complete a crossword.",
        "PE2": "In this lesson you practice ordering food and explaining there's a problem. The Rob and Jenny story develops: Jenny shows Rob around the New York office and introduces him to Barbara, the boss. Jenny and Rob then go out for lunch, and Holly — Jenny's colleague — joins them and takes over the conversation!",
        "4A": "This lesson presents the present perfect for talking about the recent past, and you learn to use it with yet and already. If you came from Level 1, you'll have seen the present perfect (but not yet and already); otherwise this is completely new. The context is housework. You start by reading and discussing two articles about housework. A vocabulary focus covers common verb phrases for housework and collocations with make and do. In a speaking activity, you discuss who does the housework in your country and whether you do any yourself. The grammar is then presented through three short conversations between family members about housework. Pronunciation focuses on the letters y and j (as in yet and jet). The lesson ends with a listening that gives tips on how to clean quickly and efficiently.",
        "4B": "You look at the present perfect for past experience with ever / never, and contrast it with the simple past. The context is shopping. You start with a speaking activity about global chain stores and a vocabulary focus on shopping. A pronunciation focus covers different ways of pronouncing the letters c and ch. You then listen to five people answering questions about shopping — that's where the grammar is presented. In Speaking, you do a mingle activity asking other people shopping-related Have you ever…? questions and following up with simple-past questions. The lesson ends with an article explaining why we often find areas with lots of the same kinds of stores.",
        "4C": "You learn how to use something, anything, nothing, etc. These words are likely familiar already, but here the grammar is focused on in detail. The context is the weekend. You start by reading an article about how many people on social media invent what they did on the weekend to make it sound more exciting. In Vocabulary, you focus on the difference between -ed and -ing adjectives. The grammar focus follows, and then you focus on three vowel sounds so you can pronounce the key grammar expressions correctly. You then answer questions about your own weekends, with one of your answers being invented. The lesson ends with a video listening about the history and possible future of the weekend.",
        "5A": "You review comparative adjectives and learn to use comparative adverbs and the structure (not) as…as to compare things. The context is recent research showing how fast the pace of life has become. You start by answering a questionnaire about how fast your life is, then read an article and infographic about the effects of the increasing pace of life. Vocabulary focuses on types of numbers (fractions, dates, percentages, etc.) that you've just seen in the infographic. The grammar is presented and practiced, with a pronunciation focus on the /ə/ sound in unstressed syllables and words. You then listen to five people talking about an aspect of their lives that has changed over the last three years, and answer the same questions about your own life.",
        "5B": "You move from comparatives to superlatives. (If you didn't use Level 1, superlatives may be new — you might want to spend more time on them.) The context is a TripAdvisor survey of cities around the world and an experiment by Reader's Digest to find out how honest 16 cities were. The present perfect is recycled in expressions like the most beautiful place I've ever been to. The lesson opens with a vocabulary focus on language for describing a city. The grammar is presented through the TripAdvisor survey, followed by a listening on the most honest cities in the world. In Pronunciation and Speaking, you look at sentence stress in superlative questions and then ask and answer some. The lesson ends with you writing a description of where you live.",
        "5C": "You review quantifiers and learn to use too much / many and (not) enough. The context is a magazine article about the latest medical research into drinks. The lesson opens with a questionnaire focused on drinks — and what you drink when. You then listen to a nutritionist talking about what kinds of liquids we should drink. In Reading, the article is about confusing health advice on drinks, with a vocabulary focus on health and the body. You then work on the grammar, followed by a pronunciation focus on the /ʌ/ sound. The lesson ends with a speaking activity where you discuss more general lifestyle habits using the new quantifiers.",
        "PE3": "In this third Practical English lesson you review some basic shopping vocabulary and learn key phrases for taking things back to a store. The story develops: Rob decides he's out of shape and needs to exercise. Holly invites him to join her and some friends for a game of basketball. Rob accepts, but first needs to buy some sneakers. He buys a pair without trying them on and then realizes they're too small. He takes them back to the store and manages to exchange them. Later, he accepts an invitation to go running with Jenny very early in the morning in Central Park.",
        "6A": "You're introduced to the future forms will and won't for the first time, with a specific focus: using them to make predictions, especially in response to what someone says to you. The context is pessimists and optimists. The lesson opens with a vocabulary focus on common opposite verbs (pass – fail, buy – sell). The grammar is presented through eight situations showing the typical predictions an optimist or pessimist might make (You won't like it, That'll be interesting). In Pronunciation, you practice the contracted forms of will / won't. You then listen to a radio show about positive thinking and read an article arguing that negative thinking can actually be good for you. Finally, you answer a questionnaire to find out whether you're a positive or negative thinker.",
        "6B": "You continue working with will. Here you learn that as well as making predictions, will can be used for promises, offers, and decisions. The context is an article and listening about the true story of a couple whose promise to love each other was kept only after a chain of strange circumstances. The grammar is presented through some humorous typical offers, promises, and decisions, with a pronunciation focus on stress in two-syllable verbs (promise, decide). Next, Vocabulary focuses on certain verbs used with back (come back, take back, etc.), which you then put into practice in a final speaking activity.",
        "6C": "This final lesson of File 6 consolidates the verb forms you've studied in the first half of the book. Present, past, and future forms are reviewed through the context of dream interpretation. The lesson is light-hearted, but the symbols and their interpretations come from serious sources. You start by listening to a psychoanalyst interpreting a patient's dream. After focusing on and reviewing the different forms in the conversation, you ask and answer questions using all the verb forms you've studied. A vocabulary focus covers modifiers like fairly, really, and incredibly. In Pronunciation you look at the possible pronunciations of the letters ea, and the lesson ends with a video listening about the meaning of dreams.",
        "7A": "The context is advice for \"surviving\" stressful situations like the first day in a new job. The material is based on a website called lifehack that gives \"tips for life.\" You start by reading useful advice on what to do and say (and not do or say) when you start a new office job. You then listen to two people describing their first day at work and how it went. In Vocabulary, the focus is on high-frequency verbs followed by the infinitive; in Grammar, you learn when to use the infinitive (after certain verbs, after adjectives, etc.). You also read and retell two more How to… texts (surviving meeting your partner's parents for the first time, and surviving a first date). In Pronunciation and Speaking, you practice the weak form of to in infinitive phrases and linking. Finally, in Writing you write your own tips on a different subject.",
        "7B": "Cartoons about happiness posted on Instagram by two well-known illustrators provide the context for learning three common uses of the verb + -ing form (often called the gerund). The lesson opens with the cartoons, which lead into Vocabulary and Grammar focusing on common verbs followed by the gerund and other uses of the gerund. A Listening and Speaking activity covers the Bank of Happiness in Tallinn, Estonia, with an interview with its founder, Airi Kivi. In Pronunciation, you look at the six pronunciations of the letter o and the /ŋ/ sound. The lesson ends with a speaking activity where you talk about things you love, like, don't mind, etc. doing.",
        "7C": "The title and main context come from a press article about an experiment to see how well someone could learn a foreign language in just one month. At the end of the month, the person traveled to the country itself and carried out a series of tasks to see how much he had actually learned. The lesson opens with you talking about whether you use English outside the classroom. You then read about Americans' problems learning foreign languages, and about an experiment to see how much Spanish an American student, Max, could learn in a month. Next is a grammar focus on verbs expressing obligation: have to / don't have to and must. You listen to find out how Max did in Puerto Rico when his class finished, and then do the challenges yourself. The Vocabulary and Pronunciation focus is on common verb + preposition combinations (bad at, afraid of, etc.) and stress on prepositions. In Writing, you write a formal email to a language school asking for information.",
        "PE4": "In this lesson you practice describing symptoms and buying medicine. Early in the morning, Rob and Jenny go running in Central Park, and Jenny invites Rob for dinner. But Rob isn't feeling too well, and in the afternoon he goes to a pharmacy. Later, in the evening, he has dinner at Jenny's apartment.",
        "8A": "You learn to use should / shouldn't for giving advice. The lesson opens with you reading a problem sent to a newspaper advice column by a young woman looking for advice, and listening to the advice given. This leads into the grammar presentation, followed by a pronunciation focus on the /ʊ/ and /u/ sounds. Then a speaking and listening activity has you listen to a radio call-in show and discuss the advice given to three callers. Finally, Vocabulary and Speaking focuses on different meanings of get, recycled in a questionnaire.",
        "8B": "This lesson presents the first conditional through the humorous context of \"Murphy's Law\" — the principle that if something bad can happen, it will. The lesson opens with a text about the origins of Murphy's Law, and you try to match two halves of some common examples. This leads into the grammar of the first conditional, followed by a listening with two true stories that are real examples of Murphy's Law. The vocabulary and speaking focus is on verbs that are often confused (know / meet, borrow / lend), practiced in a questionnaire. The lesson ends with a pronunciation focus on homophones (wear – where, write – right, etc.).",
        "8C": "The context is a short story by the famous American writer O. Henry (1862–1910), which has a characteristic \"twist\" at the end. You read and listen to the first part of the story and then practice reading aloud with good sentence rhythm in Pronunciation. Examples from the story lead into the grammar focus on possessive pronouns. You then watch or listen to the first two parts; Parts 3 and 4 are dramatized in video listening. Finally, there's a vocabulary and writing focus on using adverbs of manner. This lesson is a good reminder of the value of reading Graded Readers (sometimes called Easy Readers) in English. They help consolidate what you know and build your vocabulary; many come with audio or as e-books, useful for listening and pronunciation. The Oxford Bookworms series level 2 includes a book called New Yorkers with a selection of O. Henry stories.",
        "9A": "A survival quiz, where you have to choose what you'd do in various situations involving animals and insects, sets the context for learning the second conditional for hypothetical and imaginary situations. The lesson opens with Vocabulary: you learn the names of common animals, and Pronunciation focuses on how to pronounce English animal words that may look similar in your native language. Next, you listen to an interview about the five most dangerous animals in North America. This leads into Reading and Speaking: you answer the quiz questions and find out whether you chose the best option. Questions from the quiz lead into Grammar, where the second conditional is analyzed and practiced. Finally, both grammar and vocabulary are recycled in Speaking.",
        "9B": "You study the present perfect with for and since to talk about unfinished actions or states. The context is phobias, opening with information from a website called fearof.net. You learn some words related to fear. In Listening and Speaking, you hear two women talking about the phobias they suffer from. In Grammar, examples of the present perfect are taken from the listening and analyzed before you go to the Grammar Bank. You then look at phrases with for and since. In Pronunciation, you work on sentence stress in present-perfect sentences to prepare for the speaking activity — a survey to find out how long the people around you have done certain things.",
        "9C": "The main focus is how to describe your or somebody else's life, contrasting the simple past (for completed actions or situations) with the present perfect (for situations or actions that started in the past but are still true now). The context is famous mothers and daughters, and famous fathers and sons. You start by learning verb phrases often used in biographies. There's a pronunciation focus on word stress in those phrases and on the /ɔr/ sound. The vocabulary is recycled in Reading, where you read about the lives of the actress Janet Leigh and her daughter Jamie Lee Curtis. The contrast between the verb forms used for the mother (who has died) and her daughter (who is still alive) shows you a fundamental difference between how the simple past and present perfect are used in English. In Listening, you hear about another famous parent–child pair: David Bowie and his son Duncan Jones. The lesson finishes with a speaking activity where you talk about the life of an older person you know well, leading into Writing — a short biography about someone you know or a famous person.",
        "PE5": "You learn how to give and understand simple directions, both in the street and for public transportation. In the storyline, Rob is with Holly in Brooklyn. Jenny calls to confirm their dinner date in Manhattan and gives Rob directions on the subway to the restaurant. But Rob arrives late: when he gets there, Jenny is leaving the restaurant after waiting an hour, and they have an argument.",
        "10A": "You learn how English expresses movement using a verb + an adverb or preposition (walk under the bridge, go out of the door, etc.), and the context is sports. At the start, Vocabulary and Pronunciation has you look at various sports and the verbs that go with them, then practice pronouncing the names of sports in English before doing a questionnaire about which sports you like and don't. In Vocabulary and Grammar, you focus on words that describe movement (up, down, along, through, etc.) and learn how to combine them with verbs. In Reading and Speaking, you read some comments posted on a website called The Atlantic about women's sports. Finally, in Writing, you read a model essay about public running events and then write your own essay about an activity you enjoy in your free time.",
        "10B": "This lesson introduces phrasal verbs and how they work. Phrasal verbs are a key feature of English used very frequently by native speakers. You've probably already learned some in Level 1 (wake up, get up, turn off); here you review the ones you've met so far and learn more common ones, including how they work grammatically. The context is the pros and cons of getting up early. The lesson opens with Reading and Speaking: you read a text about Ella, a baker, or Peter, a DJ with an early-morning radio show, and tell a partner what you found out. In Vocabulary, the focus is on common phrasal verbs; in Grammar, the word order of phrasal verbs is analyzed. In Listening, you hear a radio show about the advantages of getting up early. In Pronunciation you get more practice with linking. The lesson finishes with Speaking, where the phrasal verbs are recycled in a questionnaire.",
        "10C": "This lesson focuses on inventions — first by different nationalities across different centuries, and later (in the video listening) by women. The lesson opens with Vocabulary and Pronunciation: nationality adjectives and the three sounds /ʃ/, /tʃ/, and /dʒ/. Inventions through the ages set the context for the present and past passive in Grammar. In Speaking, you ask quiz questions that use the passive. The lesson ends with a video listening covering six things invented by women.",
        "11A": "You learn to use used to to talk about repeated past actions, with school experiences as the main context. The lesson opens with a vocabulary focus on school subjects. You then read an article in which three teachers talk about a student of theirs who became famous. Extracts from the article are used to present the grammar of used to / didn't use to. A pronunciation focus follows on how to pronounce the new language. In Listening and Speaking, you hear six people talking about whether they liked school or not, which leads into a speaking activity where you talk about your own elementary, middle, or high school experience.",
        "11B": "This lesson presents the modal verb might to express possibility, through the context of a very indecisive person. The lesson opens with speaking — you interview a partner to find out whether they're indecisive. In the Grammar Bank, you see that may is an alternative to might; both are common, but to avoid confusion you focus on might in oral practice. Then in Pronunciation, you work on some common diphthongs. A listening then asks whether there's too much choice in today's world. Finally, in Vocabulary and Speaking, you get practice with word building (forming nouns).",
        "11C": "The topic is twins. The lesson opens with Reading and Listening about a website called Twin Strangers, which helps you find your lookalike anywhere in the world. The vocabulary focus is on different words and phrases used to express similarity, and the structure So am I / Neither am I is presented in Grammar through the true case of identical twins who were separated at birth but reunited 40 years later. Pronunciation focuses on the two possible pronunciations of th: /ð/ as in neither, and /θ/ as in both. The lesson ends with a speaking activity where you first complete some sentences so they're true about you, then try to find someone like you. At this level, this structure is hard to use fluently — for now you just practice the present forms So am / do I and Neither am / do I.",
        "PE6": "In this final Practical English lesson you learn vocabulary related to calling, leaving messages, and responding to news. Rob and Jenny are depressed that his stay in New York is coming to an end. Rob goes off to do his last interview. Meanwhile, Barbara is trying to get in touch with him; Rob gets her message and tries to call her back but has trouble getting through. In the final scene, Rob and Jenny meet in Central Park, both with news for each other. Jenny tells hers first — she has sent Barbara an email resigning, because she wants to move to London. Rob's news: Barbara has offered him a permanent job in New York, which he has accepted. Jenny desperately calls Barbara and tells her not to open the email, and all ends well. They have a future in New York. The story continues in American English File Level 3.",
        "12A": "The past perfect is presented through the context of strange-but-true stories from around the world. The lesson opens with Reading and Vocabulary: you read three stories and sequence the events in each in the correct order, and study the time expressions used. In Grammar, a sentence from one of the stories presents the past perfect. In Pronunciation, you look at two pronunciations of the letter i and learn some spelling and pronunciation rules. The lesson finishes with Speaking: you read two more strange-but-true stories and retell them to a partner.",
        "12B": "This lesson is a clear introduction to reported (or indirect) speech. You focus just on reported statements — reported questions come in Level 3. The context is gossiping. The lesson opens with Listening: two elderly women gossip about a conversation one of them overheard between a young couple, Jack and Emma, who live next door. You later find out that she had completely misunderstood what she heard, as often happens. The grammar section presents reported speech by contrasting what Emma actually said with how the woman reported it. In Grammar and Vocabulary, you focus on how say and tell are used; in Speaking, you practice reporting what others have said. Pronunciation focuses on how double consonants are pronounced and the effect they have on the preceding vowel sound. The lesson finishes with a traditional story about the harmful effects of gossip, and you talk about the subject.",
        "12C": "In this final lesson, you learn to use questions without auxiliaries (Who painted this picture?) and contrast them with questions with auxiliaries (When did he paint it?). The lesson opens with some review of question words in Pronunciation and Vocabulary. The grammar is presented through a quiz that tests your memory on information that has come up in the book. (If you only used the second half of Level 2 — Multipack B — just do the second half of the quiz, questions 8–15.) Then in Speaking, you practice making questions with or without auxiliaries and ask and answer them with a partner. The lesson finishes with a video listening of a trivia-night quiz, where you can play along by answering the questions.",
    },
    "intermediate": {
        "1A": "The topic of this first lesson is food and cooking. The lesson opens with some quotes about food, leading into the Vocabulary Bank where you expand your knowledge of words and phrases related to food and cooking. A pronunciation focus on vowel sounds is relevant to this lexical area and especially useful if you're not yet familiar with the American English File sound–picture system. You then do a food questionnaire before listening to six people, each answering one of the questions. You read an article about new research showing that eating at the right time can make us happier and healthier. In the second half, you listen to an interview with Marianna Leivaditaki, the head chef at Morito, a popular restaurant in London. Extracts from the interview lead into the grammar focus on the simple present and present continuous, and you're introduced to the concept of action and non-action verbs. The lesson ends with a speaking activity where you discuss statements related to food, cooking, and restaurants.",
        "1B": "The context is the family. You start by reviewing family vocabulary and talking about family life in the US and in your country. The grammar focus is on the three most common future forms — you'll have studied them all separately but probably haven't differentiated between them before. A pronunciation focus covers sentence-stress patterns in future forms. In the second half, the focus shifts to relationships between siblings. You extend your knowledge of adjectives to describe personality and practice the word stress in these adjectives. You then read an article about how birth order affects our personality. The lesson ends with a listening and speaking activity about a time you or a sibling behaved badly, and a writing focus on describing a person.",
        "PE1": "This is the first of five Practical English lessons (one every other File) where you learn and practice functional language. The content is built around video. There's a storyline with two characters: Jenny Zielinski, an American journalist in the New York office of a magazine called NewYork 24seven, and Rob Walker, a British journalist for the same magazine who is now working in New York. If you did Level 1 or Level 2, you'll already know them; if not, the first episode opens with a brief summary of the story so far. In the first scene, Jenny takes Rob to meet her parents — they arrive late (because of Rob, who has also forgotten the chocolates). Jenny tells her parents about her new promotion, and you practice reacting to what other people say (to good, bad, interesting, and surprising news). In the second scene, Rob struggles to impress Jenny's father at first, but then they find a shared interest — a jazz musician.",
        "2A": "You review some important uses of the present perfect and how it contrasts with the simple past, and learn common words and phrases for talking about money. The lesson opens with a money quiz, which leads into the vocabulary focus, followed by pronunciation practice highlighting different pronunciations of the letters o and or. The new vocabulary is reinforced through a reading article about a woman who tried to spend as little money as possible for an entire year. In the second half, a conversation where two people argue about money provides the context for the grammar focus. This leads into a money questionnaire where you ask and answer questions in the present perfect and simple past. Finally, you read and listen to true stories about three people who lost money in different scams.",
        "2B": "You review the present perfect (with for and since) and meet the present perfect continuous for the first time. The context is the story of a group of Spanish and British tourists whose vacation to Uganda changed their lives and led them to set up a charity — originally to build a new school for orphan children, but now expanded into many different projects. The lesson opens with a short radio show about the charity Adelante Africa, followed by an interview with Jane Cadwallader, one of the founding members. Sentences from the listening contextualize the grammar presentation. A pronunciation focus on sentence stress in present-perfect-continuous sentences follows, and you put the grammar into practice in a speaking activity. The first half ends with you writing an informal email. In the second half, you read a blog by a TV host who took part in a 500-mile challenge to the South Pole to raise money for charity. The lexical focus here is on using strong adjectives like furious and exhausted. The lesson ends with a video documentary about a charity bake sale at Oxford University Press.",
        "3A": "The context is an episode of the well-known TV series Top Gear, in which the host Rutledge Wood and colleagues organize a race across southern Florida using several different modes of transportation. The lesson opens with vocabulary related to transportation, focused especially on road travel. A pronunciation focus contrasts the consonant sounds /ʃ/, /dʒ/, and /tʃ/. You then read about three of the participants in the race, who traveled by seaplane, scooter, car, and boat. The first half ends with you discussing what the result would be if the race were held in your nearest big city. In the second half, you review what you know about comparatives and superlatives, then go to the Grammar Bank to extend that knowledge. This leads into a listening about the causes of car accidents, based on detailed research from the US. Another pronunciation focus covers linking in fast speech, which helps you understand the listening. You then discuss some statements about road transportation. The lesson ends with a writing focus: an article about transportation in your town or city.",
        "3B": "This lesson examines common stereotypes about men and women, based on recent research. It opens with a speaking activity on stereotypes, with a special focus on generalizing. This leads into an article about whether certain common stereotypes are true. Next is the grammar of articles: when (and when not) to use an article, and which one. A pronunciation focus covers the schwa in unstressed syllables and words, plus the two pronunciations of the. In the second half, you listen to two people talking about children and stereotypes, then do a speaking activity about toys you played with as a child and clothes you wore. The lesson ends with a vocabulary focus on verbs and adjectives with dependent prepositions.",
        "PE2": "The functional focus is on more ways of expressing opinions and agreeing and disagreeing with other people's opinions. In the first scene, Rob interviews Kerri, a British singer visiting New York. In the second scene, Don (the new boss), Jenny, and Rob take Kerri out to lunch. During lunch, Kerri criticizes what she sees as the \"fake friendliness\" of people in New York and compares the city unfavorably to London. Don strongly disagrees; Rob sides with Kerri. In the final scene, Kerri has to eat her words: a genuinely friendly taxi driver comes to the restaurant to return the phone she had left in the cab.",
        "4A": "The main topic is manners in today's world — how people should behave in a variety of common situations. The first half focuses on phone etiquette. The lesson opens with a vocabulary focus on words and phrases related to phones. A short article about a conductor asking an audience member to leave after their phone rang during a concert provides the context for common ways of expressing obligation using must, have to, and should. You'll have seen these verbs separately, but probably haven't contrasted them before. In Pronunciation, you work on silent letters in words like should and wrong. You then put the new grammar into practice in a speaking activity about annoying things people do with their phones. In the second half, you read an article extracted from Debrett's Handbook about modern manners. In Listening, the focus is on people's problems with rude relatives. This leads into an extended speaking activity where you discuss \"modern manners\" and their relative importance in different situations.",
        "4B": "The grammar focus is how to use be able to in the tenses and forms where can / can't can't be used. The main context is how to learn a new skill, and the new grammar is presented through two conversations about people's abilities. A pronunciation focus follows on sentence stress in sentences with can / could / be able to. You then listen to a journalist who tried to learn to play the trumpet in 20 hours. You put the new language into practice in Speaking, talking about how well you think you'd be able to do certain things after 20 hours. In the second half, there's a vocabulary focus on adjectives with both -ed and -ing forms (disappointed / disappointing). You then read a forum with tips for practicing your English outside the classroom. This leads into a short grammar activity on reflexive pronouns and a speaking activity about learning English. Finally, you watch a video about Alex Rawlings, a British language teacher with a talent for languages (he speaks 11).",
        "5A": "The topic is sports. The lesson opens with a vocabulary focus on words and phrases connected with sports, then a pronunciation focus on two tricky vowel sounds, /ɔr/ and /ər/. A speaking activity about sports follows, designed to work whether or not you play. You then read about the superstitions many athletes have. The second half is about sportsmanship. You listen to an interview with a soccer referee, and then the grammar (narrative tenses: simple past, past continuous, and past perfect) is presented through stories about people helping others in sports. You practice telling anecdotes, and the lesson ends with a writing focus on stories.",
        "5B": "Different kinds of relationships are the main theme. The lesson opens with two stories from Instagram's #thewaywemet about two couples who met their partners in unusual circumstances. You then listen to another person talking about where he met his partner — extracts from the listening lead into the grammar, which reviews and reinforces used to for past habits and states and contrasts it with how we express present habits. The pronunciation focus is on the different ways the letter s can be pronounced, plus the pronunciation of used to. A controlled oral grammar practice stage follows. The second half is about friendships. It opens with a vocabulary focus on words and phrases related to relationships. You then listen to a radio show about friendships, and the lesson ends with a speaking activity where you present your opinion on a particular aspect of friendship.",
        "PE3": "In this third Practical English lesson, you learn key phrases for asking permission to do something and for asking other people to do something for you. In the first scene, Jenny meets Monica, an old friend, in the street, and they have a coffee together. Monica tells Jenny she's going to get married, and Jenny tells Monica about Rob. In the next scene, Rob arrives and joins them, but Monica has to leave. Rob then tells Jenny that an old friend of his, Paul, is coming to stay, and asks if Jenny can pick him up at the airport since he has to work late. Jenny agrees. In the third scene, Jenny brings Paul to Rob's apartment. She's tired because she had to wait a long time and the traffic was terrible, so she leaves Rob and Paul to have a night out together.",
        "6A": "The topic is the movies. The lesson opens with a reading text about working as an extra in a movie. This provides the context for reviewing and extending the passive forms, and past participles are then focused on in Pronunciation. In the second half, movie vocabulary is presented, and then you listen to the true story of a young Polish student who — by chance, and because of her excellent English — got to work for a world-famous movie director. Movie language is then put into practice in a questionnaire where you talk about your own movie preferences and experiences. Finally, in Writing, you write a description of a movie you'd recommend.",
        "6B": "The overall topic is the image people give of themselves to the world, both on social media and in person, and how we tend to judge people at first sight based on appearance. The lesson opens with a light-hearted article about what people's profile photos on social media say about them, followed by a short speaking activity where you interpret your own profile photo and those of friends and family. This leads into the grammar of modals of deduction, presented through a conversation about a photo. In the second half, Vocabulary focuses on the body and verbs related to parts of the body (touch, point, etc.). Pronunciation looks at diphthongs (combinations of two vowel sounds). In Reading and Listening, you read about a journalist who met a charisma coach, then listen to what happened when the coach followed the journalist for a couple of days and the tips he gave him. The lesson finishes with a video about a personal stylist.",
        "7A": "This lesson is about education and looks at two different angles on the topic. It opens with a vocabulary focus that reviews and extends your knowledge of education vocabulary, followed by a pronunciation focus on the letter u and a speaking activity where you talk about your own education. You then read and listen to the account of an educational experiment, televised, where five teachers from China went to a British school for four weeks and taught three subjects to half of the Year 9 students. You then discuss the Chinese education system, the British, and your own. In the second half, the grammar — first conditional sentences and the use of the present tense in future time clauses — is presented through the context of exams. You then read an online forum where people discuss whether or not it's worth going to college and read about two people's contrasting experiences. Finally, you have a debate on various topics related to education.",
        "7B": "The topic is people's homes. In the first half, you start by reading an article about the advantages and disadvantages, in the US, of living with your parents as an adult. This leads into you discussing the situation in your own country. The grammar (second conditionals) is presented through online comments where young people respond to the article and say whether they'd like to leave home and live independently. A pronunciation focus on sentence stress and rhythm follows, plus oral practice of the second conditional. In the second half, there's a vocabulary focus on words related to houses and where people live. This leads into a pronunciation section on the letter c and its three possible pronunciations: /s/, /ʃ/, and /k/. You then listen to an audio guide about a London building (now a museum) where both the composer George Handel and the musician Jimi Hendrix once lived. You describe your own dream house. The lesson ends with writing — a description of your house or apartment for a home-rental website.",
        "PE4": "In the fourth episode, the main functional focus is on expressions for making and responding to suggestions. In the first scene, Rob and Paul play pool and reminisce about old times. Paul thinks Rob has changed a lot and is becoming very \"American,\" which he suggests is because of Jenny. In the next scene, Jenny joins them for a meal, and they then decide what to do. They can't agree, and in the end Paul and Rob decide to go to a gig Kerri (from Episode 2) is doing, while Jenny — rather upset — calls Monica and goes over to see her. The last scene takes place in the office. Jenny is at work, ready for a meeting with Don, but Rob calls in saying he doesn't feel well and isn't going to make it.",
        "8A": "The topic is work. In the first half, you learn words and phrases related to work, recycled and practiced orally in Pronunciation and Speaking. The grammar focuses on when to use a gerund (or -ing form) versus an infinitive, with the context of a questionnaire that helps you see what kind of job would best suit your personality. The grammar is practiced in a speaking activity. The first half ends with you writing a cover email for a job application. In the second half, you read about a TV show called Shark Tank, in which contestants try to convince a panel of business people to invest in a product or service. In Listening, you hear a contestant talking about his experience on the British version of the show, Dragons' Den. Finally, in Speaking, you take part in a role-play where you present a new product to the class, as if you were appearing on the show.",
        "8B": "Shopping and customer service are the main themes, with reported speech reviewed and extended. The lesson opens with an article about someone's shopping experience, followed by a discussion of how helpful or unhelpful salespeople can be — that article provides the context for the presentation of reported speech. Grammar is followed by shopping vocabulary and a questionnaire. In the second half, you read five stories about good customer service. This leads into the different pronunciations of the letters ai. In Listening, you hear a true story about bad customer service and then talk about your own experiences. Vocabulary focuses on how to make nouns from verbs. You then watch a video about complaining and how to do it politely and successfully, and you role-play making complaints. Finally, in Writing, you're shown how to write an email of complaint.",
        "9A": "This lesson presents the third conditional in the context of different aspects of luck. It opens with you saying what you'd do in different situations where a stranger needed help. This leads into reading and listening to the writer Bernard Hare talking about how he was helped by a stranger when he was a student. You then listen to three more people talking about being helped by strangers. Extracts from those stories introduce the grammar, further practiced in pronunciation with a focus on the stress patterns in third conditionals. The second half opens with you talking about how lucky or unlucky you consider yourself to be. This leads into a reading about research by Richard Wiseman on how to improve your luck. A vocabulary focus on adverb and adjective formation follows, reinforced through a writing game.",
        "9B": "You review and extend your knowledge of quantifiers (a lot of / plenty of, too much, not enough, etc.) through the topic of digital detoxes. The first half opens with a vocabulary focus on electronic devices and the phrasal verbs that go with them, followed by pronunciation practice on linking words. You then listen to a journalist who decided to go on a three-day digital-detox course. The first half ends with you discussing digital detoxes and whether you can live without the internet. The second half opens with grammar, presented through sentences related to the internet and electronic devices, and a pronunciation focus on the often-tricky combinations -ough and -augh. You then read and discuss an article about how to \"clean up\" your digital life — emails, old software, and so on. The lesson ends with a writing focus: a magazine article analyzing the advantages and disadvantages of smartphones.",
        "PE5": "In this final episode, you learn how to ask questions in an indirect way — beginning with Could you tell me…? or Do you know…? In the first scene, Jenny arrives at Rob's apartment and is surprised to find Paul still there, since Rob had said he was leaving. Paul tells Jenny that Rob is planning to go back to the UK, and she leaves upset, just as Rob arrives. Rob is furious with Paul for telling Jenny something that simply isn't true, and makes it clear to Paul how serious he is about the relationship. In the next scene, Rob tries to explain and make things right, but Jenny isn't convinced he's serious about the relationship. In the final scene, however, Rob does his best to prove that he is.",
        "10A": "The theme is icons — both people and objects. The first half focuses on nine famous people who died in 2016. This context is used to review and extend your knowledge of relative clauses and leads into a quiz with relative clauses. Finally, the new grammar (non-defining clauses) is reinforced in a writing activity about Umberto Eco, the Italian author of The Name of the Rose. The second half focuses on four American design icons such as the Tiffany lamp. You listen to information about these icons and how they were designed, then talk about iconic people and objects you admire. The lexical and pronunciation focus is on compound nouns, and the lesson ends with a vocabulary race reviewing compound nouns you've met earlier in the book.",
        "10B": "The topic is murder mysteries: first, the true story of Jack the Ripper and three theories as to who he was, and then a well-known short story by Ruth Rendell. The lesson opens with a vocabulary focus on words and phrases related to crime. You then activate the new vocabulary by completing an article about Jack the Ripper. In Listening, you hear an expert on Jack the Ripper giving his opinion on three theories about who he was. The grammar focus is tag questions, further practiced in Pronunciation and Speaking. In the second half, you read and answer questions about the first two parts of the Ruth Rendell short story May and June, then listen to and answer questions on the third part. The lesson ends with a video about Ruth Rendell and Agatha Christie.",
    },
    "upper-intermediate": {
        "1A": "The topic and grammar focus of this first lesson is questions. Even at this level, forming questions correctly is still a common pain point. This lesson reviews all aspects of question formation, including indirect questions, negative questions, and questions that end with a preposition. By the end, you should be forming questions more accurately and confidently. The lesson has two distinct halves. In the first, you read two interviews from Q&A, a regular feature in The Guardian newspaper, with the gymnast Simone Biles and the actor Dan Stevens. You then focus on the grammar of question formation, followed by Pronunciation reviewing how to use intonation in questions to show interest. In the second half, the topic is job interviews and you read an article about the kind of \"extreme\" questions some companies now use. The vocabulary focus is on figuring out the meaning of new words in a text from context. This is followed by a listening where you hear four speakers talk about strange questions they've been asked in interviews. The lesson ends with Speaking, where you role-play extreme interviews and write a question of your own.",
        "1B": "The topic is understanding and explaining mysterious and unusual events. The first half opens with a reading based on a true story: the disappearance of three lighthouse keepers in Scotland. You then listen to the end of the story, in which a detective tries to solve the mysterious disappearance. This leads into the grammar focus on auxiliary verbs, which includes a review of tag questions and So do I / Neither do I, plus the use of auxiliaries for emphasis and in reply questions. You then work on intonation and sentence rhythm in questions and sentences using auxiliaries. The first half ends with you pretending to be a psychic and completing sentences about a partner. In the second half, the focus shifts to an unusual personality test: you listen to a mysterious voice guiding you on a walk through a forest, take notes, and analyze your answers. You then discuss other non-mainstream ways of analyzing personality. Grammar in Context focuses on how to use the structure the…, the… + comparatives (e.g., the sooner, the better). In Vocabulary, you expand your knowledge of compound adjectives to describe personality, and use modifiers and compound adjectives to talk about people you know.",
        "CE1": "This is the first of five Colloquial English lessons featuring interviews and conversations commissioned and filmed specially for American English File. The first section, The Interview, has an interview related to one or more of the topics in the preceding Files. The interviewees all have unique first-hand experience in their field and offer interesting perspectives, while giving you a chance to engage with authentic, unscripted speech. The second part, The Conversation, is an authentic unedited conversation between three people about an aspect of the same topic — designed to make you more confident at following a conversation at natural speed. Watching it on video makes it easier to follow who's saying what, and to focus on the language of such conversations (emphasizing a point, responding to an idea, etc.). It's worth watching the video a final time with the script or subtitles to see what you did and didn't understand, and to develop your awareness of features of spoken English (elision, false starts, discourse markers, hesitation, etc.). In this lesson, the person interviewed is Jeff Neil, a career coach, with a focus on formal language. In The Conversation, you watch three people discussing whether it's OK to slightly exaggerate on your résumé. You then discuss this and a couple of other related questions, focusing on ways to emphasize your ideas.",
        "2A": "The topic is medicine. The first half opens with a first-aid quiz, testing your own knowledge and sparking discussion. You then expand your vocabulary of medical words to describe symptoms, illnesses, and treatment. A pronunciation focus on consonant sounds follows. You then listen to three speakers talking about a time when someone needed first aid. Finally, you discuss whether you've ever received or given first aid, and what you could do in certain emergencies. The second half opens with a light-hearted conversation between a doctor and a difficult patient, leading into the grammar focus where you review and extend your knowledge of the present perfect simple and continuous. These can be problematic because of interference from your native language. After practicing the grammar, you read an article from The Sunday Times on cyberchondriacs — people who obsessively search for medical information online. You focus on summarizing each paragraph and on medical phrases, finishing with a discussion about hypochondria and cyberchondria. Finally, the grammar and vocabulary are consolidated in the Writing Bank, where you write an informal email explaining to a friend why you haven't been well and what you've been doing recently.",
        "2B": "The topic is age. The lesson opens with an article about friendship between people with a big age difference, followed by a speaking activity in which you discuss having a friend of a different generation and the advantages this can bring. The first half ends with the grammar focus, where you extend your knowledge of how to use adjectives. You learn to use nationality adjectives as nouns when talking about the people from a particular country (the British, the French) or a particular group (the rich, the unemployed), and you also focus on adjective order when two or more describe a noun. In the second half, the angle is age-appropriate dressing. It opens with a photo and article about how women of different generations can wear the same clothes, leading into a vocabulary focus on clothes and fashion. Pronunciation looks at short and long vowel sounds and diphthongs. You then listen to a radio show on whether men and women should dress their age. In Speaking, you give your opinion on clothes and fashion. A writing task brings the vocabulary and grammar together: you write two ads to sell items of clothing online. The lesson ends with a documentary about a small Welsh company whose jeans have become a global fashion item.",
        "3A": "The topic is air travel, though both speaking activities work even if you've never flown. In the first half, you listen to some announcements heard on planes and trains, and Vocabulary then focuses on air-travel vocabulary. You read an article about where best to sit on a plane for comfort, safety, and service. In Grammar in Context, you also learn how to use so / such…that. Finally, you do a speaking activity on different aspects of travel. In the second half, you listen to an interview with a pilot who answers some of the questions air travelers frequently ask themselves. This is followed by a grammar focus on narrative tenses. You review the three you already know (simple past, past continuous, and past perfect) and learn a new one: the past perfect continuous. Pronunciation focuses on difficult irregular past verb forms and sentence rhythm. In the final speaking activity, you read and retell a couple of real flying stories and then tell a partner a travel anecdote.",
        "3B": "The topic is stories and reading. The lesson opens with a grammar focus on adverbs and adverbial phrases and their position in sentences, presented through four 50-word stories with a twist. A vocabulary focus on certain pairs of adverbs that are often confused follows, and in Pronunciation the focus is on word stress and emphatic intonation on certain adverbs. You then write your own 50-word story. In the second half, you start by talking about your reading habits, or about why you don't read for pleasure. You then read and listen to a short story by the French author Guy de Maupassant. The ending is on audio to create more suspense. Finally, you go to the Writing Bank to prepare for writing longer stories.",
        "CE2": "In The Interview, the person interviewed is Marion Pomeranc, the manager of a non-profit organization in New York City called Learning Leaders and the author of three children's books. In The Conversation, you watch three people discussing whether there are any books they think everyone should read. You then discuss this question and a couple of related ones, focusing on vague language (I mean, sort of, etc.) and phrases for referring to what someone else has said (as you were saying, etc.).",
        "4A": "The topic is the environment and climate change. The first half opens with a quiz to see if you're as environmentally friendly as you think. You then look at an infographic with predictions about the environment. This leads into the grammar focus on two tenses that will be new for most students: the future perfect and future continuous. In the second half, you expand your weather vocabulary. A pronunciation focus on combinations of vowels that can be pronounced in different ways (ea, oo) follows. You then read an article from a website called the Climate Stories Project, in which six people from different continents talk about how they're affected by climate change. You listen to an interview with a meteorologist, and finally talk about your own experiences with climate change and extreme weather.",
        "4B": "The topic is risk. In the first half, you listen to four people answering the question Are you a risk-taker? and then interview a partner to find out if they are. This is followed by the grammar focus on conditionals. You extend your knowledge of future time clauses and real conditionals, and see the variety of tenses that can be used besides the simple present and simple future. In Pronunciation, you look at linked phrases like and above all, as far as, etc. In the second half, you read an article about the rise in popularity of extreme sports, followed by a vocabulary focus on common collocations with take (take a risk, take seriously, etc.). You then go to the Writing Bank to focus on for-and-against essays. Finally, you watch a documentary about a young Irish surfer who talks about the risks and rewards of the sport.",
        "5A": "The topic is survival. In the first half, you talk about how you think you'd react in an emergency and read about a reality TV show in which groups of participants have to survive on a remote uninhabited island. You then listen to an interview with one of the participants talking about the best and worst experiences on the island. The vocabulary focus is on feelings (devastated, stunned, etc.), and Pronunciation looks at word stress in three- and four-syllable adjectives. The second half is based on the true story (later made into a documentary for Discovery TV) of three young backpackers and their guide who got lost in the Amazon jungle. You read and listen to the story. The grammar focus is on unreal conditionals — the second and third conditionals. You'll have seen both structures before, but practice with them is essential, especially with third conditionals. Finally, you go to the Writing Bank and focus on writing a blog post.",
        "5B": "The topics in this lesson are things you'd like to be different, or that annoy you in daily life, and regrets you have about the present and the past. They provide the context for learning to use I wish…. To make this easier to absorb, the grammar is split into two separate presentations with two visits to the Grammar Bank. This is a very difficult grammar point — especially the difference between wish + simple past and wish + would — so don't expect to nail it immediately. The first half opens with the grammar presentation of I wish + simple past, using different kinds of social media to express things you'd like to be different, plus wish + would to express annoyance. A vocabulary and speaking focus on different ways of expressing feelings follows — with a verb or with an -ed or -ing adjective (It annoys me / I'm annoyed / It's annoying). In the second half, you read an article in which a journalist asked people to tweet about their biggest regrets, followed by the second grammar focus using wish + past perfect for past regrets. Pronunciation focuses on sentence rhythm and intonation, and you then practice the new structure talking in small groups about some past regrets. The lesson ends with a poem about regret, which you listen to before writing your own.",
        "CE3": "In The Interview, the person interviewed is Candida Brady, a British journalist and filmmaker. In The Conversation, you watch three people discussing whether they think we'll ever be plastic-free. You then discuss this question and a couple of related ones, focusing on different ways that people respond to what another person has said.",
        "6A": "The context is several different angles on sleep. At the start of the first half, you listen to three people who all have some kind of sleep problem. Sentences from the listening provide the context for the grammar presentation, which reviews the use of used to for repeated past actions and introduces be used to and get used to (doing something) for actions or activities that have become, or are becoming, familiar. The pronunciation focus is on the /s/ and /z/ sounds in used to. You then read an article about the benefits of segmented sleep (sleeping for a few hours, waking up for a couple of hours, then going back to sleep), followed by short articles you read separately and tell a partner about — on what some people do in their waking hours in the middle of the night. The second half opens with a vocabulary focus on words and phrases related to sleep (yawn, be a light sleeper). A listening podcast by a sleep expert follows. The lesson ends with a speaking activity to recycle the new vocabulary.",
        "6B": "The topic is music and how it affects our emotions. In the first half, you listen to an interview with a music psychologist who explains why we listen to music and how it can affect us emotionally. You then talk about what kinds of music you listen to when you're in certain moods. The lesson continues with a grammar focus on the uses of gerunds and infinitives. You review the basic rules about when to use a gerund or an infinitive after a verb, then learn about certain verbs (remember, try) that can be followed by either a gerund or an infinitive, but with a change in meaning. The vocabulary and pronunciation focus is on words related to music, including \"borrowed\" words such as cello, choir, and ballet, plus other foreign words used in English. The second half opens with a text about research on the importance of finding the right music for the right task. You then read what four surgeons say about playing music while they work. A speaking activity follows where you discuss some statements about music. The lesson ends with a documentary about pianist Isata Kanneh-Mason and her large family — all of whom are very talented musicians.",
        "7A": "The topic is arguments: what causes them, how to argue, and how to win online arguments. The first half opens with the grammar presentation: you listen to some people arguing, a context where past modals of deduction occur naturally. You've already learned present modals of deduction (must / might / can't + base form) and should (+ base form) for advice in Level 3. Here, you learn how to use these same modals to make deductions or speculate about the past (You must have taken a wrong turn, Somebody might have stolen it) and to make criticisms (You shouldn't have said that). Pronunciation focuses on weak forms of have in sentences with past modals (You should have told me). In Reading & Speaking, you read an article aimed at helping students sharing an apartment avoid arguments, and discuss the solutions. In the second half, you start by role-playing an argument. You then listen to a psychologist talking about how to argue in a sensible and controlled way, and put the advice into action in another role-play. Grammar in Context focuses on the use of would rather, followed by a vocabulary focus on verbs that are sometimes confused (argue and discuss, etc.). The lesson ends with an article about the best ways to win an online argument, which you put into practice by simulating an online discussion.",
        "7B": "The general topic is body language. The first half opens with the grammar presentation on verbs of the senses and how they are used grammatically. You also look at uses of as (He works as a builder, She's as tall as me, I enjoy activities such as swimming and jogging, etc.). You then look at movie stills of actors in well-known movies and discuss who the people are, how they're feeling, and what they're doing, using She looks…, He looks like…, She looks as if…. You then practice using the same structures with sounds, feels, tastes, etc. In Reading & Listening, you read an exercise on how to improve your acting skills, then try it out. You listen to three more exercises and complete the instructions. Finally, you do the three acting exercises you listened to. In the second half, you extend your vocabulary related to the body — first reviewing facial features, then learning new body parts along with verbs and verb phrases connected to the body. You then do a speaking activity where you describe photos to each other and put the grammar and vocabulary into practice. The pronunciation focus is on silent consonants (e.g., in calf and thumb). You then read an article about how to spot a liar, and do a speaking activity where you have to figure out if your partner is telling the truth or lying. The lesson ends with you writing a description of a photo.",
        "CE4": "In The Interview, the person interviewed is Simon Callow, a British actor, stage director, and author. In The Conversation, you watch three people discussing whether a live performance is always better than a recorded one. You then discuss this question and a couple of related ones, focusing on phrases for giving yourself time to think, checking if others agree with you, and phrases for apologizing for interrupting.",
        "8A": "The topic is crime. The lesson opens with a Metropolitan Police podcast giving practical tips on how to stay safe in city streets. A vocabulary focus on crime and punishment follows, presented through a quiz based on information from an ex-burglar, plus a pronunciation focus on the different pronunciations of the letter u. The first half ends with you talking about local crime in your area, witnessing crimes, and any experience you have of crimes such as theft and vandalism. In the second half, some light-hearted news stories about crimes that went wrong provide a natural context for reviewing passive forms, and you also learn how to use the causative have (I had my bag stolen) and the structure it is said that… / he is said to…. You then read an article about a man who was a victim of identity theft after posting photos online. You discuss whether certain activities should be illegal and how perpetrators should be punished. The lesson ends with you writing a magazine article expressing your opinion on either the legality of downloading music or squatters' rights.",
        "8B": "The topic is the media, and in particular the very current issue of fake news. The first half opens with you talking about the different media you use to get the news and which sections of news interest you. You then listen to two stories from the press and read two more — providing the context to review the basic rules of reported speech. You then decide which story is in fact fake (invented). Extracts from the four stories introduce reporting verbs such as offer, convince, admit, deny, etc., which are followed by gerund or infinitive constructions. After the Grammar Bank, where you learn more reporting verbs, there's a pronunciation focus on word stress in two-syllable verbs. In the second half, the vocabulary of the media is developed in the Vocabulary Bank along with a speaking activity about the media. You then read an article about how to spot fake news. Finally, you watch a short documentary about the history of journalism.",
        "9A": "The topic and lexical area is business and advertising. In the first half, the focus is on honesty (or dishonesty) in advertising. You look at words and phrases related to advertising, then discuss famous misleading advertisements. A speaking activity follows where you discuss various aspects of advertising in general, including language like viral ads, logos, and pop-ups. You then listen to a radio show about how companies try to trick us through misleading advertisements. This leads into the grammar: clauses of contrast after expressions like Even though…, In spite of…, etc., and clauses of purpose after expressions like so that…, in order to…, etc. The advertising and business topic continues in the second half, where you read a chapter from a book about the razor-and-blades business model — developed after King Camp Gillette invented the disposable razor blade. In Vocabulary, you look at words and phrases related to business, followed by a pronunciation focus on how stress changes in words that can be used both as nouns and verbs (export, increase, etc.). You finish by talking about aspects of business in your country or region.",
        "9B": "The context is cities. In the first half, you read about author and philosopher Alain de Botton's vision on how to make a modern city attractive to live in. You then listen to five people who talk about the most beautiful city they've ever been to. You discuss which of the places mentioned you'd like to visit, plus your favorite and least favorite cities. The grammar focus follows, where you extend your knowledge of uncountable nouns (luggage, furniture, etc.) and plural nouns (news, politics). The first half finishes with a speaking game to practice the grammar. In the second half, you read an article about a city in South Korea designed as a showpiece of modern urban design. A speaking activity follows on modern cities and the changes population growth might bring. A vocabulary focus on word building with prefixes and suffixes follows, with a pronunciation focus on word stress. You then practice the vocabulary by discussing different aspects of cities and regions you know. The lesson ends with you writing a report on the features of a city you know well.",
        "CE5": "In The Interview, the person interviewed is George Tannenbaum, an ad executive who owns an ad agency and is the director of an international one. In The Conversation, you watch three people discussing whether people are influenced by advertising campaigns. You then discuss this question and a couple of related ones, focusing on correcting something someone has said and phrases to make something clearer.",
        "10A": "The topic is science. In the first half, you start by reviewing science-related vocabulary through a quiz of questions often asked by children that parents struggle to answer, then listen to an expert answering each question. The vocabulary focus is on more words related to science, and Pronunciation deals with changing stress in word families (science, scientist, scientific). The first half ends with you interviewing a partner about science-related issues. In the second half, you read about the plausibility of some ideas from science fiction and whether they might actually become reality. The grammar — review and extension of the use of a variety of quantifiers — is presented through sentences from the article and finally practiced in another science quiz.",
        "10B": "The topic of this final lesson is public speaking. In the first half, you start by listening to a program about the controversy surrounding Neil Armstrong's famous words when he stepped on the moon (Did he make a mistake by omitting an indefinite article?). This leads into the Grammar, where you review and extend your knowledge of the use and non-use of the definite and indefinite articles. You then read a short text about what makes a good speech according to Cicero, before focusing on eight sound bites from famous speeches. You then read about the circumstances in which four of the speeches were written. You discuss which speech you'd most like to have heard, great speakers you know of, and past or present politicians who are either good or bad speakers. In the second half, you listen to a radio show in which an expert gives tips for giving a good presentation, and a young woman talks about an international public-speaking competition she took part in. The vocabulary focus is on word pairs joined with and and or (sick and tired, all or nothing). Then in Pronunciation, you learn how pausing in the correct places and stressing sentences correctly will make you much easier to understand if you're giving a presentation in English. You then have the chance to give a short presentation. The lesson ends with a documentary on speaking in public.",
    },
    "advanced": {
        "1A": "In this first File the grammar has a strong review element, but it groups and re-presents key structures in a challenging way. Each lesson also brings a substantial input of new vocabulary, reflecting how important vocabulary is at this level. This lesson has two main contexts. In the first half the focus is family: the context is the story behind a Frida Kahlo painting of her family tree. You listen to an audio guide to find out about Frida Kahlo and her family. This leads you into talking about aspects of your own family and then discussing family-related issues in general, where you're encouraged to use more sophisticated expressions for agreeing and disagreeing. A grammar focus on the different uses of have as a main and auxiliary verb follows. In the second half, you review previously learned words and phrases to describe personality and learn some new ones. A pronunciation focus on using a dictionary to check pronunciation follows (so it's helpful to have a paper or online dictionary at hand). In Reading you focus on how to look up phrasal verbs and idioms, and then read and answer a quiz assessing personality based on the well-known Myers-Briggs test.",
        "1B": "The topic is work. In the first half, you read three articles from a weekly series in the Guardian newspaper, where ordinary people write a short paragraph showing how they really feel about their jobs. This sets up a discussion about how you'd feel doing each of those different jobs. You then expand your vocabulary related to the world of work. In the second half, the focus moves to what motivates people to feel happy at work, and you look at the criteria used in the annual Sunday Times survey for the 100 best companies to work for. You then listen to an interview with a woman who works for Skyscanner, a global travel comparison website with its main office in Edinburgh, whose employees are among the happiest according to a recent survey. Examples from the listening lead into the grammar focus: linkers expressing reason, result, purpose, and contrast. Pronunciation focuses on the rhythm of spoken English. You then write a job application. The lesson ends with a writing assignment: a cover email to apply for a job.",
        "CE1": "In this lesson the person interviewed is Eliza Carthy, an English folk musician known for both singing and playing the violin. In a three-part interview she talks about her musical family and ancestors, her life as a musician, and the effect it has on her own children. A language focus follows on the discourse markers Eliza Carthy uses — reviewing some you should already know and previewing some that come up in 3B. In the ON THE STREET section, people are asked about their family tree and if there's anyone in their family they'd like to know more about. The lesson ends with a speaking activity based on families and work.",
        "2A": "The main topic is the English language. The first half opens with a spelling test, followed by a review of Spell it Out by David Crystal. The review looks at the origins of English spelling and leads into a discussion about how important (or not) spelling is in English and in other languages. A pronunciation focus on common sound–spelling relationships in English follows. The grammar focus is on pronouns: a review of what you should already know, plus advanced points such as using they to refer to a singular subject when the gender of the person is not specified or known. The second half opens with a vocabulary focus on terminology used to describe aspects of language — collocation, phrasal verbs, synonyms, register, idioms — terms that will be used throughout the course, consolidated through a language quiz where you learn words and phrases under these headings. A second pronunciation focus then helps you understand different native English-speakers' accents — an interesting challenge at this level. The lesson ends with an interview with a non-native English speaker who has lived for many years in the US, talking about her experiences of learning, speaking, and understanding English.",
        "2B": "The topic is childhood memories. The theme is explored first through an extract from Boy, Roald Dahl's autobiography, where he explains how an experience at school inspired him to write Charlie and the Chocolate Factory. The grammar focus here is on past forms: you review narrative tenses (simple past and continuous, past perfect and continuous) for describing specific incidents in the past. You also review used to for situations and repeated past actions, and learn an alternative form: would + infinitive. The first half ends with speaking and writing activities about childhood, where you put what you've just learned into practice. In the second half, there's a lexical and pronunciation focus on abstract nouns (childhood, boredom, fear, etc.) and word stress with suffixes. You also study common collocations using abstract nouns. A listening task follows: you first hear three people talking about childhood memories, then listen to an interview about a book that talks about research into our earliest memories (what age we have them and what they usually consist of). You then talk about your own early memories.",
        "3A": "This lesson deals with relationships. First, you discuss a light-hearted list of \"best break-up lines\" before reading the true story of how Sophie Calle, a French artist, got back at a boyfriend who left her. In Pronunciation, you look at French words and expressions (rendezvous and others) which are commonly used in English but pronounced in a way that's close to their French pronunciation. A vocabulary focus follows on verbs and idioms related to get — probably the most versatile verb in English. In the second half, you look at a regular feature in the Guardian newspaper called \"Blind Date.\" You then listen to a radio show about dos and don'ts on first dates. The grammar focus is also on different uses of get, and the lesson ends with a questionnaire that recycles both lexical and grammatical examples of this verb.",
        "3B": "The topic is history, as seen in historical movies and TV shows. The lesson opens by introducing the vocabulary of conflict and warfare through three texts describing memorable scenes from historical movies. The pronunciation focus is on shifting word stress in some of the word \"families\" you've just learned. You then describe memorable scenes of your own and write a paragraph about the movie or show and the scene. (It can help to research a movie or TV show in advance.) In the second part, the topic shifts to historical accuracy in movies. You read an extract from a movie blog and then listen to an interview with a scriptwriter. Finally, the discourse markers you've been exposed to throughout the lesson are focused on, and the lesson ends with the grammar put into practice through a communication activity called Guess the sentence.",
        "CE2": "In the first part of this lesson the person interviewed is Mary Beard, a professor of Classics at the University of Cambridge, who frequently appears on TV and in the media talking about history. In a three-part interview she talks about how to get people interested in ancient history and what we can learn from it, the importance of considering ordinary people's lives when studying history, and her view on historical movies. A language focus follows on typical collocations Mary Beard uses. In the ON THE STREET section, people are asked which historical period they'd like to go back to and whether there's a person from history they particularly admire.",
        "4A": "This lesson has two main contexts: noise and silence. The first half focuses on sounds. It opens with a vocabulary focus on verbs and nouns to describe sounds and the human voice, and a pronunciation focus on the consonant clusters that occur in many of these words (screech, splash, etc.). You then read an article about a woman who has a phobia of sound in her daily life. You then listen to five people talking about noises they don't like. The first half ends with you talking about noises you hate and sounds you love. In the second half, the focus is on \"breaking the silence\" — the silence that exists between people in cities. You speculate about a photo of Peggy Gruner, a grandma, which leads into the grammar focus on speculation and deduction. You then listen to an interview with a co-founder of the organization \"Talk to me London,\" which looks for different ways to encourage strangers to talk to each other — their vision is to build a friendlier city through small conversations between strangers. A short listening based on real people's experiences of starting conversations in cities follows. Finally, you talk about how friendly people are in places you know.",
        "4B": "The two main contexts of this lesson are books and translation. However, the angles also apply to movies and TV shows, so if you don't read much, just substitute. The first half opens with an article about spoilers and whether knowing how a book or movie ends really affects our enjoyment. You then discuss the topic. This leads into a vocabulary focus on adjectives commonly used to describe books or movies, and a pronunciation focus on the /ɔ/ sound. You then talk about your reading habits past and present. The grammar focus is on inversion for dramatic effect after adverbs or adverbial phrases. The first half ends with writing a review, including a focus on using participle clauses. In the second half, the topic shifts to the role of the translator. You read a blog about translating a novel from Portuguese into English, study the changes the translator makes as he refines his translation, and consider how his approach could help you with your own writing in English. You then listen to an interview with another translator talking about the pros and cons and some of the trickier aspects of the job.",
        "5A": "The topic is time: how we try to save time through multitasking and why this may be less efficient than focusing on the present moment one task at a time, plus how we feel about waiting. In the first half, you start by discussing multitasking. You then read two short extracts about time management — one about how multitasking, although possible, can be dangerous, and the other about a popular current trend in psychology called mindfulness (being aware of the present and what you're thinking and doing), which is thought to help focus attention more efficiently. You then listen to a well-known meditation exercise called \"The Chocolate Meditation,\" which gives you a practical experience of mindfulness. (It's even more enjoyable if you have a small bar of chocolate at hand.) This leads into the grammar focus on distancing — using certain language (apparently, it seems, etc.) to \"distance\" ourselves from the information we're passing on. In the second half, you talk about things you hate waiting for and listen to people complaining about waiting. You then learn expressions related to time, with a pronunciation focus on short phrases where words are normally linked together. The lesson ends with you answering questions in a time questionnaire that recycles all the vocabulary.",
        "5B": "The topic is money and materialism. In the first half, you read an article called Do women really want to marry for money?, where two women answer the question in different ways and then give their own opinion on the subject. This leads into the grammar focus on special uses of the past tense after expressions like I wish, I would rather, etc., and you ask and answer some questions on past and present wishes. The second half opens with a lexical focus on words, phrases, and idioms related to money. You then listen to an interview with Surita Gupta, the former vice-president of Women's World Banking (WWB), who explains the WWB's initiative to help women in developing countries escape poverty by providing them with bank loans to start small businesses. Finally, Pronunciation looks at the difference between US and UK accents.",
        "CE3": "In this lesson the person interviewed is Jordan Friedman, a specialist in the field of stress and stress reduction. In a three-part interview he talks about what causes stress, the effect it can have on the mind and body, and different ways of managing stress. A language focus on compound nouns (which Jordan Friedman frequently uses in the interview) follows. In the ON THE STREET section, people answer questions about how stressed they are and how they manage their stress. The lesson ends with you talking about stress-related issues.",
        "6A": "The topics are how to survive stressful life events and how to change your life for the better. You start by doing a jigsaw reading. Both texts (one from the Guardian, one from wikiHow) give advice — one for a young adult living with parents and the other about coping with exam stress. You tell a partner about the tips suggested in your text and together assess their usefulness. This leads into you writing some tips on a topic you have some experience of. The grammar focus is on the common pattern of verb + object + infinitive or gerund. In the second half, you listen to a School of Life presentation about small pleasures. You then choose your own topic for a presentation, study tips on giving one, and present it in small groups. In Vocabulary and Pronunciation, you extend your knowledge of compound adjectives and look at where to stress compounds, plus words with suffixes and prefixes.",
        "6B": "The topic is behavioral addictions and obsessions, such as being addicted to shopping. (Alcohol and substance addiction aren't included as these can be sensitive subjects.) You start by studying vocabulary related to phones and technology. A pronunciation focus on the minimal pairs /æ/ and /ʌ/ follows. You then read an article by a journalist who found himself without his cell phone for an afternoon, and the effect this had on him. You then discuss the implications of dependence on cell phones. The grammar focus reviews conditional sentences and introduces mixed conditionals plus alternatives to if such as as long as and provided that. In the second half, you work on dependent prepositions after adjectives (addicted to, hooked on). You then listen to a doctor talking about addictions and how to deal with them. In Speaking, you talk about yourself or people you know who have behavioral addictions. The writing section is about presenting a balanced argument in a discursive essay.",
        "7A": "The topic is control. In the first half, the angle is control in education: through a listening, you find out about the QI phenomenon — a TV quiz show and series of books based on principles the authors think should be applied to education (e.g., giving children control over their learning). The pronunciation focus is on intonation and linking in exclamations such as How annoying!. The vocabulary focus is on word formation — adding prefixes to change the meaning of a word (bilingual, anti-social, etc.). The second half focuses on the absurdity of some health and safety rules in the UK. You read a review of a book, In the Interests of Safety, which discusses rules we should or shouldn't have to follow these days. You then go into the grammar — modal verbs and other expressions used to talk about permission, obligation, and necessity — and put it into practice discussing the advantages or disadvantages of possible laws. The lesson ends with you writing a report.",
        "7B": "The topic is art. In the first half the focus is on installations and modern sculptures — things many people find difficult to accept as art. You try to identify which photos show works of art and which ordinary objects, then listen to an expert explaining which pieces are works of art, what they're trying to convey, and the best way to enjoy seeing them in a gallery. In the grammar focus you work on verbs of the senses and the structures that follow them. The pronunciation focus is on the letters -ure, which can be pronounced /ər/ or /ʊr/ (sculpture, allure). The first half ends with you learning the words for six different kinds of art, discussing favorite works of art, artists, museums, and art galleries, and the images you have in your house or on your computer or phone. In the second part, you read and listen to an article about a famous forger, Wolfgang Beltracchi, and how he and his wife managed to fool the art world. This leads into a speaking activity on fake items and your attitude toward buying something fake. In Vocabulary, you look at some idioms with colors (out of the blue, etc.).",
        "CE4": "In this lesson the person interviewed is the artist and illustrator Quentin Blake, probably the best-known British illustrator of children's books. In a three-part interview he talks about why he became an illustrator, the relationship between author and illustrator (and in particular his relationship with Roald Dahl), and how he goes about producing his illustrations. A language focus follows on how Quentin Blake uses the verb get, which reviews and extends what you learned in lesson 3A. In the ON THE STREET section, people answer the questions Is there a book that you particularly liked or like because of the illustrations? and Do you have a favorite painting or poster in your house?. The lesson ends with you talking about illustrations.",
        "8A": "The topic is health and medicine. The first half opens with a quiz on medical vocabulary, reviewing words taught in previous levels of American English File. You then read an article about treatments or habits that doctors themselves say they'd never have or do, and discuss it. A listening on four people's experiences of alternative medicine follows, then you talk about your own experiences and opinions. The second half opens with a grammar focus on gerunds and infinitives — you look at perfect, continuous, and passive gerunds and infinitives, and some new uses. You then listen to a radio show about common medical advice for everyday issues (e.g., the amount of water we should drink) and whether or not it's really true. In Vocabulary you learn some common similes, and the lesson ends focusing on the /ə/ sound.",
        "8B": "The topic is travel and tourism. In the first half, you start by doing an authentic questionnaire from www.virgin.com, a travel website, to find out what kind of traveler you are (it tends to be surprisingly accurate). This leads into vocabulary, where you learn new travel-related words and phrases. You then read a newspaper article in which the writer attacks travelers and defends the reputation of tourists. The writing focus is on a discursive essay arguing in favor of or against a statement — here, the topic is tourism. In the second half, the grammar (language for expressing future plans and arrangements) is presented through a series of WhatsApp messages. You then move on to a listening about a disastrous flight. The Speaking is about your own bad journeys. The pronunciation focus is on homophones — words pronounced the same but spelled differently (site and sight, etc.).",
        "9A": "The topic of the first part is animals; the second part is vegetarianism and various controversial issues relating to animals. In the first half, you read a newspaper article about a journalist's attitude toward pets. You then expand your vocabulary related to animals and the natural world, which you put into practice in a speaking activity, followed by a focus on idioms and sayings with animals. The second half opens with a grammar focus on ellipsis, followed by the pronunciation of weak and strong forms of auxiliary verbs and to. You then listen to a radio show where two people debate the pros and cons of being vegetarian. This sets up the discussions in Speaking, where you debate various animal issues, such as zoos and hunting.",
        "9B": "The topic is food. In the first half, the focus is on eating out. You start by expanding your vocabulary related to ways of preparing food, which will help you understand menus in English. A pronunciation focus follows on words with silent syllables (vegetables, chocolate). You then listen to some tips about eating out from a book written by a well-known British food critic, discuss them, and talk about your own experiences of eating out. This half of the lesson ends with you writing an email of complaint. In the second half, the focus shifts to eating in. You first study the grammar of compound and possessive nouns (a recipe book, a chef's hat). You then read a magazine article about comfort food — food that often provides a nostalgic or sentimental feeling to the person eating it — where well-known people talk about their choices, and you talk about yours. The lesson ends with a vocabulary section on food adjectives ending in -y (salty, creamy, etc.).",
        "CE5": "In this lesson the person interviewed is George McGavin, a well-known entomologist. In a three-part interview he talks about why he became interested in arthropods (insects, spiders, and crustacea), why he thinks people have phobias of insects, and how he feels about killing and eating insects. A language focus follows on the informal and vague language he uses. In the ON THE STREET section, people answer the questions What's the most interesting wild animal that you've ever seen in the wild? and Is there anywhere you'd particularly like to go to see animals or the natural world?. The lesson ends with you talking about insects and the natural world.",
        "10A": "The topic is emigrating to another country. The lesson opens with listening and speaking: you hear a British couple who emigrated to Spain in 1997 talking about their experiences, then talk about people you know who have gone to live in another country, with the pros and cons. The grammar section follows, where you work on adding emphasis by using clauses or phrases that emphasize one part of a sentence (sometimes called cleft sentences). In Pronunciation, you work on the intonation patterns in this kind of sentence. The first half ends with a speaking activity in which you complete some cleft sentence stems with your own ideas and compare them with a partner. In the second half, you read and discuss an article by Angela Masajo, a college student who was born in the Philippines and recently got American citizenship. The vocabulary focus is on words that are often confused (foreigner and stranger, etc.). Immigration is very much part of the modern world but can be a sensitive topic — the lesson keeps the discussion broad rather than asking you to talk about immigration in your own country directly.",
        "10B": "This lesson focuses on two different angles on sports. In the first half, you read a newspaper article, Battle of the workouts, which compares similar activities (tennis and squash, yoga and Pilates, etc.) that people might take up to get in shape, and looks at the pros and cons of each. A focus on word building follows: forming nouns and verbs from common adjectives (strong, long, deep, etc.). In the second half, there's a pronunciation focus on homographs — words spelled the same but pronounced differently according to meaning (row, etc.). You then work on relative clauses, both defining and non-defining. Finally, you look at some statements from a controversial new book criticizing sports called Foul Play, and listen to an interview with a well-known American sports journalist, Ron Kantowski, in which he gives his opinion on these issues.",
    },
}


def _to_student_voice(course_id: str, lesson_code: str, original: str) -> str:
    """Return a student-voice rewrite if we have a hand-crafted one; else
    fall back to the original TG paragraph."""
    return STUDENT_VOICE_SUMMARIES.get(course_id, {}).get(lesson_code, original)


SECTION_RE = re.compile(
    r"(?m)^\s*(\d+)\s*\t+\s*"
    r"(?:[a-z]\s+)?"                       # optional icon prefix (e.g. 'r ')
    r"([A-Z][A-Z &/-]{2,60})"              # uppercase title
    r"(?:\s{2,}(.{0,80}?))?\s*$"           # optional subtitle
)
LEADIN_RE = re.compile(r"(?m)^\s*OPTIONAL\s+LEAD-?IN[^\n]*", re.IGNORECASE)
NOISE_PREFIX = re.compile(r"^(?:e\s+\d|Focus on|Play |Tell |Get |Read |Books |Now |Ask |Highlight)", re.IGNORECASE)


def _clean_subtitle(s: str) -> str:
    """Cut the subtitle at audio markers / sentence starts."""
    if not s:
        return ""
    s = re.sub(r"\s+e\s+\d.*$", "", s)        # cut at "e 5.21"
    s = re.sub(r"\s+/.*$", "", s) if s.startswith("/") else s
    s = s.strip(" .,;:")
    if NOISE_PREFIX.match(s):
        return ""
    if len(s) > 70:
        s = s[:70].rsplit(" ", 1)[0] + "…"
    return s


# Section names commonly seen in Review & Check pages.
RC_SECTIONS = [
    ("vocab",   r"^\s*VOCABULARY\s*$"),
    ("gram",    r"^\s*GRAMMAR\s*$"),
    ("pron",    r"^\s*PRONUNCIATION\s*$"),
    ("read",    r"CAN\s+YOU\s+understand\s+this\s+text\??"),
    ("listen",  r"CAN\s+YOU\s+understand\s+these\s+people\??"),
    ("speak",   r"CAN\s+YOU\s+say\s+this\s+in\s+English\??"),
]


def find_all_lesson_plans(doc) -> list[tuple[int, str]]:
    """Walk the whole TG, return ordered list of (page, paragraph) for each
    'Lesson plan' heading found. Skips false positives from front matter and
    from incidental occurrences inside exercise text."""
    results: list[tuple[int, str]] = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        for m in LESSON_PLAN_RE.finditer(text):
            after = text[m.end():]
            end_m = END_RE.search(after)
            chunk = after[:end_m.start()] if end_m else after
            cleaned = clean_paragraph(chunk.strip())
            cleaned = re.sub(r"\n\s*[GVP]\s+[a-z].*$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
            if len(cleaned) < 80:
                continue
            if cleaned.lower().startswith(("step", "all lesson", "this teacher")):
                continue
            # Real lesson plan paragraphs always start with a capital letter
            # describing the lesson ("This lesson…", "The context…", "In this
            # lesson…").  False positives that match "Lesson plan" inside
            # exercise instructions tend to start with punctuation or with an
            # imperative verb addressed to the teacher (Focus on…, Tell Sts…).
            first = cleaned.lstrip()
            if not first or not first[0].isalpha() or not first[0].isupper():
                continue
            if re.match(r"^(Focus on|Tell Sts|Get Sts|Play the audio|Now play|Highlight|Ask Sts|Remind Sts|Books open|Books closed|Put Sts|Check answers|Elicit|Demonstrate)\b", first):
                continue
            results.append((i + 1, cleaned))
    return results


def fallback_summary(lesson: dict) -> str:
    """Generate a short summary from topics when TG doesn't provide one."""
    t = lesson.get("topics", {})
    bits: list[str] = []
    if lesson["type"] == "practical_english":
        fn = t.get("function", "").strip()
        voc = t.get("vocabulary", "").strip()
        pron = t.get("pronunciation", "").strip()
        if fn:
            bits.append(f"Inglês funcional: {fn}.")
        if voc:
            bits.append(f"Vocabulário: {voc}.")
        if pron:
            bits.append(f"Pronúncia: {pron}.")
    elif lesson["type"] == "review":
        covers = lesson.get("covers_files", [])
        if covers:
            bits.append(
                f"Revisão dos Files {' e '.join(map(str, covers))}: consolidação de gramática, vocabulário, pronúncia, listening e leitura. "
                "Inclui exercícios de Can you…?, listening, leitura e teste de comunicação oral."
            )
    else:  # lesson
        if t.get("grammar"):
            bits.append(f"Ponto gramatical: {t['grammar']}.")
        if t.get("vocabulary"):
            bits.append(f"Vocabulário: {t['vocabulary']}.")
        if t.get("pronunciation"):
            bits.append(f"Pronúncia: {t['pronunciation']}.")
        spk = t.get("speaking") or ""
        lis = t.get("listening") or ""
        rd  = t.get("reading") or ""
        skills = [s for s in (spk, lis, rd) if s.strip()]
        if skills:
            bits.append("Atividades de produção/compreensão: " + "; ".join(skills) + ".")
    return " ".join(bits).strip() or "Sem resumo disponível."


def _lesson_text_range(doc, lessons: list[dict], idx: int) -> str:
    """Concatenate text from this lesson's TG pages until the next lesson starts."""
    cur = lessons[idx]
    nxt_page = lessons[idx + 1]["tg_page"] if idx + 1 < len(lessons) else len(doc) + 1
    parts: list[str] = []
    for p in range(cur["tg_page"] - 1, min(nxt_page - 1, len(doc))):
        parts.append(doc[p].get_text("text"))
    return "\n".join(parts), cur["tg_page"], nxt_page - 1


def extract_steps_for_normal_lesson(doc, lessons: list[dict], idx: int) -> list[dict]:
    """For Lessons A/B and PE: numbered sections only.
    (The 'OPTIONAL LEAD-IN (books closed)' from the TG is a classroom warm-up
    for the teacher — it doesn't apply to self-study, so we skip it.)"""
    text, first_page, last_page = _lesson_text_range(doc, lessons, idx)
    steps: list[dict] = []
    seen_numbers: set[int] = set()
    for m in SECTION_RE.finditer(text):
        n = int(m.group(1))
        if n in seen_numbers:
            continue
        title = m.group(2).strip()
        subtitle = _clean_subtitle(m.group(3) or "")
        # Reject titles that look like noise
        if len(title) < 3:
            continue
        if title in {"RAD TIME", "EPISODE"}:
            continue
        seen_numbers.add(n)
        steps.append({
            "id": str(n),
            "number": n,
            "label": title,
            "subtitle": subtitle,
            "type": "section",
        })
    steps.sort(key=lambda s: s.get("number", 0))
    return steps


def extract_steps_for_review(doc, lessons: list[dict], idx: int) -> list[dict]:
    """For Review & Check: detect known bold section markers."""
    text, _, _ = _lesson_text_range(doc, lessons, idx)
    steps: list[dict] = []
    for sid, pattern in RC_SECTIONS:
        if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            label = {
                "vocab":  "VOCABULARY",
                "gram":   "GRAMMAR",
                "pron":   "PRONUNCIATION",
                "read":   "CAN YOU understand this text?",
                "listen": "CAN YOU understand these people?",
                "speak":  "CAN YOU say this in English?",
            }[sid]
            steps.append({"id": sid, "label": label, "type": "section"})
    return steps


def enrich_with_summaries(course_data: dict) -> None:
    """Open the TG PDF and add a 'summary' to each lesson.

    Strategy: scan the TG once to find every 'Lesson plan' paragraph (in PDF
    order), then assign them to non-review lessons sequentially.  This is
    robust against running-header drift (e.g. the next lesson's plan appearing
    on the previous lesson's last page).
    """
    pdf_path = ROOT / course_data["tg_pdf_path"]
    if not pdf_path.exists():
        print(f"  TG PDF não encontrado: {pdf_path}")
        return
    doc = fitz.open(pdf_path)
    plans = find_all_lesson_plans(doc)
    non_review = [l for l in course_data["lessons"] if l["type"] != "review"]
    if len(plans) < len(non_review):
        print(f"  Aviso: {len(plans)} planos encontrados, {len(non_review)} aulas esperam plano.")
    plan_iter = iter(plans)
    for lesson in course_data["lessons"]:
        if lesson["type"] == "review":
            lesson["summary"] = fallback_summary(lesson)
            lesson["summary_source"] = "topics"
            continue
        try:
            page, paragraph = next(plan_iter)
        except StopIteration:
            lesson["summary"] = fallback_summary(lesson)
            lesson["summary_source"] = "topics"
            continue
        lesson["summary"] = _to_student_voice(course_data["id"], lesson["code"], paragraph)
        lesson["summary_source"] = "tg"
        # Use the actual page where the Lesson plan paragraph lives so the
        # "Ver plano no TG" deep link lands exactly on the summary.
        lesson["tg_page"] = page

    # Now extract steps (depends on final tg_page values)
    lessons = course_data["lessons"]
    for i, lesson in enumerate(lessons):
        if lesson["type"] == "review":
            lesson["steps"] = extract_steps_for_review(doc, lessons, i)
        else:
            lesson["steps"] = extract_steps_for_normal_lesson(doc, lessons, i)
        # Fallback for lessons with no detectable structure (e.g., 12B board game)
        if not lesson["steps"]:
            lesson["steps"] = [
                {"id": "complete", "label": "Completar a aula", "type": "section"}
            ]
        # Workbook and ChatGPT conversation are surfaced inside the
        # "Recursos desta aula" section now (handled in the frontend).
    doc.close()


def _attach_music(course_id: str, lessons: list[dict]) -> None:
    pool = MUSIC.get(course_id, {})
    for lesson in lessons:
        song = pool.get(lesson["code"])
        if song:
            lesson["music"] = song


def main() -> None:
    for cid, data in COURSES.items():
        enrich_with_summaries(data)
        _attach_music(cid, data["lessons"])
        out = OUT_DIR / f"{cid}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        from_tg = sum(1 for l in data["lessons"] if l.get("summary_source") == "tg")
        total_steps = sum(len(l.get("steps", [])) for l in data["lessons"])
        print(f"Wrote {out} ({len(data['lessons'])} lessons, {from_tg} resumos extraídos do TG, {total_steps} steps no total)")


if __name__ == "__main__":
    main()
