# ====================================================
# حقوق النشر © بوت صانع | جميع الحقوق محفوظة
# صُنع بواسطة بوت المصنع الرسمي
# ====================================================

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os

Token = "{TOKEN}"
Id = {OWNER_ID}

bot = telebot.TeleBot(Token)
DB = "db.json"
sess = {}

def load():
    if not os.path.exists(DB):
        return {"channels": [], "users": []}
    with open(DB, "r") as f:
        return json.load(f)

def save(data):
    with open(DB, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_owner(uid):
    return uid == Id

def check_admin(ch_input):
    try:
        if ch_input.startswith("https://t.me/"):
            uname = ch_input.replace("https://t.me/", "").split("/")[0]
            chat = bot.get_chat(f"@{uname}")
        else:
            chat = bot.get_chat(ch_input)
        admins = [a.user.id for a in bot.get_chat_administrators(chat.id)]
        if Id in admins:
            return True, chat.id, chat.title, f"https://t.me/{chat.username}" if chat.username else ""
        return False, None, None, None
    except:
        return False, None, None, None

def check_sub(uid):
    db = load()
    if not db["channels"]:
        return True, []
    missing = []
    for ch in db["channels"]:
        try:
            m = bot.get_chat_member(ch["id"], uid)
            if m.status in ["left", "kicked"]:
                missing.append(ch)
        except:
            missing.append(ch)
    return len(missing) == 0, missing

def sub_markup(missing):
    mu = InlineKeyboardMarkup()
    for ch in missing:
        mu.add(InlineKeyboardButton(f"📢 {ch['name']}", url=ch["link"]))
    mu.add(InlineKeyboardButton("✅ تحققت من اشتراكي", callback_data="check_sub"))
    return mu

def require_sub(fn):
    def wrapper(msg):
        ok, missing = check_sub(msg.from_user.id)
        if not ok:
            bot.send_message(
                msg.chat.id,
                "╔══════════════════╗\n║  🔐 اشتراك إجباري  ║\n╚══════════════════╝\n\n"
                "يجب عليك الاشتراك في القنوات التالية\nللاستمتاع باستخدام البوت 💙",
                reply_markup=sub_markup(missing)
            )
            return
        fn(msg)
    return wrapper

def owner_mu():
    mu = InlineKeyboardMarkup(row_width=2)
    mu.add(
        InlineKeyboardButton("➕ إضافة قناة", callback_data="add_channel"),
        InlineKeyboardButton("🗑 حذف قناة", callback_data="del_channel"),
        InlineKeyboardButton("📋 قائمة القنوات", callback_data="list_channels"),
        InlineKeyboardButton("👥 عدد المستخدمين", callback_data="users_count"),
        InlineKeyboardButton("📢 إذاعة للجميع", callback_data="broadcast"),
    )
    mu.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
    return mu

@bot.message_handler(commands=["start"])
@require_sub
def start(message):
    db = load()
    uid = message.from_user.id
    if uid not in db["users"]:
        db["users"].append(uid)
        save(db)
    name = message.from_user.first_name
    mu = InlineKeyboardMarkup()
    mu.add(InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/XVSJQ"))
    if is_owner(uid):
        mu.add(InlineKeyboardButton("🛠 لوحة المالك", callback_data="owner_panel"))
    bot.send_message(
        message.chat.id,
        f"✨ *أهلاً وسهلاً، {name}!* ✨\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "*ارسل رسالتك وسوف ارد عليك باقرب وقت *✨\n"
        "━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown", reply_markup=mu
    )

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = call.from_user.id
    cid = call.message.chat.id
    mid = call.message.message_id
    db = load()

    if call.data == "check_sub":
        ok, missing = check_sub(uid)
        if ok:
            bot.answer_callback_query(call.id, "✅ تم التحقق! يمكنك الاستخدام الآن", show_alert=True)
            bot.delete_message(cid, mid)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ لم تشترك في جميع القنوات بعد!", show_alert=True)
        return

    if call.data == "back_home":
        bot.answer_callback_query(call.id)
        name = call.from_user.first_name
        mu = InlineKeyboardMarkup()
        mu.add(InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/XVSJQ"))
        if is_owner(uid):
            mu.add(InlineKeyboardButton("🛠 لوحة المالك", callback_data="owner_panel"))
        bot.edit_message_text(
            f"✨ *أهلاً وسهلاً، {name}!* ✨\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "ارسل رسالتك وسوف ارد عليك باقرب وقت ✨\n"
            "━━━━━━━━━━━━━━━━━━",
            cid, mid, parse_mode="Markdown", reply_markup=mu
        )

    elif call.data == "owner_panel":
        if not is_owner(uid):
            bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية!", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            "🛠 *لوحة المالك*\n\nاختر الإجراء المطلوب 👇",
            cid, mid, parse_mode="Markdown", reply_markup=owner_mu()
        )

    elif call.data == "add_channel":
        if not is_owner(uid): return
        bot.answer_callback_query(call.id)
        msg = bot.send_message(
            cid,
            "📢 *إضافة قناة اشتراك إجباري*\n\n"
            "أرسل رابط القناة أو يوزرها:\n"
            "مثال:\n`https://t.me/mychannel`\nأو\n`@mychannel`",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_add_ch)

    elif call.data == "del_channel":
        if not is_owner(uid): return
        bot.answer_callback_query(call.id)
        if not db["channels"]:
            bot.answer_callback_query(call.id, "📭 لا توجد قنوات مضافة!", show_alert=True)
            return
        mu = InlineKeyboardMarkup()
        for i, ch in enumerate(db["channels"]):
            mu.add(InlineKeyboardButton(f"🗑 {ch['name']}", callback_data=f"delch_{i}"))
        mu.add(InlineKeyboardButton("🔙 رجوع", callback_data="owner_panel"))
        bot.edit_message_text("🗑 *اختر القناة للحذف:*", cid, mid, parse_mode="Markdown", reply_markup=mu)

    elif call.data.startswith("delch_"):
        if not is_owner(uid): return
        idx = int(call.data.split("_")[1])
        if idx < len(db["channels"]):
            removed = db["channels"].pop(idx)
            save(db)
            bot.answer_callback_query(call.id, f"✅ تم حذف {removed['name']}", show_alert=True)
        bot.edit_message_text(
            "🛠 *لوحة المالك*\n\nاختر الإجراء المطلوب 👇",
            cid, mid, parse_mode="Markdown", reply_markup=owner_mu()
        )

    elif call.data == "list_channels":
        if not is_owner(uid): return
        bot.answer_callback_query(call.id)
        if not db["channels"]:
            text = "📭 لا توجد قنوات مضافة حتى الآن."
        else:
            text = "📋 *القنوات المضافة:*\n\n"
            for i, ch in enumerate(db["channels"], 1):
                text += f"{i}. {ch['name']} — `{ch['id']}`\n"
        bot.edit_message_text(text, cid, mid, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup().add(
                                  InlineKeyboardButton("🔙 رجوع", callback_data="owner_panel")))

    elif call.data == "users_count":
        if not is_owner(uid): return
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            f"👥 *إجمالي المستخدمين:* `{len(db['users'])}`",
            cid, mid, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 رجوع", callback_data="owner_panel"))
        )

    elif call.data == "broadcast":
        if not is_owner(uid): return
        bot.answer_callback_query(call.id)
        msg = bot.send_message(
            cid,
            "📢 *إذاعة للجميع*\n\nأرسل الرسالة التي تريد إذاعتها:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_bc)

def process_add_ch(message):
    if not is_owner(message.from_user.id): return
    ok, chat_id, title, link = check_admin(message.text.strip())
    if not ok:
        bot.send_message(message.chat.id,
                         "❌ *فشل إضافة القناة!*\n\nأنت لست أدمن في هذه القناة.",
                         parse_mode="Markdown")
        return
    db = load()
    for ch in db["channels"]:
        if ch["id"] == str(chat_id):
            bot.send_message(message.chat.id, "❌ *هذه القناة مضافة بالفعل!*", parse_mode="Markdown")
            return
    db["channels"].append({"name": title, "id": str(chat_id), "link": link or message.text.strip()})
    save(db)
    mu = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 العودة للوحة", callback_data="owner_panel"))
    bot.send_message(
        message.chat.id,
        f"✅ *تمت إضافة القناة بنجاح!*\n\n📢 الاسم: {title}\n🆔 ID: `{chat_id}`\n🔗 الرابط: {link or message.text.strip()}",
        parse_mode="Markdown", reply_markup=mu
    )

def process_bc(message):
    if not is_owner(message.from_user.id): return
    db = load()
    ok = fail = 0
    st = bot.send_message(message.chat.id, "📤 جاري الإرسال...")
    for uid in db["users"]:
        if uid == Id:
            continue
        try:
            bot.copy_message(uid, message.chat.id, message.message_id)
            ok += 1
        except:
            fail += 1
    bot.edit_message_text(
        f"✅ *تمت الإذاعة بنجاح*\n\n✓ تم الإرسال لـ: {ok} مستخدم\n✗ فشل الإرسال لـ: {fail} مستخدم",
        message.chat.id, st.message_id, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 العودة للوحة", callback_data="owner_panel"))
    )

@bot.message_handler(content_types=[
    "text", "photo", "video", "audio", "voice",
    "document", "sticker", "animation", "video_note", "contact", "location"
], func=lambda m: m.chat.id != Id and not (m.text and m.text.startswith('/')))
@require_sub
def handle_user_msg(message):
    uid = message.from_user.id
    try:
        
        sent = bot.copy_message(Id, message.chat.id, message.message_id)
        sess[sent.message_id] = uid
        
       
        if message.content_type == "sticker":
            bot.reply_to(message, "✅ تم إرسال الملصق إلى المالك، سيتم الرد عليك قريباً.")
        elif message.content_type == "photo":
            bot.reply_to(message, "✅ تم إرسال الصورة إلى المالك، سيتم الرد عليك قريباً.")
        elif message.content_type == "video":
            bot.reply_to(message, "✅ تم إرسال الفيديو إلى المالك، سيتم الرد عليك قريباً.")
        elif message.content_type == "voice":
            bot.reply_to(message, "✅ تم إرسال التسجيل الصوتي إلى المالك، سيتم الرد عليك قريباً.")
        else:
            bot.reply_to(message, "✅ تم إرسال رسالتك إلى المالك، سيتم الرد عليك قريباً.")
    except Exception as e:
        print(f"خطأ في إرسال الرسالة: {e}")
        bot.reply_to(message, "❌ حدث خطأ في إرسال الرسالة. الرجاء المحاولة مرة أخرى لاحقاً.")

@bot.message_handler(func=lambda m: m.chat.id == Id and m.reply_to_message is not None)
def handle_owner_reply(message):
    uid = sess.get(message.reply_to_message.message_id)
    if uid:
        try:
            bot.copy_message(uid, message.chat.id, message.message_id)
            bot.reply_to(message, "✅ تم إرسال الرد بنجاح")
        except Exception as e:
            print(f"خطأ في إرسال الرد: {e}")
            bot.reply_to(message, "❌ فشل إرسال الرد")
    else:
        bot.reply_to(message, "❌ لم أتمكن من العثور على المستخدم، قد تكون الرسالة قديمة")

if __name__ == "__main__":
    print("شغال...")
    bot.infinity_polling()