import os
import json
import random
import time
import re
import threading
from flask import Flask
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

AUTO_SPIN = {
    "pragmatic": [10, 20, 30, 50],
    "pgsoft": [10, 30, 50, 80],
}

MAIN_OTOMATIS = ["✅❌✅", "❌✅✅", "✅❌❌", "❌✅❌"]
LAST_REPLY_TIME = 0
COOLDOWN_SECONDS = 5

BUY_FREE_SPIN_RULES = [
    "Saat scatter muncul 2× berturut tapi belum pecah besar",
    "Saat pola scatter sering muncul tapi belum masuk free spin",
    "Saat 2 scatter muncul minimal 3× dalam 50 spin terakhir",
]

BET_RULES = [
    "Naikkan bet setelah pecah besar",
    "Turunkan bet jika 30 spin belum pecah",
    "Naikkan bet 1 tingkat setelah scatter muncul beruntun",
    "Reset bet jika pola terasa dingin",
]

def load_games():
    with open("games.json", "r", encoding="utf-8") as f:
        return json.load(f)

def jam_gacor():
    # UTC+7 / WIB time
    now = datetime.utcnow() + timedelta(hours=7)

    start = now + timedelta(minutes=random.randint(3, 35))
    end = start + timedelta(minutes=random.randint(45, 120))

    return f"{start:%H.%M} - {end:%H.%M}"

def manual_spin():
    return random.randint(3, 20)

def make_trick(game_name, provider):
    auto1, auto2 = random.sample(AUTO_SPIN[provider], 2)

    lines = [
        f"🎰 <b>{game_name.upper()}</b> 🎰",
        f"✅ Manual Spin {manual_spin()}×",
    ]

    if provider == "pragmatic":
        lines += [
            f"✅ Auto Spin {auto1}× ({random.choice(MAIN_OTOMATIS)}) – Taruhan Ganda {random.choice(['ON', 'OFF'])}",
            f"✅ Manual Spin {manual_spin()}×",
            f"✅ Auto Spin {auto2}× ({random.choice(MAIN_OTOMATIS)}) – Taruhan Ganda {random.choice(['ON', 'OFF'])}",
            f"✅ {random.choice(BET_RULES)}",
        ]

        if random.choice([True, False]):
            lines.append(f"🟢 BELI FREE SPIN: {random.choice(BUY_FREE_SPIN_RULES)}")

    else:
        lines += [
            f"✅ Auto Spin {auto1}×",
            f"✅ Manual Spin {manual_spin()}×",
            f"✅ Auto Spin {auto2}×",
            f"✅ {random.choice(BET_RULES)}",
        ]

    return "\n".join(lines)

def provider_for_game(data, game_name):
    for provider, games in data["providers"].items():
        if game_name in games:
            return provider
    return "pragmatic"

def build_family_text(family_key):
    data = load_games()
    family = data["families"][family_key]

    text = f"🔥 {family['title']}\n"
    text += f"⏰ Jam Gacor: {jam_gacor()}\n\n"

    blocks = []
    for game in family["games"]:
        provider = provider_for_game(data, game)
        blocks.append(make_trick(game, provider))

    text += "\n\n━━━━━━━━━━━━\n\n".join(blocks)
    return text

def build_provider_text(provider):
    data = load_games()
    games = random.sample(data["providers"][provider], 5)

    title = "PG SOFT" if provider == "pgsoft" else "PRAGMATIC"
    text = f"🔥 TOP 5 {title} GACOR\n"
    text += f"⏰ Jam Gacor: {jam_gacor()}\n\n"

    blocks = [make_trick(game, provider) for game in games]
    text += "\n\n━━━━━━━━━━━━\n\n".join(blocks)
    return text

def build_random_text():
    data = load_games()
    all_games = []

    for provider, games in data["providers"].items():
        for game in games:
            all_games.append((game, provider))

    selected = random.sample(all_games, 5)

    text = f"🔥 TOP 5 GAME GACOR RANDOM\n"
    text += f"⏰ Jam Gacor: {jam_gacor()}\n\n"

    blocks = [make_trick(game, provider) for game, provider in selected]
    text += "\n\n━━━━━━━━━━━━\n\n".join(blocks)
    return text

