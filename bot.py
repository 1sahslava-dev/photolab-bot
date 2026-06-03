"""
PHOTO LAB by V.F. — Telegram Quiz Bot
Тест после каждой темы курса по фотоделу
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
#  ДАННЫЕ КУРСА
#  Добавляй новые темы сюда в том же формате
# ─────────────────────────────────────────
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
                    "Лучи от верхней и нижней точек объекта пересекаются "
                    "в отверстии и меняются местами на противоположной стене."
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
                    "Ибн аль-Хайсам около 1000 г. н.э. описал принцип "
                    "в «Книге оптики» — это стало основой всей последующей оптики."
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
    # ── Сюда добавляй следующие темы ──
    # {
    #     "module": 1,
    #     "topic": 2,
    #     "title": "Экспозиция",
    #     "questions": [ ... ]
    # },
]

# Индекс тем по ключу "m{module}_t{topic}"
TOPICS_INDEX = {
    f"m{t['module']}_t{t['topic']}": i
    for i, t in enumerate(COURSE)
}

# ─────────────────────────────────────────
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────

def get_user_state(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Получить или создать состояние пользователя."""
    if "state" not in context.user_data:
        context.user_data["state"] = {
            "topic_key": None,
            "q_index": 0,
            "score": 0,
            "total": 0,
            "answered": False,
            "results": {},   # topic_key -> {"score": x, "total": y}
        }
    return context.user_data["state"]


def topic_keyboard():
    """Клавиатура выбора темы."""
    buttons = []
    for t in COURSE:
        key = f"m{t['module']}_t{t['topic']}"
        label = f"М{t['module']}·Т{t['topic']} — {t['title']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"start_{key}")])
    buttons.append([InlineKeyboardButton("📊 Мой прогресс", callback_data="progress")])
    return InlineKeyboardMarkup(buttons)


def answer_keyboard(topic_key: str, q_index: int, num_options: int):
    """Клавиатура вариантов ответа."""
    letters = ["А", "Б", "В", "Г", "Д"]
    buttons = []
    for i in range(num_options):
        cb = f"ans_{topic_key}_{q_index}_{i}"
        buttons.append([InlineKeyboardButton(f"{letters[i]}", callback_data=cb)])
    return InlineKeyboardMarkup(buttons)


def next_keyboard(topic_key: str, q_index: int, total: int):
    """Кнопка перехода к следующему вопросу или результатам."""
    if q_index + 1 < total:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("Следующий вопрос →", callback_data=f"next_{topic_key}_{q_index + 1}")
        ]])
    else:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("Посмотреть результат 🏁", callback_data=f"result_{topic_key}")
        ]])


def score_emoji(score: int, total: int) -> str:
    pct = score / total if total else 0
    if pct == 1.0:
        return "🏆"
    elif pct >= 0.66:
        return "⭐"
    else:
        return "📚"


