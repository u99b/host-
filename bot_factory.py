import telebot
from telebot import types
import sqlite3
import os
import requests
import subprocess
import threading
import time
from datetime import datetime

# ==================== CONFIG ====================
ADMIN_TOKEN = "8718808536:AAHBpKcp-92k_ZsxYDqOni-q6nBk1gyOofg"   # توكن بوت المصنع
ADMIN_ID    = 7662457749                 # ايدي الأدمن الرئيسي
FACTORY_TAG = "@Namiro_1"  # حقوق بوت صانع

bot = telebot.TeleBot(ADMIN_TOKEN)

# ==================== TEMPLATES ====================
bot_templates = {
    '1': 'bots_templates/1_image_gen.py',
    '2': 'bots_templates/2_roulette.py',
    '3': 'bots_templates/3_downloader.py',
    '4': 'bots_templates/4_group_mgmt.py',
    '5': 'bots_templates/5_group_protection.py',
    '6': 'bots_templates/6_vip_store.py',
    '7': 'bots_templates/7_contact.py',
    '8': 'bots_templates/8_claude_ai.py',
    '9': 'bots_templates/9_blood_text.py',
}

bot_type_names = {
    '1': '🎨 بوت توليد الصور',
    '2': '🎰 بوت الروليت',
    '3': '⬇️ بوت تحميل يوتيوب وسوشيال',
    '4': '⚙️ بوت إدارة مجموعات',
    '5': '🛡 بوت حماية مجموعات',
    '6': '🛒 بوت متجر VIP',
    '7': '📞 بوت تواصل',
    '8': '🤖 بوت Claude AI',
    '9': '🩸 بوت كتابة الدم',
}

os.makedirs('bots_templates', exist_ok=True)
os.makedirs('created_bots', exist_ok=True)

# ==================== DATABASE ====================
conn = sqlite3.connect("factory.db", check_same_thread=False)
db_lock = threading.Lock()

