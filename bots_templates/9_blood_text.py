# ====================================================
# بوت كتابة الدم - محول من PHP إلى Python
# ====================================================

import telebot
import requests
import re
from telebot import types

TOKEN = "{TOKEN}"
OWNER_ID = {OWNER_ID}

bot = telebot.TeleBot(TOKEN)

PHOTOFUNIA_URL = "https://m.photofunia.com/ar/categories/all_effects/blood_writing"
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8",
    "Origin": "https://m.photofunia.com",
    "Referer": "https://m.photofunia.com/ar/effects/blood_writing",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/139.0.0.0 Mobile Safari/537.36"
}

def get_blood_image(text):
    try:
        session = requests.Session()
        resp = session.post(
            PHOTOFUNIA_URL,
            data={"text": text},
            headers=HEADERS,
            allow_redirects=True,
            timeout=30
        )
        html = resp.text
        # البحث عن رابط الصورة
        match = re.search(r'https://u\.photofunia\.com/[^\s"\']+\.jpg', html)
        if match:
            return match.group(0)
        match2 = re.search(r'src="(https://u\.photofunia\.com/[^"]+)"', html)
        if match2:
            return match2.group(1)
    except Exception as e:
        return None
    return None

@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(
        msg.chat.id,
        "🩸 *بوت كتابة الدم*\n\n"
        "أرسل أي نص وسأحوله لصورة بخط الدم!\n\n"
        "مثال: اكتب اسمك أو أي كلمة تريدها",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
def handle_text(msg):
    text = msg.text.strip()
    if len(text) > 50:
        bot.send_message(msg.chat.id, "⚠️ النص طويل جداً! أرسل 50 حرف أو أقل.")
        return
    wait_msg = bot.send_message(msg.chat.id, "⏳ جاري إنشاء الصورة...")
    img_url = get_blood_image(text)
    bot.delete_message(msg.chat.id, wait_msg.message_id)
    if img_url:
        bot.send_photo(
            msg.chat.id,
            img_url,
            caption=f"🩸 نصك: *{text}*",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(msg.chat.id, "❌ فشل إنشاء الصورة، حاول مرة أخرى.")

if __name__ == "__main__":
    print("🩸 Blood Text Bot Started...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