# ─────────────────────────────────────────
#  ХЭНДЛЕРЫ
# ─────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start — приветствие."""
    name = update.effective_user.first_name or "друг"
    text = (
        f"👋 Привет, {name}!\n\n"
        "Это бот курса *PHOTO LAB by V.F.*\n"
        "Здесь ты можешь проверить знания после каждой темы.\n\n"
        "Выбери тему для теста:"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=topic_keyboard()
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /menu — вернуться в меню."""
    await update.message.reply_text(
        "📚 Выбери тему:",
        reply_markup=topic_keyboard()
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех inline-кнопок."""
    query = update.callback_query
    await query.answer()
    data = query.data
    state = get_user_state(context)

    # ── Выбор темы ──
    if data.startswith("start_"):
        topic_key = data[6:]
        if topic_key not in TOPICS_INDEX:
            await query.edit_message_text("Тема не найдена.")
            return

        topic = COURSE[TOPICS_INDEX[topic_key]]
        state["topic_key"] = topic_key
        state["q_index"] = 0
        state["score"] = 0
        state["total"] = len(topic["questions"])
        state["answered"] = False

        await query.edit_message_text(
            topic["intro"],
            parse_mode="Markdown"
        )
        await send_question(query.message.chat_id, context, topic_key, 0)
        return

    # ── Ответ на вопрос ──
    if data.startswith("ans_"):
        parts = data.split("_")
        # ans_{topic_key}_{q_index}_{choice}
        # topic_key может содержать _ поэтому собираем обратно
        choice = int(parts[-1])
        q_index = int(parts[-2])
        topic_key = "_".join(parts[1:-2])

        if state.get("answered"):
            return

        state["answered"] = True
        topic = COURSE[TOPICS_INDEX[topic_key]]
        q = topic["questions"][q_index]
        total_q = len(topic["questions"])
        is_correct = (choice == q["correct"])

        if is_correct:
            state["score"] += 1
            reply = q["explanation"]
        else:
            reply = q["wrong_explanation"]

        reply += f"\n\n_Вопрос {q_index + 1} из {total_q}_"

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=reply,
            parse_mode="Markdown",
            reply_markup=next_keyboard(topic_key, q_index, total_q)
        )
        return

    # ── Следующий вопрос ──
    if data.startswith("next_"):
        parts = data.split("_")
        q_index = int(parts[-1])
        topic_key = "_".join(parts[1:-1])
        state["answered"] = False
        await send_question(query.message.chat_id, context, topic_key, q_index)
        return

    # ── Результат ──
    if data.startswith("result_"):
        topic_key = data[7:]
        topic = COURSE[TOPICS_INDEX[topic_key]]
        score = state["score"]
        total = state["total"]
        emoji = score_emoji(score, total)

        # Сохраняем результат
        state["results"][topic_key] = {"score": score, "total": total}

        pct = int(score / total * 100) if total else 0
        bar = "█" * score + "░" * (total - score)

        if score == total:
            comment = "Отлично! Тема усвоена полностью. 🎯"
        elif score >= total * 0.66:
            comment = "Хороший результат! Перечитай моменты, где ошибся."
        else:
            comment = "Стоит вернуться к материалу и повторить тему."

        text = (
            f"{emoji} *Результат теста*\n"
            f"_{topic['title']}_\n\n"
            f"`{bar}` {score}/{total} ({pct}%)\n\n"
            f"{comment}\n\n"
            "Выбери следующую тему:"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=topic_keyboard()
        )
        return

    # ── Прогресс ──
    if data == "progress":
        results = state.get("results", {})
        if not results:
            text = "📊 *Прогресс*\n\nПока нет пройденных тестов.\nВыбери тему и начни!"
        else:
            lines = ["📊 *Твой прогресс:*\n"]
            total_score = 0
            total_q = 0
            for key, res in results.items():
                idx = TOPICS_INDEX.get(key)
                if idx is None:
                    continue
                topic = COURSE[idx]
                s, t = res["score"], res["total"]
                total_score += s
                total_q += t
                bar = "█" * s + "░" * (t - s)
                lines.append(f"*{topic['title']}*\n`{bar}` {s}/{t}\n")
            if total_q:
                overall = int(total_score / total_q * 100)
                lines.append(f"_Общий результат: {total_score}/{total_q} ({overall}%)_")
            text = "\n".join(lines)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("← Назад к темам", callback_data="back_menu")
            ]])
        )
        return

    # ── Назад в меню ──
    if data == "back_menu":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📚 Выбери тему:",
            reply_markup=topic_keyboard()
        )
        return


async def send_question(chat_id, context, topic_key, q_index):
    """Отправить вопрос с вариантами ответов."""
    topic = COURSE[TOPICS_INDEX[topic_key]]
    q = topic["questions"][q_index]
    letters = ["А", "Б", "В", "Г", "Д"]
    total = len(topic["questions"])

    options_text = "\n".join(
        f"*{letters[i]}* — {opt}"
        for i, opt in enumerate(q["options"])
    )

    text = (
        f"📝 Вопрос {q_index + 1} из {total}\n\n"
        f"{q['text']}\n\n"
        f"{options_text}"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=answer_keyboard(topic_key, q_index, len(q["options"]))
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Используй /start для начала или /menu для выбора темы."
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