def build_single_game_text(game_key):
    data = load_games()
    game = data["single_games"][game_key]

    text = f"🔥 TRIK GAME SPESIFIK\n"
    text += f"⏰ Jam Gacor: {jam_gacor()}\n\n"
    text += make_trick(game["name"], game["provider"])
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Bot Trik Gacor aktif!\n\n"
        "Command:\n"
        "/zeus /starlight /sweet /sugar /gatot /mahjong\n"
        "/pragmatic /pgsoft /random"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 DAFTAR COMMAND BOT\n\n"
        "🎰 Family Game:\n"
        "/zeus /gates /olympus\n"
        "/starlight /princess\n"
        "/sweet /bonanza\n"
        "/sugar /rush\n"
        "/gatot /gatotkaca\n"
        "/mahjong /mw\n\n"
        "🎲 Provider:\n"
        "/pragmatic\n"
        "/pgsoft\n\n"
        "🔥 Random:\n"
        "/random\n\n"
        "Bisa juga ketik biasa:\n"
        "zeus bang, mahjong dong, pgsoft, pragmatic"
    )

async def text_detector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_games()
    text = update.message.text.lower()

    global LAST_REPLY_TIME
    trigger_words = [
        "trik",
        "pola",
        "info",
        "bang",
        "dong",
        "hari ini",
        "help",
        "tolong",
        "gacor"
    ]

    should_reply = False

    if len(text.split()) <= 2:
        should_reply = True

    if any(word in text for word in trigger_words):
        should_reply = True

    if not should_reply:
        return

    now = time.time()

    if now - LAST_REPLY_TIME < COOLDOWN_SECONDS:
        return

    LAST_REPLY_TIME = now

    # family alias detect dulu
    for alias, family_key in data["aliases"].items():
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, text):
            await update.message.reply_text(
                build_family_text(family_key),
                parse_mode="HTML"
            )
            return

    # single game alias detect
    for alias, game_key in sorted(data.get("single_aliases", {}).items(), key=lambda x: len(x[0]), reverse=True):
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, text):
            await update.message.reply_text(
                build_single_game_text(game_key),
                parse_mode="HTML"
            )
            return

    # provider detect
    if "pgsoft" in text or "pg soft" in text:
        await update.message.reply_text(build_provider_text("pgsoft"), parse_mode="HTML")
        return

    if "pragmatic" in text or "prag" in text:
        await update.message.reply_text(build_provider_text("pragmatic"), parse_mode="HTML")
        return

    if "random" in text or "acak" in text:
        await update.message.reply_text(build_random_text(), parse_mode="HTML")
        return

async def family_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_games()
    command = update.message.text.split()[0].replace("/", "").lower()
    family_key = data["aliases"].get(command)

    if not family_key:
        await update.message.reply_text("Command belum tersedia bro.")
        return

    await update.message.reply_text(
    build_family_text(family_key),
    parse_mode="HTML"
)

async def pragmatic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
    build_provider_text("pragmatic"),
    parse_mode="HTML"
)

async def pgsoft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
    build_provider_text("pgsoft"),
    parse_mode="HTML"
)

async def random_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
    build_random_text(),
    parse_mode="HTML"
)

async def single_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_games()
    command = update.message.text.split()[0].replace("/", "").lower()

    if command not in data["single_games"]:
        return

    await update.message.reply_text(
        build_single_game_text(command),
        parse_mode="HTML"
)

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN belum diisi di file .env")

    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()

    data = load_games()
    family_commands = list(data["aliases"].keys())

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler(family_commands, family_command))
    app.add_handler(CommandHandler("pragmatic", pragmatic))
    app.add_handler(CommandHandler("pgsoft", pgsoft))
    app.add_handler(CommandHandler("random", random_cmd))
    single_game_commands = list(data["single_games"].keys())
    app.add_handler(CommandHandler(single_game_commands, single_game_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_detector))

    print("Bot jalan...")
    app.run_polling()

if __name__ == "__main__":
    main()