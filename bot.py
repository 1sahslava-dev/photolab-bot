"""
PHOTO LAB by V.F. — Telegram Quiz Bot v2
Совместим с python-telegram-bot 21.x и Python 3.13
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
                "explanation": "✅ Верно!\nЛучи от верхней и нижней точек объекта пересекаются в отверстии и меняются местами на противоположной стене.",
                "wrong_explanation": "❌ Не совсем.\nПравильный ответ: *«Световые лучи пересекаются в точке отверстия»*.\nИменно это пересечение и создаёт перевёрнутую проекцию.",
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
                "explanation": "✅ Верно!\nИбн аль-Хайсам около 1000 г. н.э. описал принцип в «Книге оптики».",
                "wrong_explanation": "❌ Не совсем.\nПравильный ответ: *«Ибн аль-Хайсам (~1000 г. н.э.)»*.\nМо-цзы описал эффект раньше, но как наблюдение — без научного объяснения.",
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
                "explanation": "✅ Верно!\nПринцип один: свет → отверстие/линза → изображение.\nИзменился только носитель: стена → плёнка → цифровая матрица.",
                "wrong_explanation": "❌ Не совсем.\nПравильный ответ: *«Свет проходит через отверстие/линзу»*.\nЭто фундаментальный принцип, который не изменился за 1000 лет.",
            },
        ],
    },
]

TOPICS_INDEX = {
    f"m{t['module']}_t{t['topic']}": i
    for i, t in enumerate(COURSE)
}


def get_state(context):
    if "state" not in context.user_data:
        context.user_data["state"] = {
            "topic_key": None,
            "q_index": 0,
            "score": 0,
            "total": 0,
            "answered": False,
            "results": {},
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
    buttons = [
        [InlineKeyboardButton(letters[i], callback_data=f"ans_{topic_key}_{q_index}_{i}")]
        for i in range(num_options)
    ]
    return InlineKeyboardMarkup(buttons)


def next_keyboard(topic_key, q_index, total):
    if q_index + 1 < total:
        btn = InlineKeyboardButton("Следующий вопрос →", callback_data=f"next_{topic_key}_{q_index + 1}")
    else:
        btn = InlineKeyboardButton("Посмотреть результат 🏁", callback_data=f"result_{topic_key}")
    return InlineKeyboardMarkup([[btn]])


async def send_question(chat_id, context, topic_key, q_index):
    topic = COURSE[TOPICS_INDEX[topic_key]]
    q = topic["questions"][q_index]
    letters = ["А", "Б", "В", "Г", "Д"]
    total = len(topic["questions"])
    options_text = "\n".join(f"*{letters[i]}* — {opt}" for i, opt in enumerate(q["options"]))
    text = f"📝 Вопрос {q_index + 1} из {total}\n\n{q['text']}\n\n{options_text}"
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=answer_keyboard(topic_key, q_index, len(q["options"]))
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "друг"
    await update.message.reply_text(
        f"👋 Привет, {name}!\n\nЭто бот курса *PHOTO LAB by V.F.*\nВыбери тему для теста:",
        parse_mode="Markdown",
        reply_markup=topic_keyboard()
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📚 Выбери тему:", reply_markup=topic_keyboard())


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    state = get_state(context)

    if data.startswith("start_"):
        topic_key = data[6:]
        if topic_key not in TOPICS_INDEX:
            await query.edit_message_text("Тема не найдена.")
            return
        topic = COURSE[TOPICS_INDEX[topic_key]]
        state.update({
            "topic_key": topic_key,
            "q_index": 0,
            "score": 0,
            "total": len(topic["questions"]),
            "answered": False,
        })
        await query.edit_message_text(topic["intro"], parse_mode="Markdown")
        await send_question(query.message.chat_id, context, topic_key, 0)

    elif data.startswith("ans_"):
        parts = data.split("_")
        choice = int(parts[-1])
        q_index = int(parts[-2])
        topic_key = "_".join(parts[1:-2])
        if state.get("answered"):
            return
        state["answered"] = True
        topic = COURSE[TOPICS_INDEX[topic_key]]
        q = topic["questions"][q_index]
        is_correct = (choice == q["correct"])
        if is_correct:
            state["score"] += 1
            reply = q["explanation"]
        else:
            reply = q["wrong_explanation"]
        reply += f"\n\n_Вопрос {q_index + 1} из {len(topic['questions'])}_"
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=reply,
            parse_mode="Markdown",
            reply_markup=next_keyboard(topic_key, q_index, len(topic["questions"]))
        )

    elif data.startswith("next_"):
        parts = data.split("_")
        q_index = int(parts[-1])
        topic_key = "_".join(parts[1:-1])
        state["answered"] = False
        await send_question(query.message.chat_id, context, topic_key, q_index)

    elif data.startswith("result_"):
        topic_key = data[7:]
        topic = COURSE[TOPICS_INDEX[topic_key]]
        score = state["score"]
        total = state["total"]
        state["results"][topic_key] = {"score": score, "total": total}
        pct = int(score / total * 100) if total else 0
        bar = "█" * score + "░" * (total - score)
        if score == total:
            comment = "Отлично! Тема усвоена полностью. 🎯"
        elif score >= total * 0.66:
            comment = "Хороший результат! Перечитай моменты, где ошибся."
        else:
            comment = "Стоит вернуться к материалу и повторить тему."
        emoji = "🏆" if score == total else ("⭐" if score >= total * 0.66 else "📚")
        text = (
            f"{emoji} *Результат теста*\n_{topic['title']}_\n\n"
            f"`{bar}` {score}/{total} ({pct}%)\n\n{comment}\n\nВыбери следующую тему:"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=topic_keyboard()
        )

    elif data == "progress":
        results = state.get("results", {})
        if not results:
            text = "📊 *Прогресс*\n\nПока нет пройденных тестов.\nВыбери тему и начни!"
        else:
            lines = ["📊 *Твой прогресс:*\n"]
            total_score = total_q = 0
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

    elif data == "back_menu":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📚 Выбери тему:",
            reply_markup=topic_keyboard()
        )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Используй /start для начала или /menu для выбора темы.")


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
    main()