def init_db():
    with db_lock:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                token TEXT UNIQUE,
                username TEXT,
                name TEXT,
                bot_type TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'active',
                group_id INTEGER DEFAULT NULL,
                added_to_group INTEGER DEFAULT 0,
                folder TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS mandatory_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                channel_name TEXT,
                added_by INTEGER
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS extra_admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                added_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS custom_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                name TEXT,
                filename TEXT,
                requirements TEXT,
                added_by INTEGER,
                added_at TEXT
            )
        """)
        conn.commit()

init_db()

# ==================== HELPERS ====================

def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    c = conn.cursor()
    c.execute("SELECT id FROM extra_admins WHERE user_id=?", (user_id,))
    return c.fetchone() is not None

def get_extra_admins():
    c = conn.cursor()
    c.execute("SELECT * FROM extra_admins")
    return c.fetchall()

def get_bot_info(token):
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        data = r.json()
        if data.get("ok"):
            return data["result"]
    except:
        pass
    return None

def token_valid(token):
    return get_bot_info(token) is not None

def save_user(user):
    with db_lock:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (id, username, first_name, joined_at) VALUES (?, ?, ?, ?)",
                  (user.id, user.username or "", user.first_name or "", datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()

def get_all_bots():
    c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE status != 'deleted'")
    return c.fetchall()

def get_user_bots(owner_id):
    c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE owner_id=? AND status != 'deleted'", (owner_id,))
    return c.fetchall()

def get_abandoned_bots():
    c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE added_to_group=0 AND status='active'")
    return c.fetchall()

def get_mandatory_channels():
    c = conn.cursor()
    c.execute("SELECT * FROM mandatory_channels")
    return c.fetchall()

def check_subscription(user_id):
    channels = get_mandatory_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            member = bot.get_chat_member(ch[1], user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            pass
    return True

def mandatory_keyboard():
    channels = get_mandatory_channels()
    if not channels:
        return None
    kb = types.InlineKeyboardMarkup()
    for ch in channels:
        kb.add(types.InlineKeyboardButton(f"📢 {ch[2]}", url=f"https://t.me/{ch[1].replace('@','')}"))
    kb.add(types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
    return kb

def load_dynamic_templates():
    """تحميل القوالب المضافة من قاعدة البيانات"""
    c = conn.cursor()
    c.execute("SELECT key, name, filename FROM custom_templates")
    rows = c.fetchall()
    for key, name, filename in rows:
        bot_templates[key] = f"bots_templates/{filename}"
        bot_type_names[key] = name

def get_next_template_key():
    """الحصول على مفتاح القالب التالي"""
    existing = set(bot_templates.keys())
    i = 10  # نبدأ من 10 للقوالب المخصصة
    while str(i) in existing:
        i += 1
    return str(i)

def get_custom_templates():
    c = conn.cursor()
    c.execute("SELECT * FROM custom_templates ORDER BY id")
    return c.fetchall()

# ==================== BOT CREATION ENGINE ====================

def create_bot_file(user_id, token, template_key):
    try:
        info = get_bot_info(token)
        if not info:
            return False, None, "التوكن غير صحيح"

        bot_username = info.get("username", "UnknownBot")
        bot_name     = info.get("first_name", "Bot")
        template_path = bot_templates.get(template_key)

        if not template_path or not os.path.exists(template_path):
            return False, None, "القالب غير موجود في السيرفر"

        bot_folder = f"created_bots/{user_id}_{int(time.time())}"
        os.makedirs(bot_folder, exist_ok=True)

        with open(template_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # للقوالب التي تستخدم {TOKEN} مباشرة
        code = code.replace('{TOKEN}', token)
        code = code.replace('{OWNER_ID}', str(user_id))

        with open(os.path.join(bot_folder, "bot.py"), 'w', encoding='utf-8') as f:
            f.write(code)

        # كتابة ملف .env لأي قالب يحتاج متغيرات البيئة (مثل template 5)
        with open(os.path.join(bot_folder, ".env"), 'w', encoding='utf-8') as f:
            f.write(f"TELEGRAM_BOT_TOKEN={token}\n")
            f.write(f"OWNER_ID={user_id}\n")

        reqs_map = {
            '1': "pyTelegramBotAPI\nurllib3\nrequests",
            '2': "pyTelegramBotAPI",
            '3': "python-telegram-bot\nyt-dlp\naiofiles\nasyncio-throttle\nPillow\nrequests",
            '4': "pyTelegramBotAPI",
            '5': "python-telegram-bot\naiofiles",
            '6': "pyTelegramBotAPI",
            '7': "pyTelegramBotAPI",
            '8': "pyTelegramBotAPI\nrequests",
            '9': "pyTelegramBotAPI\nrequests",
        }
        with open(os.path.join(bot_folder, "requirements.txt"), 'w') as f:
            f.write(reqs_map.get(template_key, "pyTelegramBotAPI"))

        with db_lock:
            c = conn.cursor()
            c.execute("""
                INSERT INTO bots (owner_id, token, username, name, bot_type, created_at, status, folder)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
            """, (user_id, token, bot_username, bot_name,
                  bot_type_names.get(template_key, template_key),
                  datetime.now().strftime("%Y-%m-%d %H:%M"), bot_folder))
            conn.commit()

        _run_bot(bot_folder)
        return True, bot_username, bot_name

    except Exception as e:
        return False, None, str(e)


def _run_bot(bot_folder):
    def run():
        try:
            subprocess.check_call(
                ["pip", "install", "-r", os.path.join(bot_folder, "requirements.txt")],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            # تحميل متغيرات البيئة من .env
            env = os.environ.copy()
            env_file = os.path.join(bot_folder, ".env")
            if os.path.exists(env_file):
                with open(env_file) as ef:
                    for line in ef:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            env[k.strip()] = v.strip()
            while True:
                proc = subprocess.Popen(
                    ["python3", os.path.join(bot_folder, "bot.py")],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    env=env
                )
                proc.wait()
                print(f"[صانع] البوت في {bot_folder} توقف. إعادة تشغيل...")
                time.sleep(5)
        except Exception as e:
            print(f"[صانع] خطأ في {bot_folder}: {e}")

    threading.Thread(target=run, daemon=True).start()

# ==================== INLINE KEYBOARDS ====================

def admin_main_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    # Row 1: المهملات فقط (بدون السيرفر)
    kb.add(
        types.InlineKeyboardButton("🗑 المهملات",        callback_data="menu_trash"),
    )
    # Row 2: انشاء بوت | معلومات بوت | حذف بوت
    kb.add(
        types.InlineKeyboardButton("⚙️ انشاء بوت",    callback_data="menu_create"),
        types.InlineKeyboardButton("ℹ️ معلومات بوت", callback_data="menu_info"),
        types.InlineKeyboardButton("🗑 حذف بوت",      callback_data="menu_delete"),
    )
    # Row 3: تشغيل بوت | ايقاف بوت
    kb.add(
        types.InlineKeyboardButton("▶️ تشغيل بوت",   callback_data="menu_activate_one"),
        types.InlineKeyboardButton("⏸ ايقاف بوت",    callback_data="menu_deactivate_one"),
    )
    # Row 4: تشغيل الكل | ايقاف الكل
    kb.add(
        types.InlineKeyboardButton("🔛 تشغيل الكل",  callback_data="menu_activate_all"),
        types.InlineKeyboardButton("🔕 ايقاف الكل",  callback_data="menu_deactivate_all"),
    )
    # Row 5: المتروكات | المحذوفات | حذف الكل
    kb.add(
        types.InlineKeyboardButton("🤖 المتروكات",    callback_data="menu_abandoned"),
        types.InlineKeyboardButton("🚫 المحذوفات",    callback_data="menu_deleted"),
        types.InlineKeyboardButton("❌ حذف الكل",     callback_data="confirm_delete_all_ask"),
    )
    # Row 6: تحديث البوتات | عرض البوتات | الاحصائيات
    kb.add(
        types.InlineKeyboardButton("♻️ تحديث البوتات", callback_data="menu_refresh"),
        types.InlineKeyboardButton("ℹ️ عرض البوتات",  callback_data="menu_display_all"),
        types.InlineKeyboardButton("🤖 الاحصائيات",   callback_data="menu_stats"),
    )
    # Row 7: قائمة البوتات | حذف المنتهيات
    kb.add(
        types.InlineKeyboardButton("📋 قائمة البوتات",  callback_data="menu_list_all"),
        types.InlineKeyboardButton("🗑 حذف المنتهيات",  callback_data="menu_delete_expired"),
    )
    # Row 8: خدمي (اجباري)
    kb.add(
        types.InlineKeyboardButton("خدمي : ✅",           callback_data="menu_promote"),
    )
    # Row 9: اجباري المصنوعات
    kb.add(
        types.InlineKeyboardButton("اجباري المصنوعات :",  callback_data="noop"),
        types.InlineKeyboardButton("يوجد العدد : 1",      callback_data="menu_mandatory"),
    )
    # Row 10: إدارة القوالب
    kb.add(
        types.InlineKeyboardButton("📤 رفع قالب جديد",   callback_data="menu_upload_template"),
        types.InlineKeyboardButton("📋 القوالب المخصصة", callback_data="menu_list_templates"),
    )
    # Row 11: تحديث المصنع
    kb.add(
        types.InlineKeyboardButton("🔄 تحديث المصنع",    callback_data="menu_clear_admins"),
    )
    return kb

def user_main_kb(uid=None):
    kb = types.InlineKeyboardMarkup(row_width=2)
    # Row 1: قائمة بوتاتك | انشاء بوت
    kb.add(
        types.InlineKeyboardButton("• قائمة بوتاتك •",  callback_data="menu_list_mine"),
        types.InlineKeyboardButton("• انشاء بوت •",     callback_data="menu_create"),
    )
    # Row 2: معلومات عن البوت (full width)
    kb.add(
        types.InlineKeyboardButton("• معلومات عن البوت •", callback_data="menu_info"),
    )
    # Row 3: زر لوحة الإدارة للأدمن فقط
    if uid and is_admin(uid):
        kb.add(
            types.InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="menu_admin_panel"),
        )
    return kb

def bot_type_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for key, name in bot_type_names.items():
        kb.add(types.InlineKeyboardButton(name, callback_data=f"type_{key}"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back"))
    return kb

def cancel_inline_kb(back_cb="menu_back"):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("❌ الغاء", callback_data=back_cb))
    return kb

# ==================== USER STATES ====================
user_states = {}

# ==================== HELPERS: send/edit main menu ====================

def send_main_menu(uid, name, message_id=None):
    text = (
        f"👋 أهلاً {name}!\n🏭 مرحباً بك في صانع البوتات\n\n{FACTORY_TAG}"
    )
    kb = user_main_kb(uid=uid)
    if message_id:
        try:
            bot.edit_message_text(text, uid, message_id, reply_markup=kb)
            return
        except:
            pass
    bot.send_message(uid, text, reply_markup=kb)

def back_to_main(call):
    uid = call.from_user.id
    name = call.from_user.first_name
    user_states.pop(uid, None)
    send_main_menu(uid, name, call.message.message_id)

# ==================== /start ====================

@bot.message_handler(commands=["start"])
def start(msg):
    save_user(msg.from_user)
    uid  = msg.from_user.id
    name = msg.from_user.first_name

    if not check_subscription(uid):
        channels = get_mandatory_channels()
        ch_text = "\n".join([f"📢 {ch[2]}" for ch in channels])
        bot.send_message(uid,
            f"مرحباً {name}!\n\n⚠️ يجب الاشتراك في القنوات التالية أولاً:\n{ch_text}",
            reply_markup=mandatory_keyboard())
        return

    send_main_menu(uid, name)

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_sub_callback(call):
    uid = call.from_user.id
    if check_subscription(uid):
        bot.answer_callback_query(call.id, "✅ تم التحقق!")
        bot.delete_message(uid, call.message.message_id)
        send_main_menu(uid, call.from_user.first_name)
    else:
        bot.answer_callback_query(call.id, "❌ لم تشترك بعد!", show_alert=True)

# ==================== NOOP ====================

@bot.callback_query_handler(func=lambda c: c.data == "noop")
def noop_handler(call):
    bot.answer_callback_query(call.id)

# ==================== BACK ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_back")
def cb_back(call):
    user_states.pop(call.from_user.id, None)
    back_to_main(call)

# ==================== انشاء بوت ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_create")
def create_bot_start(call):
    uid = call.from_user.id
    if not check_subscription(uid):
        bot.answer_callback_query(call.id, "⚠️ يجب الاشتراك أولاً!", show_alert=True)
        return
    bot.edit_message_text("🤖 اختر نوع البوت الذي تريد إنشاءه:",
                          uid, call.message.message_id, reply_markup=bot_type_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("type_"))
def bot_type_selected(call):
    uid = call.from_user.id
    template_key = call.data.replace("type_", "")
    user_states[uid] = {"step": "waiting_token", "template": template_key, "msg_id": call.message.message_id}
    bot.edit_message_text(
        f"✅ اخترت: {bot_type_names.get(template_key)}\n\n🔑 أرسل توكن البوت (من @BotFather):",
        uid, call.message.message_id,
        reply_markup=cancel_inline_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "waiting_token")
def receive_token(msg):
    uid = msg.from_user.id
    state = user_states.get(uid, {})
    msg_id = state.get("msg_id")

    token = msg.text.strip()
    try:
        bot.delete_message(uid, msg.message_id)
    except:
        pass

    if not token_valid(token):
        bot.edit_message_text("❌ التوكن غير صحيح! أرسل توكن صحيح:",
                              uid, msg_id, reply_markup=cancel_inline_kb())
        return

    c = conn.cursor()
    c.execute("SELECT id, status FROM bots WHERE token=?", (token,))
    existing = c.fetchone()
    if existing:
        # لو موجود ومش محذوف = مسجل فعلاً
        user_states.pop(uid, None)
        back_kb = types.InlineKeyboardMarkup()
        back_kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back"))
        bot.edit_message_text("⚠️ هذا البوت مسجل مسبقاً!", uid, msg_id,
                              reply_markup=back_kb)
        return

    bot.edit_message_text("⏳ جاري التحقق من التوكن وإنشاء البوت...", uid, msg_id)

    template_key = state["template"]
    success, bot_username, bot_name = create_bot_file(uid, token, template_key)
    user_states.pop(uid, None)
    kb = user_main_kb(uid=uid)

    if success:
        success_text = (
            f"✅ **تم إنشاء البوت بنجاح!**\n\n"
            f"🤖 الاسم: `{bot_name}`\n"
            f"👤 اليوزر: @{bot_username}\n"
            f"📌 النوع: {bot_type_names.get(template_key)}\n\n"
            f"{FACTORY_TAG}"
        )
        bot.edit_message_text(success_text, uid, msg_id, parse_mode="Markdown", reply_markup=kb)
        # إشعار الأدمن الرئيسي إذا لم يكن هو المنشئ
        if uid != ADMIN_ID:
            try:
                c2 = conn.cursor()
                c2.execute("SELECT first_name, username FROM users WHERE id=?", (uid,))
                user_row = c2.fetchone()
                creator_name = (user_row[0] if user_row else str(uid))
                creator_user = (f"@{user_row[1]}" if user_row and user_row[1] else f"ID:{uid}")
                bot.send_message(ADMIN_ID,
                    f"🆕 **تم إنشاء بوت جديد!**\n\n"
                    f"👤 المنشئ: {creator_name} ({creator_user})\n"
                    f"🤖 البوت: @{bot_username}\n"
                    f"📌 النوع: {bot_type_names.get(template_key)}",
                    parse_mode="Markdown")
            except:
                pass
    else:
        bot.edit_message_text(f"❌ حدث خطأ: {bot_name}", uid, msg_id, reply_markup=kb)

# ==================== قائمة البوتات ====================

@bot.callback_query_handler(func=lambda c: c.data in ["menu_list_all", "menu_list_mine"])
def list_bots(call):
    uid = call.from_user.id
    if call.data == "menu_list_all" and is_admin(uid):
        bots = get_all_bots()
        title = "📋 **جميع البوتات:**"
    else:
        bots = get_user_bots(uid)
        title = "📋 **بوتاتك:**"

    back_kb = types.InlineKeyboardMarkup()
    back_kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back"))

    if not bots:
        bot.edit_message_text("❌ لا يوجد بوتات.", uid, call.message.message_id, reply_markup=back_kb)
        return
    text = f"{title}\n\n"
    for i, b in enumerate(bots, 1):
        icon = "🟢" if b[7] == "active" else "🔴"
        text += f"{i}. {icon} @{b[3]} | {b[5]} | {b[6]}\n"
    # تيليغرام يقبل 4096 حرف كحد أقصى
    if len(text) > 4000:
        text = text[:4000] + "\n\n...والمزيد"
    try:
        bot.edit_message_text(text, uid, call.message.message_id, parse_mode="Markdown", reply_markup=back_kb)
    except Exception:
        bot.edit_message_text(text, uid, call.message.message_id, reply_markup=back_kb)

# ==================== معلومات بوت ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_info")
def bot_info_start(call):
    uid = call.from_user.id
    user_states[uid] = {"step": "info_waiting_username", "msg_id": call.message.message_id}
    bot.edit_message_text("🔍 أرسل يوزر البوت أو توكنه:",
                          uid, call.message.message_id, reply_markup=cancel_inline_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "info_waiting_username")
def bot_info_show(msg):
    uid = msg.from_user.id
    msg_id = user_states[uid].get("msg_id")
    try:
        bot.delete_message(uid, msg.message_id)
    except:
        pass

    query = msg.text.strip().replace("@", "")
    c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE username=? OR token=?", (query, query))
    b = c.fetchone()
    user_states.pop(uid, None)
    kb = user_main_kb(uid=uid)

    if not b:
        bot.edit_message_text("❌ البوت غير موجود في قاعدة البيانات.", uid, msg_id, reply_markup=kb)
        return
    bot.edit_message_text(
        f"ℹ️ **معلومات البوت:**\n\n"
        f"🤖 الاسم: `{b[4]}`\n👤 اليوزر: @{b[3]}\n🔑 التوكن: `{b[2]}`\n"
        f"📌 النوع: {b[5]}\n👑 المطور ID: `{b[1]}`\n📅 تاريخ الانشاء: `{b[6]}`\n"
        f"⚡ الحالة: {'🟢 نشط' if b[7] == 'active' else '🔴 موقوف'}",
        uid, msg_id, parse_mode="Markdown", reply_markup=kb)

# ==================== ADMIN: حذف بوت ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_delete")
def delete_bot_start(call):
    if not is_admin(call.from_user.id):
        return
    uid = call.from_user.id
    user_states[uid] = {"step": "delete_waiting_username", "msg_id": call.message.message_id}
    bot.edit_message_text("🗑 أرسل يوزر البوت المراد حذفه:",
                          uid, call.message.message_id, reply_markup=cancel_inline_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "delete_waiting_username")
def delete_bot_confirm(msg):
    uid = msg.from_user.id
    msg_id = user_states[uid].get("msg_id")
    try:
        bot.delete_message(uid, msg.message_id)
    except:
        pass

    username = msg.text.strip().replace("@", "")
    with db_lock:
        c = conn.cursor()
        # احذف الملفات أولاً
        c.execute("SELECT folder FROM bots WHERE username=?", (username,))
        row = c.fetchone()
        if row and row[0] and os.path.exists(row[0]):
            import shutil
            try:
                shutil.rmtree(row[0])
            except:
                pass
        # احذف من قاعدة البيانات نهائياً
        c.execute("DELETE FROM bots WHERE username=?", (username,))
        conn.commit()
        result = c.rowcount

    user_states.pop(uid, None)
    kb = admin_main_kb()
    if result == 0:
        bot.edit_message_text("❌ البوت غير موجود!", uid, msg_id, reply_markup=kb)
    else:
        bot.edit_message_text(f"✅ تم حذف البوت @{username} نهائياً من قاعدة البيانات والملفات.", uid, msg_id, reply_markup=kb)

# ==================== ADMIN: تشغيل/ايقاف ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_activate_all")
def activate_all(call):
    if not is_admin(call.from_user.id): return
    with db_lock:
        c = conn.cursor()
        c.execute("UPDATE bots SET status='active' WHERE status='stopped'")
        conn.commit(); count = c.rowcount
    bot.answer_callback_query(call.id, f"✅ تم تشغيل {count} بوت.")
    back_to_main(call)

@bot.callback_query_handler(func=lambda c: c.data == "menu_deactivate_all")
def deactivate_all(call):
    if not is_admin(call.from_user.id): return
    with db_lock:
        c = conn.cursor()
        c.execute("UPDATE bots SET status='stopped' WHERE status='active'")
        conn.commit(); count = c.rowcount
    bot.answer_callback_query(call.id, f"⏸ تم ايقاف {count} بوت.")
    back_to_main(call)

@bot.callback_query_handler(func=lambda c: c.data == "menu_activate_one")
def activate_one_start(call):
    if not is_admin(call.from_user.id): return
    uid = call.from_user.id
    user_states[uid] = {"step": "activate_one", "msg_id": call.message.message_id}
    bot.edit_message_text("▶️ أرسل يوزر البوت لتشغيله:",
                          uid, call.message.message_id, reply_markup=cancel_inline_kb())

@bot.callback_query_handler(func=lambda c: c.data == "menu_deactivate_one")
def deactivate_one_start(call):
    if not is_admin(call.from_user.id): return
    uid = call.from_user.id
    user_states[uid] = {"step": "deactivate_one", "msg_id": call.message.message_id}
    bot.edit_message_text("⏸ أرسل يوزر البوت لايقافه:",
                          uid, call.message.message_id, reply_markup=cancel_inline_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("step") in ["activate_one", "deactivate_one"])
def toggle_one_bot(msg):
    uid = msg.from_user.id
    state = user_states.get(uid, {})
    msg_id = state.get("msg_id")
    try:
        bot.delete_message(uid, msg.message_id)
    except:
        pass

    step = state["step"]
    new_status = "active" if step == "activate_one" else "stopped"
    username = msg.text.strip().replace("@", "")
    with db_lock:
        c = conn.cursor()
        c.execute("UPDATE bots SET status=? WHERE username=?", (new_status, username))
        conn.commit()
    user_states.pop(uid, None)
    icon = "▶️" if new_status == "active" else "⏸"
    kb = admin_main_kb()
    bot.edit_message_text(f"{icon} تم تغيير حالة @{username} إلى {new_status}",
                          uid, msg_id, reply_markup=kb)

# ==================== ADMIN: حذف الكل ====================

@bot.callback_query_handler(func=lambda c: c.data == "confirm_delete_all_ask")
def delete_all_bots(call):
    if not is_admin(call.from_user.id): return
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ تأكيد", callback_data="confirm_delete_all"),
           types.InlineKeyboardButton("❌ الغاء", callback_data="cancel_delete_all"))
    bot.edit_message_text("⚠️ هل تريد حذف جميع البوتات؟",
                          call.from_user.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ["confirm_delete_all", "cancel_delete_all"])
def delete_all_confirm(call):
    if call.data == "confirm_delete_all":
        with db_lock:
            c = conn.cursor()
            c.execute("SELECT folder FROM bots")
            folders = c.fetchall()
            import shutil
            for (folder,) in folders:
                if folder and os.path.exists(folder):
                    try:
                        shutil.rmtree(folder)
                    except:
                        pass
            c.execute("DELETE FROM bots")
            conn.commit()
        bot.edit_message_text("✅ تم حذف جميع البوتات.", call.message.chat.id, call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(
                                  types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")))
    else:
        back_to_main(call)

# ==================== ADMIN: المتروكات / المحذوفات / المهملات ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_abandoned")
def show_abandoned(call):
    if not is_admin(call.from_user.id): return
    bots = get_abandoned_bots()
    back_kb = types.InlineKeyboardMarkup()
    back_kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back"))
    if not bots:
        bot.edit_message_text("✅ لا يوجد بوتات متروكة.", call.from_user.id,
                              call.message.message_id, reply_markup=back_kb)
        return
    text = "🤖 **البوتات المتروكة:**\n\n"
    for b in bots:
        text += f"• @{b[3]} | {b[5]} | {b[6]}\n"
    bot.edit_message_text(text, call.from_user.id, call.message.message_id,
                          parse_mode="Markdown", reply_markup=back_kb)

@bot.callback_query_handler(func=lambda c: c.data in ["menu_deleted", "menu_trash"])
def show_deleted(call):
    if not is_admin(call.from_user.id): return
    c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE status='deleted'")
    bots = c.fetchall()
    back_kb = types.InlineKeyboardMarkup()
    back_kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back"))
    if not bots:
        bot.edit_message_text("✅ لا يوجد بوتات محذوفة.", call.from_user.id,
                              call.message.message_id, reply_markup=back_kb)
        return
    text = "🗑 **البوتات المحذوفة:**\n\n"
    for b in bots:
        text += f"• @{b[3]} | {b[5]} | {b[6]}\n"
    bot.edit_message_text(text, call.from_user.id, call.message.message_id,
                          parse_mode="Markdown", reply_markup=back_kb)

@bot.callback_query_handler(func=lambda c: c.data == "menu_delete_expired")
def delete_expired(call):
    if not is_admin(call.from_user.id): return
    bots = get_abandoned_bots()
    if not bots:
        bot.answer_callback_query(call.id, "✅ لا يوجد بوتات منتهية.")
        back_to_main(call)
        return
    with db_lock:
        c = conn.cursor()
        c.execute("SELECT folder FROM bots WHERE added_to_group=0")
        folders = c.fetchall()
        import shutil
        for (folder,) in folders:
            if folder and os.path.exists(folder):
                try:
                    shutil.rmtree(folder)
                except:
                    pass
        c.execute("DELETE FROM bots WHERE added_to_group=0")
        conn.commit(); count = c.rowcount
    bot.answer_callback_query(call.id, f"✅ تم حذف {count} بوت منتهي.")
    back_to_main(call)

# ==================== ADMIN: الاحصائيات ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_stats")
def show_stats(call):
    if not is_admin(call.from_user.id): return
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM bots WHERE status='active'"); active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bots WHERE status='stopped'"); stopped = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bots WHERE status='deleted'"); deleted = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users"); users_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bots WHERE added_to_group=0 AND status='active'"); abandoned = c.fetchone()[0]
    back_kb = types.InlineKeyboardMarkup()
    back_kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back"))
    bot.edit_message_text(
        f"📊 **الاحصائيات:**\n\n🟢 بوتات نشطة: `{active}`\n🔴 بوتات موقوفة: `{stopped}`\n"
        f"🗑 بوتات محذوفة: `{deleted}`\n🤖 بوتات متروكة: `{abandoned}`\n👥 المستخدمون: `{users_count}`",
        call.from_user.id, call.message.message_id, parse_mode="Markdown", reply_markup=back_kb)

# ==================== ADMIN: عرض البوتات ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_display_all")
def display_all_bots(call):
    if not is_admin(call.from_user.id): return
    bots = get_all_bots()
    back_kb = types.InlineKeyboardMarkup()
    back_kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back"))
    if not bots:
        bot.edit_message_text("❌ لا يوجد بوتات.", call.from_user.id,
                              call.message.message_id, reply_markup=back_kb)
        return
    text = "📋 **جميع البوتات:**\n\n"
    for i, b in enumerate(bots, 1):
        icon = "🟢" if b[7] == "active" else "🔴"
        text += f"{i}. {icon} @{b[3]}\n   📌 {b[5]} | 👑 `{b[1]}` | 📅 {b[6]}\n\n"
    bot.edit_message_text(text, call.from_user.id, call.message.message_id,
                          parse_mode="Markdown", reply_markup=back_kb)

@bot.callback_query_handler(func=lambda c: c.data == "menu_refresh")
def refresh_bots(call):
    if not is_admin(call.from_user.id): return
    bots = get_all_bots(); updated = 0
    for b in bots:
        info = get_bot_info(b[2])
        if info:
            with db_lock:
                c = conn.cursor()
                c.execute("UPDATE bots SET username=?, name=? WHERE id=?",
                          (info.get("username", b[3]), info.get("first_name", b[4]), b[0]))
                conn.commit()
            updated += 1
    bot.answer_callback_query(call.id, f"✅ تم تحديث {updated} بوت.")
    back_to_main(call)

# ==================== ADMIN: اجباري المصنوعات ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_mandatory")
def mandatory_menu(call):
    if not is_admin(call.from_user.id): return
    channels = get_mandatory_channels()
    text = "📢 **الاشتراك الاجباري:**\n\n"
    if channels:
        for ch in channels:
            text += f"• {ch[2]} (`{ch[1]}`)\n"
    else:
        text += "لا يوجد قنوات اجبارية.\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ اضافة قناة", callback_data="add_channel"),
           types.InlineKeyboardButton("🗑 حذف قناة", callback_data="del_channel"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back"))
    bot.edit_message_text(text, call.from_user.id, call.message.message_id,
                          parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "add_channel")
def add_channel_start(call):
    uid = call.from_user.id
    user_states[uid] = {"step": "add_channel", "msg_id": call.message.message_id}
    bot.edit_message_text("📢 أرسل يوزر القناة (مثل: @mychannel):",
                          uid, call.message.message_id, reply_markup=cancel_inline_kb("menu_mandatory"))

@bot.callback_query_handler(func=lambda c: c.data == "del_channel")
def del_channel_start(call):
    uid = call.from_user.id
    channels = get_mandatory_channels()
    if not channels:
        bot.answer_callback_query(call.id, "❌ لا توجد قنوات!")
        return
    kb = types.InlineKeyboardMarkup()
    for ch in channels:
        kb.add(types.InlineKeyboardButton(f"🗑 {ch[2]}", callback_data=f"remove_ch_{ch[0]}"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_mandatory"))
    bot.edit_message_text("اختر القناة للحذف:", uid, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("remove_ch_"))
def remove_channel(call):
    ch_id = int(call.data.replace("remove_ch_", ""))
    with db_lock:
        c = conn.cursor()
        c.execute("DELETE FROM mandatory_channels WHERE id=?", (ch_id,))
        conn.commit()
    bot.answer_callback_query(call.id, "✅ تم حذف القناة.")
    # go back to mandatory menu
    mandatory_menu(call)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "add_channel")
def add_channel_receive(msg):
    uid = msg.from_user.id
    msg_id = user_states[uid].get("msg_id")
    try:
        bot.delete_message(uid, msg.message_id)
    except:
        pass

    channel = msg.text.strip()
    if not channel.startswith("@"):
        channel = "@" + channel
    try:
        chat = bot.get_chat(channel)
        ch_name = chat.title or channel
        with db_lock:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO mandatory_channels (channel_id, channel_name, added_by) VALUES (?,?,?)",
                      (channel, ch_name, uid))
            conn.commit()
        user_states.pop(uid, None)
        kb = admin_main_kb()
        bot.edit_message_text(f"✅ تم اضافة {ch_name} للاشتراك الاجباري!", uid, msg_id, reply_markup=kb)
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {str(e)}\nتأكد أن البوت أدمن في القناة!",
                              uid, msg_id, reply_markup=cancel_inline_kb("menu_mandatory"))

# ==================== ADMIN: رفع ادمن / مسح رفع ادمن ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_promote")
def promote_admin_start(call):
    if call.from_user.id != ADMIN_ID: return
    uid = call.from_user.id
    user_states[uid] = {"step": "promote_admin", "msg_id": call.message.message_id}
    bot.edit_message_text("👑 أرسل ID أو يوزر الشخص المراد رفعه أدمن:",
                          uid, call.message.message_id, reply_markup=cancel_inline_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "promote_admin")
def promote_admin_receive(msg):
    uid = msg.from_user.id
    msg_id = user_states[uid].get("msg_id")
    try:
        bot.delete_message(uid, msg.message_id)
    except:
        pass

    query = msg.text.strip().replace("@", "")
    try:
        target = bot.get_chat(int(query) if query.isdigit() else f"@{query}")
        target_id = target.id
        target_name = getattr(target, "first_name", "") or str(target_id)
        target_user = getattr(target, "username", "") or ""
        if target_id == ADMIN_ID:
            bot.edit_message_text("⚠️ هذا هو الأدمن الرئيسي بالفعل!",
                                  uid, msg_id, reply_markup=admin_main_kb())
            user_states.pop(uid, None)
            return
        with db_lock:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO extra_admins (user_id, username, first_name, added_at) VALUES (?, ?, ?, ?)",
                      (target_id, target_user, target_name, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
        user_states.pop(uid, None)
        bot.edit_message_text(f"✅ تم رفع **{target_name}** أدمن!\n👤 ID: `{target_id}`",
                              uid, msg_id, parse_mode="Markdown", reply_markup=admin_main_kb())
        try:
            bot.send_message(target_id, f"🎉 تم تعيينك أدمن في بوت المصنع!\n\n{FACTORY_TAG}")
        except:
            pass
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {str(e)}", uid, msg_id, reply_markup=admin_main_kb())
        user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data == "menu_clear_admins")
def clear_admins_menu(call):
    if call.from_user.id != ADMIN_ID: return
    admins = get_extra_admins()
    if not admins:
        bot.answer_callback_query(call.id, "✅ لا يوجد أدمنز مرفوعين حالياً.")
        return
    kb = types.InlineKeyboardMarkup()
    for adm in admins:
        label = f"🗑 {adm[3] or adm[2] or adm[1]} (ID: {adm[1]})"
        kb.add(types.InlineKeyboardButton(label, callback_data=f"remove_admin_{adm[1]}"))
    kb.add(types.InlineKeyboardButton("🧹 مسح الكل", callback_data="remove_all_admins"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع",     callback_data="menu_back"))
    text = "👑 **الأدمنز المرفوعين:**\n\n"
    for adm in admins:
        text += f"• {adm[3] or adm[2] or adm[1]} | ID: `{adm[1]}` | {adm[4]}\n"
    text += "\nاختر الأدمن للحذف:"
    bot.edit_message_text(text, call.from_user.id, call.message.message_id,
                          parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("remove_admin_"))
def remove_single_admin(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ غير مصرح!")
        return
    target_id = int(call.data.replace("remove_admin_", ""))
    with db_lock:
        c = conn.cursor()
        c.execute("DELETE FROM extra_admins WHERE user_id=?", (target_id,))
        conn.commit()
    bot.answer_callback_query(call.id, f"✅ تم إزالة الأدمن.")
    try:
        bot.send_message(target_id, "⚠️ تم إزالة صلاحياتك كأدمن.")
    except:
        pass
    clear_admins_menu(call)

@bot.callback_query_handler(func=lambda c: c.data == "remove_all_admins")
def remove_all_admins_cb(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ غير مصرح!")
        return
    admins = get_extra_admins()
    with db_lock:
        c = conn.cursor()
        c.execute("DELETE FROM extra_admins")
        conn.commit()
    for adm in admins:
        try:
            bot.send_message(adm[1], "⚠️ تم إزالة صلاحياتك كأدمن.")
        except:
            pass
    bot.edit_message_text(f"✅ تم مسح جميع الأدمنز المرفوعين ({len(admins)}).",
                          call.message.chat.id, call.message.message_id,
                          reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")))



# ==================== ADMIN: نظام رفع القوالب ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_upload_template")
def upload_template_start(call):
    if not is_admin(call.from_user.id): return
    uid = call.from_user.id
    user_states[uid] = {"step": "upload_template_waiting_file", "msg_id": call.message.message_id}
    bot.edit_message_text(
        "📤 **رفع قالب بوت جديد**\n\n"
        "أرسل ملف `.py` الخاص بالبوت.\n\n"
        "⚠️ **تعليمات مهمة:**\n"
        "• يجب أن يحتوي الكود على `{TOKEN}` بدل التوكن\n"
        "• يجب أن يحتوي على `{OWNER_ID}` بدل ايدي المطور\n"
        "• مثال: `bot = telebot.TeleBot(\"{TOKEN}\")`\n\n"
        "سيتم استبدالهم تلقائياً عند إنشاء كل بوت.",
        uid, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=cancel_inline_kb("menu_admin_panel")
    )

AI_ZAID_API = "https://ai-zaid-v2.vercel.app/api/chat?message="

def analyze_code_with_claude(code: str) -> dict:
    import json as _json, re as _re, urllib.parse as _up

    prompt = (
        "أنت محلل كود Python لبوتات Telegram. "
        "حلل الكود وأصلحه بهذه القواعد:\n"
        "1. أي توكن Telegram أو متغير يحمله (tok, token, BOT_TOKEN...) استبدله بـ {TOKEN} في كل مكان\n"
        "2. أي OWNER_ID أو ADMIN_ID رقمي استبدله بـ {OWNER_ID}\n"
        "3. أصلح المتغيرات غير المعرفة والأسماء الخاطئة\n"
        "4. لا تغير منطق البوت\n\n"
        'رد بـ JSON فقط هكذا بدون أي نص زيادة:\n'
        '{"fixed_code":"الكود كاملاً هنا","token_found":true,"owner_found":true,"notes":"ملاحظات"}\n\n'
        f"الكود:\n{code}"
    )

    try:
        encoded = _up.quote(prompt)
        r = requests.get(AI_ZAID_API + encoded, timeout=30)
        raw = r.json().get("response", "")

        # محاولة استخراج JSON
        json_match = _re.search(r'\{[^{}]*"fixed_code"[^{}]*\}', raw, _re.DOTALL)
        if json_match:
            return _json.loads(json_match.group(0))

        # إذا رجع كود مباشرة داخل markdown
        code_match = _re.search(r'```python\n(.*?)```', raw, _re.DOTALL)
        if code_match:
            fixed = code_match.group(1).strip()
            return {
                "fixed_code": fixed,
                "token_found": "{TOKEN}" in fixed,
                "owner_found": "{OWNER_ID}" in fixed,
                "notes": "تم الاستخراج من كود مباشر"
            }

        return {"fixed_code": None, "token_found": False, "owner_found": False,
                "notes": f"رد غير متوقع من AI"}

    except Exception as e:
        return {
            "fixed_code": None,
            "token_found": False,
            "owner_found": False,
            "notes": f"فشل الاتصال بـ ai-zaid: {e}",
        }



@bot.message_handler(
    content_types=["document"],
    func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "upload_template_waiting_file"
)
def upload_template_receive_file(msg):
    import re as _re

    uid = msg.from_user.id
    state = user_states.get(uid, {})
    msg_id = state.get("msg_id")

    if not is_admin(uid):
        return

    doc = msg.document
    if not doc.file_name.endswith(".py"):
        bot.send_message(uid, "❌ الملف يجب أن يكون `.py` فقط!")
        return

    try:
        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)
        code = downloaded.decode("utf-8")
    except Exception as e:
        bot.send_message(uid, f"❌ فشل تنزيل الملف: {e}")
        return

    # إشعار المستخدم أن Claude يحلل الكود
    analyzing_msg = bot.send_message(uid, "🤖 Claude AI يحلل الكود ويصلحه... لحظة")

    info_lines = []

    # ===== تحليل Claude AI =====
    result = analyze_code_with_claude(code)

    if result["fixed_code"]:
        # Claude نجح
        code = result["fixed_code"]
        if result["token_found"]:
            info_lines.append("🔑 Claude استخرج التوكن واستبدله بـ `{TOKEN}`")
        else:
            info_lines.append("⚠️ Claude: لم يجد توكن في الكود")
        if result["owner_found"]:
            info_lines.append("👤 Claude استخرج OWNER_ID واستبدله بـ `{OWNER_ID}`")
        else:
            info_lines.append("⚠️ Claude: لم يجد OWNER_ID في الكود")
        if result["notes"]:
            info_lines.append(f"📝 ملاحظات Claude: {result['notes']}")
    else:
        # Claude فشل → fallback للـ regex القديم
        info_lines.append(f"⚠️ {result['notes']}")
        info_lines.append("🔄 يتم استخدام التحليل التلقائي بدلاً منه...")

        TOKEN_RE = _re.compile(r'(\d{8,12}:[A-Za-z0-9_-]{20,})')
        token_match = TOKEN_RE.search(code)
        if token_match and '{TOKEN}' not in token_match.group(0):
            code = code.replace(token_match.group(1), '{TOKEN}')
            info_lines.append("🔑 تم استخراج التوكن (regex) → `{TOKEN}`")
        elif '{TOKEN}' in code:
            info_lines.append("✅ الملف يحتوي على `{TOKEN}` مسبقاً")
        else:
            info_lines.append("❌ لم يتم العثور على توكن!")

        OWNER_RE = _re.compile(r'(?:OWNER_ID|ADMIN_ID|owner_id|admin_id)\s*=\s*(\d{7,12})')
        owner_match = OWNER_RE.search(code)
        if owner_match:
            code = code.replace(owner_match.group(1), '{OWNER_ID}', 1)
            info_lines.append("👤 تم استخراج OWNER_ID (regex) → `{OWNER_ID}`")
        elif '{OWNER_ID}' in code:
            info_lines.append("✅ الملف يحتوي على `{OWNER_ID}` مسبقاً")
        else:
            info_lines.append("⚠️ لم يتم العثور على OWNER_ID")

    try:
        bot.delete_message(uid, analyzing_msg.message_id)
    except:
        pass

    user_states[uid] = {
        "step": "upload_template_waiting_name",
        "msg_id": msg_id,
        "code": code,
        "filename": doc.file_name,
    }

    summary = "\n".join(info_lines)
    bot.send_message(
        uid,
        f"✅ تم تحليل الملف: `{doc.file_name}`\n\n"
        f"{summary}\n\n"
        f"📝 أرسل **اسم القالب** الذي سيظهر في القائمة\n"
        f"مثال: `🎮 بوت الألعاب`",
        parse_mode="Markdown",
        reply_markup=cancel_inline_kb("menu_admin_panel")
    )

@bot.message_handler(
    func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "upload_template_waiting_name"
)
def upload_template_receive_name(msg):
    uid = msg.from_user.id
    state = user_states.get(uid, {})
    msg_id = state.get("msg_id")

    if not is_admin(uid):
        return

    template_name = msg.text.strip()
    if len(template_name) < 2 or len(template_name) > 50:
        bot.send_message(uid, "❌ الاسم يجب أن يكون بين 2 و 50 حرف!")
        return

    code     = state["code"]
    filename = state["filename"]

    # الحصول على مفتاح جديد
    key = get_next_template_key()

    # حفظ الملف في مجلد القوالب
    save_path = f"bots_templates/custom_{key}_{filename}"
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as e:
        bot.send_message(uid, f"❌ فشل حفظ الملف: {e}")
        user_states.pop(uid, None)
        return

    # حفظ في قاعدة البيانات
    with db_lock:
        c = conn.cursor()
        c.execute(
            "INSERT INTO custom_templates (key, name, filename, requirements, added_by, added_at) VALUES (?,?,?,?,?,?)",
            (key, template_name, f"custom_{key}_{filename}", "pyTelegramBotAPI\nrequests",
             uid, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()

    # تحديث القوالب في الذاكرة
    bot_templates[key] = save_path
    bot_type_names[key] = template_name

    user_states.pop(uid, None)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="menu_admin_panel"))

    bot.send_message(
        uid,
        f"✅ **تم إضافة القالب بنجاح!**\n\n"
        f"🔑 المفتاح: `{key}`\n"
        f"📌 الاسم: {template_name}\n"
        f"📁 الملف: `custom_{key}_{filename}`\n\n"
        f"الحين يظهر في قائمة إنشاء البوت للجميع!",
        parse_mode="Markdown",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data == "menu_list_templates")
def list_custom_templates(call):
    if not is_admin(call.from_user.id): return
    uid = call.from_user.id

    templates = get_custom_templates()
    back_kb = types.InlineKeyboardMarkup()

    if templates:
        for t in templates:
            back_kb.add(types.InlineKeyboardButton(
                f"🗑 حذف: {t[2]}", callback_data=f"del_template_{t[1]}"
            ))

    back_kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin_panel"))

    if not templates:
        text = "📋 لا يوجد قوالب مخصصة مضافة بعد."
    else:
        text = f"📋 **القوالب المخصصة ({len(templates)}):**\n\n"
        for t in templates:
            text += f"🔑 `{t[1]}` | {t[2]}\n📁 {t[3]}\n📅 {t[6]}\n\n"

    bot.edit_message_text(text, uid, call.message.message_id,
                          parse_mode="Markdown", reply_markup=back_kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_template_"))
def delete_custom_template(call):
    if not is_admin(call.from_user.id): return
    uid = call.from_user.id
    key = call.data.replace("del_template_", "")

    with db_lock:
        c = conn.cursor()
        c.execute("SELECT filename FROM custom_templates WHERE key=?", (key,))
        row = c.fetchone()
        if row:
            filepath = f"bots_templates/{row[0]}"
            if os.path.exists(filepath):
                os.remove(filepath)
            c.execute("DELETE FROM custom_templates WHERE key=?", (key,))
            conn.commit()

    # إزالة من الذاكرة
    bot_templates.pop(key, None)
    bot_type_names.pop(key, None)

    bot.answer_callback_query(call.id, "✅ تم حذف القالب.")
    list_custom_templates(call)

# ==================== ADMIN: لوحة الإدارة ====================

@bot.callback_query_handler(func=lambda c: c.data == "menu_admin_panel")
def admin_panel(call):
    if not is_admin(call.from_user.id): return
    uid = call.from_user.id
    name = call.from_user.first_name
    text = (
        f"👑 لوحة الإدارة\n🏭 صانع البوتات\n\n{FACTORY_TAG}"
    )
    kb = admin_main_kb()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_back"))
    bot.edit_message_text(text, uid, call.message.message_id, reply_markup=kb)

# ==================== HEALTH CHECK SERVER (port 8080 for Back4app) ====================

def start_health_server():
    """Starts a minimal HTTP server on port 8080 so Back4app health checks pass."""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, format, *args):
            pass  # silence access logs

    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()

# ==================== MAIN ====================

if __name__ == "__main__":
    os.makedirs('created_bots', exist_ok=True)
    os.makedirs('bots_templates', exist_ok=True)
    load_dynamic_templates()   # تحميل القوالب المخصصة من DB

    # Start health-check server in background thread
    threading.Thread(target=start_health_server, daemon=True).start()
    print("✅ Health-check server running on port 8080")

    print(f"🏭 Bot Factory Started... | {FACTORY_TAG}")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
