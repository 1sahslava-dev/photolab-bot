"""
PHOTO LAB by V.F. — Telegram Quiz Bot
Тест после каждой темы + контрольный тест + сертификат при 100%
"""

import os
import io
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

# ── Регистрация шрифтов ──
try:
    pdfmetrics.registerFont(TTFont('R',   '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('RB',  '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('RI',  '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf'))
    pdfmetrics.registerFont(TTFont('RS',  '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'))
    pdfmetrics.registerFont(TTFont('RSB', '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('RSI', '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf'))
    FONTS_OK = True
except Exception as e:
    logger.warning(f"Шрифты не загружены: {e}")
    FONTS_OK = False

# ─────────────────────────────────────────
#  КУРС
# ─────────────────────────────────────────
ACTIVE_TOPICS = 2
COURSE = [
    {
        "module": 1,
        "topic": 1,
        "title": "Камера-обскура",
        "subtitle": "Фотография до фотографии",
        "intro": (
            "📷 *Модуль 1 · Тема 1*\n"
            "*Камера-обскура*\n\n"
            "Фотография началась не с плёнки и не с цифровой камеры.\n"
            "Она началась с тёмной комнаты и маленького отверстия.\n\n"
            "Готов проверить, как усвоил материал? 👇"
        ),
        "questions": [
            {
                "text": "❓ Почему изображение в камере-обскуре получается перевёрнутым?",
                "options": [
                    "Внутри стоит зеркало",
                    "Световые лучи пересекаются в точке отверстия",
                    "Тёмное пространство переворачивает лучи",
                    "Линза изменяет направление света",
                ],
                "correct": 1,
                "explanation": (
                    "✅ Верно!\n"
                    "Лучи от верхней и нижней точек объекта пересекаются в отверстии "
                    "и меняются местами на противоположной стене."
                ),
                "wrong_explanation": (
                    "❌ Не совсем.\n"
                    "Правильный ответ: *«Световые лучи пересекаются в точке отверстия»*.\n"
                    "Именно это пересечение и создаёт перевёрнутую проекцию."
                ),
            },
            {
                "text": "❓ Кто первым дал научное описание принципа камеры-обскуры?",
                "options": [
                    "Леонардо да Винчи",
                    "Жозеф Ньепс",
                    "Ибн аль-Хайсам (~1000 г. н.э.)",
                    "Мо-цзы (Китай, 400 до н.э.)",
                ],
                "correct": 2,
                "explanation": (
                    "✅ Верно!\n"
                    "Ибн аль-Хайсам около 1000 г. н.э. описал принцип в «Книге оптики»."
                ),
                "wrong_explanation": (
                    "❌ Не совсем.\n"
                    "Правильный ответ: *«Ибн аль-Хайсам (~1000 г. н.э.)»*.\n"
                    "Мо-цзы описал эффект раньше, но как наблюдение — без научного объяснения."
                ),
            },
            {
                "text": "❓ Что общего у камеры-обскуры и современного смартфона?",
                "options": [
                    "Оба используют плёнку",
                    "Оба работают без электричества",
                    "Свет проходит через отверстие/линзу и проецирует изображение",
                    "Оба изобретены в XIX веке",
                ],
                "correct": 2,
                "explanation": (
                    "✅ Верно!\n"
                    "Принцип один: свет → отверстие/линза → изображение.\n"
                    "Изменился только носитель: стена → плёнка → цифровая матрица."
                ),
                "wrong_explanation": (
                    "❌ Не совсем.\n"
                    "Правильный ответ: *«Свет проходит через отверстие/линзу»*.\n"
                    "Это фундаментальный принцип, который не изменился за 1000 лет."
                ),
            },
        ],
    },
    {
        "module": 1,
        "topic": 2,
        "title": "Ньепс и первая фотография",
        "subtitle": "Как свет научился сохранять изображение",
        "intro": (
            "📷 *Модуль 1 · Тема 2*\n"
            "*PL-002 — Ньепс и первая сохранённая фотография*\n\n"
            "До Ньепса изображение можно было увидеть — но нельзя было сохранить.\n"
            "Он изменил это навсегда.\n\n"
            "Готов проверить знания? 👇"
        ),
        "questions": [
            {
                "text": "❓ Кто создал первую сохранившуюся фотографию?",
                "options": [
                    "Луи Дагерр",
                    "Жозеф Нисефор Ньепс",
                    "Уильям Генри Фокс Тальбот",
                ],
                "correct": 1,
                "explanation": (
                    "✅ Верно!\n"
                    "Ньепс первым смог сохранить изображение, полученное с помощью камеры. "
                    "Дагерр и Тальбот развивали фотографию позже."
                ),
                "wrong_explanation": (
                    "❌ Не совсем.\n"
                    "Правильный ответ: *«Жозеф Нисефор Ньепс»*.\n"
                    "Дагерр и Тальбот развивали фотографию позже."
                ),
            },
            {
                "text": "❓ Как назывался процесс Ньепса?",
                "options": [
                    "Гелиография",
                    "Дагерротип",
                    "Коллодий",
                ],
                "correct": 0,
                "explanation": (
                    "✅ Верно!\n"
                    "Ньепс называл свой метод гелиографией — «рисованием солнцем»."
                ),
                "wrong_explanation": (
                    "❌ Не совсем.\n"
                    "Правильный ответ: *«Гелиография»*.\n"
                    "От греч. helios — солнце, grapho — рисую."
                ),
            },
            {
                "text": "❓ Почему экспозиция у Ньепса была такой долгой?",
                "options": [
                    "Камера была слишком маленькой",
                    "Материал был очень малочувствительным к свету",
                    "Объектив переворачивал изображение",
                ],
                "correct": 1,
                "explanation": (
                    "✅ Верно!\n"
                    "Светочувствительный слой реагировал на свет очень медленно — "
                    "около 8 часов экспозиции."
                ),
                "wrong_explanation": (
                    "❌ Не совсем.\n"
                    "Правильный ответ: *«Материал был очень малочувствительным к свету»*."
                ),
            },
            {
                "text": "❓ На чём Ньепс получил своё знаменитое изображение?",
                "options": [
                    "На стеклянной пластине",
                    "На бумажном негативе",
                    "На металлической пластине с битумным покрытием",
                ],
                "correct": 2,
                "explanation": (
                    "✅ Верно!\n"
                    "Металлическая пластина с битумом Иудейским — "
                    "именно на ней появился «Вид из окна в Ле Гра»."
                ),
                "wrong_explanation": (
                    "❌ Не совсем.\n"
                    "Правильный ответ: *«Металлическая пластина с битумным покрытием»*."
                ),
            },
            {
                "text": "❓ Что стало главным прорывом Ньепса?",
                "options": [
                    "Он сделал цветную фотографию",
                    "Он смог сохранить изображение, созданное светом",
                    "Он изобрёл цифровую матрицу",
                ],
                "correct": 1,
                "explanation": (
                    "✅ Верно!\n"
                    "До Ньепса изображение исчезало. "
                    "Ньепс доказал, что световой образ можно зафиксировать навсегда."
                ),
                "wrong_explanation": (
                    "❌ Не совсем.\n"
                    "Правильный ответ: *«Он смог сохранить изображение, созданное светом»*."
                ),
            },
        ],
    },
    # ── Сюда добавляй следующие темы ──
]

# ─────────────────────────────────────────
#  КОНТРОЛЬНЫЕ ТЕСТЫ
# ─────────────────────────────────────────
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

TOPICS_INDEX = {
    f"m{t['module']}_t{t['topic']}": i
    for i, t in enumerate(COURSE)
}


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
    for t in COURSE[:ACTIVE_TOPICS]:
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
    await update.message.reply_text(
        f"👋 Привет, {name}!\n\nЭто бот курса *PHOTO LAB by V.F.*\nВыбери тему для теста:",
        parse_mode="Markdown", reply_markup=topic_keyboard()
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        state["results"][topic_key] = {"score": score, "total": total}
        pct = int(score/total*100) if total else 0
        bar = "█"*score + "░"*(total-score)
        if score == total:          comment = "Отлично! Тема усвоена полностью. 🎯"
        elif score >= total*0.66:   comment = "Хороший результат! Перечитай моменты, где ошибся."
        else:                       comment = "Стоит вернуться к материалу и повторить тему."
        text = (
            f"{score_emoji(score,total)} *Результат теста*\n_{topic['title']}_\n\n"
            f"`{bar}` {score}/{total} ({pct}%)\n\n{comment}\n\nВыбери следующую тему:"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id, text=text,
            parse_mode="Markdown", reply_markup=topic_keyboard()
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
            lines = ["📊 *Твой прогресс:*\n"]
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

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("Установи переменную окружения BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
