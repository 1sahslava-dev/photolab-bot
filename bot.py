"""
PHOTO LAB by V.F. — Telegram Quiz Bot
Тест после каждой темы + контрольный тест + сертификат при 100%
"""

import os
import io
import json
import logging
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Google Sheets ──
SPREADSHEET_ID = "1mYegUYatBVeOIrFmb6BWgqhFglgTHoc_KbJUOIwEqHU"
SHEET_NAME = "Лист1"
TOPICS_SHEET_NAME = "Темы"
QUESTIONS_SHEET_NAME = "Вопросы"

# Telegram user_id администратора курса — только ему доступна команда /reload.
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "773394538"))

def get_sheets_client():
    """Получить клиент Google Sheets из переменной окружения."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if not creds_json:
            logger.warning("GOOGLE_CREDENTIALS не найден")
            return None
        creds_data = json.loads(creds_json)
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logger.error(f"Ошибка подключения к Google Sheets: {e}")
        return None


def save_result_to_sheets(user_id: int, username: str, topic_key: str,
                           score: int, total: int):
    """Сохранить результат теста в Google Sheets."""
    try:
        client = get_sheets_client()
        if not client:
            return
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        sheet.append_row([user_id, username, topic_key, score, total, date_str])
        logger.info(f"Результат сохранён: {user_id} {topic_key} {score}/{total}")
    except Exception as e:
        logger.error(f"Ошибка сохранения в Sheets: {e}")


def load_results_from_sheets(user_id: int) -> dict:
    """Загрузить результаты пользователя из Google Sheets."""
    try:
        client = get_sheets_client()
        if not client:
            return {}
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        all_rows = sheet.get_all_values()
        results = {}
        for row in all_rows[1:]:  # пропускаем заголовок
            if len(row) >= 5 and str(row[0]) == str(user_id):
                topic_key = row[2]
                try:
                    results[topic_key] = {
                        "score": int(row[3]),
                        "total": int(row[4])
                    }
                except (ValueError, IndexError):
                    pass
        return results
    except Exception as e:
        logger.error(f"Ошибка загрузки из Sheets: {e}")
        return {}
async def ensure_results_loaded(user_id: int, state: dict):
    """Догружает результаты из Google Sheets, если в памяти бота их нет (например, после рестарта на Railway)."""
    if not state.get("results"):
        saved = load_results_from_sheets(user_id)
        if saved:
            state["results"] = saved
            logger.info(f"Догружены результаты для {user_id}: {saved}")


# ─────────────────────────────────────────
#  ЗАГРУЗКА КУРСА ИЗ GOOGLE ТАБЛИЦЫ
# ─────────────────────────────────────────
LETTERS = ["A", "B", "C", "D"]


def _clean(value) -> str:
    return str(value).strip() if value is not None else ""


def load_course_from_sheets():
    """
    Строит список тем курса (COURSE) из двух вкладок таблицы:
    "Темы" (module, topic, title, subtitle, intro, active) и
    "Вопросы" (module, topic, question_order, text,
    option_a..option_d, correct, explanation).
    Возвращает None при ошибке подключения/формата — тогда прежний
    COURSE в памяти бота не трогаем.
    """
    client = get_sheets_client()
    if not client:
        logger.error("Нет подключения к Google Sheets — курс не обновлён")
        return None
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        topics_rows = spreadsheet.worksheet(TOPICS_SHEET_NAME).get_all_records()
        questions_rows = spreadsheet.worksheet(QUESTIONS_SHEET_NAME).get_all_records()

        questions_by_topic = {}
        for row in questions_rows:
            try:
                key = (int(row["module"]), int(row["topic"]))
            except (KeyError, ValueError):
                continue
            questions_by_topic.setdefault(key, []).append(row)

        course = []
        for row in topics_rows:
            try:
                module = int(row["module"])
                topic = int(row["topic"])
            except (KeyError, ValueError):
                continue

            active_val = _clean(row.get("active", "TRUE")).upper()
            if active_val in ("FALSE", "0", "НЕТ", "ЛОЖЬ"):
                continue

            q_rows = sorted(
                questions_by_topic.get((module, topic), []),
                key=lambda r: int(r.get("question_order", 0) or 0)
            )
            questions = []
            for q in q_rows:
                options = [_clean(q.get(f"option_{l.lower()}")) for l in LETTERS]
                options = [o for o in options if o]
                if len(options) < 2:
                    continue
                correct_letter = _clean(q.get("correct")).upper()
                correct_index = LETTERS.index(correct_letter) if correct_letter in LETTERS[:len(options)] else 0

                text = _clean(q.get("text"))
                if text and not text.startswith("❓"):
                    text = f"❓ {text}"

                explanation_text = _clean(q.get("explanation"))
                correct_option_text = options[correct_index]

                questions.append({
                    "text": text,
                    "options": options,
                    "correct": correct_index,
                    "explanation": f"✅ Верно!\n{explanation_text}",
                    "wrong_explanation": (
                        f"❌ Не совсем.\nПравильный ответ: *«{correct_option_text}»*.\n{explanation_text}"
                    ),
                })

            if not questions:
                continue

            course.append({
                "module": module,
                "topic": topic,
                "title": _clean(row.get("title")),
                "subtitle": _clean(row.get("subtitle")),
                "intro": _clean(row.get("intro")),
                "questions": questions,
            })

        course.sort(key=lambda t: (t["module"], t["topic"]))
        return course
    except Exception as e:
        logger.error(f"Ошибка загрузки курса из Sheets: {e}")
        return None


def apply_course(new_course: list):
    """Заменяет глобальный COURSE и пересобирает индекс тем."""
    global COURSE, TOPICS_INDEX
    COURSE = new_course
    TOPICS_INDEX = {
        f"m{t['module']}_t{t['topic']}": i
        for i, t in enumerate(COURSE)
    }
# ── Регистрация шрифтов ──
# Шрифты лежат в репозитории (папка fonts/) — не полагаемся на системные
# шрифты хостинга, их может не быть на Railway/другом сервере.
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
try:
    pdfmetrics.registerFont(TTFont('R',   os.path.join(FONTS_DIR, 'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('RB',  os.path.join(FONTS_DIR, 'DejaVuSans-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('RI',  os.path.join(FONTS_DIR, 'DejaVuSans-Oblique.ttf')))
    pdfmetrics.registerFont(TTFont('RS',  os.path.join(FONTS_DIR, 'DejaVuSerif.ttf')))
    pdfmetrics.registerFont(TTFont('RSB', os.path.join(FONTS_DIR, 'DejaVuSerif-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('RSI', os.path.join(FONTS_DIR, 'DejaVuSerif-Italic.ttf')))
    FONTS_OK = True
except Exception as e:
    logger.warning(f"Шрифты не загружены: {e}")
    FONTS_OK = False

# ─────────────────────────────────────────
#  КУРС
# ─────────────────────────────────────────
# Список тем заполняется динамически из Google Таблицы при старте бота
# (см. load_course_from_sheets / apply_course) и обновляется командой /reload.
COURSE = []
MILESTONE_TESTS = {
    10: {
        "title": "Контрольный тест · Модуль 1",
        "description": "Проверь знания по всем темам Модуля 1",
        "module_name": "Модуль 1 — Истоки фотографии",
        "topics_count": 10,
        "unlock_message": (
            "🏆 *Ты прошёл все 10 тем Модуля 1!*\n\n"
            "Время проверить, как всё сложилось в голове.\n"
            "7 вопросов по всем темам модуля — вперемешку.\n\n"
            "Готов к контрольному тесту? 👇"
        ),
        "questions": [
            {
                "text": "❓ Что такое Camera Obscura?",
                "options": [
                    "Первый цифровой фотоаппарат",
                    "Тёмная комната с маленьким отверстием для проекции изображения",
                    "Метод проявки плёнки",
                ],
                "correct": 1,
                "explanation": "✅ Верно! Camera Obscura — тёмное пространство, в котором свет через маленькое отверстие создаёт перевёрнутое изображение.",
                "wrong_explanation": "❌ Правильный ответ: *«Тёмная комната с маленьким отверстием»*.",
            },
            {
                "text": "❓ Почему изображение в Camera Obscura перевёрнутое?",
                "options": [
                    "Из-за зеркала внутри",
                    "Световые лучи пересекаются в точке отверстия",
                    "Из-за формы линзы",
                ],
                "correct": 1,
                "explanation": "✅ Верно! Лучи пересекаются в отверстии и меняются местами.",
                "wrong_explanation": "❌ Правильный ответ: *«Световые лучи пересекаются в точке отверстия»*.",
            },
            {
                "text": "❓ Кто первым научно описал принцип Camera Obscura?",
                "options": [
                    "Леонардо да Винчи",
                    "Ибн аль-Хайсам",
                    "Жозеф Ньепс",
                ],
                "correct": 1,
                "explanation": "✅ Верно! Ибн аль-Хайсам описал принцип в «Книге оптики» около 1000 г. н.э.",
                "wrong_explanation": "❌ Правильный ответ: *«Ибн аль-Хайсам»*.",
            },
            {
                "text": "❓ Кто создал первую сохранившуюся фотографию?",
                "options": [
                    "Луи Дагерр",
                    "Жозеф Нисефор Ньепс",
                    "Уильям Тальбот",
                ],
                "correct": 1,
                "explanation": "✅ Верно! Ньепс в 1826–1827 годах получил первое стабильное фотографическое изображение.",
                "wrong_explanation": "❌ Правильный ответ: *«Жозеф Нисефор Ньепс»*.",
            },
            {
                "text": "❓ Как назывался метод съёмки Ньепса?",
                "options": [
                    "Дагерротип",
                    "Гелиография",
                    "Тальботипия",
                ],
                "correct": 1,
                "explanation": "✅ Верно! Гелиография — «рисование солнцем».",
                "wrong_explanation": "❌ Правильный ответ: *«Гелиография»*.",
            },
            {
                "text": "❓ На чём Ньепс зафиксировал первую фотографию?",
                "options": [
                    "На бумаге с серебром",
                    "На стеклянной пластине",
                    "На металлической пластине с битумным покрытием",
                ],
                "correct": 2,
                "explanation": "✅ Верно! Металлическая пластина с битумом Иудейским.",
                "wrong_explanation": "❌ Правильный ответ: *«Металлическая пластина с битумным покрытием»*.",
            },
            {
                "text": "❓ Что объединяет Camera Obscura и изобретение Ньепса?",
                "options": [
                    "Оба используют цифровую матрицу",
                    "Оба основаны на принципе: свет → отверстие → изображение",
                    "Оба изобретены в одно время",
                ],
                "correct": 1,
                "explanation": "✅ Верно! Ньепс взял принцип Camera Obscura и добавил светочувствительный материал.",
                "wrong_explanation": "❌ Правильный ответ: *«Оба основаны на принципе: свет → отверстие → изображение»*.",
            },
        ],
    },
}

TOPICS_INDEX = {}

# ─────────────────────────────────────────
#  ГЕЙМИФИКАЦИЯ: XP, УРОВНИ, ЗНАЧКИ
# ─────────────────────────────────────────
XP_PER_TOPIC = 20  # максимум XP за тему при 100% правильных ответов
MODULE_TOTAL_TOPICS = 10  # столько тем в модуле по плану (порог контрольного теста)

LEVELS = [
    (0,   "Новичок 🌱"),
    (40,  "Любитель 📷"),
    (80,  "Практик 🎞️"),
    (120, "Знаток истории 📚"),
    (160, "Мастер модуля 🏅"),
    (200, "Фотоисторик 🏆"),
]

BADGES = {
    "perfect_start": {
        "emoji": "🥇",
        "title": "Идеальный старт",
        "desc": "100% в первой пройденной теме",
    },
    "no_mistakes_streak": {
        "emoji": "🔥",
        "title": "Без ошибок",
        "desc": "3 темы подряд на 100%",
    },
    "module_complete": {
        "emoji": "📸",
        "title": "Историк фотографии",
        "desc": "Все темы модуля пройдены",
    },
    "perfectionist": {
        "emoji": "💯",
        "title": "Перфекционист",
        "desc": "Все темы модуля на 100%",
    },
}


def calc_topic_xp(score: int, total: int) -> int:
    if not total:
        return 0
    return round(XP_PER_TOPIC * score / total)


def calc_total_xp(results: dict) -> int:
    return sum(calc_topic_xp(r.get("score", 0), r.get("total", 0)) for r in results.values())


def get_level(xp: int):
    """Возвращает (текущий_уровень_название, xp_текущего_порога, следующий_уровень_название, xp_следующего_порога)."""
    current_name, current_threshold = LEVELS[0][1], LEVELS[0][0]
    next_name, next_threshold = None, None
    for i, (threshold, name) in enumerate(LEVELS):
        if xp >= threshold:
            current_name, current_threshold = name, threshold
            if i + 1 < len(LEVELS):
                next_threshold, next_name = LEVELS[i + 1]
            else:
                next_threshold, next_name = None, None
        else:
            break
    return current_name, current_threshold, next_name, next_threshold


def calc_badges(results: dict) -> set:
    """Возвращает множество id значков, заработанных на основе текущих результатов."""
    earned = set()
    ordered_keys = [f"m{t['module']}_t{t['topic']}" for t in COURSE]

    completed_in_order = [k for k in ordered_keys if k in results]
    if completed_in_order:
        first = results[completed_in_order[0]]
        if first.get("total") and first["score"] == first["total"]:
            earned.add("perfect_start")

    streak = 0
    for k in ordered_keys:
        r = results.get(k)
        if r and r.get("total") and r["score"] == r["total"]:
            streak += 1
            if streak >= 3:
                earned.add("no_mistakes_streak")
        else:
            streak = 0

    completed = len(results)
    if completed >= MODULE_TOTAL_TOPICS:
        earned.add("module_complete")
        if all(
            results.get(k) and results[k].get("total") and results[k]["score"] == results[k]["total"]
            for k in ordered_keys
        ):
            earned.add("perfectionist")

    return earned


def xp_bar(xp: int, current_threshold: int, next_threshold):
    if next_threshold is None:
        return "█" * 10
    span = next_threshold - current_threshold
    done = xp - current_threshold
    filled = min(10, max(0, round(10 * done / span))) if span else 10
    return "█" * filled + "░" * (10 - filled)


# ─────────────────────────────────────────
#  ГЕНЕРАЦИЯ СЕРТИФИКАТА
# ─────────────────────────────────────────
def generate_certificate(name: str, milestone_n: int, date_str: str, cert_num: str) -> io.BytesIO:
    mt = MILESTONE_TESTS[milestone_n]
    W, H = landscape(A4)

    GOLD  = HexColor('#c9a84c')
    GOLD2 = HexColor('#e8c96a')
    NAVY  = HexColor('#0e1b2e')
    CREAM2= HexColor('#e8dcc0')
    GRAPH = HexColor('#4a4a5a')
    BEIGE = HexColor('#faf7f0')
    BEIGE2= HexColor('#f0ead8')

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))

    # Background
    c.setFillColor(BEIGE);  c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(BEIGE2)
    for x,y in [(0,0),(W-60,0),(0,H-60),(W-60,H-60)]:
        c.rect(x,y,60,60,fill=1,stroke=0)

    # Borders
    c.setStrokeColor(GOLD);  c.setLineWidth(3);   c.rect(20,20,W-40,H-40,fill=0,stroke=1)
    c.setStrokeColor(GOLD2); c.setLineWidth(0.8); c.rect(26,26,W-52,H-52,fill=0,stroke=1)
    c.setStrokeColor(NAVY);  c.setLineWidth(0.4); c.rect(30,30,W-60,H-60,fill=0,stroke=1)

    # Corner ornaments
    def corner(cx, cy, rot):
        c.saveState(); c.translate(cx,cy); c.rotate(rot)
        c.setStrokeColor(GOLD); c.setLineWidth(1.5)
        c.line(0,0,35,0); c.line(0,0,0,35)
        c.setLineWidth(0.7); c.line(8,0,8,8); c.line(0,8,8,8)
        c.setFillColor(GOLD); c.circle(0,0,3,fill=1,stroke=0)
        c.restoreState()

    corner(32,32,0); corner(W-32,32,90); corner(W-32,H-32,180); corner(32,H-32,270)

    # Header
    c.setFillColor(NAVY); c.rect(20,H-100,W-40,80,fill=1,stroke=0)
    c.setStrokeColor(GOLD);  c.setLineWidth(0.8); c.line(20,H-100,W-20,H-100)
    c.setStrokeColor(GOLD2); c.setLineWidth(0.4); c.line(20,H-104,W-20,H-104)
    c.setFillColor(GOLD);  c.setFont('RSB',11)
    c.drawCentredString(W/2, H-62, 'PHOTO LAB by V.F.')
    c.setFillColor(CREAM2); c.setFont('RI',8)
    c.drawCentredString(W/2, H-76, 'Курс по истории и практике фотографии')
    c.setStrokeColor(GOLD); c.setLineWidth(0.5)
    c.line(W/2-160,H-66,W/2-100,H-66)
    c.line(W/2+100,H-66,W/2+160,H-66)

    # Certificate label
    c.setFillColor(NAVY); c.setFont('RB',9)
    c.drawCentredString(W/2, H-130, 'С Е Р Т И Ф И К А Т')
    c.setStrokeColor(GOLD);  c.setLineWidth(1.5); c.line(W/2-80,H-135,W/2+80,H-135)
    c.setStrokeColor(GOLD2); c.setLineWidth(0.4); c.line(W/2-90,H-138,W/2+90,H-138)

    # Title
    c.setFillColor(NAVY); c.setFont('RSB',16)
    c.drawCentredString(W/2, H-168, 'об успешном прохождении')
    c.setFillColor(GRAPH); c.setFont('RS',11)
    c.drawCentredString(W/2, H-186, mt['module_name'])

    # Divider
    c.setStrokeColor(GOLD); c.setLineWidth(0.6)
    c.line(W/2-200,H-200,W/2-30,H-200)
    c.line(W/2+30,H-200,W/2+200,H-200)
    c.setFillColor(GOLD)
    c.circle(W/2,H-200,3,fill=1,stroke=0)
    c.circle(W/2-28,H-200,1.5,fill=1,stroke=0)
    c.circle(W/2+28,H-200,1.5,fill=1,stroke=0)

    # Awarded to
    c.setFillColor(GRAPH); c.setFont('RI',10)
    c.drawCentredString(W/2, H-224, 'настоящим подтверждает, что')

    # Name
    c.setFillColor(NAVY); c.setFont('RSB',32)
    c.drawCentredString(W/2, H-268, name)
    c.setStrokeColor(GOLD); c.setLineWidth(1.2)
    c.line(W/2-180,H-278,W/2+180,H-278)

    # Description
    c.setFillColor(GRAPH); c.setFont('RS',10)
    c.drawCentredString(W/2, H-304, f'успешно прошёл(-а) курс «{mt["module_name"]}»,')
    c.drawCentredString(W/2, H-320, 'продемонстрировав отличные знания истории и принципов фотографии.')

    # Score badge
    bx, by2 = W/2, H-375
    c.setFillColor(NAVY);  c.circle(bx,by2,34,fill=1,stroke=0)
    c.setStrokeColor(GOLD);  c.setLineWidth(2);   c.circle(bx,by2,34,fill=0,stroke=1)
    c.setStrokeColor(GOLD2); c.setLineWidth(0.8); c.circle(bx,by2,30,fill=0,stroke=1)
    c.setFillColor(GOLD);  c.setFont('RSB',16); c.drawCentredString(bx,by2+4,'100%')
    c.setFillColor(CREAM2); c.setFont('R',7);   c.drawCentredString(bx,by2-10,'результат')

    # Bottom info boxes — по центру
    box_w=160; box_h=44; gap=16
    total_w = 3*box_w + 2*gap
    start_x = W/2 - total_w/2
    by3 = 48

    for i,(lbl,val) in enumerate([
        ('Модуль',       '1 из 1'),
        ('Тем пройдено', f'{mt["topics_count"]} из {mt["topics_count"]}'),
        ('Дата выдачи',  date_str),
    ]):
        bx3 = start_x + i*(box_w+gap)
        c.setFillColor(BEIGE2)
        c.setStrokeColor(GOLD); c.setLineWidth(0.6)
        c.roundRect(bx3,by3,box_w,box_h,3,fill=1,stroke=1)
        c.setFillColor(GOLD);  c.setFont('RB',7)
        c.drawCentredString(bx3+box_w/2, by3+30, lbl.upper())
        c.setFillColor(NAVY);  c.setFont('RSB',11)
        c.drawCentredString(bx3+box_w/2, by3+13, val)

    # Cert ID
    c.setFillColor(HexColor('#bbbbbb')); c.setFont('R',6.5)
    c.drawCentredString(W/2, 33, f'Сертификат № {cert_num}  •  photolabvf  •  PHOTO LAB by V.F.')

    c.save()
    buf.seek(0)
    return buf


# ─────────────────────────────────────────
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────

def get_state(context):
    if "state" not in context.user_data:
        context.user_data["state"] = {
            "topic_key": None, "q_index": 0,
            "score": 0, "total": 0, "answered": False,
            "results": {}, "milestone_shown": set(),
            "in_milestone": False, "milestone_n": None,
            "m_q_index": 0, "m_score": 0, "m_answered": False,
            "awaiting_name": False, "cert_milestone_n": None,
            "cert_counter": 0,
        }
    return context.user_data["state"]


def topic_keyboard():
    buttons = []
    for t in COURSE:
        key = f"m{t['module']}_t{t['topic']}"
        label = f"М{t['module']}·Т{t['topic']} — {t['title']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"start_{key}")])
    buttons.append([InlineKeyboardButton("📊 Мой прогресс", callback_data="progress")])
    return InlineKeyboardMarkup(buttons)


def answer_keyboard(topic_key, q_index, num_options):
    letters = ["А", "Б", "В", "Г", "Д"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(letters[i], callback_data=f"ans_{topic_key}_{q_index}_{i}")]
        for i in range(num_options)
    ])


def next_keyboard(topic_key, q_index, total):
    if q_index + 1 < total:
        btn = InlineKeyboardButton("Следующий вопрос →", callback_data=f"next_{topic_key}_{q_index+1}")
    else:
        btn = InlineKeyboardButton("Посмотреть результат 🏁", callback_data=f"result_{topic_key}")
    return InlineKeyboardMarkup([[btn]])


def milestone_answer_keyboard(n, q_index, num_options):
    letters = ["А", "Б", "В", "Г", "Д"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(letters[i], callback_data=f"mans_{n}_{q_index}_{i}")]
        for i in range(num_options)
    ])


def milestone_next_keyboard(n, q_index, total):
    if q_index + 1 < total:
        btn = InlineKeyboardButton("Следующий вопрос →", callback_data=f"mnext_{n}_{q_index+1}")
    else:
        btn = InlineKeyboardButton("Посмотреть результат 🏁", callback_data=f"mresult_{n}")
    return InlineKeyboardMarkup([[btn]])


def score_emoji(score, total):
    pct = score / total if total else 0
    if pct == 1.0:    return "🏆"
    elif pct >= 0.66: return "⭐"
    else:             return "📚"


def milestone_grade(score, total):
    pct = score / total if total else 0
    if pct == 1.0:    return "🏆 Идеальный результат! Сертификат заслужен."
    elif pct >= 0.85: return "⭐ Отлично! Материал усвоен."
    elif pct >= 0.70: return "👍 Хорошо! Пара моментов требует внимания."
    elif pct >= 0.50: return "📚 Неплохо, но стоит повторить темы."
    else:             return "🔄 Рекомендуем вернуться к материалу."


async def send_question(chat_id, context, topic_key, q_index):
    topic = COURSE[TOPICS_INDEX[topic_key]]
    q = topic["questions"][q_index]
    letters = ["А", "Б", "В", "Г", "Д"]
    total = len(topic["questions"])
    options_text = "\n".join(f"*{letters[i]}* — {opt}" for i, opt in enumerate(q["options"]))
    text = f"📝 Вопрос {q_index+1} из {total}\n\n{q['text']}\n\n{options_text}"
    await context.bot.send_message(
        chat_id=chat_id, text=text, parse_mode="Markdown",
        reply_markup=answer_keyboard(topic_key, q_index, len(q["options"]))
    )


async def send_milestone_question(chat_id, context, n, q_index):
    mt = MILESTONE_TESTS[n]
    q = mt["questions"][q_index]
    letters = ["А", "Б", "В", "Г", "Д"]
    total = len(mt["questions"])
    options_text = "\n".join(f"*{letters[i]}* — {opt}" for i, opt in enumerate(q["options"]))
    text = (
        f"🎯 *Контрольный тест* — вопрос {q_index+1} из {total}\n\n"
        f"{q['text']}\n\n{options_text}"
    )
    await context.bot.send_message(
        chat_id=chat_id, text=text, parse_mode="Markdown",
        reply_markup=milestone_answer_keyboard(n, q_index, len(q["options"]))
    )


async def check_milestone(chat_id, context, state):
    completed = len(state.get("results", {}))
    shown = state.get("milestone_shown", set())
    for n, mt in MILESTONE_TESTS.items():
        if completed >= n and n not in shown:
            shown.add(n)
            state["milestone_shown"] = shown
            await context.bot.send_message(
                chat_id=chat_id,
                text=mt["unlock_message"],
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Пройти контрольный тест", callback_data=f"mstart_{n}")],
                    [InlineKeyboardButton("Позже →", callback_data="back_menu")],
                ])
            )
            return True
    return False


# ─────────────────────────────────────────
#  ХЭНДЛЕРЫ
# ─────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "друг"
    state = get_state(context)
    # Загружаем результаты из Google Sheets если память пустая
    await ensure_results_loaded(update.effective_user.id, state)
    await update.message.reply_text(
        f"👋 Привет, {name}!\n\nЭто бот курса *PHOTO LAB by V.F.*\nВыбери тему для теста:",
        parse_mode="Markdown", reply_markup=topic_keyboard()
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = get_state(context)
    await ensure_results_loaded(update.effective_user.id, state)
    await update.message.reply_text("📚 Выбери тему:", reply_markup=topic_keyboard())


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений — принимает имя для сертификата"""
    state = get_state(context)

    if state.get("awaiting_name"):
        name = update.message.text.strip()
        if len(name) < 2 or len(name) > 60:
            await update.message.reply_text(
                "Пожалуйста, введи имя и фамилию (от 2 до 60 символов)."
            )
            return

        state["awaiting_name"] = False
        n = state.get("cert_milestone_n")
        state["cert_counter"] = state.get("cert_counter", 0) + 1
        cert_num = f"PL-M1-{update.effective_user.id}-{state['cert_counter']:03d}"
        date_str = datetime.now().strftime("%d.%m.%Y")

        await update.message.reply_text("⏳ Генерирую сертификат...")

        try:
            pdf_buf = generate_certificate(name, n, date_str, cert_num)
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=pdf_buf,
                filename=f"certificate_photolab_{name.replace(' ', '_')}.pdf",
                caption=(
                    f"🏆 *Поздравляем, {name}!*\n\n"
                    f"Твой сертификат об окончании курса\n"
                    f"*«Истоки фотографии»* готов.\n\n"
                    f"№ {cert_num}"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка генерации сертификата: {e}")
            await update.message.reply_text(
                "Что-то пошло не так при создании сертификата. Попробуй ещё раз — напиши /menu."
            )
            return

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📚 Продолжай курс:",
            reply_markup=topic_keyboard()
        )
    else:
        await update.message.reply_text(
            "Используй /start для начала или /menu для выбора темы."
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    state = get_state(context)
    await ensure_results_loaded(query.from_user.id, state)
    # ── Выбор темы ──
    if data.startswith("start_"):
        topic_key = data[6:]
        if topic_key not in TOPICS_INDEX:
            await query.edit_message_text("Тема не найдена.")
            return
        topic = COURSE[TOPICS_INDEX[topic_key]]
        state.update({
            "topic_key": topic_key, "q_index": 0,
            "score": 0, "total": len(topic["questions"]),
            "answered": False, "in_milestone": False,
        })
        await query.edit_message_text(topic["intro"], parse_mode="Markdown")
        await send_question(query.message.chat_id, context, topic_key, 0)

    # ── Ответ ──
    elif data.startswith("ans_"):
        parts = data.split("_")
        choice = int(parts[-1]); q_index = int(parts[-2])
        topic_key = "_".join(parts[1:-2])
        if state.get("answered"): return
        state["answered"] = True
        topic = COURSE[TOPICS_INDEX[topic_key]]
        q = topic["questions"][q_index]
        is_correct = (choice == q["correct"])
        if is_correct: state["score"] += 1; reply = q["explanation"]
        else: reply = q["wrong_explanation"]
        reply += f"\n\n_Вопрос {q_index+1} из {len(topic['questions'])}_"
        await context.bot.send_message(
            chat_id=query.message.chat_id, text=reply, parse_mode="Markdown",
            reply_markup=next_keyboard(topic_key, q_index, len(topic["questions"]))
        )

    # ── Следующий вопрос ──
    elif data.startswith("next_"):
        parts = data.split("_")
        q_index = int(parts[-1]); topic_key = "_".join(parts[1:-1])
        state["answered"] = False
        await send_question(query.message.chat_id, context, topic_key, q_index)

    # ── Результат темы ──
    elif data.startswith("result_"):
        topic_key = data[7:]
        topic = COURSE[TOPICS_INDEX[topic_key]]
        score = state["score"]; total = state["total"]

        # XP и уровень ДО обновления результата темы (чтобы поймать level-up)
        xp_before = calc_total_xp(state.get("results", {}))
        level_before, *_ = get_level(xp_before)
        badges_before = calc_badges(state.get("results", {}))

        state["results"][topic_key] = {"score": score, "total": total}

        xp_gained = calc_topic_xp(score, total)
        xp_after = calc_total_xp(state["results"])
        level_after, lvl_threshold, next_level_name, next_threshold = get_level(xp_after)
        badges_after = calc_badges(state["results"])
        new_badges = badges_after - badges_before

        pct = int(score/total*100) if total else 0
        bar = "█"*score + "░"*(total-score)
        if score == total:          comment = "Отлично! Тема усвоена полностью. 🎯"
        elif score >= total*0.66:   comment = "Хороший результат! Перечитай моменты, где ошибся."
        else:                       comment = "Стоит вернуться к материалу и повторить тему."

        xp_line = f"\n\n⚡ *+{xp_gained} XP*  (всего: {xp_after} XP)"
        next_line = (
            f"\n_До уровня «{next_level_name}»: {next_threshold - xp_after} XP_"
            if next_threshold is not None else "\n_Максимальный уровень достигнут!_"
        )

        text = (
            f"{score_emoji(score,total)} *Результат теста*\n_{topic['title']}_\n\n"
            f"`{bar}` {score}/{total} ({pct}%)\n\n{comment}"
            f"{xp_line}\n`{xp_bar(xp_after, lvl_threshold, next_threshold)}`{next_line}"
            f"\n\nВыбери следующую тему:"
        )
        # Сохраняем результат в Google Sheets
        user_id = query.from_user.id
        username = query.from_user.username or query.from_user.first_name or str(user_id)
        save_result_to_sheets(user_id, username, topic_key, score, total)

        await context.bot.send_message(
            chat_id=query.message.chat_id, text=text,
            parse_mode="Markdown", reply_markup=topic_keyboard()
        )

        # Отдельное сообщение при повышении уровня
        if level_after != level_before:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"🎉 *Новый уровень!*\nТеперь ты — *{level_after}*",
                parse_mode="Markdown"
            )

        # Отдельное сообщение за каждый новый значок
        for badge_id in new_badges:
            b = BADGES[badge_id]
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"{b['emoji']} *Новый значок: «{b['title']}»*\n_{b['desc']}_",
                parse_mode="Markdown"
            )

        await check_milestone(query.message.chat_id, context, state)

    # ── Контрольный тест: старт ──
    elif data.startswith("mstart_"):
        n = int(data[7:])
        if n not in MILESTONE_TESTS:
            await query.edit_message_text("Тест не найден.")
            return
        mt = MILESTONE_TESTS[n]
        state.update({
            "in_milestone": True, "milestone_n": n,
            "m_q_index": 0, "m_score": 0, "m_answered": False,
        })
        await query.edit_message_text(
            f"🎯 *{mt['title']}*\n_{mt['description']}_\n\n"
            f"Всего {len(mt['questions'])} вопросов. Начинаем!",
            parse_mode="Markdown"
        )
        await send_milestone_question(query.message.chat_id, context, n, 0)

    # ── Контрольный тест: ответ ──
    elif data.startswith("mans_"):
        parts = data.split("_")
        choice = int(parts[-1]); q_index = int(parts[-2]); n = int(parts[1])
        if state.get("m_answered"): return
        state["m_answered"] = True
        mt = MILESTONE_TESTS[n]
        q = mt["questions"][q_index]
        is_correct = (choice == q["correct"])
        if is_correct: state["m_score"] += 1; reply = q["explanation"]
        else: reply = q["wrong_explanation"]
        reply += f"\n\n_Вопрос {q_index+1} из {len(mt['questions'])}_"
        await context.bot.send_message(
            chat_id=query.message.chat_id, text=reply, parse_mode="Markdown",
            reply_markup=milestone_next_keyboard(n, q_index, len(mt["questions"]))
        )

    # ── Контрольный тест: следующий вопрос ──
    elif data.startswith("mnext_"):
        parts = data.split("_")
        q_index = int(parts[-1]); n = int(parts[1])
        state["m_answered"] = False
        await send_milestone_question(query.message.chat_id, context, n, q_index)

    # ── Контрольный тест: результат ──
    elif data.startswith("mresult_"):
        n = int(data[8:])
        mt = MILESTONE_TESTS[n]
        score = state["m_score"]; total = len(mt["questions"])
        pct = int(score/total*100) if total else 0
        bar = "█"*score + "░"*(total-score)
        grade = milestone_grade(score, total)
        state["in_milestone"] = False

        if score == total:
            # 100% — предлагаем сертификат
            state["awaiting_name"] = True
            state["cert_milestone_n"] = n
            text = (
                f"🎯 *Контрольный тест завершён!*\n"
                f"_{mt['title']}_\n\n"
                f"`{bar}` {score}/{total} ({pct}%)\n\n"
                f"{grade}\n\n"
                f"🏆 *Ты набрал 100%!*\n"
                f"Введи своё *имя и фамилию* — и я пришлю тебе именной сертификат:"
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=text, parse_mode="Markdown"
            )
        else:
            # Меньше 100% — без сертификата
            text = (
                f"🎯 *Контрольный тест завершён!*\n"
                f"_{mt['title']}_\n\n"
                f"`{bar}` {score}/{total} ({pct}%)\n\n"
                f"{grade}\n\n"
                f"Для получения сертификата нужен результат *100%*.\n"
                f"Повтори темы и попробуй снова!"
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id, text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Пройти тест снова", callback_data=f"mstart_{n}")
                ], [
                    InlineKeyboardButton("📚 К темам", callback_data="back_menu")
                ]])
            )

    # ── Прогресс ──
    elif data == "progress":
        results = state.get("results", {})
        if not results:
            text = "📊 *Прогресс*\n\nПока нет пройденных тестов.\nВыбери тему и начни!"
        else:
            xp = calc_total_xp(results)
            level_name, lvl_threshold, next_name, next_threshold = get_level(xp)
            earned_badges = calc_badges(results)

            lines = [
                f"🏅 *Уровень: {level_name}*",
                f"`{xp_bar(xp, lvl_threshold, next_threshold)}`  {xp} XP",
            ]
            if next_threshold is not None:
                lines.append(f"_До «{next_name}»: {next_threshold - xp} XP_\n")
            else:
                lines.append("_Максимальный уровень достигнут!_\n")

            if earned_badges:
                badge_line = "  ".join(BADGES[b]["emoji"] for b in earned_badges)
                lines.append(f"🎖 *Значки:* {badge_line}\n")

            lines.append("📊 *Темы:*")
            total_score = total_q = 0
            for key, res in results.items():
                idx = TOPICS_INDEX.get(key)
                if idx is None: continue
                topic = COURSE[idx]
                s, t = res["score"], res["total"]
                total_score += s; total_q += t
                bar = "█"*s + "░"*(t-s)
                lines.append(f"*{topic['title']}*\n`{bar}` {s}/{t}\n")
            if total_q:
                overall = int(total_score/total_q*100)
                lines.append(f"_Общий результат: {total_score}/{total_q} ({overall}%)_")
            completed = len(results)
            for n in sorted(MILESTONE_TESTS.keys()):
                if completed < n:
                    lines.append(f"\n🎯 До контрольного теста: ещё {n-completed} тем")
                    break
            text = "\n".join(lines)
        await context.bot.send_message(
            chat_id=query.message.chat_id, text=text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("← Назад к темам", callback_data="back_menu")
            ]])
        )

    # ── Назад в меню ──
    elif data == "back_menu":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📚 Выбери тему:", reply_markup=topic_keyboard()
        )


# ─────────────────────────────────────────
#  ЗАПУСК
# ─────────────────────────────────────────

async def reload_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-команда: перечитать темы и вопросы из Google Таблицы без передеплоя."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Эта команда доступна только администратору курса.")
        return
    await update.message.reply_text("🔄 Обновляю темы из Google Таблицы...")
    new_course = load_course_from_sheets()
    if new_course is None:
        await update.message.reply_text(
            "❌ Не удалось загрузить данные из таблицы. Проверь листы «Темы» и «Вопросы», доступ сервис-аккаунта и попробуй снова."
        )
        return
    apply_course(new_course)
    if not new_course:
        await update.message.reply_text(
            "⚠️ Таблица прочитана, но активных тем не найдено — проверь столбец «active» и структуру листов."
        )
        return
    await update.message.reply_text(f"✅ Готово! Загружено тем: {len(new_course)}.")


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("Установи переменную окружения BOT_TOKEN")

    initial_course = load_course_from_sheets()
    apply_course(initial_course or [])
    if not initial_course:
        logger.warning(
            "Не удалось загрузить курс из Google Таблицы при старте — бот запущен с пустым списком тем. "
            "Проверь листы «Темы»/«Вопросы» и выполни /reload после исправления."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("reload", reload_course))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
