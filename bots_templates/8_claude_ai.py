# ====================================================
# بوت Claude AI - محول من PHP إلى Python
# ====================================================

import telebot
import requests
from telebot import types

TOKEN = "{TOKEN}"
OWNER_ID = {OWNER_ID}
CHANNEL = "@Namiro_1"
API_URL = "https://devil.xo.je/v/ai/claude.php"

bot = telebot.TeleBot(TOKEN)

def ask_claude(message_text):
    try:
        resp = requests.get(API_URL, params={"message": message_text}, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return data.get("response", "عذراً، لم أستطع معالجة طلبك.")
            elif data.get("response"):
                return data["response"]
            elif data.get("error"):
                return f"⚠️ خطأ: {data['error']}"
    except Exception as e:
        return f"⚠️ خطأ في الاتصال: {str(e)}"
    return "⚠️ عذراً، حدث خطأ. حاول مرة أخرى."

@bot.message_handler(commands=["start"])
def start(msg):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📢 قناة البوت", url=f"https://t.me/{CHANNEL.replace('@','')}"))
    bot.send_message(
        msg.chat.id,
        f"*مرحباً بك في بوت المحادثة بالذكاء الاصطناعي!*\n\n"
        f"أنا بوت يعمل بنموذج *Claude AI*\n\n"
        f"📌 *الطريقة:*\n"
        f"فقط أرسل سؤالك وسأجيبك فوراً.\n\n"
        f"📢 *قناة البوت:* {CHANNEL}",
        parse_mode="Markdown",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
def handle_message(msg):
    bot.send_chat_action(msg.chat.id, "typing")
    reply = ask_claude(msg.text)
    bot.send_message(msg.chat.id, reply, parse_mode="Markdown")

if __name__ == "__main__":
    print("🤖 Claude AI Bot Started...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
