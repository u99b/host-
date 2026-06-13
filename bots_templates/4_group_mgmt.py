# ====================================================
# حقوق النشر © بوت صانع | جميع الحقوق محفوظة
# صُنع بواسطة بوت المصنع الرسمي
# ====================================================


import telebot
from telebot import types
import re
import time
import os
import json
from collections import defaultdict, deque
import random
import threading
import datetime
import zoneinfo

BOT_TOKEN = os.environ.get('BOT_TOKEN', '{TOKEN}')
DEVELOPER_ID = os.environ.get('DEVELOPER_ID', '{OWNER_ID}')

if not BOT_TOKEN:
    BOT_TOKEN = '{TOKEN}'
if not DEVELOPER_ID:
    DEVELOPER_ID = '{OWNER_ID}'

try:
    DEVELOPER_ID = int(DEVELOPER_ID)
except ValueError:
    print("Developer ID must be an integer.")
    exit()

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DATA_DIR = "group_data"
ADMIN_DATA_FILE = "admin_data.json"
db = {}
admin_db = {}
user_states = {}
last_message_tracker = {}
chat_member_cache = {}

def load_admin_data():
    global admin_db
    try:
        if os.path.exists(ADMIN_DATA_FILE):
            with open(ADMIN_DATA_FILE, 'r', encoding='utf-8') as f:
                admin_db = json.load(f)
        else:
            admin_db = {
                "maintenance_mode": False,
                "new_member_alert": False,
                "subscribed_channels": [],
                "deactivated_groups": [],
                "users": {},
                "notified_admin_groups": []
            }
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading admin data: {e}")
        admin_db = {
                "maintenance_mode": False,
                "new_member_alert": False,
                "subscribed_channels": [],
                "deactivated_groups": [],
                "users": {},
                "notified_admin_groups": []
        }

def save_admin_data():
    try:
        with open(ADMIN_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(admin_db, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving admin data: {e}")

load_admin_data()

def save_group_data(chat_id):
    if chat_id in db:
        os.makedirs(DATA_DIR, exist_ok=True)
        file_path = os.path.join(DATA_DIR, f"{chat_id}.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(db[chat_id], f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving data for chat {chat_id}: {e}")

def load_all_data():
    global db
    if not os.path.exists(DATA_DIR):
        return
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            try:
                chat_id_str = os.path.splitext(filename)[0]
                chat_id = int(chat_id_str)
                file_path = os.path.join(DATA_DIR, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    db[chat_id] = json.load(f)
            except (ValueError, json.JSONDecodeError, IOError) as e:
                print(f"Error loading data from {filename}: {e}")

load_all_data()

FLOOD_TRACKER = defaultdict(lambda: defaultdict(lambda: deque(maxlen=20)))
UNVERIFIED_USERS = defaultdict(dict)

DEVELOPER_USERNAME = "BBBBYB2"
CHANNEL_URL = "https://t.me/ss_yj76"
GROUP_URL = "https://t.me/O790000"

ALPHABET_REGEX = {
    'arabic': re.compile(r'[\u0600-\u06FF]'),
    'persian': re.compile(r'[\u0750-\u077F]'),
    'cyrillic': re.compile(r'[\u0400-\u04FF]'),
    'chinese': re.compile(r'[\u4e00-\u9fff]'),
    'english': re.compile(r'[a-zA-Z]'),
    'latin': re.compile(r'[a-zA-Z]'),
}

FORBIDDEN_WORDS = [
    "كس", "امك", "نيج", "طيز", "كحبه", "اكحاب", "عير", "زب",
    "الله", "ربك", "الدين"
]

LANG_MAP = {
    'arabic': '☪️ العربية',
    'cyrillic': '🇷🇺 أبجدية سيريلية',
    'chinese': '🇨🇳 الصينية',
    'latin': '🔤 اللاتينية',
    'persian': '🇮🇷 الفارسية',
    'english': '🇬🇧 الإنجليزية'
}

PUNISHMENTS_MAP = {'none': '☑️ بلا عقوبة', 'warn': '❕ إنذار', 'kick': '❗️ طرد', 'ban': '🚷 حظر', 'mute': '🔇 كتم', 'delete': '🗑 حذف'}
PUNISHMENT_ICONS = {'none': '☑️', 'warn': '❕', 'kick': '❗️', 'ban': '🚷', 'mute': '🔇', 'delete': '🗑'}

MEDIA_TYPES_MAP = {
    'links': ('🔗 الروابط', {'func': lambda m: (m.entities and any(e.type in ['url', 'text_link'] for e in m.entities)) or (m.caption_entities and any(e.type in ['url', 'text_link'] for e in m.caption_entities))}),
    'story': ('📲 قصة', {'content_types': ['story']}),
    'photo': ('📸 صورة', {'content_types': ['photo']}),
    'video': ('🎞 فيديو', {'content_types': ['video']}),
    'animation': ('🎥 صورة متحركة', {'content_types': ['animation']}),
    'voice': ('🎤 بصمة صوت', {'content_types': ['voice']}),
    'audio': ('🎧 مقطع صوتي', {'content_types': ['audio']}),
    'sticker': ('🃏 ملصق', {'func': lambda m: m.content_type == 'sticker' and not getattr(m.sticker, 'is_animated', False)}),
    'animated_sticker': ('🎭 ملصقات متحركة', {'func': lambda m: m.content_type == 'sticker' and getattr(m.sticker, 'is_animated', False)}),
    'dice': ('🎲 ألعاب الرسوم المتحركة', {'content_types': ['dice']}),
    'custom_emoji': ('👾 رموز تعبيرية مخصصة', {'entity': 'custom_emoji'}),
    'document': ('💾 ملف', {'content_types': ['document']}),
    'game': ('🎮 ألعاب', {'content_types': ['game']}),
    'contact': ('🏷 جهات الاتصال', {'content_types': ['contact']}),
    'location': ('📍 الموقع', {'content_types': ['location', 'venue']}),
    'inline_bot': ('🤖 بوت انلاين', {'func': lambda m: m.via_bot is not None}),
    'spoiler': ('🗯 الرسائل المشوشة', {'entity': 'spoiler'}),
    'media_spoiler': ('🌌 الوسائط المشوشة', {'func': lambda m: hasattr(m, 'has_media_spoiler') and m.has_media_spoiler}),
    'video_note': ('👁‍🗨 بصمة فيديو', {'content_types': ['video_note']}),
}
MEDIA_KEYS_PAGE1 = list(MEDIA_TYPES_MAP.keys())[:12]
MEDIA_KEYS_PAGE2 = list(MEDIA_TYPES_MAP.keys())[12:]

def init_chat_db(chat_id):
    if chat_id not in db:
        db[chat_id] = {
            'activated': False,
            'lang': 'ar',
            'rules': {'text': "لم يتم تعيين قوانين لهذه المجموعة بعد.", 'media_type': None, 'media_id': None, 'caption': None},
            'antispam': {
                'links': {
                    'punishment': 'none', 'duration': None, 'delete': False,
                    'block_usernames': False, 'block_bot_usernames': False, 'exceptions': []
                }
            },
            'whitelist': {
                'enabled': True, 'list': []
            },
            'welcome': {
                'enabled': False,
                'message': "• نورتنا يا حلو {mention} 🐆\n• اسمك: {full_name}\n• ايديك: `{user_id}`",
                'first_join_only': False,
                'joined_users': []
            },
            'goodbye': {
                'enabled': False,
                'message': "وداعًا {mention}, نراك لاحقًا.",
                'send_private': False,
            },
            'antiflood': {
                'enabled': False, 'messages': 5, 'seconds': 3,
                'punishment': 'delete', 'duration': None, 'delete_messages': True
            },
            'anti_repeat': {
                'enabled': False,
                'punishment': 'mute',
            },
            'alphabets': {
                'arabic': {'punishment': 'none', 'delete': False},
                'persian': {'punishment': 'none', 'delete': False},
                'english': {'punishment': 'none', 'delete': False},
                'cyrillic': {'punishment': 'none', 'delete': False},
                'chinese': {'punishment': 'none', 'delete': False},
                'latin': {'punishment': 'none', 'delete': False},
            },
            'restrictions': {
                'check_on_join': True,
                'delete_messages': False,
                'enforce': {
                    'last_name': {'punishment': 'none'},
                    'username': {'punishment': 'none'},
                    'profile_photo': {'punishment': 'none'},
                    'channel_subscribe': {'punishment': 'none', 'channel': None},
                    'must_add': {'punishment': 'none', 'count': 0}
                },
                'prevent': {
                    'arabic_name': {'punishment': 'none'},
                    'chinese_name': {'punishment': 'none'},
                    'russian_name': {'punishment': 'none'},
                    'forbidden_name': {'punishment': 'none'}
                }
            },
            'warnings_settings': {
                'punishment': 'mute',
                'limit': 3,
                'mute_duration': 0,
                'warned_users': {}
            },
            'captcha': {
                'enabled': False,
                'time_limit': 3,
                'punishment': 'mute',
                'mode': 'button',
                'delete_service_message': False,
            },
            'media_restrictions': {key: {'punishment': 'none'} for key in MEDIA_TYPES_MAP.keys()},
            'night_mode': {
                'enabled': False,
                'start_hour': 23,
                'end_hour': 9,
                'notify': True,
                'timezone': 'UTC',
                'is_active_now': False
            },
            'forbidden_words': {
                'punishment': 'none',
                'delete_message': True,
                'words': FORBIDDEN_WORDS.copy()
            },
            'repeating_messages': {
                'enabled': False,
                'messages': [],
                'interval_seconds': 86400,
                'last_sent_timestamp': 0,
            },
            'paid_features': {
                'fast_repeat': False
            },
            'incognito_users': {
                'enabled': False,
                'delete_messages': False,
                'exceptions': []
            },
            'personal_replies': {},
            'long_messages': {
                'enabled': False,
                'punishment': 'none',
                'delete': False,
                'min_chars': 0,
                'max_chars': 2000
            },
            'bot_name_settings': {
                'name': None,
                'enabled': False,
                'replies': [
                    "ها", "شكو", "هلا يكلبي", "خيرك", "شكو تصيحني🤔", "حياك",
                    "كول عمري", "عيوني", "يا كمر كول", "شتريد 😒", "نعم؟",
                    "آمرني", "تدلل", "جيتك ركض", "سمعاً وطاعة", "لبيك"
                ]
            },
            'id_command': {
                'enabled': False,
                'with_photo': False
            },
            'message_counts': {},
            'secondary_owners': [],
            'managers': [],
            'delete_mode_enabled': False,
        }
        save_group_data(chat_id)

def get_user_status_in_chat(chat_id, user_id):
    cache_key = (chat_id, user_id)
    if cache_key in chat_member_cache and time.time() - chat_member_cache[cache_key]['timestamp'] < 60:
        return chat_member_cache[cache_key]['status']
    try:
        status = bot.get_chat_member(chat_id, user_id).status
        chat_member_cache[cache_key] = {'status': status, 'timestamp': time.time()}
        return status
    except Exception:
        return 'left'

def is_bot_owner(user_id):
    return user_id == DEVELOPER_ID

def is_group_creator(chat_id, user_id):
    return get_user_status_in_chat(chat_id, user_id) == 'creator'

def is_admin(chat_id, user_id):
    if is_bot_owner(user_id):
        return True
    try:
        return bot.get_chat_member(chat_id, user_id).status in ['creator', 'administrator']
    except Exception:
        return False

def is_secondary_owner(chat_id, user_id):
    init_chat_db(chat_id)
    return user_id in db[chat_id].get('secondary_owners', [])

def is_manager(chat_id, user_id):
    init_chat_db(chat_id)
    return user_id in db[chat_id].get('managers', [])

def has_full_bot_access(chat_id, user_id):
    return is_admin(chat_id, user_id) or is_secondary_owner(chat_id, user_id)

def has_manager_access(chat_id, user_id):
    return has_full_bot_access(chat_id, user_id) or is_manager(chat_id, user_id)

def get_user_rank_in_group(chat_id, user_id):
    if is_bot_owner(user_id):
        return "المطور"
    status = get_user_status_in_chat(chat_id, user_id)
    if status == 'creator':
        return "المالك"
    if is_secondary_owner(chat_id, user_id):
        return "مالك ثانوي"
    if is_manager(chat_id, user_id):
        return "مدير"
    if status == 'administrator':
        return "مشرف"
    return "عضو"

def get_admin_panel_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    alert_status = "مفعل ✅" if admin_db.get('new_member_alert') else "معطل ❌"
    maintenance_status = "متوقف ⛔️" if admin_db.get('maintenance_mode') else "يعمل ✅"
    alert_btn = types.InlineKeyboardButton(f"تنبيه الدخول: {alert_status}", callback_data="admin_toggle_alert")
    list_groups_btn = types.InlineKeyboardButton("عرض المجموعات", callback_data="admin_list_groups")
    add_channel_btn = types.InlineKeyboardButton("➕ إضافة قناة اشتراك", callback_data="admin_add_channel")
    del_channel_btn = types.InlineKeyboardButton("➖ حذف قناة اشتراك", callback_data="admin_del_channel")
    list_channels_btn = types.InlineKeyboardButton("📖 عرض القنوات", callback_data="admin_list_channels")
    maintenance_btn = types.InlineKeyboardButton(f"حالة البوت: {maintenance_status}", callback_data="admin_toggle_maintenance")
    owner_link_btn = types.InlineKeyboardButton("رابط المالك", url=f"https://t.me/{DEVELOPER_USERNAME}")
    stats_btn = types.InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")
    stop_group_btn = types.InlineKeyboardButton("ايقاف بوت بمجموعة", callback_data="admin_stop_group")
    start_group_btn = types.InlineKeyboardButton("تشغيل بوت بمجموعة", callback_data="admin_start_group")
    markup.add(alert_btn, list_groups_btn)
    markup.add(add_channel_btn)
    markup.add(del_channel_btn, list_channels_btn)
    markup.add(maintenance_btn, stats_btn)
    markup.add(stop_group_btn, start_group_btn)
    markup.add(owner_link_btn)
    text = "⚙️ <b>لوحة تحكم المالك</b>"
    return text, markup

def get_bot_name_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('bot_name_settings', {})
    enabled = settings.get('enabled', False)
    name = settings.get('name')
    status_text = "مفعل" if enabled else "معطل"
    name_text = f"<code>{name}</code>" if name else "لم يتم التعيين بعد"
    text = f"""🗣️ <b>إعدادات اسم البوت</b>
هنا يمكنك تحديد اسم للبوت وعندما يذكره أي شخص، سيقوم البوت بالرد عليه.

<b>الحالة:</b> {status_text}
<b>الاسم الحالي:</b> {name_text}
"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_btn_text = "تعطيل" if enabled else "تفعيل"
    markup.add(types.InlineKeyboardButton(toggle_btn_text, callback_data=f"botname_toggle_enabled_{chat_id}"))
    markup.add(types.InlineKeyboardButton("تحديد / تغيير الاسم", callback_data=f"botname_set_name_{chat_id}"))
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}"))
    return text, markup


def get_personal_replies_menu(chat_id):
    init_chat_db(chat_id)
    text = "⚙️ <b>إدارة الردود الشخصية</b>\n\nاختر من القائمة أدناه:"
    markup = types.InlineKeyboardMarkup(row_width=2)
    add_btn = types.InlineKeyboardButton("➕ إضافة رد", callback_data=f"personal_add_{chat_id}")
    list_btn = types.InlineKeyboardButton("📖 قائمة الكلمات", callback_data=f"personal_list_{chat_id}")
    remove_btn = types.InlineKeyboardButton("➖ إزالة كلمة", callback_data=f"personal_remove_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"commands_open_main_{chat_id}")
    markup.add(add_btn)
    markup.add(list_btn, remove_btn)
    markup.add(back_btn)
    return text, markup

def get_long_messages_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('long_messages', {})
    enabled = settings.get('enabled', False)
    punishment = settings.get('punishment', 'none')
    delete = settings.get('delete', False)
    min_chars = settings.get('min_chars', 0)
    max_chars = settings.get('max_chars', 2000)
    status_text = "مفعل" if enabled else "معطل"
    punishment_text = PUNISHMENTS_MAP.get(punishment, 'بلا عقوبة').split(' ', 1)[1]
    delete_text = "نعم ✔️" if delete else "لا ✖️"
    min_text = str(min_chars) if min_chars > 0 else "غير محدد"
    max_text = str(max_chars) if max_chars > 0 else "غير محدد"
    text = f"""📏 <b>الـرسـائـل الـطـويـلـة</b>
من هذه القائمة يمكنك تعيين الحد الأدنى/الأقصى لعدد الأحرف بالرسائل المرسلة من قبل المستخدمين.

<b>الحالة:</b> {status_text}
<b>العقوبة:</b> {punishment_text}
<b>حذف:</b> {delete_text}
<b>الـحـد الأدنى للأحـرف:</b> {min_text} حـرف
<b>الـحـد الأقـصـى للأحـرف:</b> {max_text} حـرف
"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_btn_text = "تعطيل" if enabled else "تفعيل"
    markup.add(types.InlineKeyboardButton(toggle_btn_text, callback_data=f"longmsg_toggle_enabled_{chat_id}"))
    punishments_row = []
    for p_key in ['kick', 'warn', 'none', 'ban', 'mute']:
        p_name = PUNISHMENTS_MAP.get(p_key, f' {p_key}').split(' ', 1)[1]
        btn_text = f"✅ {p_name}" if punishment == p_key else p_name
        punishments_row.append(types.InlineKeyboardButton(btn_text, callback_data=f"longmsg_set_punish_{p_key}_{chat_id}"))
    markup.row(*punishments_row)
    delete_toggle_btn = types.InlineKeyboardButton(f"حذف الرسائل: {delete_text}", callback_data=f"longmsg_toggle_delete_{chat_id}")
    markup.add(delete_toggle_btn)
    min_btn = types.InlineKeyboardButton("الحد الأدنى للأحرف", callback_data=f"longmsg_open_min_{chat_id}")
    max_btn = types.InlineKeyboardButton("الحد الأقصى للأحرف", callback_data=f"longmsg_open_max_{chat_id}")
    markup.add(min_btn, max_btn)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}"))
    return text, markup

def get_long_messages_limit_menu(chat_id, limit_type):
    if limit_type == 'min':
        text = "اختر الحد الأدنى لعدد الأحرف."
        options = [5, 10, 20, 25, 50, 100, 200, 400, 800, 1000, 1500, 2000]
        callback_prefix = "longmsg_set_min"
    else:
        text = "اختر الحد الأقصى لعدد الأحرف."
        options = [50, 100, 150, 200, 400, 800, 1000, 1500, 2000, 2500, 3000, 3500]
        callback_prefix = "longmsg_set_max"
    markup = types.InlineKeyboardMarkup(row_width=4)
    buttons = [types.InlineKeyboardButton(str(o), callback_data=f"{callback_prefix}_{o}_{chat_id}") for o in options]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("إلغاء التحديد", callback_data=f"{callback_prefix}_0_{chat_id}"))
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"longmsg_open_main_{chat_id}"))
    return text, markup

def get_incognito_users_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('incognito_users', {})
    enabled = settings.get('enabled', False)
    delete_messages = settings.get('delete_messages', False)
    status_text = "مفعل" if enabled else "معطل"
    delete_status_text = "مفعل" if delete_messages else "معطل"
    text = f"""😶‍🌫️ <b>المستخدمون المتخفون</b>
من خلال هذه القائمة يمكنك تعيين عقوبة للمستخدمين الذين يكتبون في المجموعة علي هيئة قناة.

ℹ️ يسمح تيليجرام لكل مستخدم بالكتابة في المجموعة عن طريق الظهور بإسم قناة يمتلكها.

👮🏻‍♂️ ليس من الممكن معرفة إذا كان المستخدم الذي يكتب عبر قناة هو مشرف في المجموعة أم لا: تنطبق هذه العقوبة على أي شخص يكتب عبر قناة.

🏃🏻 عندما تحدث هذه العقوبة ، فإن المستخدم الذي كان يكتب عبر قناة سوف يواصل الكتابة إلى المجموعة ولكن بهويته الحقيقية ولم يعد يستطيع أن يرسل رسائل عبر قنوات أخرى يمتلكها.

💡 الحالة: {status_text}"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_btn_text = "تعطيل" if enabled else "تفعيل"
    toggle_btn = types.InlineKeyboardButton(toggle_btn_text, callback_data=f"incognito_toggle_enabled_{chat_id}")
    delete_toggle_btn_text = f"حذف الرسائل: {delete_status_text}"
    delete_toggle_btn = types.InlineKeyboardButton(delete_toggle_btn_text, callback_data=f"incognito_toggle_delete_{chat_id}")
    exceptions_btn = types.InlineKeyboardButton("استثناءات", callback_data=f"incognito_open_exceptions_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}")
    markup.add(toggle_btn)
    markup.add(delete_toggle_btn)
    markup.add(exceptions_btn)
    markup.add(back_btn)
    return text, markup

def get_incognito_exceptions_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('incognito_users', {})
    exceptions = settings.get('exceptions', [])
    text = """😶‍🌫️ <b>المستخدمون المتخفون - استثناءات</b>
ليس من الممكن معرفة إذا كان المستخدم الذي يكتب عبر قناة هو مشرف في المجموعة أم لا: تنطبق هذه العقوبة على أي شخص يكتب عبر قناة.

🔓 للسماح للقناة بعدم التعرض للعقوبات ، ما عليك سوى استخدام:
/free @channelUsername"""
    if exceptions:
        text += "\n\n<b>القنوات المستثناة حاليًا:</b>\n"
        text += "\n".join(f"• <code>{ch}</code>" for ch in exceptions)
    else:
        text += "\n\nلا توجد قنوات مستثناة حاليًا."
    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"incognito_open_main_{chat_id}")
    markup.add(back_btn)
    return text, markup

def get_forbidden_words_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('forbidden_words', {})
    punishment = settings.get('punishment', 'none')
    delete_message = settings.get('delete_message', True)
    text = (
        "🔤 <b>الكلمات المحظورة</b>\n\n"
        "من هذه القائمة ، يمكنك تعيين عقوبة للمستخدمين الذين يستخدمون الكلمات التي قررت حظرها.\n\n"
        f"العقوبة: {PUNISHMENTS_MAP.get(punishment, 'بلا عقوبة').split(' ', 1)[1]}\n"
        f"حذف: {'نعم ✔️' if delete_message else 'لا ✖️'}"
    )
    markup = types.InlineKeyboardMarkup(row_width=5)
    punishments_row = []
    for p_key in ['kick', 'warn', 'none', 'ban', 'mute']:
        p_name = PUNISHMENTS_MAP.get(p_key, f' {p_key}').split(' ', 1)[1]
        btn_text = f"✅ {p_name}" if punishment == p_key else p_name
        punishments_row.append(types.InlineKeyboardButton(btn_text, callback_data=f"forbiddenwords_set_punish_{p_key}_{chat_id}"))
    markup.add(*punishments_row)
    markup.row_width = 2
    add_word_btn = types.InlineKeyboardButton("➕ إضافة كلمة", callback_data=f"forbiddenwords_add_word_{chat_id}")
    remove_word_btn = types.InlineKeyboardButton("➖ إزالة كلمة", callback_data=f"forbiddenwords_remove_word_{chat_id}")
    list_words_btn = types.InlineKeyboardButton("📖 قائمة الكلمات", callback_data=f"forbiddenwords_list_words_{chat_id}")
    delete_toggle_btn_text = f"حذف الرسائل: {'مفعل' if delete_message else 'معطل'}"
    delete_toggle_btn = types.InlineKeyboardButton(delete_toggle_btn_text, callback_data=f"forbiddenwords_toggle_delete_{chat_id}")
    markup.add(add_word_btn, remove_word_btn)
    markup.add(list_words_btn, delete_toggle_btn)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}"))
    return text, markup

def get_command_guide_menu(chat_id, user_id):
    text = "📖 <b>دليل الأوامر</b>\n\nاختر رتبة لعرض الأوامر المتاحة لها."
    markup = types.InlineKeyboardMarkup(row_width=1)
    if is_group_creator(chat_id, user_id) or is_bot_owner(user_id):
        markup.add(types.InlineKeyboardButton("اوامر المالك", callback_data=f"show_cmds_owner_{chat_id}"))
        markup.add(types.InlineKeyboardButton("اوامر مالك ثانوي", callback_data=f"show_cmds_so_{chat_id}"))
        markup.add(types.InlineKeyboardButton("اوامر المدراء", callback_data=f"show_cmds_manager_{chat_id}"))
    elif is_secondary_owner(chat_id, user_id):
        markup.add(types.InlineKeyboardButton("اوامر مالك ثانوي", callback_data=f"show_cmds_so_{chat_id}"))
        markup.add(types.InlineKeyboardButton("اوامر المدراء", callback_data=f"show_cmds_manager_{chat_id}"))
    elif is_manager(chat_id, user_id):
        markup.add(types.InlineKeyboardButton("اوامر المدراء", callback_data=f"show_cmds_manager_{chat_id}"))
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"commands_open_main_{chat_id}"))
    return text, markup

def get_main_commands_menu(chat_id, user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    settings_btn = types.InlineKeyboardButton("⚙️ الإعدادات", callback_data=f"settings_open_here_{chat_id}")
    captcha_btn = types.InlineKeyboardButton("🧠 التحقق Captcha", callback_data=f"captcha_open_main_{chat_id}")
    personal_replies_btn = types.InlineKeyboardButton("🗣️ الردود الشخصية", callback_data=f"personal_open_main_{chat_id}")
    id_command_btn = types.InlineKeyboardButton("💳 اوامر الايدي", callback_data=f"idcmd_open_main_{chat_id}")
    if has_full_bot_access(chat_id, user_id):
        restrictions_btn = types.InlineKeyboardButton("🛂 القيود", callback_data=f"restrictions_open_main_{chat_id}")
        warnings_btn = types.InlineKeyboardButton("❗️إنذار المستخدمين", callback_data=f"warnings_open_main_{chat_id}")
        members_btn = types.InlineKeyboardButton("👥 إدارة الأعضاء", callback_data=f"members_open_main_{chat_id}")
        admin_roles_btn = types.InlineKeyboardButton("👑 اوامر الادمنيه", callback_data=f"adminroles_open_main_{chat_id}")
        cmd_guide_btn = types.InlineKeyboardButton("📖 دليل الأوامر", callback_data=f"cmdguide_open_main_{chat_id}")
        markup.add(settings_btn, restrictions_btn)
        markup.add(captcha_btn, warnings_btn)
        markup.add(members_btn, personal_replies_btn)
        markup.add(id_command_btn)
        markup.add(admin_roles_btn, cmd_guide_btn)
        if is_group_creator(chat_id, user_id) or is_secondary_owner(chat_id, user_id):
            delete_btn = types.InlineKeyboardButton("🗑 المسح", callback_data=f"delete_open_main_{chat_id}")
            markup.add(delete_btn)
    elif is_manager(chat_id, user_id):
        cmd_guide_btn = types.InlineKeyboardButton("📖 دليل الأوامر", callback_data=f"cmdguide_open_main_{chat_id}")
        markup.add(settings_btn, captcha_btn)
        markup.add(personal_replies_btn, id_command_btn)
        markup.add(cmd_guide_btn)
    return markup

def get_delete_menu(chat_id):
    init_chat_db(chat_id)
    is_enabled = db[chat_id].get('delete_mode_enabled', False)
    toggle_text = "تعطيل المسح ✅" if is_enabled else "تفعيل المسح ❌"
    text = "⚙️ <b>تفعيل وتعطيل المسح</b>"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(toggle_text, callback_data=f"delete_toggle_enabled_{chat_id}"))
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"commands_open_main_{chat_id}"))
    return text, markup

def get_admin_roles_menu(chat_id, user_id):
    init_chat_db(chat_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    text = "👑 <b>اوامر الادمنيه</b>\n\nهنا يمكنك إدارة الرتب الخاصة بالبوت."
    if is_group_creator(chat_id, user_id):
        markup.add(types.InlineKeyboardButton("➕ رفع مالك ثانوي", callback_data=f"adminroles_set_so_{chat_id}"))
    if has_full_bot_access(chat_id, user_id):
        markup.add(types.InlineKeyboardButton("📖 عرض المالكين الثانويين", callback_data=f"adminroles_list_so_{chat_id}"))
        markup.add(types.InlineKeyboardButton("➕ رفع مدير", callback_data=f"adminroles_set_m_{chat_id}"))
    if has_manager_access(chat_id, user_id):
        markup.add(types.InlineKeyboardButton("📖 عرض المدراء", callback_data=f"adminroles_list_m_{chat_id}"))
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"commands_open_main_{chat_id}"))
    return text, markup

def get_members_management_menu(chat_id):
    text = (
        "👥 <b>إدارة الأعضاء</b>\n\n"
        "من هذه القائمة يمكنك إدارة الإجراءات العامة على أعضاء المجموعة."
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    unban_all_btn = types.InlineKeyboardButton("الغاء حظر عن الكل", callback_data=f"members_unban_all_confirm_{chat_id}")
    unmute_all_btn = types.InlineKeyboardButton("الغاء كتم عن الكل", callback_data=f"members_unmute_all_confirm_{chat_id}")
    kick_muted_btn = types.InlineKeyboardButton("طرد مستخدمين مكتومين", callback_data=f"members_kick_muted_confirm_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"commands_open_main_{chat_id}")
    markup.add(unban_all_btn)
    markup.add(unmute_all_btn)
    markup.add(kick_muted_btn)
    markup.add(back_btn)
    return text, markup

def get_warnings_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('warnings_settings', {})
    punishment = settings.get('punishment', 'mute')
    limit = settings.get('limit', 3)
    punishment_text = {
        'mute': 'كتم', 'kick': 'طرد', 'ban': 'حظر', 'none': 'بلا عقوبة'
    }.get(punishment, 'غير معروف')
    text = (
        "❗️ <b>إنذار المستخدمين</b>\n\n"
        "قم باختيار نوع العقوبة للمستخدم الذي يتجاوز عدد الإنذارات المسموح بها.\n\n"
        "⚡️ <b>الحالي:</b>\n"
        f"  العقوبة: {punishment_text}\n"
        f"  الإنذارات المسموح بها: {limit}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    warned_users_btn = types.InlineKeyboardButton("قائمة المنذرين", callback_data=f"warnings_list_0_{chat_id}")
    clear_all_btn = types.InlineKeyboardButton("الغاء الكل", callback_data=f"warnings_clear_all_confirm_{chat_id}")
    markup.add(warned_users_btn, clear_all_btn)
    punishments = {'none': 'بلا عقوبة', 'mute': 'كتم', 'kick': 'طرد', 'ban': 'حظر'}
    punishment_buttons = []
    for p_key, p_name in punishments.items():
        text_btn = f"✅ {p_name}" if punishment == p_key else p_name
        punishment_buttons.append(types.InlineKeyboardButton(text_btn, callback_data=f"warnings_set_punish_{p_key}_{chat_id}"))
    markup.add(*punishment_buttons)
    limit_btn = types.InlineKeyboardButton("عدد الانذارات", callback_data=f"warnings_open_limit_{chat_id}")
    mute_duration_btn = types.InlineKeyboardButton("حدد مدة الكتم", callback_data=f"warnings_open_duration_{chat_id}")
    if punishment == 'mute':
        markup.add(limit_btn, mute_duration_btn)
    else:
        markup.add(limit_btn)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"commands_open_main_{chat_id}"))
    return text, markup

def get_warnings_limit_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('warnings_settings', {})
    current_limit = settings.get('limit', 3)
    text = "اختر عدد الإنذارات المسموح بها لكل شخص."
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for i in [2, 3, 4, 5, 6]:
        btn_text = f"✅ {i}" if current_limit == i else str(i)
        buttons.append(types.InlineKeyboardButton(btn_text, callback_data=f"warnings_set_limit_{i}_{chat_id}"))
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"warnings_open_main_{chat_id}"))
    return text, markup

def get_warned_users_list_menu(chat_id, page=0):
    init_chat_db(chat_id)
    warned_users_data = db[chat_id].get('warnings_settings', {}).get('warned_users', {})
    if not warned_users_data:
        text = "لا يوجد مستخدمين تم إنذارهم."
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"warnings_open_main_{chat_id}"))
        return text, markup
    warned_users = sorted(list(warned_users_data.items()), key=lambda item: int(item[1].get('count', 0)), reverse=True)
    items_per_page = 5
    start = page * items_per_page
    end = start + items_per_page
    paginated_users = warned_users[start:end]
    text = "👤 <b>قائمة المستخدمين المنذرين:</b>\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    limit = db[chat_id]['warnings_settings']['limit']
    for user_id_str, data in paginated_users:
        user_id = int(user_id_str)
        try:
            member = bot.get_chat_member(chat_id, user_id)
            user = member.user
            user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
            username = f"@{user.username}" if user.username else user_mention
        except Exception:
            username = f"مستخدم [{user_id}]"
        reason = data.get('reason', 'سبب غير محدد.')
        count = data.get('count', 0)
        user_text = f"{username} [{user_id}] قام بـ {reason}\n"
        user_text += f"• عدد الإنذارات: ({count}/{limit}) ❕\n"
        punishment_status = "لم تتم معاقبته بعد"
        if data.get('punished'):
            punishment_type = db[chat_id]['warnings_settings']['punishment']
            punishment_status = {
                'mute': 'مكتوم 🔇', 'kick': 'مطروود ❗️', 'ban': 'محظور 🚷'
            }.get(punishment_type, 'معاقب')
        user_text += f"• العقوبة: {punishment_status}\n"
        if data.get('manually_unpunished'):
            user_text += "~ تم إلغاء العقوبة عن العضو\n"
        text += user_text + "\n"
        if data.get('punished') and not data.get('manually_unpunished'):
             markup.add(types.InlineKeyboardButton(f"إلغاء كتم/حظر {username}", callback_data=f"warnings_unpunish_{user_id}_{page}_{chat_id}"))
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"warnings_list_{page-1}_{chat_id}"))
    if end < len(warned_users):
        nav_buttons.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"warnings_list_{page+1}_{chat_id}"))
    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"warnings_open_main_{chat_id}"))
    return text, markup

def get_main_settings_menu(chat_id, user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"commands_open_main_{chat_id}")
    if has_full_bot_access(chat_id, user_id):
        forbidden_words_btn = types.InlineKeyboardButton("🔤 الكلمات المحظورة", callback_data=f"forbiddenwords_open_main_{chat_id}")
        whitelist_btn = types.InlineKeyboardButton("قائمة بيضاء", callback_data=f"settings_whitelist_{chat_id}")
        welcome_btn = types.InlineKeyboardButton("الترحيب", callback_data=f"settings_welcome_{chat_id}")
        goodbye_btn = types.InlineKeyboardButton("وداعاً", callback_data=f"settings_goodbye_{chat_id}")
        antiflood_btn = types.InlineKeyboardButton("مانع التكرار (Flood)", callback_data=f"settings_antiflood_{chat_id}")
        antirepeat_btn = types.InlineKeyboardButton("🚫 منع تكرار الرسائل", callback_data=f"antirepeat_open_main_{chat_id}")
        rules_btn = types.InlineKeyboardButton("📜 قوانين المجموعة", callback_data=f"settings_rules_{chat_id}")
        media_btn = types.InlineKeyboardButton("📸 منع الوسائط", callback_data=f"media_open_menu_1_{chat_id}")
        alphabets_btn = types.InlineKeyboardButton("الحروف الهجائية", callback_data=f"settings_alphabets_{chat_id}")
        night_mode_btn = types.InlineKeyboardButton("🌒 الوضع الليلي", callback_data=f"nightmode_open_main_{chat_id}")
        incognito_btn = types.InlineKeyboardButton("😶‍🌫️ المستخدمون المتخفون", callback_data=f"incognito_open_main_{chat_id}")
        repeating_msg_btn = types.InlineKeyboardButton("🕑 تكرار الرسائل 🗣", callback_data=f"repeatingmsg_open_main_{chat_id}")
        long_messages_btn = types.InlineKeyboardButton("📏 الـرسـائـل الـطـويـلـة", callback_data=f"longmsg_open_main_{chat_id}")
        bot_name_btn = types.InlineKeyboardButton("🗣️ اسم البوت", callback_data=f"botname_open_main_{chat_id}")
        markup.add(forbidden_words_btn, whitelist_btn)
        markup.add(welcome_btn, goodbye_btn)
        markup.add(antiflood_btn, antirepeat_btn)
        markup.add(rules_btn, media_btn)
        markup.add(alphabets_btn, night_mode_btn)
        markup.add(incognito_btn, repeating_msg_btn)
        markup.add(long_messages_btn, bot_name_btn)
        markup.add(back_btn)
    elif is_manager(chat_id, user_id):
        welcome_btn = types.InlineKeyboardButton("الترحيب", callback_data=f"settings_welcome_{chat_id}")
        goodbye_btn = types.InlineKeyboardButton("وداعاً", callback_data=f"settings_goodbye_{chat_id}")
        markup.add(welcome_btn, goodbye_btn)
        markup.add(back_btn)
    return markup

def get_rules_menu(chat_id):
    init_chat_db(chat_id)
    rules_data = db[chat_id].get('rules', {})
    current_rules_text = rules_data.get('text') or rules_data.get('caption')
    text = "📜 <b>إعدادات قوانين المجموعة</b>\n\n"
    if current_rules_text:
        text += "القوانين الحالية:\n"
        text += "<blockquote>" + current_rules_text[:200] + ("..." if len(current_rules_text) > 200 else "") + "</blockquote>"
    else:
        text += "لم يتم تعيين قوانين للمجموعة بعد."
    markup = types.InlineKeyboardMarkup(row_width=2)
    set_btn = types.InlineKeyboardButton("تعيين / تعديل القوانين", callback_data=f"rules_set_{chat_id}")
    delete_btn = types.InlineKeyboardButton("حذف القوانين", callback_data=f"rules_delete_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}")
    markup.add(set_btn)
    if current_rules_text and (rules_data.get('text') or rules_data.get('media_id')):
        markup.add(delete_btn)
    markup.add(back_btn)
    return text, markup

def get_repeating_messages_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('repeating_messages', {})
    enabled = settings.get('enabled', False)
    tz_name = db[chat_id].get('night_mode', {}).get('timezone', 'UTC')
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except zoneinfo.ZoneInfoNotFoundError:
        tz = zoneinfo.ZoneInfo('UTC')
    current_time_str = datetime.datetime.now(tz).strftime('%d/%m/%Y, %I:%M %p').replace("AM", "ص").replace("PM", "م")
    text = (
        "🕑 <b>تكرار الرسائل</b> 🗣\n\n"
        "من هذه القائمة يمكنك تعيين الرسائل التي سيتم إرسالها بشكل متكرر إلى المجموعة كل بضع دقائق/ساعات أو كل بضع رسائل.\n\n"
        f"الوقت الحالي: {current_time_str}"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    toggle_btn_text = f"الحالة: {'تعطيل' if enabled else 'تفعيل'}"
    markup.add(types.InlineKeyboardButton(toggle_btn_text, callback_data=f"repeatingmsg_toggle_enabled_{chat_id}"))
    if enabled:
        interval_seconds = settings.get('interval_seconds', 86400)
        if interval_seconds < 3600:
            interval_text = f"كل {interval_seconds // 60} دقائق"
        else:
            interval_text = f"كل {interval_seconds // 3600} ساعات"
        markup.add(types.InlineKeyboardButton("➕ اضافه رساله مسموح بها تكرار", callback_data=f"repeatingmsg_add_message_{chat_id}"))
        markup.add(types.InlineKeyboardButton(f"🔁 التكرار: {interval_text}", callback_data=f"repeatingmsg_open_interval_{chat_id}"))
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}"))
    return text, markup

def get_repeating_interval_menu(chat_id):
    text = "👉🏻 حدد عدد مرات تكرار الرسالة."
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🕑 الساعات", callback_data="noop"))
    hours_buttons = []
    for h in [1, 2, 3, 4, 6, 8, 12, 24]:
        hours_buttons.append(types.InlineKeyboardButton(f"{h}", callback_data=f"repeatingmsg_set_interval_hours_{h}_{chat_id}"))
    markup.add(*hours_buttons)
    markup.add(types.InlineKeyboardButton("⏳ الدقائق", callback_data="noop"))
    minutes_buttons_free = []
    for m in [10, 15, 20, 30]:
        minutes_buttons_free.append(types.InlineKeyboardButton(f"{m}", callback_data=f"repeatingmsg_set_interval_minutes_{m}_{chat_id}"))
    markup.add(*minutes_buttons_free)
    minutes_buttons_paid = []
    for m in [1, 2, 3, 5]:
        btn_text = f"{m}"
        minutes_buttons_paid.append(types.InlineKeyboardButton(btn_text, callback_data=f"repeatingmsg_set_interval_minutes_{m}_{chat_id}"))
    markup.add(*minutes_buttons_paid)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"repeatingmsg_open_main_{chat_id}"))
    return text, markup

def get_night_mode_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('night_mode', {})
    enabled = settings.get('enabled', False)
    start_hour = settings.get('start_hour', 23)
    end_hour = settings.get('end_hour', 9)
    notify = settings.get('notify', True)
    tz_name = settings.get('timezone', 'UTC')
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
        now = datetime.datetime.now(tz)
        current_time_str = now.strftime('%d/%m/%Y, %I:%M %p').replace("AM", "ص").replace("PM", "م")
    except zoneinfo.ZoneInfoNotFoundError:
        tz_name = 'UTC'
        tz = zoneinfo.ZoneInfo(tz_name)
        now = datetime.datetime.now(tz)
        current_time_str = now.strftime('%d/%m/%Y, %I:%M %p').replace("AM", "ص").replace("PM", "م")
        db[chat_id]['night_mode']['timezone'] = 'UTC'
        save_group_data(chat_id)
    text = "قم باختيار احد الاجراءات التي تريدها لتقييد المجموعة\n\n"
    if enabled:
        status_text = "🤫 الوضع الصامت"
        details = (
            f"├ فعال من الساعة  {start_hour} الى {end_hour}\n"
            f"└ إشعار البدء و الانتهاء: {'✔️' if notify else '✖️'}\n\n"
        )
        text += f"الحالة: {status_text}\n{details}"
    else:
        status_text = "❌ غير مفعّل"
        text += f"الحالة: {status_text}\n\n"
    text += f"الوقت الحالي: {current_time_str}"
    markup = types.InlineKeyboardMarkup(row_width=1)
    toggle_btn_text = "تعطيل" if enabled else "تفعيل"
    markup.add(types.InlineKeyboardButton(toggle_btn_text, callback_data=f"nightmode_toggle_enabled_{chat_id}"))
    markup.add(types.InlineKeyboardButton("ضبط وقت الوضع الليلي", callback_data=f"nightmode_open_time_{chat_id}"))
    notify_btn_text = f"إشعارالبدء والانتهاء: {'تعطيل' if notify else 'تفعيل'}"
    markup.add(types.InlineKeyboardButton(notify_btn_text, callback_data=f"nightmode_toggle_notify_{chat_id}"))
    markup.add(types.InlineKeyboardButton("توقيت المحلي", callback_data=f"nightmode_set_timezone_{chat_id}"))
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}"))
    return text, markup

def get_night_mode_time_menu(chat_id, step='start', start_hour=None):
    if step == 'start':
        text = "في هذه القائمة يمكنك تحديد فاصل ساعة وكل يوم ، في تلك الساعات سيتم تمكين الوضع الليلي.\n\n👉🏻 تحديد وقت بداية إرسال الرسالة :"
    else:
        text = f"تم تحديد وقت البدء في الساعة {start_hour}.\n\n👉🏻 الآن، حدد وقت انتهاء الوضع الليلي:"
    markup = types.InlineKeyboardMarkup(row_width=6)
    buttons = [types.InlineKeyboardButton(str(i), callback_data=f"nightmode_set_hour_{i}_{chat_id}") for i in range(24)]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"nightmode_open_main_{chat_id}"))
    return text, markup

def get_media_menu(chat_id, page=1):
    init_chat_db(chat_id)
    text = "اختر نوع الوسائط لضبط عقوبتها."
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    keys_to_show = MEDIA_KEYS_PAGE1 if page == 1 else MEDIA_KEYS_PAGE2
    settings = db[chat_id].get('media_restrictions', {})
    for key in keys_to_show:
        display_name = MEDIA_TYPES_MAP[key][0]
        punishment = settings.get(key, {}).get('punishment', 'none')
        icon = PUNISHMENT_ICONS.get(punishment, '☑️')
        btn_text = f"{icon} {display_name}"
        buttons.append(types.InlineKeyboardButton(btn_text, callback_data=f"media_open_punish_{key}_{chat_id}"))
    markup.add(*buttons)
    row = []
    if page == 1 and MEDIA_KEYS_PAGE2:
        row.append(types.InlineKeyboardButton("التالي ⬅️", callback_data=f"media_open_menu_2_{chat_id}"))
    if page == 2:
        row.append(types.InlineKeyboardButton("➡️ السابق", callback_data=f"media_open_menu_1_{chat_id}"))
    markup.row(*row)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}"))
    return text, markup

def get_media_punishment_menu(chat_id, media_key):
    init_chat_db(chat_id)
    settings = db[chat_id].get('media_restrictions', {})
    current_punishment = settings.get(media_key, {}).get('punishment', 'none')
    media_name = MEDIA_TYPES_MAP.get(media_key, ('',))[0]
    text = f"اختر عقوبة لـ <b>{media_name}</b>."
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    punishments = ['none', 'warn', 'kick', 'ban', 'mute', 'delete']
    for p_key in punishments:
        p_name = PUNISHMENTS_MAP.get(p_key)
        text_btn = f"✅ {p_name}" if current_punishment == p_key else p_name
        buttons.append(types.InlineKeyboardButton(text_btn, callback_data=f"media_set_punish_{media_key}_{p_key}_{chat_id}"))
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"media_open_menu_1_{chat_id}"))
    return text, markup

def get_captcha_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('captcha', {})
    status = "مفعل ✅" if settings.get('enabled') else "غير مفعّل ❌"
    time_limit = settings.get('time_limit', 3)
    punishment = PUNISHMENTS_MAP.get(settings.get('punishment'), '🔇 كتم').split(' ')[1]
    mode_map = {'button': 'ضغط على زر', 'math': 'رياضيات'}
    mode = mode_map.get(settings.get('mode', 'button'), 'ضغط على زر')
    mode_desc = "سيتعين على المستخدم الضغط على زر بسيط ليتم إلغاء الكتم عنه.\n هي طريقة تحقق بسيطة ولكنها أقل أمانًا." if settings.get('mode') == 'button' else "سيتعين على المستخدم حل عملية حسابية مع 3 محاولات."
    delete_service_msg_status = "مفعّل" if settings.get('delete_service_message') else "غير مفعّل"
    text = (
        "🧠 <b>التحقق Captcha</b>\n"
        "من خلال تنشيط اختبار التحقق CAPTCHA ، عندما يدخل مستخدم إلى المجموعة لن يتمكن من إرسال رسائل حتى يؤكد أنه ليس روبوت .\n\n"
        "🕑 يمكنك أيضًا أن تقرر تعيين العقوبات بالأسفل أدناه لأولئك الذين لن يحلوا اختبار التحقق CAPTCHA خلال الوقت المطلوب وما إذا كان سيتم مسح رسالة الخدمة أم لا في حالة الفشل .\n\n"
        f"<b>الحالة:</b> {status}\n"
        f"<b>🕒 الوقت:</b> {time_limit} دقائق\n"
        f"<b>⛔️ العقوبة:</b> {punishment}\n"
        f"<b>🗂 الوضع:</b> {mode}\n"
        f"└ {mode_desc}\n"
        f"<b>🗑 حذف رسالة الخدمة:</b> {delete_service_msg_status}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_btn_text = "تعطيل" if settings.get('enabled') else "تفعيل"
    toggle_btn = types.InlineKeyboardButton(toggle_btn_text, callback_data=f"captcha_toggle_enabled_{chat_id}")
    mode_btn = types.InlineKeyboardButton("الوضع", callback_data=f"captcha_open_mode_{chat_id}")
    time_btn = types.InlineKeyboardButton("الوقت", callback_data=f"captcha_edit_time_{chat_id}")
    punishment_btn = types.InlineKeyboardButton("العقوبة", callback_data=f"captcha_open_punishment_{chat_id}")
    delete_btn_text = "تعطيل حذف الرسالة" if settings.get('delete_service_message') else "تفعيل حذف الرسالة"
    delete_btn = types.InlineKeyboardButton(delete_btn_text, callback_data=f"captcha_toggle_delete_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"commands_open_main_{chat_id}")
    markup.add(toggle_btn)
    markup.add(mode_btn, time_btn)
    markup.add(punishment_btn)
    markup.add(delete_btn)
    markup.add(back_btn)
    return text, markup

def get_captcha_mode_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('captcha', {})
    current_mode = settings.get('mode', 'button')
    text = "اختر وضع التحقق المطلوب."
    markup = types.InlineKeyboardMarkup(row_width=1)
    button_mode_text = f"✅ ضغط ع زر" if current_mode == 'button' else "ضغط ع زر"
    math_mode_text = f"✅ رياضيات" if current_mode == 'math' else "رياضيات"
    button_mode_btn = types.InlineKeyboardButton(button_mode_text, callback_data=f"captcha_set_mode_button_{chat_id}")
    math_mode_btn = types.InlineKeyboardButton(math_mode_text, callback_data=f"captcha_set_mode_math_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"captcha_open_main_{chat_id}")
    markup.add(button_mode_btn, math_mode_btn)
    markup.add(back_btn)
    return text, markup

def get_captcha_punishment_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('captcha', {})
    current_punishment = settings.get('punishment', 'mute')
    punishment_enabled = current_punishment != 'none'
    text = "اختر العقوبة للمستخدمين الذين يفشلون في التحقق."
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_text = "تعطيل العقوبة" if punishment_enabled else "تفعيل العقوبة"
    toggle_callback = f"captcha_set_punishment_none_{chat_id}" if punishment_enabled else f"captcha_set_punishment_mute_{chat_id}"
    markup.add(types.InlineKeyboardButton(toggle_text, callback_data=toggle_callback))
    punishments = {'mute': 'كتم', 'kick': 'طرد', 'ban': 'حظر'}
    buttons = []
    if punishment_enabled:
        for p_key, p_name in punishments.items():
            text_btn = f"✅ {p_name}" if current_punishment == p_key else p_name
            buttons.append(types.InlineKeyboardButton(text_btn, callback_data=f"captcha_set_punishment_{p_key}_{chat_id}"))
        markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"captcha_open_main_{chat_id}"))
    return text, markup

def get_restrictions_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('restrictions', {})
    join_status = "مفعل ✔️" if settings.get('check_on_join', True) else "معطل ✖️"
    delete_status = "مفعل ✔️" if settings.get('delete_messages', False) else "غير مفعّل ✖️"
    text = (
        "<b>🛂 إعدادات القيود</b>\n\n"
        "🚪 <b>تحقق من الإنضمام</b>\n"
        "إذا كان مفعلاً ، فسيقوم البوت بالتحقق من الإلتزامات والمنع حتى عندما ينضم المستخدمون إلى المجموعة ، وكذلك عند إرسال رسالة.\n"
        f"الحالة: {join_status}\n\n"
        "🗑 <b>حذف الرسائل</b>\n"
        "إذا كان مفعلاً ، فسيحذف البوت الرسائل المرسلة من قبل المستخدمين الذين لم يمتثلوا للالتزامات / منع.\n"
        f"الحالة: {delete_status}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    enforce_btn = types.InlineKeyboardButton("الإلزام بـ", callback_data=f"restrictions_open_enforce_{chat_id}")
    prevent_btn = types.InlineKeyboardButton("منع", callback_data=f"restrictions_open_prevent_{chat_id}")
    toggle_join_btn = types.InlineKeyboardButton("تبديل التحقق عند الانضمام", callback_data=f"restrictions_toggle_check_on_join_{chat_id}")
    toggle_delete_btn = types.InlineKeyboardButton("تبديل حذف الرسائل", callback_data=f"restrictions_toggle_delete_messages_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"commands_open_main_{chat_id}")
    markup.add(enforce_btn, prevent_btn)
    markup.add(toggle_join_btn)
    markup.add(toggle_delete_btn)
    markup.add(back_btn)
    return text, markup

def get_enforce_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('restrictions', {}).get('enforce', {})
    text = "<b>الإلزام بـ</b>\n\nاختر أحد القيود لتحديد عقوبته."
    markup = types.InlineKeyboardMarkup(row_width=1)
    options = {
        'last_name': 'اسم العائلة',
        'username': 'المعرّف',
        'profile_photo': 'صورة الملف الشخصي',
        'channel_subscribe': 'إلزام بالقناة',
        'must_add': 'وجوب الإضافة'
    }
    buttons = []
    for key, name in options.items():
        punishment_key = settings.get(key, {}).get('punishment', 'none')
        punishment_text = PUNISHMENTS_MAP.get(punishment_key, '☑️ بلا عقوبة').split(' ', 1)[1]
        buttons.append(types.InlineKeyboardButton(f"{name}: {punishment_text}", callback_data=f"restrictions_edit_punish_enforce_{key}_{chat_id}"))
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"restrictions_open_main_{chat_id}"))
    return text, markup

def get_prevent_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('restrictions', {}).get('prevent', {})
    text = "<b>منع...</b>\n\nاختر أحد أنواع المنع لتحديد عقوبته."
    markup = types.InlineKeyboardMarkup(row_width=1)
    options = {
        'arabic_name': 'الاسم بالحروف العربية',
        'chinese_name': 'اسم صيني',
        'russian_name': 'الاسم الروسي',
        'forbidden_name': 'الاسم المزعج'
    }
    buttons = []
    for key, name in options.items():
        punishment_key = settings.get(key, {}).get('punishment', 'none')
        punishment_text = PUNISHMENTS_MAP.get(punishment_key, '☑️ بلا عقوبة').split(' ', 1)[1]
        buttons.append(types.InlineKeyboardButton(f"{name}: {punishment_text}", callback_data=f"restrictions_edit_punish_prevent_{key}_{chat_id}"))
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"restrictions_open_main_{chat_id}"))
    return text, markup

def get_punishment_menu_for_restriction(chat_id, r_type, r_key):
    init_chat_db(chat_id)
    current_punishment = db[chat_id].get('restrictions', {}).get(r_type, {}).get(r_key, {}).get('punishment', 'none')
    options_map = {
        'enforce': {
            'last_name': 'اسم العائلة', 'username': 'المعرّف', 'profile_photo': 'صورة الملف الشخصي',
            'channel_subscribe': 'إلزام بالقناة', 'must_add': 'وجوب الإضافة'
        },
        'prevent': {
            'arabic_name': 'الاسم بالحروف العربية', 'chinese_name': 'اسم صيني', 'russian_name': 'الاسم الروسي',
            'forbidden_name': 'الاسم المزعج'
        }
    }
    restriction_name = options_map.get(r_type, {}).get(r_key, r_key)
    text = f"اختر عقوبة لـ <b>{restriction_name}</b>."
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    plain_punishments = {'none': 'بلا عقوبة', 'warn': 'انذار', 'kick': 'طرد', 'ban': 'حظر', 'mute': 'كتم'}
    for p_key, p_name in plain_punishments.items():
        text_btn = f"✅ {p_name}" if current_punishment == p_key else p_name
        buttons.append(types.InlineKeyboardButton(text_btn, callback_data=f"restrictions_set_punish_{r_type}_{r_key}_{p_key}_{chat_id}"))
    markup.add(*buttons)
    back_callback = f"restrictions_open_{r_type}_{chat_id}"
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=back_callback))
    return text, markup

def get_whitelist_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('whitelist', {})
    status = "مفعل" if settings.get('enabled') else "معطل"
    text = (
        "انها قائمة تم إنشاؤها من قبل موظفينا, في القنوات والمجموعات التي تقدم محتوى جاد, ومنظمة تنظيما جيدا بدون ارباح وبالتالي لا تعتبر مزعجه .\n"
        "وسيتم تجاهل القنوات والمجموعات الواردة في هذه القائمة بواسطة الكشف عن الرسائل الإلكترونية المزعجه في المجموعة (كلا الروابط والتوجيه).\n\n"
        "يمكنك مراجعة القائمة بالضغط على الزر في الأسفل.\n\n"
        f"<b>الحالة:</b> {status}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    add_btn = types.InlineKeyboardButton("اضافه", callback_data=f"whitelist_add_{chat_id}")
    remove_btn = types.InlineKeyboardButton("ازاله", callback_data=f"whitelist_remove_{chat_id}")
    view_btn = types.InlineKeyboardButton("روابط قائمه البيضاء", callback_data=f"whitelist_view_{chat_id}")
    toggle_btn_text = "تعطيل" if settings.get('enabled') else "تفعيل"
    toggle_btn = types.InlineKeyboardButton(toggle_btn_text, callback_data=f"whitelist_toggle_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}")
    markup.add(add_btn, remove_btn)
    markup.add(view_btn)
    markup.add(toggle_btn)
    markup.add(back_btn)
    return text, markup

def get_welcome_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('welcome', {})
    status = "مفعّل ✅" if settings.get('enabled') else "غير مفعّل ❌"
    mode_text = "إرسال رسالة الترحيب فقط عند انضمام المستخدم لأول مرة" if settings.get('first_join_only') else "إرسال رسالة الترحيب في كل انضمام للمستخدمين في المجموعة"
    text = (
        "💬 <b>رسالة الترحيب</b>\n"
        "من هذه القائمة ، يمكنك تعيين رسالة ترحيب سيتم إرسالها عندما ينضم شخص ما إلى المجموعة.\n\n"
        f"<b>الحالة:</b> {status}\n"
        f"<b>الوضع:</b> {mode_text}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_btn_text = "تعطيل" if settings.get('enabled') else "تفعيل"
    toggle_btn = types.InlineKeyboardButton(toggle_btn_text, callback_data=f"welcome_toggle_{chat_id}")
    edit_btn = types.InlineKeyboardButton("تعديل رساله ترحيب", callback_data=f"welcome_edit_{chat_id}")
    mode_btn_text = "الترحيب للكل" if settings.get('first_join_only') else "الترحيب للأعضاء الجدد فقط"
    mode_btn = types.InlineKeyboardButton(mode_btn_text, callback_data=f"welcome_toggle_mode_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}")
    markup.add(toggle_btn)
    markup.add(edit_btn)
    markup.add(mode_btn)
    markup.add(back_btn)
    return text, markup

def get_goodbye_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('goodbye', {})
    status = "مفعّل ✅" if settings.get('enabled') else "غير مفعّل ❌"
    private_status = "مفعّل ✅" if settings.get('send_private') else "غير مفعّل ❌"
    text = (
        "👋🏻 <b>وداعًا</b>\n"
        "من هذه القائمة يمكنك تعيين رسالة وداع سيتم إرسالها في المجموعة عندما يغادر شخص ما المجموعة.\n\n"
        f"<b>الحالة:</b> {status}\n"
        f"<b>إرسالها في الخاص:</b> {private_status}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_btn_text = "تعطيل" if settings.get('enabled') else "تفعيل"
    toggle_btn = types.InlineKeyboardButton(toggle_btn_text, callback_data=f"goodbye_toggle_{chat_id}")
    edit_btn = types.InlineKeyboardButton("تعديل", callback_data=f"goodbye_edit_{chat_id}")
    private_toggle_text = "تعطيل الإرسال الخاص" if settings.get('send_private') else "تفعيل الإرسال الخاص"
    private_toggle_btn = types.InlineKeyboardButton(private_toggle_text, callback_data=f"goodbye_toggle_private_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}")
    markup.add(toggle_btn)
    markup.add(edit_btn)
    markup.add(private_toggle_btn)
    markup.add(back_btn)
    return text, markup

def get_alphabets_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('alphabets', {})
    text = "🕉 <b>الحروف الهجائية</b>\nتحديد عقوبة للمستخدمين الذين يقومون بإرسال رسائل مكتوبة بأبجديات معينة.\n\n"
    markup = types.InlineKeyboardMarkup(row_width=2)
    lang_buttons = []
    lang_order = ['arabic', 'cyrillic', 'chinese', 'latin', 'persian', 'english']
    for lang_key in lang_order:
        if lang_key in settings:
            lang_settings = settings[lang_key]
            punishment_key = lang_settings.get('punishment', 'none')
            punishment_text = PUNISHMENTS_MAP.get(punishment_key, '☑️ بلا عقوبة').split(' ', 1)[1]
            lang_name = LANG_MAP.get(lang_key, lang_key)
            text += f"{lang_name} (?)\n  └ الحالة: {punishment_text}\n\n"
            lang_buttons.append(types.InlineKeyboardButton(lang_name, callback_data=f"alphabets_edit_{lang_key}_{chat_id}"))
    markup.add(*lang_buttons)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}"))
    return text, markup

def get_alphabet_punishment_menu(chat_id, lang):
    init_chat_db(chat_id)
    settings = db[chat_id].get('alphabets', {}).get(lang, {})
    current_punishment = settings.get('punishment', 'none')
    lang_name = LANG_MAP.get(lang, lang)
    text = f"اختر العقوبة التي سيتم تطبيقها عند استخدام أحرف <b>{lang_name}</b>."
    markup = types.InlineKeyboardMarkup(row_width=2)
    plain_punishments = {'none': 'بلا عقوبة', 'warn': 'انذار', 'kick': 'طرد', 'ban': 'حظر', 'mute': 'كتم'}
    for p_key, p_name in plain_punishments.items():
        text_btn = f"✅ {p_name}" if current_punishment == p_key else p_name
        markup.add(types.InlineKeyboardButton(text_btn, callback_data=f"alphabets_set_punish_{lang}_{p_key}_{chat_id}"))
    delete_status = '✅' if settings.get('delete') else '❌'
    delete_btn = types.InlineKeyboardButton(f"حذف الرسائل {delete_status}", callback_data=f"alphabets_toggle_delete_{lang}_{chat_id}")
    markup.add(delete_btn)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_alphabets_{chat_id}"))
    return text, markup

def get_antiflood_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('antiflood', {})
    enabled = settings.get('enabled', False)
    status_text = "مفعل ✅" if enabled else "معطل ❌"
    punishments = {'delete': 'حذف', 'warn': 'انذار', 'kick': 'طرد', 'ban': 'حظر', 'mute': 'كتم', 'none': 'بلا عقوبة'}
    punishment_text = punishments.get(settings.get('punishment'), 'غير محدد')
    text = (
        "🗣 <b>مانع التكرار (Flood)</b>\n"
        "من هذه القائمة، يمكنك معاقبة من يرسل رسائل كثيرة في وقت قصير (Spam).\n\n"
        f"<b>الحالة:</b> {status_text}\n"
        f"يتم تفعيل المانع، في حال قام مستخدم بإرسال:\n"
        f"<b>{settings.get('messages', 5)}</b> رسائل في <b>{settings.get('seconds', 3)}</b> ثواني.\n\n"
        f"<b>العقوبة:</b> {punishment_text}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_btn_text = "تعطيل" if enabled else "تفعيل"
    toggle_btn = types.InlineKeyboardButton(toggle_btn_text, callback_data=f"antiflood_toggle_enabled_{chat_id}")
    time_btn = types.InlineKeyboardButton("الوقت", callback_data=f"antiflood_time_{chat_id}")
    messages_btn = types.InlineKeyboardButton("الرسائل", callback_data=f"antiflood_messages_{chat_id}")
    punishment_btn = types.InlineKeyboardButton("العقوبة", callback_data=f"antiflood_punishment_{chat_id}")
    delete_toggle_text = f"حذف الرسائل {'✅' if settings.get('delete_messages') else '❌'}"
    delete_toggle_btn = types.InlineKeyboardButton(delete_toggle_text, callback_data=f"antiflood_toggle_delete_{chat_id}")
    back_btn = types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}")
    markup.add(toggle_btn)
    markup.add(time_btn, messages_btn)
    markup.add(punishment_btn)
    markup.add(delete_toggle_btn)
    markup.add(back_btn)
    return text, markup

def get_anti_repeat_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('anti_repeat', {})
    enabled = settings.get('enabled', False)
    status_text = "مفعل ✅" if enabled else "معطل ❌"
    punishment = settings.get('punishment', 'mute')
    punishment_text = PUNISHMENTS_MAP.get(punishment, '🔇 كتم').split(' ')[1]
    text = (
        "🚫 <b>منع تكرار نفس الرسالة</b>\n"
        "هذه الميزة تعاقب المستخدم الذي يرسل نفس الرسالة مرتين متتاليتين.\n\n"
        f"<b>الحالة:</b> {status_text}\n"
        f"<b>العقوبة:</b> {punishment_text}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_btn_text = "تعطيل" if enabled else "تفعيل"
    markup.add(types.InlineKeyboardButton(toggle_btn_text, callback_data=f"antirepeat_toggle_enabled_{chat_id}"))
    punishments_row = []
    for p_key in ['warn', 'kick', 'ban', 'mute']:
        p_name = PUNISHMENTS_MAP.get(p_key, f' {p_key}').split(' ', 1)[1]
        btn_text = f"✅ {p_name}" if punishment == p_key else p_name
        punishments_row.append(types.InlineKeyboardButton(btn_text, callback_data=f"antirepeat_set_punish_{p_key}_{chat_id}"))
    markup.row(*punishments_row)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_open_here_{chat_id}"))
    return text, markup

def get_antiflood_time_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('antiflood', {})
    text = (
        "من هنا يمكنك تحديد الوقت المعتبر لحساب مانع الرسائل المكررة.\n\n"
        f"✅ حالياً، يتم تفعيل مانع الرسائل المكررة، عندما يقوم مستخدم بإرسال عدد {settings.get('messages')} من الرسائل خلال {settings.get('seconds')} من الثواني."
    )
    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = [types.InlineKeyboardButton(str(i), callback_data=f"antiflood_set_time_{i}_{chat_id}") for i in [2,3,4,5,6,7,8,9,10,12,13,14,15,20]]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_antiflood_{chat_id}"))
    return text, markup

def get_antiflood_messages_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('antiflood', {})
    text = (
        "من هنا يمكنك تحديد الحد الأقصى لكمية الرسائل المسموح إرسالها في وقت محدد.\n\n"
        f"✅ حالياً، مانع الرسائل المكررة يتم تفعيله اذا تم إرسال {settings.get('messages')} من الرسائل خلال {settings.get('seconds')} من الثواني."
    )
    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = [types.InlineKeyboardButton(str(i), callback_data=f"antiflood_set_msg_{i}_{chat_id}") for i in [2,3,4,5,6,7,8,9,10,12,13,14,15,20]]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_antiflood_{chat_id}"))
    return text, markup

def get_antiflood_punishment_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('antiflood', {})
    current_punishment = settings.get('punishment')
    text = "اختر العقوبة التي سيتم تطبيقها عند تكرار الرسائل."
    markup = types.InlineKeyboardMarkup(row_width=2)
    none_btn = types.InlineKeyboardButton("بلا عقوبة", callback_data=f"antiflood_set_punish_none_{chat_id}")
    warn_btn = types.InlineKeyboardButton("انذار", callback_data=f"antiflood_set_punish_warn_{chat_id}")
    mute_btn = types.InlineKeyboardButton("كتم", callback_data=f"antiflood_set_punish_mute_{chat_id}")
    ban_btn = types.InlineKeyboardButton("حظر", callback_data=f"antiflood_set_punish_ban_{chat_id}")
    kick_btn = types.InlineKeyboardButton("طرد", callback_data=f"antiflood_set_punish_kick_{chat_id}")
    delete_btn = types.InlineKeyboardButton("حذف", callback_data=f"antiflood_set_punish_delete_{chat_id}")
    markup.add(none_btn, warn_btn)
    markup.add(mute_btn, ban_btn)
    markup.add(kick_btn, delete_btn)
    if current_punishment in ['mute', 'ban']:
        duration_btn = types.InlineKeyboardButton(f"تحديد مدة {current_punishment}", callback_data=f"antiflood_open_duration_{chat_id}")
        markup.add(duration_btn)
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"settings_antiflood_{chat_id}"))
    return text, markup

def get_id_command_menu(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('id_command', {})
    enabled = settings.get('enabled', False)
    with_photo = settings.get('with_photo', False)
    status_text = "مفعل ✅" if enabled else "معطل ❌"
    photo_status_text = "مفعل ✅" if with_photo else "معطل ❌"
    text = f"""⚙️ <b>إعدادات أوامر الايدي</b>
هنا يمكنك التحكم في أمر `ايدي`.

<b>حالة الأمر:</b> {status_text}
<b>إظهار الصورة:</b> {photo_status_text}
"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_enabled_btn_text = "تعطيل الأمر" if enabled else "تفعيل الأمر"
    toggle_photo_btn_text = "تعطيل الصورة" if with_photo else "تفعيل الصورة"
    markup.add(types.InlineKeyboardButton(toggle_enabled_btn_text, callback_data=f"idcmd_toggle_enabled_{chat_id}"))
    markup.add(types.InlineKeyboardButton(toggle_photo_btn_text, callback_data=f"idcmd_toggle_photo_{chat_id}"))
    markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"commands_open_main_{chat_id}"))
    return text, markup

def get_all_known_user_ids_in_chat(chat_id):
    init_chat_db(chat_id)
    user_ids = set()
    warned_users = db[chat_id].get('warnings_settings', {}).get('warned_users', {})
    user_ids.update(int(uid) for uid in warned_users.keys())
    joined_users = db[chat_id].get('welcome', {}).get('joined_users', [])
    user_ids.update(joined_users)
    unverified_users = UNVERIFIED_USERS.get(chat_id, {})
    user_ids.update(unverified_users.keys())
    if chat_id in FLOOD_TRACKER:
        user_ids.update(FLOOD_TRACKER[chat_id].keys())
    return user_ids

def _unban_all_task(chat_id, message_id):
    try:
        init_chat_db(chat_id)
        bot.edit_message_text("⏳ جارِ البحث عن المستخدمين المحظورين وإلغاء الحظر...", chat_id, message_id, reply_markup=None)
        count = 0
        warned_users = db[chat_id].get('warnings_settings', {}).get('warned_users', {})
        punishment_type = db[chat_id].get('warnings_settings', {}).get('punishment')
        if punishment_type == 'ban':
            for user_id_str, data in list(warned_users.items()):
                user_id = int(user_id_str)
                if data.get('punished'):
                    try:
                        bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
                        count += 1
                        time.sleep(0.5)
                    except Exception:
                        pass
        bot.edit_message_text(f"✅ اكتملت العملية. تم إلغاء حظر {count} مستخدم.", chat_id, message_id)
    except Exception as e:
        try:
            bot.edit_message_text(f"⚠️ حدث خطأ: {e}", chat_id, message_id)
        except:
            pass

def _unmute_all_task(chat_id, message_id):
    try:
        init_chat_db(chat_id)
        bot.edit_message_text("⏳ جارِ البحث عن المستخدمين المكتومين وإلغاء الكتم...", chat_id, message_id, reply_markup=None)
        count = 0
        known_user_ids = get_all_known_user_ids_in_chat(chat_id)
        for user_id in list(known_user_ids):
            try:
                member = bot.get_chat_member(chat_id, user_id)
                if member.status == 'restricted' and not member.can_send_messages:
                    bot.restrict_chat_member(chat_id, user_id, can_send_messages=True)
                    count += 1
                    time.sleep(0.5)
            except Exception:
                pass
        bot.edit_message_text(f"✅ اكتملت العملية. تم إلغاء كتم {count} مستخدم.", chat_id, message_id)
    except Exception as e:
        try:
            bot.edit_message_text(f"⚠️ حدث خطأ: {e}", chat_id, message_id)
        except:
            pass

def _kick_muted_task(chat_id, message_id):
    try:
        init_chat_db(chat_id)
        bot.edit_message_text("⏳ جارِ البحث عن المستخدمين المكتومين وطردهم...", chat_id, message_id, reply_markup=None)
        count = 0
        known_user_ids = get_all_known_user_ids_in_chat(chat_id)
        for user_id in list(known_user_ids):
            try:
                member = bot.get_chat_member(chat_id, user_id)
                if member.status == 'restricted' and not member.can_send_messages:
                    bot.kick_chat_member(chat_id, user_id)
                    bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
                    count += 1
                    time.sleep(0.5)
            except Exception:
                pass
        bot.edit_message_text(f"✅ اكتملت العملية. تم طرد {count} مستخدم مكتوم.", chat_id, message_id)
    except Exception as e:
        try:
            bot.edit_message_text(f"⚠️ حدث خطأ: {e}", chat_id, message_id)
        except:
            pass

def is_night_mode_active(chat_id):
    init_chat_db(chat_id)
    settings = db[chat_id].get('night_mode', {})
    if not settings.get('enabled'):
        return False
    start_hour = settings.get('start_hour', 23)
    end_hour = settings.get('end_hour', 9)
    tz_name = settings.get('timezone', 'UTC')
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
        now_hour = datetime.datetime.now(tz).hour
    except zoneinfo.ZoneInfoNotFoundError:
        return False
    if start_hour < end_hour:
        return start_hour <= now_hour < end_hour
    else:
        return now_hour >= start_hour or now_hour < end_hour

def send_stored_message(chat_id, msg_data):
    try:
        msg_type = msg_data.get('type')
        content = msg_data.get('content')
        caption = msg_data.get('caption')
        if msg_type == 'text':
            bot.send_message(chat_id, content)
        elif msg_type == 'photo':
            bot.send_photo(chat_id, content, caption=caption)
        elif msg_type == 'video':
            bot.send_video(chat_id, content, caption=caption)
        elif msg_type == 'animation':
            bot.send_animation(chat_id, content, caption=caption)
        elif msg_type == 'document':
            bot.send_document(chat_id, content, caption=caption)
        elif msg_type == 'audio':
            bot.send_audio(chat_id, content, caption=caption)
        elif msg_type == 'voice':
            bot.send_voice(chat_id, content, caption=caption)
    except Exception as e:
        print(f"Failed to send stored message to {chat_id}: {e}")
        if 'chat not found' in str(e) or 'bot was kicked' in str(e):
             if chat_id in db:
                 del db[chat_id]
                 save_group_data(chat_id)

def check_subscription(user_id):
    if not admin_db.get('subscribed_channels'):
        return True, []
    unsubscribed_channels = []
    for channel in admin_db.get('subscribed_channels', []):
        try:
            member = bot.get_chat_member(channel['id'], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsubscribed_channels.append(channel)
        except Exception:
            unsubscribed_channels.append(channel)
    if unsubscribed_channels:
        return False, unsubscribed_channels
    else:
        return True, []

def repeating_messages_scheduler():
    while True:
        try:
            all_chat_ids = list(db.keys())
            now = time.time()
            for chat_id in all_chat_ids:
                if admin_db.get('maintenance_mode') or chat_id in admin_db.get('deactivated_groups', []):
                    continue
                init_chat_db(chat_id)
                chat_db = db[chat_id]
                settings = chat_db.get('repeating_messages')
                if not settings or not settings.get('enabled') or not settings.get('messages'):
                    continue
                last_sent = settings.get('last_sent_timestamp', 0)
                interval = settings.get('interval_seconds', 86400)
                if now > last_sent + interval:
                    message_to_send = random.choice(settings['messages'])
                    send_stored_message(chat_id, message_to_send)
                    db[chat_id]['repeating_messages']['last_sent_timestamp'] = now
                    save_group_data(chat_id)
        except Exception as e:
            print(f"Error in repeating messages scheduler: {e}")
        time.sleep(60)

def night_mode_scheduler():
    while True:
        try:
            all_chat_ids = list(db.keys())
            for chat_id in all_chat_ids:
                if admin_db.get('maintenance_mode') or chat_id in admin_db.get('deactivated_groups', []):
                    continue
                init_chat_db(chat_id)
                chat_db = db[chat_id]
                settings = chat_db.get('night_mode')
                if not settings or not settings.get('enabled'):
                    if settings.get('is_active_now'):
                        db[chat_id]['night_mode']['is_active_now'] = False
                        save_group_data(chat_id)
                    continue
                is_currently_active = is_night_mode_active(chat_id)
                was_active = settings.get('is_active_now', False)
                if is_currently_active and not was_active:
                    db[chat_id]['night_mode']['is_active_now'] = True
                    save_group_data(chat_id)
                    if settings.get('notify'):
                        bot.send_message(chat_id, "🌒 تم تفعيل الوضع الليلي. سيتم تقييد إرسال الرسائل.")
                elif not is_currently_active and was_active:
                    db[chat_id]['night_mode']['is_active_now'] = False
                    save_group_data(chat_id)
                    if settings.get('notify'):
                        bot.send_message(chat_id, "☀️ انتهى الوضع الليلي. يمكنكم الآن إرسال الرسائل.")
        except Exception as e:
            print(f"Error in night mode scheduler: {e}")
        time.sleep(60)

@bot.message_handler(commands=['start'])
def send_start(message):
    if message.chat.type != 'private':
        return
    user_id_str = str(message.from_user.id)
    if user_id_str not in admin_db.get('users', {}):
        admin_db.setdefault('users', {})[user_id_str] = {
            'first_name': message.from_user.first_name,
            'username': message.from_user.username
        }
        save_admin_data()
        if admin_db.get('new_member_alert'):
            user_info = (
                f"👤 <b>عضو جديد بدأ البوت</b>\n\n"
                f"<b>الاسم:</b> {message.from_user.first_name}\n"
                f"<b>المعرف:</b> @{message.from_user.username}\n"
                f"<b>الايدي:</b> <code>{message.from_user.id}</code>\n\n"
                f"<b>إجمالي عدد المستخدمين:</b> {len(admin_db['users'])}"
            )
            bot.send_message(DEVELOPER_ID, user_info)
    bot_username = bot.get_me().username
    user_first_name = message.from_user.first_name
    photo_url = "https://t.me/Belawi0/15"
    welcome_caption = (
        f"أهلاً بك {user_first_name} في بوت الحماية!\n"
        f"أنا بوت مخصص لحماية المجموعات من المحتوى المزعج والمستخدمين المزعجين.\n\n"
        "للبدء، أضفني إلى مجموعتك وارفعني مشرفاً مع كافة الصلاحيات."
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    add_btn = types.InlineKeyboardButton("➕ اضفني الى مجموعتك", url=f"https://t.me/{bot_username}?startgroup=true")
    channel_btn = types.InlineKeyboardButton("القناة", url=CHANNEL_URL)
    group_btn = types.InlineKeyboardButton("المجموعة", url=GROUP_URL)
    support_btn = types.InlineKeyboardButton("الدعم", url=f"https://t.me/{DEVELOPER_USERNAME}")
    markup.add(add_btn)
    markup.add(channel_btn, group_btn)
    markup.add(support_btn)
    bot.send_photo(message.chat.id, photo_url, caption=welcome_caption, reply_markup=markup)

def _send_developer_info(message):
    photo_url = "https://t.me/Belawi0/14"
    markup = types.InlineKeyboardMarkup(row_width=2)
    owner_button = types.InlineKeyboardButton("المالك", url="https://t.me/BBBBYB2")
    source_button = types.InlineKeyboardButton("السورس", url="https://t.me/Belawi0")
    markup.add(owner_button, source_button)
    bot.send_photo(message.chat.id, photo_url, reply_markup=markup, reply_to_message_id=message.message_id)

@bot.message_handler(commands=['المطور', 'السورس'])
def developer_command(message):
    _send_developer_info(message)

@bot.message_handler(func=lambda message: message.text and message.text.strip() in ["مطور السورس", "المطور", "السورس"])
def developer_text_handler(message):
    _send_developer_info(message)

@bot.message_handler(func=lambda message: message.text and message.text.strip() == "رتبتي")
def my_rank_command_handler(message):
    chat_id = message.chat.id
    if message.chat.type == 'private':
        return
    user_id = message.from_user.id
    rank = get_user_rank_in_group(chat_id, user_id)
    bot.reply_to(message, f"رتبتك في المجموعة هي: <b>{rank}</b>")

@bot.message_handler(func=lambda message: message.text and message.text.strip() == "المالك")
def owner_command_handler(message):
    chat_id = message.chat.id
    if message.chat.type == 'private':
        return
    try:
        admins = bot.get_chat_administrators(chat_id)
        creator_member = next((admin for admin in admins if admin.status == 'creator'), None)

        if creator_member:
            creator = creator_member.user
            markup = types.InlineKeyboardMarkup()
            owner_button = types.InlineKeyboardButton(
                text=creator.first_name,
                url=f"tg://user?id={creator.id}"
            )
            markup.add(owner_button)

            try:
                pfp = bot.get_user_profile_photos(creator.id, limit=1)
                if pfp.total_count > 0:
                    photo_id = pfp.photos[0][0].file_id
                    bot.send_photo(chat_id, photo_id, reply_markup=markup)
                else:
                    bot.send_message(chat_id, "لم يتم العثور على صورة لمالك المجموعة.", reply_markup=markup)
            except Exception as e:
                bot.reply_to(message, "لا يمكنني الوصول إلى معلومات المالك.")
                print(f"Error getting owner's profile photo: {e}")
        else:
            bot.reply_to(message, "لم أتمكن من العثور على مالك هذه المجموعة.")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء محاولة العثور على المالك.")
        print(f"Error getting chat administrators: {e}")

@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in ['ايدي', 'أ', 'أيدي', 'id'])
def id_command_handler(message):
    chat_id = message.chat.id
    if message.chat.type == 'private':
        return
    init_chat_db(chat_id)
    id_settings = db[chat_id].get('id_command', {})
    if not id_settings.get('enabled', False):
        return
    user = message.from_user
    user_id_str = str(user.id)
    message_count = db[chat_id].get('message_counts', {}).get(user_id_str, 0)
    user_name = user.first_name
    user_username = f"@{user.username}" if user.username else "لا يوجد"
    rank = get_user_rank_in_group(chat_id, user.id)
    caption_text = (
        f"<b>• اسمك :</b> {user_name}\n"
        f"<b>• معرفك :</b> {user_username}\n"
        f"<b>• ايديك :</b> <code>{user.id}</code>\n"
        f"<b>• رتبتك :</b> {rank}\n"
        f"<b>• رسائلك :</b> {message_count}"
    )
    if id_settings.get('with_photo', False):
        try:
            pfp = bot.get_user_profile_photos(user.id, limit=1)
            if pfp.total_count > 0:
                photo_id = pfp.photos[0][0].file_id
                bot.send_photo(chat_id, photo_id, caption=caption_text, reply_to_message_id=message.message_id)
            else:
                bot.reply_to(message, caption_text)
        except Exception as e:
            print(f"Error getting profile photo for {user.id}: {e}")
            bot.reply_to(message, caption_text)
    else:
        bot.reply_to(message, caption_text)

@bot.message_handler(commands=['admin', 'settings', 'الاوامر'])
def commands_handler(message):
    if message.chat.type == 'private':
        if message.from_user.id == DEVELOPER_ID:
            text, markup = get_admin_panel_menu()
            bot.send_message(message.chat.id, text, reply_markup=markup)
        return
    if admin_db.get('maintenance_mode'):
        bot.reply_to(message, "البوت في وضع صيانة.")
        return
    if message.chat.id in admin_db.get('deactivated_groups', []):
        return
    chat_id = message.chat.id
    user_id = message.from_user.id
    init_chat_db(chat_id)
    if not has_manager_access(chat_id, user_id):
        return
    is_subscribed, unsubscribed_channels = check_subscription(user_id)
    if not is_subscribed:
        markup = types.InlineKeyboardMarkup()
        for ch in unsubscribed_channels:
            markup.add(types.InlineKeyboardButton(f"اشترك في {ch.get('username') or ch['id']}", url=f"https://t.me/{ch.get('username') or ('c/' + str(ch['id'])[4:])}"))
        bot.reply_to(message, "عليك الاشتراك في القنوات التالية أولاً:", reply_markup=markup)
        return
    if not db[chat_id].get('activated', False):
        markup = types.InlineKeyboardMarkup()
        activate_btn = types.InlineKeyboardButton("تفعيل البوت", callback_data=f"activate_bot_{chat_id}")
        markup.add(activate_btn)
        bot.reply_to(message, "البوت غير مفعل. اضغط للتفعيل.", reply_markup=markup)
    else:
        markup = get_main_commands_menu(chat_id, user_id)
        bot.reply_to(message, "اختر من القائمة:", reply_markup=markup)

@bot.message_handler(commands=['rules', 'القوانين'])
def show_rules(message):
    chat_id = message.chat.id
    if admin_db.get('maintenance_mode') or chat_id in admin_db.get('deactivated_groups', []):
        return
    init_chat_db(chat_id)
    if not db[chat_id].get('activated', False):
        return
    rules = db[chat_id].get('rules', {})
    media_type = rules.get('media_type')
    media_id = rules.get('media_id')
    text = rules.get('text')
    caption = rules.get('caption')
    if not any([media_id, text, caption]):
        bot.reply_to(message, "لم يتم تعيين قوانين لهذه المجموعة بعد.")
        return
    try:
        if media_type == 'photo':
            bot.send_photo(chat_id, media_id, caption=caption)
        elif media_type == 'video':
            bot.send_video(chat_id, media_id, caption=caption)
        elif media_type == 'animation':
            bot.send_animation(chat_id, media_id, caption=caption)
        elif media_type == 'document':
            bot.send_document(chat_id, media_id, caption=caption)
        elif text:
            bot.send_message(chat_id, text)
        else:
            bot.reply_to(message, "حدث خطأ أثناء عرض القوانين.")
    except Exception as e:
        print(f"Error sending rules for chat {chat_id}: {e}")
        bot.reply_to(message, "لا يمكن عرض القوانين حالياً، قد تكون قد حُذفت.")

@bot.message_handler(commands=['free'])
def free_channel_handler(message):
    chat_id = message.chat.id
    if admin_db.get('maintenance_mode') or chat_id in admin_db.get('deactivated_groups', []):
        return
    user_id = message.from_user.id
    if not is_admin(chat_id, user_id):
        bot.reply_to(message, "هذا الأمر للمشرفين فقط.")
        return
    try:
        channel_username = message.text.split()[1]
        if not channel_username.startswith('@'):
            bot.reply_to(message, "الرجاء إدخال اسم مستخدم القناة الصحيح، يجب أن يبدأ بـ @.")
            return
    except IndexError:
        bot.reply_to(message, "الرجاء تحديد اسم مستخدم القناة بعد الأمر. مثال: `/free @mychannel`")
        return
    init_chat_db(chat_id)
    exceptions = db[chat_id]['incognito_users']['exceptions']
    if channel_username not in exceptions:
        exceptions.append(channel_username)
        save_group_data(chat_id)
        bot.reply_to(message, f"✅ تم إضافة القناة {channel_username} إلى الاستثناءات.")
    else:
        bot.reply_to(message, f"⚠️ القناة {channel_username} موجودة بالفعل في الاستثناءات.")

def get_target_user_from_message(message):
    target_user_id = None
    target_user_name = None
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
        target_user_name = message.reply_to_message.from_user.first_name
        return target_user_id, target_user_name
    parts = message.text.split()
    if len(parts) > 2:
        identifier = parts[-1]
        try:
            target_user_id = int(identifier)
            try:
                member = bot.get_chat_member(message.chat.id, target_user_id).user
                target_user_name = member.first_name
            except Exception:
                target_user_name = f"User ID {target_user_id}"
            return target_user_id, target_user_name
        except ValueError:
            return None, None
    return None, None

def get_users_list_string(chat_id, user_ids):
    if not user_ids:
        return None
    users_info = []
    for user_id in user_ids:
        try:
            user = bot.get_chat_member(chat_id, user_id).user
            if user.username:
                users_info.append(f"@{user.username}")
            else:
                users_info.append(f"<a href='tg://user?id={user_id}'>{user.first_name}</a>")
        except Exception:
            pass
    return " - ".join(users_info)

def execute_punishment(chat_id, user_id, punishment, user_first_name, duration=0):
    try:
        markup = types.InlineKeyboardMarkup()
        msg_text = ""
        user_mention = f"<a href='tg://user?id={user_id}'>{user_first_name}</a>"
        if punishment == 'kick':
            bot.kick_chat_member(chat_id, user_id)
            bot.unban_chat_member(chat_id, user_id)
            msg_text = f"تم طرد {user_mention}."
            bot.send_message(chat_id, msg_text)
        elif punishment == 'ban':
            until_date = time.time() + duration if duration > 0 else 0
            bot.ban_chat_member(chat_id, user_id, until_date=until_date if until_date > 0 else None)
            msg_text = f"تم حظر {user_mention}."
            markup.add(types.InlineKeyboardButton("الغاء الحظر", callback_data=f"punish_undo_{user_id}_ban_{chat_id}"))
            bot.send_message(chat_id, msg_text, reply_markup=markup)
        elif punishment == 'mute':
            until_date = time.time() + duration if duration > 0 else 0
            bot.restrict_chat_member(chat_id, user_id, can_send_messages=False, until_date=until_date)
            msg_text = f"تم كتم {user_mention}."
            markup.add(types.InlineKeyboardButton("الغاء الكتم", callback_data=f"punish_undo_{user_id}_mute_{chat_id}"))
            bot.send_message(chat_id, msg_text, reply_markup=markup)
    except Exception as e:
        print(f"Failed to execute punishment {punishment} on user {user_id} in {chat_id}: {e}")

def handle_warning(chat_id, user_id, user_first_name, reason="مخالفة القوانين"):
    init_chat_db(chat_id)
    settings = db[chat_id]['warnings_settings']
    warned_users = settings.get('warned_users', {})
    user_id_str = str(user_id)
    user_mention = f"<a href='tg://user?id={user_id}'>{user_first_name}</a>"
    if user_id_str not in warned_users:
        warned_users[user_id_str] = {'count': 0, 'punished': False, 'manually_unpunished': False}
    if warned_users[user_id_str].get('punished'):
        return
    warned_users[user_id_str]['count'] += 1
    warned_users[user_id_str]['reason'] = reason
    count = warned_users[user_id_str]['count']
    limit = settings['limit']
    db[chat_id]['warnings_settings']['warned_users'] = warned_users
    save_group_data(chat_id)
    bot.send_message(chat_id, f"تحذير ({count}/{limit}) للمستخدم {user_mention} بسبب: {reason}.")
    if count >= limit:
        punishment = settings['punishment']
        if punishment != 'none':
            duration = settings.get('mute_duration', 0) if punishment == 'mute' else 0
            execute_punishment(chat_id, user_id, punishment, user_first_name, duration)
            warned_users[user_id_str]['punished'] = True
            db[chat_id]['warnings_settings']['warned_users'] = warned_users
            save_group_data(chat_id)
            bot.send_message(chat_id, f"تم تطبيق عقوبة {punishment} على {user_mention} لتجاوز حد الإنذارات.")

def apply_punishment(chat_id, user_id, punishment, user_first_name, reason="مخالفة تم اكتشافها"):
    if punishment == 'none' or punishment == 'delete':
        return
    if punishment == 'warn':
        handle_warning(chat_id, user_id, user_first_name, reason)
    else:
        execute_punishment(chat_id, user_id, punishment, user_first_name)

def check_and_apply_restrictions(user, chat_id, message=None):
    init_chat_db(chat_id)
    restrictions = db[chat_id]['restrictions']
    def handle_violation(punishment, reason):
        if message and restrictions['delete_messages']:
            try:
                bot.delete_message(chat_id, message.message_id)
            except:
                pass
        if punishment == 'warn':
            handle_warning(chat_id, user.id, user.first_name, reason)
        else:
            execute_punishment(chat_id, user.id, punishment, user.first_name)
        return True
    full_name = f"{user.first_name} {user.last_name or ''}".lower()
    for r_key, r_settings in restrictions['prevent'].items():
        punishment = r_settings['punishment']
        if punishment == 'none':
            continue
        violation = False
        reason = ""
        if r_key == 'arabic_name' and ALPHABET_REGEX['arabic'].search(full_name):
            violation = True
            reason = "استخدام اسم عربي"
        elif r_key == 'chinese_name' and ALPHABET_REGEX['chinese'].search(full_name):
            violation = True
            reason = "استخدام اسم صيني"
        elif r_key == 'russian_name' and ALPHABET_REGEX['cyrillic'].search(full_name):
            violation = True
            reason = "استخدام اسم روسي"
        elif r_key == 'forbidden_name' and any(word in full_name for word in FORBIDDEN_WORDS):
            violation = True
            reason = "استخدام اسم ممنوع"
        if violation:
            return handle_violation(punishment, reason)
    for r_key, r_settings in restrictions['enforce'].items():
        punishment = r_settings['punishment']
        if punishment == 'none':
            continue
        violation = False
        reason = ""
        if r_key == 'last_name' and not user.last_name:
            violation = True
            reason = "عدم وجود اسم عائلة"
        elif r_key == 'username' and not user.username:
            violation = True
            reason = "عدم وجود معرّف"
        elif r_key == 'profile_photo':
            try:
                if bot.get_user_profile_photos(user.id, limit=1).total_count == 0:
                    violation = True
                    reason = "عدم وجود صورة ملف شخصي"
            except:
                pass
        if violation:
            return handle_violation(punishment, reason)
    return False

def captcha_timeout_handler(chat_id, user_id):
    if chat_id in db and user_id in UNVERIFIED_USERS.get(chat_id, {}):
        user_info = UNVERIFIED_USERS[chat_id][user_id]
        captcha_settings = db[chat_id]['captcha']
        punishment = captcha_settings.get('punishment', 'mute')
        try:
            user_first_name = bot.get_chat_member(chat_id, user_id).user.first_name
        except Exception:
            user_first_name = "المستخدم"
        if punishment != 'none':
            execute_punishment(chat_id, user_id, punishment, user_first_name)
        else:
            bot.send_message(chat_id, f"{user_first_name} فشل في حل التحقق في الوقت المحدد. سيبقى مكتومًا.")
        try:
            bot.delete_message(chat_id, user_info['message_id'])
            if captcha_settings.get('delete_service_message') and 'service_message_id' in user_info:
                bot.delete_message(chat_id, user_info['service_message_id'])
        except Exception:
            pass
        del UNVERIFIED_USERS[chat_id][user_id]

@bot.message_handler(content_types=['new_chat_members'])
def new_member_handler(message):
    chat_id = message.chat.id
    init_chat_db(chat_id)
    for new_user in message.new_chat_members:
        if new_user.id == bot.get_me().id:
            markup = types.InlineKeyboardMarkup()
            activate_btn = types.InlineKeyboardButton("اضغط هنا للتفعيل", callback_data=f"activate_bot_{chat_id}")
            markup.add(activate_btn)
            bot.send_message(chat_id, "تمت إضافة البوت بنجاح ✅\nاضغط على زر التفعيل لتشغيل البوت في المجموعة.", reply_markup=markup)
            try:
                member_status = bot.get_chat_member(chat_id, bot.get_me().id)
                if member_status.status == 'administrator' and chat_id not in admin_db.get('notified_admin_groups', []):
                    chat_info = bot.get_chat(chat_id)
                    invite_link = chat_info.invite_link or bot.export_chat_invite_link(chat_id)
                    admin_notification = (
                        f"🎉 <b>تم رفعي مشرفًا في مجموعة جديدة</b>\n\n"
                        f"<b>اسم المجموعة:</b> {chat_info.title}\n"
                        f"<b>ايدي المجموعة:</b> <code>{chat_id}</code>\n"
                        f"<b>الرابط:</b> {invite_link}"
                    )
                    bot.send_message(DEVELOPER_ID, admin_notification)
                    admin_db.setdefault('notified_admin_groups', []).append(chat_id)
                    save_admin_data()
            except Exception as e:
                print(f"Error notifying admin about promotion: {e}")
            return
    if admin_db.get('maintenance_mode') or chat_id in admin_db.get('deactivated_groups', []):
        return
    if not db[chat_id].get('activated', False):
        return
    for new_user in message.new_chat_members:
        captcha_settings = db[chat_id].get('captcha', {})
        if captcha_settings.get('enabled') and not new_user.is_bot:
            try:
                bot.restrict_chat_member(
                    chat_id, new_user.id,
                    can_send_messages=False, can_send_media_messages=False,
                    can_send_other_messages=False, can_add_web_page_previews=False
                )
                user_mention = f"<a href='tg://user?id={new_user.id}'>{new_user.first_name}</a>"
                user_info_to_store = {
                    'entry_time': time.time(),
                    'message_id': None,
                    'answer': None,
                    'attempts_left': 3,
                    'service_message_id': message.message_id
                }
                if captcha_settings.get('mode') == 'button':
                    text = f"أهلاً بك {user_mention}!\nعليك الضغط على الزر أدناه للتحقق من أنك إنسان حقيقي وليس روبوت."
                    markup = types.InlineKeyboardMarkup()
                    verify_btn = types.InlineKeyboardButton("اضغط هنا للتحقق", callback_data=f"captcha_verify_{new_user.id}")
                    markup.add(verify_btn)
                    captcha_msg = bot.send_message(chat_id, text, reply_markup=markup)
                    user_info_to_store['message_id'] = captcha_msg.message_id
                elif captcha_settings.get('mode') == 'math':
                    num1 = random.randint(1, 10)
                    num2 = random.randint(1, 10)
                    answer = num1 + num2
                    text = f"أهلاً بك {user_mention}!\nلإثبات أنك لست روبوت، قم بحل المسألة التالية: {num1} + {num2} = ?"
                    captcha_msg = bot.send_message(chat_id, text)
                    user_info_to_store['message_id'] = captcha_msg.message_id
                    user_info_to_store['answer'] = answer
                UNVERIFIED_USERS[chat_id][new_user.id] = user_info_to_store
                timer = threading.Timer(
                    captcha_settings.get('time_limit', 3) * 60,
                    captcha_timeout_handler,
                    args=[chat_id, new_user.id]
                )
                timer.start()
            except Exception as e:
                print(f"Captcha Error: {e}")
            return
        if db[chat_id]['restrictions']['check_on_join']:
            if check_and_apply_restrictions(new_user, chat_id):
                return
        welcome_settings = db[chat_id].get('welcome', {})
        if welcome_settings.get('enabled'):
            if welcome_settings.get('first_join_only') and new_user.id in welcome_settings.get('joined_users', []):
                continue

            db[chat_id]['welcome'].setdefault('joined_users', []).append(new_user.id)
            save_group_data(chat_id)

            welcome_message = welcome_settings.get('message', "مرحباً بك {mention} في المجموعة!")
            user_mention = f"<a href='tg://user?id={new_user.id}'>{new_user.first_name}</a>"

            formatted_message = welcome_message.format(
                mention=user_mention,
                first_name=new_user.first_name,
                last_name=new_user.last_name or "",
                full_name=f"{new_user.first_name} {new_user.last_name or ''}".strip(),
                username=f"@{new_user.username}" if new_user.username else "لا يوجد",
                user_id=new_user.id,
                bot_username=f"@{bot.get_me().username}"
            )

            markup = types.InlineKeyboardMarkup(row_width=1)
            try:
                admins = bot.get_chat_administrators(chat_id)
                creator_member = next((admin for admin in admins if admin.status == 'creator'), None)
                if creator_member:
                    creator = creator_member.user
                    owner_button = types.InlineKeyboardButton(
                        text="اسم المالك",
                        url=f"tg://user?id={creator.id}"
                    )
                    markup.add(owner_button)
            except Exception as e:
                print(f"Could not get group owner for welcome message: {e}")
            try:
                chat_info = bot.get_chat(chat_id)
                group_link = chat_info.invite_link
                if not group_link:
                    if chat_info.username:
                        group_link = f"https://t.me/{chat_info.username}"
                    else:
                        group_link = bot.export_chat_invite_link(chat_id)
                if group_link:
                    group_button = types.InlineKeyboardButton(
                        text="اسم المجموعة",
                        url=group_link
                    )
                    markup.add(group_button)
            except Exception as e:
                print(f"Could not get group link for welcome message: {e}")

            bot.send_message(chat_id, formatted_message, reply_markup=markup if markup.keyboard else None)

@bot.message_handler(content_types=['left_chat_member'])
def left_member_handler(message):
    chat_id = message.chat.id
    if admin_db.get('maintenance_mode') or chat_id in admin_db.get('deactivated_groups', []):
        return
    init_chat_db(chat_id)
    if not db[chat_id].get('activated', False):
        return
    goodbye_settings = db[chat_id].get('goodbye', {})
    if not goodbye_settings.get('enabled'):
        return
    user = message.left_chat_member
    user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    goodbye_message = goodbye_settings.get('message', "وداعًا {mention}.")
    formatted_message = goodbye_message.format(
        mention=user_mention,
        first_name=user.first_name,
        last_name=user.last_name or "",
        full_name=f"{user.first_name} {user.last_name or ''}".strip(),
        username=f"@{user.username}" if user.username else "لا يوجد",
        user_id=user.id
    )
    bot.send_message(chat_id, formatted_message)
    if goodbye_settings.get('send_private'):
        try:
            chat_info = bot.get_chat(chat_id)
            group_link = chat_info.invite_link
            if not group_link:
                group_link = bot.export_chat_invite_link(chat_id)
            private_message = f"{formatted_message}\n\nرابط المجموعة: {group_link}"
            bot.send_message(user.id, private_message)
        except Exception:
            pass

@bot.message_handler(func=lambda m: m.text and m.text.strip().startswith("مسح"))
def handle_delete_commands(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type == 'private':
        return

    if not (is_group_creator(chat_id, user_id) or is_secondary_owner(chat_id, user_id)):
        return

    command = message.text.strip()

    if command == "مسح" and message.reply_to_message:
        init_chat_db(chat_id)
        if db[chat_id].get('delete_mode_enabled', False):
            try:
                bot.delete_message(chat_id, message.reply_to_message.message_id)
                bot.delete_message(chat_id, message.message_id)
            except Exception as e:
                print(f"Error deleting message on reply: {e}")
        return

    parts = command.split()
    if len(parts) == 2 and parts[0] == "مسح":
        try:
            count = int(parts[1])
            if not 1 <= count <= 100:
                return

            message_ids_to_delete = [message.message_id - i for i in range(count)]
            bot.delete_messages(chat_id=chat_id, message_ids=message_ids_to_delete)

        except ValueError:
            pass
        except Exception as e:
            try:
                for i in range(count):
                    bot.delete_message(chat_id, message.message_id - i)
            except Exception as final_e:
                 print(f"Error in bulk delete: {final_e}")

@bot.message_handler(func=lambda message: message.text and (message.text.startswith("رفع مالك ثانوي") or message.text.startswith("تنزيل مالك ثانوي") or message.text.startswith("رفع مدير") or message.text.startswith("تنزيل مدير")))
def handle_promotion_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    is_promoting = message.text.startswith("رفع")
    is_so = "مالك ثانوي" in message.text
    role_name = "مالك ثانوي" if is_so else "مدير"
    role_list_key = 'secondary_owners' if is_so else 'managers'
    if is_promoting:
        if is_so and not is_group_creator(chat_id, user_id):
            bot.reply_to(message, "فقط منشئ المجموعة يمكنه تنفيذ هذا الأمر.")
            return
        if not is_so and not has_full_bot_access(chat_id, user_id):
            bot.reply_to(message, "ليس لديك الصلاحية لتنفيذ هذا الأمر.")
            return
        target_user_id, target_user_name = get_target_user_from_message(message)
        if not target_user_id:
            bot.reply_to(message, "يرجى الرد على رسالة المستخدم أو استخدام الايدي الخاص به.")
            return
        if target_user_id == bot.get_me().id:
            bot.reply_to(message, "لا يمكنك ترقيتي.")
            return
        if is_admin(chat_id, target_user_id):
            bot.reply_to(message, f"{target_user_name} هو مشرف بالفعل في المجموعة.")
            return
        init_chat_db(chat_id)
        if target_user_id not in db[chat_id][role_list_key]:
            db[chat_id][role_list_key].append(target_user_id)
            save_group_data(chat_id)
            bot.reply_to(message, f"✅ تم رفع {target_user_name} | <code>{target_user_id}</code> ليصبح {role_name} في البوت.")
        else:
            bot.reply_to(message, f"⚠️ {target_user_name} هو {role_name} بالفعل.")
    else:
        if is_so and not is_group_creator(chat_id, user_id):
            bot.reply_to(message, "فقط منشئ المجموعة يمكنه تنفيذ هذا الأمر.")
            return
        if not is_so and not has_full_bot_access(chat_id, user_id):
            bot.reply_to(message, "ليس لديك الصلاحية لتنفيذ هذا الأمر.")
            return
        target_user_id, target_user_name = get_target_user_from_message(message)
        if not target_user_id:
            bot.reply_to(message, "يرجى الرد على رسالة المستخدم أو استخدام الايدي الخاص به.")
            return
        init_chat_db(chat_id)
        if target_user_id in db[chat_id][role_list_key]:
            db[chat_id][role_list_key].remove(target_user_id)
            save_group_data(chat_id)
            bot.reply_to(message, f"✅ تم تنزيل {target_user_name} | <code>{target_user_id}</code> من رتبة {role_name} في البوت.")
        else:
            bot.reply_to(message, f"⚠️ {target_user_name} ليس {role_name} بالفعل.")

@bot.message_handler(func=lambda message: message.text and message.text.strip() in ["المالكين الثانويين", "المدراء"])
def handle_list_command(message):
    chat_id = message.chat.id
    init_chat_db(chat_id)
    is_so_list = "المالكين" in message.text.strip()
    role_list_key = 'secondary_owners' if is_so_list else 'managers'
    role_name = "المالكين الثانويين" if is_so_list else "المدراء"
    id_list = db[chat_id].get(role_list_key, [])
    if not id_list:
        bot.reply_to(message, f"لا يوجد {role_name} في هذه المجموعة.")
        return
    users_string = get_users_list_string(chat_id, id_list)
    if users_string:
        bot.reply_to(message, f"قائمة {role_name}:\n{users_string}")
    else:
        bot.reply_to(message, f"قائمة {role_name} فارغة.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split('_')
    action = data[0]
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if action == "admin":
        if user_id != DEVELOPER_ID:
            bot.answer_callback_query(call.id, "هذا الأمر للمالك فقط.", show_alert=True)
            return
        sub_action = data[1]
        if sub_action == "toggle":
            if data[2] == "alert":
                admin_db['new_member_alert'] = not admin_db.get('new_member_alert', False)
            elif data[2] == "maintenance":
                admin_db['maintenance_mode'] = not admin_db.get('maintenance_mode', False)
            save_admin_data()
            text, markup = get_admin_panel_menu()
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        elif sub_action == "list":
            if data[2] == "groups":
                group_links = []
                for group_chat_id in db.keys():
                    try:
                        chat_info = bot.get_chat(group_chat_id)
                        link = chat_info.invite_link or bot.export_chat_invite_link(group_chat_id)
                        group_links.append(f"• {chat_info.title}: {link}")
                    except Exception:
                        group_links.append(f"• <code>{group_chat_id}</code>: (لا يمكن إنشاء رابط)")
                if group_links:
                    bot.answer_callback_query(call.id)
                    bot.send_message(call.message.chat.id, "<b>روابط المجموعات المضافة:</b>\n" + "\n".join(group_links))
                else:
                    bot.answer_callback_query(call.id, "لا توجد مجموعات مضافة حاليًا.", show_alert=True)
            elif data[2] == "channels":
                channels = admin_db.get('subscribed_channels', [])
                if channels:
                    channel_list = "\n".join(f"• @{ch['username']} (<code>{ch['id']}</code>)" for ch in channels)
                    bot.answer_callback_query(call.id)
                    bot.send_message(call.message.chat.id, f"<b>قنوات الاشتراك الإجباري:</b>\n{channel_list}")
                else:
                    bot.answer_callback_query(call.id, "لا توجد قنوات للاشتراك الإجباري.", show_alert=True)
        elif sub_action == "add" and data[2] == "channel":
            user_states[user_id] = {'state': 'awaiting_channel_add'}
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "أرسل معرف القناة (username) أو ايدي القناة (ID).")
        elif sub_action == "del" and data[2] == "channel":
            user_states[user_id] = {'state': 'awaiting_channel_del'}
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "أرسل معرف القناة (username) أو ايدي القناة (ID) لحذفها.")
        elif sub_action == "stats":
            total_users = len(admin_db.get('users', {}))
            total_groups = len(db)
            stats_text = (
                f"📊 <b>إحصائيات البوت</b>\n\n"
                f"👥 <b>إجمالي المستخدمين:</b> {total_users}\n"
                f"🏢 <b>إجمالي المجموعات:</b> {total_groups}"
            )
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, stats_text)
        elif sub_action == "stop" and data[2] == "group":
            user_states[user_id] = {'state': 'awaiting_group_deactivate'}
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "أرسل ايدي المجموعة التي تريد إيقاف البوت فيها.")
        elif sub_action == "start" and data[2] == "group":
            user_states[user_id] = {'state': 'awaiting_group_activate'}
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "أرسل ايدي المجموعة التي تريد إعادة تشغيل البوت فيها.")
        return

    if action == 'noop':
        bot.answer_callback_query(call.id)
        return

    try:
        if action == "activate":
            if data[1] == 'bot':
                target_chat_id = int(data[-1])
                if not is_admin(target_chat_id, user_id):
                    bot.answer_callback_query(call.id, "يجب أن تكون مشرفاً لتفعيل البوت.", show_alert=True)
                    return
                init_chat_db(target_chat_id)
                db[target_chat_id]['activated'] = True
                save_group_data(target_chat_id)
                bot.edit_message_text("تم تفعيل البوت بنجاح!", chat_id, call.message.message_id, reply_markup=None)
                markup = get_main_commands_menu(target_chat_id, user_id)
                bot.send_message(target_chat_id, "يمكنك الآن التحكم بإعدادات البوت عبر الأوامر أو لوحة التحكم.", reply_markup=markup)
        elif action == "cmdguide":
            target_chat_id = int(data[-1])
            if not has_manager_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                return
            if data[1] == "open" and data[2] == "main":
                text, markup = get_command_guide_menu(target_chat_id, user_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "show" and data[1] == "cmds":
            role = data[2]
            target_chat_id = int(data[-1])
            if not has_manager_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                return

            back_callback = f"cmdguide_open_main_{target_chat_id}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("رجوع", callback_data=back_callback))

            text = "لا توجد معلومات."
            if role == "owner":
                text = "👑 <b>أوامر المالك</b>\n\n- جميع صلاحيات المالك الثانوي.\n- رفع وتنزيل المالكين الثانويين في البوت."
            elif role == "so":
                text = "💎 <b>أوامر مالك ثانوي</b>\n\n- جميع صلاحيات المدراء.\n- التحكم الكامل في جميع إعدادات البوت (الوسائط، القيود، الحماية، ...).\n- إدارة إنذارات المستخدمين.\n- إدارة شاملة للأعضاء (طرد، حظر، كتم).\n- رفع وتنزيل المدراء في البوت.\n- تفعيل وتعطيل المسح."
            elif role == "manager":
                text = "🛡 <b>أوامر المدراء</b>\n\n- التحكم في إعدادات الترحيب والمغادرة.\n- إدارة نظام التحقق (Captcha).\n- إضافة وحذف الردود الشخصية.\n- التحكم بإعدادات أمر `ايدي`.\n- عرض قوائم الرتب."

            bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "delete":
            target_chat_id = int(data[-1])
            if not (is_group_creator(target_chat_id, user_id) or is_secondary_owner(target_chat_id, user_id)):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك والمالك الثانوي فقط.", show_alert=True)
                return
            sub_action = data[1]
            if sub_action == "open" and data[2] == "main":
                text, markup = get_delete_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle" and data[2] == "enabled":
                init_chat_db(target_chat_id)
                db[target_chat_id]['delete_mode_enabled'] = not db[target_chat_id].get('delete_mode_enabled', False)
                save_group_data(target_chat_id)
                text, markup = get_delete_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "adminroles":
            target_chat_id = int(data[-1])
            if not has_manager_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                return
            sub_action = data[1]
            if sub_action == "open" and data[2] == "main":
                text, markup = get_admin_roles_menu(target_chat_id, user_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set":
                role = data[2]
                if role == 'so':
                    if not is_group_creator(target_chat_id, user_id):
                        bot.answer_callback_query(call.id, "فقط منشئ المجموعة يمكنه رفع مالك ثانوي.", show_alert=True)
                        return
                    user_states[user_id] = {'state': 'awaiting_promote_so', 'chat_id': target_chat_id}
                    bot.answer_callback_query(call.id)
                    bot.send_message(chat_id, "قم بالرد على رسالة المستخدم أو أرسل الايدي الخاص به لرفعه مالك ثانوي.")
                elif role == 'm':
                    if not has_full_bot_access(target_chat_id, user_id):
                        bot.answer_callback_query(call.id, "ليس لديك الصلاحية لرفع مدير.", show_alert=True)
                        return
                    user_states[user_id] = {'state': 'awaiting_promote_m', 'chat_id': target_chat_id}
                    bot.answer_callback_query(call.id)
                    bot.send_message(chat_id, "قم بالرد على رسالة المستخدم أو أرسل الايدي الخاص به لرفعه مدير.")
            elif sub_action == "list":
                role = data[2]
                if role == 'so' and not has_full_bot_access(target_chat_id, user_id):
                    bot.answer_callback_query(call.id, "ليس لديك صلاحية لعرض هذه القائمة.", show_alert=True)
                    return
                if role == 'm' and not has_manager_access(target_chat_id, user_id):
                    bot.answer_callback_query(call.id, "ليس لديك صلاحية لعرض هذه القائمة.", show_alert=True)
                    return
                role_list_key = 'secondary_owners' if role == 'so' else 'managers'
                role_list = db[target_chat_id].get(role_list_key, [])
                role_name = "المالكين الثانويين" if role == 'so' else "المدراء"
                if not role_list:
                    bot.answer_callback_query(call.id, f"لا يوجد {role_name} في هذه المجموعة.", show_alert=True)
                    return
                markup = types.InlineKeyboardMarkup()
                text = f"📋 <b>قائمة {role_name}:</b>\nاضغط على اسم المستخدم لعرض خياراته."
                for member_id in role_list:
                    try:
                        member = bot.get_chat_member(target_chat_id, member_id).user
                        user_name = member.first_name
                    except Exception:
                        user_name = f"User ID {member_id}"
                    markup.add(types.InlineKeyboardButton(user_name, callback_data=f"adminroles_options_{role}_{member_id}_{target_chat_id}"))
                markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"adminroles_open_main_{target_chat_id}"))
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "options":
                role = data[2]
                target_user_id = int(data[3])
                can_demote = False
                if role == 'so' and is_group_creator(target_chat_id, user_id):
                    can_demote = True
                if role == 'm' and has_full_bot_access(target_chat_id, user_id):
                    can_demote = True
                if not can_demote:
                    bot.answer_callback_query(call.id, "ليس لديك الصلاحية لإدارة هذا المستخدم.", show_alert=True)
                    return
                try:
                    member = bot.get_chat_member(target_chat_id, target_user_id).user
                    user_name = member.first_name
                except:
                    user_name = f"User ID {target_user_id}"
                role_name_single = "المالك الثانوي" if role == 'so' else "المدير"
                text = f"إدارة المستخدم: {user_name}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(f"تنزيل {role_name_single}", callback_data=f"adminroles_demote_{role}_{target_user_id}_{target_chat_id}"))
                markup.add(types.InlineKeyboardButton("رجوع", callback_data=f"adminroles_list_{role}_{target_chat_id}"))
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "demote":
                role = data[2]
                target_user_id = int(data[3])
                can_demote = False
                if role == 'so' and is_group_creator(target_chat_id, user_id):
                    can_demote = True
                if role == 'm' and has_full_bot_access(target_chat_id, user_id):
                    can_demote = True
                if not can_demote:
                    bot.answer_callback_query(call.id, "ليس لديك الصلاحية لإزالة هذا المستخدم.", show_alert=True)
                    return
                role_list_key = 'secondary_owners' if role == 'so' else 'managers'
                if target_user_id in db[target_chat_id].get(role_list_key, []):
                    db[target_chat_id][role_list_key].remove(target_user_id)
                    save_group_data(target_chat_id)
                    bot.answer_callback_query(call.id, "تمت إزالة المستخدم بنجاح.", show_alert=True)
                    call.data = f"adminroles_list_{role}_{target_chat_id}"
                    callback_handler(call)
                    return
                else:
                    bot.answer_callback_query(call.id, "المستخدم غير موجود في القائمة بالفعل.", show_alert=True)
        elif action == "punish" and data[1] == "undo":
            target_chat_id = int(data[-1])
            if not is_admin(target_chat_id, user_id):
                 bot.answer_callback_query(call.id, "هذا الأمر للمشرفين فقط.", show_alert=True)
                 return
            user_to_unpunish = int(data[2])
            punish_type = data[3]
            try:
                member = bot.get_chat_member(target_chat_id, user_to_unpunish).user
                user_mention = f"<a href='tg://user?id={member.id}'>{member.first_name}</a>"
                admin_mention = f"<a href='tg://user?id={user_id}'>{call.from_user.first_name}</a>"
                new_text = ""
                if punish_type == 'mute':
                    bot.restrict_chat_member(target_chat_id, user_to_unpunish, can_send_messages=True)
                    new_text = f"✅ تم إلغاء كتم {user_mention} بواسطة {admin_mention}."
                elif punish_type == 'ban':
                    bot.unban_chat_member(target_chat_id, user_to_unpunish, only_if_banned=True)
                    new_text = f"✅ تم إلغاء حظر {user_mention} بواسطة {admin_mention}."
                if new_text:
                    bot.edit_message_text(new_text, chat_id, call.message.message_id, reply_markup=None)
                    bot.answer_callback_query(call.id, "تم إلغاء العقوبة.")
            except Exception as e:
                bot.answer_callback_query(call.id, f"فشل الإلغاء: {e}", show_alert=True)
                bot.edit_message_text(call.message.text + "\n(فشل الإلغاء)", chat_id, call.message.message_id, reply_markup=None)
        elif action == "botname":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open" and data[2] == "main":
                text, markup = get_bot_name_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle" and data[2] == "enabled":
                db[target_chat_id]['bot_name_settings']['enabled'] = not db[target_chat_id]['bot_name_settings']['enabled']
                save_group_data(target_chat_id)
                text, markup = get_bot_name_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set" and data[2] == "name":
                user_states[user_id] = {'state': 'awaiting_bot_name', 'chat_id': target_chat_id}
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, "أرسل الآن اسم البوت الجديد.")
        elif action == "personal":
            target_chat_id = int(data[-1])
            if not has_manager_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open" and data[2] == "main":
                text, markup = get_personal_replies_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "add":
                user_states[user_id] = {'state': 'awaiting_personal_trigger', 'chat_id': target_chat_id}
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, "أرسل الآن الكلمة التي تريد إضافة رد لها.")
            elif sub_action == "list":
                replies = db[target_chat_id].get('personal_replies', {})
                if not replies:
                    text_list = "قائمة الردود الشخصية فارغة."
                else:
                    text_list = "<b>الكلمات المضافة حالياً:</b>\n" + "\n".join(f"• <code>{word}</code>" for word in replies.keys())
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, text_list, parse_mode='HTML')
            elif sub_action == "remove":
                user_states[user_id] = {'state': 'awaiting_personal_remove', 'chat_id': target_chat_id}
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, "أرسل الكلمة التي تريد إزالة الرد الخاص بها.")
        elif action == "longmsg":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open":
                if data[2] == "main":
                    text, markup = get_long_messages_menu(target_chat_id)
                elif data[2] == "min":
                    text, markup = get_long_messages_limit_menu(target_chat_id, 'min')
                elif data[2] == "max":
                    text, markup = get_long_messages_limit_menu(target_chat_id, 'max')
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle":
                if data[2] == "enabled":
                    db[target_chat_id]['long_messages']['enabled'] = not db[target_chat_id]['long_messages']['enabled']
                elif data[2] == "delete":
                    db[target_chat_id]['long_messages']['delete'] = not db[target_chat_id]['long_messages']['delete']
                save_group_data(target_chat_id)
                text, markup = get_long_messages_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set":
                if data[2] == "punish":
                    punishment = data[3]
                    db[target_chat_id]['long_messages']['punishment'] = punishment
                elif data[2] == "min":
                    limit = int(data[3])
                    db[target_chat_id]['long_messages']['min_chars'] = limit
                elif data[2] == "max":
                    limit = int(data[3])
                    db[target_chat_id]['long_messages']['max_chars'] = limit
                save_group_data(target_chat_id)
                text, markup = get_long_messages_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "members":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = '_'.join(data[1:-1])
            init_chat_db(target_chat_id)
            if sub_action == "open_main":
                text, markup = get_members_management_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
                return
            if sub_action.endswith("confirm"):
                action_key = sub_action.replace("_confirm", "")
                confirm_map = {
                    "unban_all": "🚫 هل أنت متأكد من أنك تريد إلغاء حظر الكل؟",
                    "unmute_all": "🔊 هل أنت متأكد من أنك تريد إلغاء كتم الكل؟",
                    "kick_muted": "❗️ هل أنت متأكد من أنك تريد طرد جميع المستخدمين المكتومين؟"
                }
                text = confirm_map.get(action_key, "هل أنت متأكد؟")
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ نعم", callback_data=f"members_{action_key}_execute_{target_chat_id}"),
                           types.InlineKeyboardButton("❌ لا", callback_data=f"members_open_main_{target_chat_id}"))
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
                return
            if sub_action.endswith("execute"):
                action_key = sub_action.replace("_execute", "")
                task_map = {
                    "unban_all": _unban_all_task,
                    "unmute_all": _unmute_all_task,
                    "kick_muted": _kick_muted_task,
                }
                task_function = task_map.get(action_key)
                if task_function:
                    threading.Thread(target=task_function, args=(target_chat_id, call.message.message_id)).start()
                    bot.answer_callback_query(call.id, "تم بدء العملية في الخلفية.")
                return
        elif action == "warnings":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open" and data[2] == "main":
                text, markup = get_warnings_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set" and data[2] == "punish":
                punishment = data[3]
                db[target_chat_id]['warnings_settings']['punishment'] = punishment
                save_group_data(target_chat_id)
                text, markup = get_warnings_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "open" and data[2] == "limit":
                 text, markup = get_warnings_limit_menu(target_chat_id)
                 bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "open" and data[2] == "duration":
                user_states[user_id] = {'state': 'awaiting_warning_duration', 'chat_id': target_chat_id}
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, "أرسل مدة الكتم بالدقائق (مثال: 60 لكتم ساعة). أرسل 0 للكتم الدائم.")
            elif sub_action == "set" and data[2] == "limit":
                limit = int(data[3])
                db[target_chat_id]['warnings_settings']['limit'] = limit
                save_group_data(target_chat_id)
                text, markup = get_warnings_limit_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "list":
                page = int(data[2])
                text, markup = get_warned_users_list_menu(target_chat_id, page)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "clear" and data[2] == "all" and data[3] == "confirm":
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ نعم، قم بالإلغاء", callback_data=f"warnings_clear_all_execute_{target_chat_id}"))
                markup.add(types.InlineKeyboardButton("❌ لا، تراجع", callback_data=f"warnings_open_main_{target_chat_id}"))
                bot.edit_message_text("هل أنت متأكد من أنك تريد إلغاء جميع الإنذارات والعقوبات للمستخدمين؟", chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "clear" and data[2] == "all" and data[3] == "execute":
                warned_users = db[target_chat_id]['warnings_settings']['warned_users']
                for user_id_str, user_data in warned_users.items():
                    user_id_int = int(user_id_str)
                    if user_data.get('punished'):
                        try:
                            bot.restrict_chat_member(target_chat_id, user_id_int, can_send_messages=True)
                            bot.unban_chat_member(target_chat_id, user_id_int, only_if_banned=True)
                        except Exception:
                            pass
                db[target_chat_id]['warnings_settings']['warned_users'] = {}
                save_group_data(target_chat_id)
                bot.answer_callback_query(call.id, "تم إلغاء جميع الإنذارات والعقوبات.", show_alert=True)
                text, markup = get_warnings_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "unpunish":
                user_to_unpunish = int(data[2])
                user_to_unpunish_str = str(user_to_unpunish)
                page = int(data[3])
                warned_users = db[target_chat_id]['warnings_settings']['warned_users']
                if user_to_unpunish_str in warned_users:
                    try:
                        bot.restrict_chat_member(target_chat_id, user_to_unpunish, can_send_messages=True)
                        bot.unban_chat_member(target_chat_id, user_to_unpunish, only_if_banned=True)
                        warned_users[user_to_unpunish_str]['manually_unpunished'] = True
                        warned_users[user_to_unpunish_str]['punished'] = False
                        save_group_data(target_chat_id)
                        bot.answer_callback_query(call.id, "تم إلغاء العقوبة.")
                    except Exception:
                        bot.answer_callback_query(call.id, "فشل إلغاء العقوبة.", show_alert=True)
                text, markup = get_warned_users_list_menu(target_chat_id, page)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "repeatingmsg":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open" and data[2] == "main":
                text, markup = get_repeating_messages_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle" and data[2] == "enabled":
                db[target_chat_id]['repeating_messages']['enabled'] = not db[target_chat_id]['repeating_messages']['enabled']
                save_group_data(target_chat_id)
                text, markup = get_repeating_messages_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "add" and data[2] == "message":
                user_states[user_id] = {'state': 'awaiting_repeating_message', 'chat_id': target_chat_id}
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, "أرسل الآن الرسالة التي تريد إضافتها للتكرار.")
            elif sub_action == "open" and data[2] == "interval":
                text, markup = get_repeating_interval_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set" and data[2] == "interval":
                interval_type = data[3]
                value = int(data[4])
                if interval_type == "hours":
                    db[target_chat_id]['repeating_messages']['interval_seconds'] = value * 3600
                elif interval_type == "minutes":
                    db[target_chat_id]['repeating_messages']['interval_seconds'] = value * 60
                save_group_data(target_chat_id)
                text, markup = get_repeating_messages_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "nightmode":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open" and data[2] == "main":
                text, markup = get_night_mode_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle":
                if data[2] == "enabled":
                    db[target_chat_id]['night_mode']['enabled'] = not db[target_chat_id]['night_mode']['enabled']
                elif data[2] == "notify":
                    db[target_chat_id]['night_mode']['notify'] = not db[target_chat_id]['night_mode']['notify']
                save_group_data(target_chat_id)
                text, markup = get_night_mode_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "open" and data[2] == "time":
                user_states[user_id] = {'state': 'awaiting_night_start', 'chat_id': target_chat_id}
                text, markup = get_night_mode_time_menu(target_chat_id, step='start')
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set" and data[2] == "hour":
                hour = int(data[3])
                state_info = user_states.get(user_id, {})
                if state_info.get('state') == 'awaiting_night_start' and state_info.get('chat_id') == target_chat_id:
                    user_states[user_id]['state'] = 'awaiting_night_end'
                    user_states[user_id]['start_hour'] = hour
                    text, markup = get_night_mode_time_menu(target_chat_id, step='end', start_hour=hour)
                    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
                elif state_info.get('state') == 'awaiting_night_end' and state_info.get('chat_id') == target_chat_id:
                    start_hour = state_info['start_hour']
                    end_hour = hour
                    db[target_chat_id]['night_mode']['start_hour'] = start_hour
                    db[target_chat_id]['night_mode']['end_hour'] = end_hour
                    save_group_data(target_chat_id)
                    del user_states[user_id]
                    text, markup = get_night_mode_menu(target_chat_id)
                    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set" and data[2] == "timezone":
                user_states[user_id] = {'state': 'awaiting_timezone', 'chat_id': target_chat_id}
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, "أرسل اسم دولتك أو مدينتك باللغة الإنجليزية (مثال: `Asia/Baghdad`).")
        elif action == "media":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open":
                if data[2] == "menu":
                    page = int(data[3])
                    text, markup = get_media_menu(target_chat_id, page)
                elif data[2] == "punish":
                    media_key = data[3]
                    text, markup = get_media_punishment_menu(target_chat_id, media_key)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set":
                media_key = data[3]
                punishment = data[4]
                db[target_chat_id]['media_restrictions'][media_key]['punishment'] = punishment
                save_group_data(target_chat_id)
                text, markup = get_media_punishment_menu(target_chat_id, media_key)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "captcha":
            if data[1] == "verify":
                target_user_id = int(data[-1])
                if user_id != target_user_id:
                    bot.answer_callback_query(call.id, "هذا الزر ليس لك.", show_alert=True)
                    return
                init_chat_db(chat_id)
                captcha_settings = db[chat_id].get('captcha', {})
                if user_id in UNVERIFIED_USERS.get(chat_id, {}):
                    user_info = UNVERIFIED_USERS[chat_id][user_id]
                    bot.restrict_chat_member(chat_id, user_id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                    bot.edit_message_text(f"✅ تم التحقق بنجاح، {call.from_user.first_name}!", chat_id, call.message.message_id, reply_markup=None)
                    if captcha_settings.get('delete_service_message') and 'service_message_id' in user_info:
                        try: bot.delete_message(chat_id, user_info['service_message_id'])
                        except: pass
                    del UNVERIFIED_USERS[chat_id][user_id]
                    bot.answer_callback_query(call.id, "تم التحقق!")
                else:
                    bot.edit_message_text("تم التحقق من هذا المستخدم بالفعل.", chat_id, call.message.message_id, reply_markup=None)
                    bot.answer_callback_query(call.id)
                return
            target_chat_id = int(data[-1])
            if not has_manager_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open" and data[2] == "main":
                text, markup = get_captcha_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
                return
            if sub_action == "toggle":
                if data[2] == "enabled":
                    db[target_chat_id]['captcha']['enabled'] = not db[target_chat_id]['captcha']['enabled']
                elif data[2] == "delete":
                    db[target_chat_id]['captcha']['delete_service_message'] = not db[target_chat_id]['captcha']['delete_service_message']
                save_group_data(target_chat_id)
                text, markup = get_captcha_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "open":
                if data[2] == "mode":
                    text, markup = get_captcha_mode_menu(target_chat_id)
                elif data[2] == "punishment":
                    text, markup = get_captcha_punishment_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set":
                if data[2] == "mode":
                    db[target_chat_id]['captcha']['mode'] = data[3]
                elif data[2] == "punishment":
                    db[target_chat_id]['captcha']['punishment'] = data[3]
                save_group_data(target_chat_id)
                if data[2] == "mode":
                    text, markup = get_captcha_mode_menu(target_chat_id)
                else:
                    text, markup = get_captcha_punishment_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "edit" and data[2] == "time":
                user_states[user_id] = {'state': 'awaiting_captcha_time', 'chat_id': target_chat_id}
                bot.send_message(chat_id, "أرسل عدد الدقائق لوقت التحقق (مثال: 3).")
                bot.answer_callback_query(call.id)
        elif action == "commands":
            if data[1] == "open" and data[2] == "main":
                target_chat_id = int(data[-1])
                if not has_manager_access(target_chat_id, user_id):
                    bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                    return
                markup = get_main_commands_menu(target_chat_id, user_id)
                bot.edit_message_text("اختر من القائمة:", chat_id, call.message.message_id, reply_markup=markup)
        elif action == "settings":
            sub_action = data[1]
            target_chat_id = int(data[-1])
            init_chat_db(target_chat_id)
            if sub_action == "open" and data[2] == "here":
                if not has_manager_access(target_chat_id, user_id):
                    bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                    return
                markup = get_main_settings_menu(target_chat_id, user_id)
                bot.edit_message_text("⚙️ الإعدادات الرئيسية", chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action in ["whitelist", "antiflood", "alphabets", "rules"]:
                if not has_full_bot_access(target_chat_id, user_id):
                    bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                    return
                if sub_action == "whitelist": text, markup = get_whitelist_menu(target_chat_id)
                if sub_action == "antiflood": text, markup = get_antiflood_menu(target_chat_id)
                if sub_action == "alphabets": text, markup = get_alphabets_menu(target_chat_id)
                if sub_action == "rules": text, markup = get_rules_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action in ["welcome", "goodbye"]:
                if not has_manager_access(target_chat_id, user_id):
                    bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                    return
                if sub_action == "welcome": text, markup = get_welcome_menu(target_chat_id)
                if sub_action == "goodbye": text, markup = get_goodbye_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "rules":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "set":
                user_states[user_id] = {'state': 'awaiting_rules', 'chat_id': target_chat_id}
                bot.send_message(chat_id, "أرسل الآن رسالة القوانين. يمكن أن تكون نصًا، صورة، فيديو، أو أي نوع من الوسائط.")
                bot.answer_callback_query(call.id)
            elif sub_action == "delete":
                db[target_chat_id]['rules'] = {'text': "لم يتم تعيين قوانين لهذه المجموعة بعد.", 'media_type': None, 'media_id': None, 'caption': None}
                save_group_data(target_chat_id)
                text, markup = get_rules_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
                bot.answer_callback_query(call.id, "تم حذف القوانين.")
        elif action == "restrictions":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open":
                menu_type = data[2]
                if menu_type == "main":
                    text, markup = get_restrictions_menu(target_chat_id)
                elif menu_type == "enforce":
                    text, markup = get_enforce_menu(target_chat_id)
                elif menu_type == "prevent":
                    text, markup = get_prevent_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle":
                toggle_type = data[2]
                if toggle_type == "check":
                    db[target_chat_id]['restrictions']['check_on_join'] = not db[target_chat_id]['restrictions']['check_on_join']
                elif toggle_type == "delete":
                    db[target_chat_id]['restrictions']['delete_messages'] = not db[target_chat_id]['restrictions']['delete_messages']
                save_group_data(target_chat_id)
                text, markup = get_restrictions_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "edit" and data[2] == "punish":
                r_type = data[3]
                r_key = data[4]
                text, markup = get_punishment_menu_for_restriction(target_chat_id, r_type, r_key)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set" and data[2] == "punish":
                r_type = data[3]
                r_key = data[4]
                punishment = data[5]
                db[target_chat_id]['restrictions'][r_type][r_key]['punishment'] = punishment
                save_group_data(target_chat_id)
                text, markup = get_punishment_menu_for_restriction(target_chat_id, r_type, r_key)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "whitelist":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "toggle":
                db[target_chat_id]['whitelist']['enabled'] = not db[target_chat_id]['whitelist']['enabled']
                save_group_data(target_chat_id)
                text, markup = get_whitelist_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "add":
                user_states[user_id] = {'state': 'awaiting_whitelist_add', 'chat_id': target_chat_id}
                bot.send_message(chat_id, "أرسل رابط أو معرف لإضافته للقائمة البيضاء.")
                bot.answer_callback_query(call.id)
            elif sub_action == "remove":
                user_states[user_id] = {'state': 'awaiting_whitelist_remove', 'chat_id': target_chat_id}
                bot.send_message(chat_id, "أرسل رابط أو معرف لإزالته من القائمة البيضاء.")
                bot.answer_callback_query(call.id)
            elif sub_action == "view":
                wlist = db[target_chat_id]['whitelist']['list']
                text_list = "\n".join(f"• `{item}`" for item in wlist) if wlist else "القائمة البيضاء فارغة."
                bot.answer_callback_query(call.id, f"القائمة البيضاء:\n{text_list}", show_alert=True)
        elif action == "welcome":
            target_chat_id = int(data[-1])
            if not has_manager_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "toggle":
                if len(data) > 3 and data[2] == "mode":
                    db[target_chat_id]['welcome']['first_join_only'] = not db[target_chat_id]['welcome']['first_join_only']
                else:
                    db[target_chat_id]['welcome']['enabled'] = not db[target_chat_id]['welcome']['enabled']
                save_group_data(target_chat_id)
            elif sub_action == "edit":
                user_states[user_id] = {'state': 'awaiting_welcome_message', 'chat_id': target_chat_id}
                bot.send_message(chat_id, "أرسل الآن رسالة الترحيب الجديدة.")
                bot.answer_callback_query(call.id)
                return
            text, markup = get_welcome_menu(target_chat_id)
            bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "goodbye":
            target_chat_id = int(data[-1])
            if not has_manager_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "toggle":
                if len(data) > 3 and data[2] == "private":
                    db[target_chat_id]['goodbye']['send_private'] = not db[target_chat_id]['goodbye']['send_private']
                else:
                    db[target_chat_id]['goodbye']['enabled'] = not db[target_chat_id]['goodbye']['enabled']
                save_group_data(target_chat_id)
            elif sub_action == "edit":
                user_states[user_id] = {'state': 'awaiting_goodbye_message', 'chat_id': target_chat_id}
                bot.send_message(chat_id, "ارسل كليشه توديع شخص.")
                bot.answer_callback_query(call.id)
                return
            text, markup = get_goodbye_menu(target_chat_id)
            bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "antiflood":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "toggle" and data[2] == "enabled":
                db[target_chat_id]['antiflood']['enabled'] = not db[target_chat_id]['antiflood']['enabled']
                save_group_data(target_chat_id)
                text, markup = get_antiflood_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set":
                setting = data[2]
                value = data[3]
                if setting == "time":
                    db[target_chat_id]['antiflood']['seconds'] = int(value)
                elif setting == "msg":
                    db[target_chat_id]['antiflood']['messages'] = int(value)
                elif setting == "punish":
                    db[target_chat_id]['antiflood']['punishment'] = value
                save_group_data(target_chat_id)
                if setting == "punish":
                    text, markup = get_antiflood_punishment_menu(target_chat_id)
                    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
                    return
                text, markup = get_antiflood_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "time":
                text, markup = get_antiflood_time_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "messages":
                text, markup = get_antiflood_messages_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "punishment":
                text, markup = get_antiflood_punishment_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle" and data[2] == "delete":
                db[target_chat_id]['antiflood']['delete_messages'] = not db[target_chat_id]['antiflood']['delete_messages']
                save_group_data(target_chat_id)
                text, markup = get_antiflood_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "open" and data[2] == "duration":
                 user_states[user_id] = {'state': 'awaiting_antiflood_duration', 'chat_id': target_chat_id}
                 bot.answer_callback_query(call.id)
                 bot.send_message(chat_id, "أرسل مدة العقوبة بالدقائق (مثال: 60 لساعة). أرسل 0 للعقوبة الدائمة.")
        elif action == "antirepeat":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open" and data[2] == "main":
                text, markup = get_anti_repeat_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle" and data[2] == "enabled":
                db[target_chat_id]['anti_repeat']['enabled'] = not db[target_chat_id]['anti_repeat']['enabled']
                save_group_data(target_chat_id)
                text, markup = get_anti_repeat_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set" and data[2] == "punish":
                punishment = data[3]
                db[target_chat_id]['anti_repeat']['punishment'] = punishment
                save_group_data(target_chat_id)
                text, markup = get_anti_repeat_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "alphabets":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == 'edit':
                lang = data[2]
                text, markup = get_alphabet_punishment_menu(target_chat_id, lang)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == 'set' and data[2] == 'punish':
                lang = data[3]
                punishment = data[4]
                db[target_chat_id]['alphabets'][lang]['punishment'] = punishment
                save_group_data(target_chat_id)
                text, markup = get_alphabet_punishment_menu(target_chat_id, lang)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == 'toggle' and data[2] == 'delete':
                lang = data[3]
                db[target_chat_id]['alphabets'][lang]['delete'] = not db[target_chat_id]['alphabets'][lang]['delete']
                save_group_data(target_chat_id)
                text, markup = get_alphabet_punishment_menu(target_chat_id, lang)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "forbiddenwords":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open" and data[2] == "main":
                text, markup = get_forbidden_words_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "set" and data[2] == "punish":
                punishment = data[3]
                db[target_chat_id]['forbidden_words']['punishment'] = punishment
                save_group_data(target_chat_id)
                text, markup = get_forbidden_words_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle" and data[2] == "delete":
                db[target_chat_id]['forbidden_words']['delete_message'] = not db[target_chat_id]['forbidden_words']['delete_message']
                save_group_data(target_chat_id)
                text, markup = get_forbidden_words_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "add" and data[2] == "word":
                user_states[user_id] = {'state': 'awaiting_forbidden_add', 'chat_id': target_chat_id}
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, "أرسل الكلمة أو الكلمات التي تريد إضافتها. يمكنك إرسال عدة كلمات في رسالة واحدة، كل كلمة في سطر.")
            elif sub_action == "remove" and data[2] == "word":
                user_states[user_id] = {'state': 'awaiting_forbidden_remove', 'chat_id': target_chat_id}
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, "أرسل الكلمة أو الكلمات التي تريد إزالتها. يمكنك إرسال عدة كلمات في رسالة واحدة، كل كلمة في سطر.")
            elif sub_action == "list" and data[2] == "words":
                words = db[target_chat_id].get('forbidden_words', {}).get('words', [])
                if not words:
                    text_list = "قائمة الكلمات المحظورة فارغة."
                else:
                    text_list = "<b>الكلمات المحظورة حالياً:</b>\n" + "\n".join(f"• <code>{word}</code>" for word in words)
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, text_list, parse_mode='HTML')
        elif action == "incognito":
            target_chat_id = int(data[-1])
            if not has_full_bot_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "هذا الأمر للمالك الثانوي فما فوق.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open":
                if data[2] == "main":
                    text, markup = get_incognito_users_menu(target_chat_id)
                elif data[2] == "exceptions":
                    text, markup = get_incognito_exceptions_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle":
                if data[2] == "enabled":
                    db[target_chat_id]['incognito_users']['enabled'] = not db[target_chat_id]['incognito_users']['enabled']
                elif data[2] == "delete":
                    db[target_chat_id]['incognito_users']['delete_messages'] = not db[target_chat_id]['incognito_users']['delete_messages']
                save_group_data(target_chat_id)
                text, markup = get_incognito_users_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        elif action == "idcmd":
            target_chat_id = int(data[-1])
            if not has_manager_access(target_chat_id, user_id):
                bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
                return
            sub_action = data[1]
            init_chat_db(target_chat_id)
            if sub_action == "open" and data[2] == "main":
                text, markup = get_id_command_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
            elif sub_action == "toggle":
                toggle_type = data[2]
                if toggle_type == "enabled":
                    db[target_chat_id]['id_command']['enabled'] = not db[target_chat_id]['id_command']['enabled']
                elif toggle_type == "photo":
                    db[target_chat_id]['id_command']['with_photo'] = not db[target_chat_id]['id_command']['with_photo']
                save_group_data(target_chat_id)
                text, markup = get_id_command_menu(target_chat_id)
                bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ ما.")
        print(f"Error in callback handler: {e} with data {call.data}")

@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id, {}).get('state') in ['awaiting_whitelist_add', 'awaiting_whitelist_remove', 'awaiting_welcome_message', 'awaiting_goodbye_message', 'awaiting_captcha_time', 'awaiting_timezone', 'awaiting_rules', 'awaiting_forbidden_add', 'awaiting_forbidden_remove', 'awaiting_repeating_message', 'awaiting_personal_trigger', 'awaiting_personal_response', 'awaiting_personal_remove', 'awaiting_warning_duration', 'awaiting_antiflood_duration', 'awaiting_bot_name', 'awaiting_channel_add', 'awaiting_channel_del', 'awaiting_group_deactivate', 'awaiting_group_activate', 'awaiting_promote_so', 'awaiting_promote_m'])
def handle_state_messages(message):
    user_id = message.from_user.id
    state_info = user_states[user_id]
    state = state_info['state']
    chat_id = state_info.get('chat_id')
    if chat_id:
        init_chat_db(chat_id)
    if state == 'awaiting_channel_add':
        if user_id == DEVELOPER_ID:
            channel_id = message.text.strip()
            try:
                chat_info = bot.get_chat(channel_id)
                channel_data = {'id': chat_info.id, 'username': chat_info.username}
                if channel_data not in admin_db.get('subscribed_channels', []):
                    admin_db.setdefault('subscribed_channels', []).append(channel_data)
                    save_admin_data()
                    bot.reply_to(message, f"✅ تم إضافة القناة @{chat_info.username} بنجاح.")
                else:
                    bot.reply_to(message, "⚠️ القناة مضافة بالفعل.")
            except Exception as e:
                bot.reply_to(message, f"❌ فشل في إضافة القناة. تأكد من أن البوت مشرف في القناة وأن المعرف صحيح.\nError: {e}")
            del user_states[user_id]
        return
    if state == 'awaiting_channel_del':
        if user_id == DEVELOPER_ID:
            channel_id_to_del = message.text.strip()
            channels = admin_db.get('subscribed_channels', [])
            found = False
            for channel in channels:
                if str(channel['id']) == channel_id_to_del or channel['username'] == channel_id_to_del.replace('@', ''):
                    channels.remove(channel)
                    found = True
                    break
            if found:
                save_admin_data()
                bot.reply_to(message, f"✅ تم حذف القناة {channel_id_to_del} بنجاح.")
            else:
                bot.reply_to(message, "❌ لم يتم العثور على القناة.")
            del user_states[user_id]
        return
    if state == 'awaiting_group_deactivate':
        if user_id == DEVELOPER_ID:
            try:
                group_id = int(message.text.strip())
                if group_id not in admin_db.get('deactivated_groups', []):
                    admin_db.setdefault('deactivated_groups', []).append(group_id)
                    save_admin_data()
                    bot.reply_to(message, f"✅ تم إيقاف البوت في المجموعة <code>{group_id}</code>.")
                else:
                    bot.reply_to(message, "⚠️ البوت متوقف بالفعل في هذه المجموعة.")
            except ValueError:
                bot.reply_to(message, "❌ ايدي المجموعة غير صالح. يرجى إرسال رقم.")
            del user_states[user_id]
        return
    if state == 'awaiting_group_activate':
        if user_id == DEVELOPER_ID:
            try:
                group_id = int(message.text.strip())
                if group_id in admin_db.get('deactivated_groups', []):
                    admin_db['deactivated_groups'].remove(group_id)
                    save_admin_data()
                    bot.reply_to(message, f"✅ تم إعادة تشغيل البوت في المجموعة <code>{group_id}</code>.")
                else:
                    bot.reply_to(message, "⚠️ البوت يعمل بالفعل في هذه المجموعة.")
            except ValueError:
                bot.reply_to(message, "❌ ايدي المجموعة غير صالح. يرجى إرسال رقم.")
            del user_states[user_id]
        return
    if state == 'awaiting_personal_response':
        trigger = state_info['trigger']
        content_type = message.content_type
        reply_data = {'caption': message.caption}
        if content_type == 'text':
            reply_data['type'] = 'text'
            reply_data['content'] = message.text
        elif content_type == 'photo':
            reply_data['type'] = 'photo'
            reply_data['content'] = message.photo[-1].file_id
        elif content_type == 'video':
            reply_data['type'] = 'video'
            reply_data['content'] = message.video.file_id
        elif content_type == 'animation':
            reply_data['type'] = 'animation'
            reply_data['content'] = message.animation.file_id
        elif content_type == 'document':
            reply_data['type'] = 'document'
            reply_data['content'] = message.document.file_id
        elif content_type == 'audio':
            reply_data['type'] = 'audio'
            reply_data['content'] = message.audio.file_id
        elif content_type == 'voice':
            reply_data['type'] = 'voice'
            reply_data['content'] = message.voice.file_id
        if 'type' in reply_data:
            db[chat_id]['personal_replies'][trigger] = reply_data
            save_group_data(chat_id)
            bot.reply_to(message, f"تم حفظ الرد للكلمة '<code>{trigger}</code>' بنجاح.")
        else:
            bot.reply_to(message, "نوع الرد هذا غير مدعوم.")
        del user_states[user_id]
        return
    if state == 'awaiting_promote_so' or state == 'awaiting_promote_m':
        is_so = state == 'awaiting_promote_so'
        role_name = "مالك ثانوي" if is_so else "مدير"
        role_list_key = 'secondary_owners' if is_so else 'managers'
        try:
            target_user_id = int(message.text.strip())
            member = bot.get_chat_member(chat_id, target_user_id).user
            target_user_name = member.first_name
        except (ValueError, Exception):
            bot.reply_to(message, "الايدي غير صالح أو لا يمكن العثور على المستخدم.")
            del user_states[user_id]
            return
        if target_user_id == bot.get_me().id or is_admin(chat_id, target_user_id):
            bot.reply_to(message, "لا يمكن رفع هذا المستخدم.")
            del user_states[user_id]
            return
        if target_user_id not in db[chat_id][role_list_key]:
            db[chat_id][role_list_key].append(target_user_id)
            save_group_data(chat_id)
            bot.reply_to(message, f"✅ تم رفع {target_user_name} | <code>{target_user_id}</code> ليصبح {role_name} في البوت.")
        else:
            bot.reply_to(message, f"⚠️ {target_user_name} هو {role_name} بالفعل.")
        del user_states[user_id]
        return

    del user_states[user_id]
    if state == 'awaiting_whitelist_add':
        items = [item.strip() for item in message.text.split('\n') if item.strip()]
        for item in items:
            if item not in db[chat_id]['whitelist']['list']:
                db[chat_id]['whitelist']['list'].append(item)
        save_group_data(chat_id)
        bot.reply_to(message, f"تمت إضافة {len(items)} عنصر/عناصر إلى القائمة البيضاء.")
    elif state == 'awaiting_whitelist_remove':
        items_to_remove = [item.strip() for item in message.text.split('\n') if item.strip()]
        count = 0
        for item in items_to_remove:
            if item in db[chat_id]['whitelist']['list']:
                db[chat_id]['whitelist']['list'].remove(item)
                count += 1
        save_group_data(chat_id)
        bot.reply_to(message, f"تمت إزالة {count} عنصر/عناصر من القائمة البيضاء.")
    elif state == 'awaiting_welcome_message':
        db[chat_id]['welcome']['message'] = message.text
        save_group_data(chat_id)
        bot.reply_to(message, "تم تحديث رسالة الترحيب بنجاح.")
    elif state == 'awaiting_goodbye_message':
        db[chat_id]['goodbye']['message'] = message.text
        save_group_data(chat_id)
        bot.reply_to(message, "تم تحديث رسالة الوداع بنجاح.")
    elif state == 'awaiting_captcha_time':
        try:
            time_limit = int(message.text)
            if 1 <= time_limit <= 60:
                db[chat_id]['captcha']['time_limit'] = time_limit
                save_group_data(chat_id)
                bot.reply_to(message, f"تم ضبط وقت التحقق على {time_limit} دقيقة.")
            else:
                bot.reply_to(message, "الرجاء إدخال رقم بين 1 و 60.")
        except ValueError:
            bot.reply_to(message, "الرجاء إرسال رقم صحيح.")
    elif state == 'awaiting_warning_duration':
        try:
            duration_minutes = int(message.text)
            if duration_minutes >= 0:
                db[chat_id]['warnings_settings']['mute_duration'] = duration_minutes * 60
                save_group_data(chat_id)
                bot.reply_to(message, f"تم ضبط مدة كتم الإنذار على {duration_minutes} دقيقة.")
            else:
                 bot.reply_to(message, "الرجاء إدخال رقم موجب.")
        except ValueError:
            bot.reply_to(message, "الرجاء إرسال رقم صحيح.")
    elif state == 'awaiting_antiflood_duration':
        try:
            duration_minutes = int(message.text)
            if duration_minutes >= 0:
                db[chat_id]['antiflood']['duration'] = duration_minutes * 60
                save_group_data(chat_id)
                bot.reply_to(message, f"تم ضبط مدة العقوبة على {duration_minutes} دقيقة.")
            else:
                 bot.reply_to(message, "الرجاء إدخال رقم موجب.")
        except ValueError:
            bot.reply_to(message, "الرجاء إرسال رقم صحيح.")
    elif state == 'awaiting_bot_name':
        new_name = message.text.strip()
        if new_name:
            db[chat_id]['bot_name_settings']['name'] = new_name
            save_group_data(chat_id)
            bot.reply_to(message, f"تم تغيير اسم البوت إلى: <code>{new_name}</code>")
        else:
            bot.reply_to(message, "الاسم غير صالح. الرجاء المحاولة مرة أخرى.")
    elif state == 'awaiting_timezone':
        try:
            tz_name = message.text.strip()
            _ = zoneinfo.ZoneInfo(tz_name)
            db[chat_id]['night_mode']['timezone'] = tz_name
            save_group_data(chat_id)
            bot.reply_to(message, f"تم ضبط التوقيت المحلي على: {tz_name}")
        except zoneinfo.ZoneInfoNotFoundError:
            bot.reply_to(message, "لم يتم العثور على المنطقة الزمنية. الرجاء المحاولة مرة أخرى باستخدام اسم صالح مثل 'Asia/Baghdad' أو 'Africa/Cairo'.")
        except Exception:
            bot.reply_to(message, "حدث خطأ غير متوقع.")
    elif state == 'awaiting_rules':
        rules_data = {'text': None, 'media_type': None, 'media_id': None, 'caption': None}
        content_type = message.content_type
        if content_type == 'text':
            rules_data['text'] = message.text
        elif content_type in ['photo', 'video', 'animation', 'document']:
            rules_data['media_type'] = content_type
            rules_data['caption'] = message.caption
            if content_type == 'photo':
                rules_data['media_id'] = message.photo[-1].file_id
            elif content_type == 'video':
                rules_data['media_id'] = message.video.file_id
            elif content_type == 'animation':
                rules_data['media_id'] = message.animation.file_id
            elif content_type == 'document':
                rules_data['media_id'] = message.document.file_id
        db[chat_id]['rules'] = rules_data
        save_group_data(chat_id)
        bot.reply_to(message, "تم تحديث قوانين المجموعة بنجاح.")
    elif state == 'awaiting_forbidden_add':
        words_to_add = [word.strip().lower() for word in message.text.split('\n') if word.strip()]
        current_words = db[chat_id]['forbidden_words']['words']
        added_count = 0
        for word in words_to_add:
            if word not in current_words:
                current_words.append(word)
                added_count += 1
        save_group_data(chat_id)
        bot.reply_to(message, f"تمت إضافة {added_count} كلمة/كلمات جديدة إلى القائمة.")
    elif state == 'awaiting_forbidden_remove':
        words_to_remove = [word.strip().lower() for word in message.text.split('\n') if word.strip()]
        current_words = db[chat_id]['forbidden_words']['words']
        removed_count = 0
        for word in words_to_remove:
            if word in current_words:
                try:
                    current_words.remove(word)
                    removed_count += 1
                except ValueError:
                    pass
        save_group_data(chat_id)
        bot.reply_to(message, f"تمت إزالة {removed_count} كلمة/كلمات من القائمة.")
    elif state == 'awaiting_repeating_message':
        content_type = message.content_type
        msg_data = {'caption': message.caption}
        if content_type == 'text':
            msg_data['type'] = 'text'
            msg_data['content'] = message.text
        elif content_type == 'photo':
            msg_data['type'] = 'photo'
            msg_data['content'] = message.photo[-1].file_id
        elif content_type == 'video':
            msg_data['type'] = 'video'
            msg_data['content'] = message.video.file_id
        elif content_type == 'animation':
            msg_data['type'] = 'animation'
            msg_data['content'] = message.animation.file_id
        elif content_type == 'document':
            msg_data['type'] = 'document'
            msg_data['content'] = message.document.file_id
        elif content_type == 'audio':
            msg_data['type'] = 'audio'
            msg_data['content'] = message.audio.file_id
        elif content_type == 'voice':
            msg_data['type'] = 'voice'
            msg_data['content'] = message.voice.file_id
        if 'type' in msg_data:
            db[chat_id]['repeating_messages']['messages'].append(msg_data)
            save_group_data(chat_id)
            bot.reply_to(message, "تمت إضافة الرسالة بنجاح إلى قائمة التكرار.")
        else:
            bot.reply_to(message, "نوع الرسالة هذا غير مدعوم للتكرار.")
    elif state == 'awaiting_personal_trigger':
        trigger = message.text.strip()
        if trigger:
            user_states[user_id] = {'state': 'awaiting_personal_response', 'chat_id': chat_id, 'trigger': trigger}
            bot.reply_to(message, f"الآن أرسل الرد الذي سيتم إرساله عند كتابة '<code>{trigger}</code>'.\nيمكن أن يكون نصاً، صورة، فيديو، إلخ.")
        else:
            bot.reply_to(message, "الكلمة غير صالحة. حاول مرة أخرى.")
    elif state == 'awaiting_personal_remove':
        trigger_to_remove = message.text.strip()
        if trigger_to_remove in db[chat_id]['personal_replies']:
            del db[chat_id]['personal_replies'][trigger_to_remove]
            save_group_data(chat_id)
            bot.reply_to(message, f"تمت إزالة الرد الخاص بالكلمة '<code>{trigger_to_remove}</code>' بنجاح.")
        else:
            bot.reply_to(message, "هذه الكلمة غير موجودة في قائمة الردود.")

@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice', 'animation', 'story', 'dice', 'game', 'contact', 'location', 'venue', 'video_note'])
def main_message_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if message.chat.type == 'private':
        return
    if admin_db.get('maintenance_mode') and user_id != DEVELOPER_ID:
        return
    if chat_id in admin_db.get('deactivated_groups', []):
        return
    if message.text and message.text.strip() == "القوانين":
        show_rules(message)
        return
    init_chat_db(chat_id)
    if not db[chat_id].get('activated', False):
        return
    if user_id:
        user_id_str = str(user_id)
        counts = db[chat_id].setdefault('message_counts', {})
        counts[user_id_str] = counts.get(user_id_str, 0) + 1
        save_group_data(chat_id)
    if message.sender_chat and message.sender_chat.type == 'channel':
        incognito_settings = db[chat_id].get('incognito_users', {})
        if incognito_settings.get('enabled'):
            channel_username = f"@{message.sender_chat.username}" if message.sender_chat.username else None
            if channel_username and channel_username in incognito_settings.get('exceptions', []):
                return
            if incognito_settings.get('delete_messages', False):
                try:
                    bot.delete_message(chat_id, message.message_id)
                except Exception:
                    pass
            try:
                bot.ban_chat_sender_chat(chat_id, sender_chat_id=message.sender_chat.id)
            except Exception:
                pass
            return
    if not user_id:
        return
    if not is_admin(chat_id, user_id):
        is_subscribed, unsubscribed_channels = check_subscription(user_id)
        if not is_subscribed:
            markup = types.InlineKeyboardMarkup()
            for ch in unsubscribed_channels:
                username = ch.get('username')
                if not username:
                    try:
                        chat_info = bot.get_chat(ch['id'])
                        username = chat_info.username
                    except:
                        username = str(ch['id'])
                url = f"https://t.me/{username}"
                markup.add(types.InlineKeyboardButton(f"اشترك في @{username}", url=url))
            bot.reply_to(message, "عليك الاشتراك في القنوات التالية أولاً لاستخدام البوت:", reply_markup=markup)
            try:
                bot.delete_message(chat_id, message.message_id)
            except:
                pass
            return
    if message.text:
        bot_name_settings = db[chat_id].get('bot_name_settings', {})
        bot_name = bot_name_settings.get('name')
        if bot_name_settings.get('enabled') and bot_name:
            text_lower = message.text.lower()
            if bot_name.lower() in text_lower or 'بوت' in text_lower:
                user_mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
                reply_text = random.choice(bot_name_settings['replies'])
                bot.reply_to(message, f"{reply_text} {user_mention}")
                return
        personal_replies = db[chat_id].get('personal_replies', {})
        for trigger, reply_data in personal_replies.items():
            if trigger.lower() in message.text.lower():
                send_stored_message(chat_id, reply_data)
                return
    if has_full_bot_access(chat_id, user_id):
        return
    if db[chat_id].get('night_mode', {}).get('is_active_now', False):
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        return
    captcha_settings = db[chat_id].get('captcha', {})
    if user_id in UNVERIFIED_USERS.get(chat_id, {}):
        user_info = UNVERIFIED_USERS[chat_id][user_id]
        if captcha_settings.get('mode') == 'math' and user_info.get('answer') is not None:
            is_correct = False
            try:
                if message.text and int(message.text) == user_info['answer']:
                    is_correct = True
                    bot.restrict_chat_member(chat_id, user_id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                    bot.send_message(chat_id, f"✅ تم التحقق بنجاح، {message.from_user.first_name}!")
                    bot.delete_message(chat_id, user_info['message_id'])
                    if captcha_settings.get('delete_service_message') and 'service_message_id' in user_info:
                         bot.delete_message(chat_id, user_info['service_message_id'])
                    del UNVERIFIED_USERS[chat_id][user_id]
            except (ValueError, TypeError):
                pass
            if not is_correct:
                user_info['attempts_left'] -= 1
                if user_info['attempts_left'] > 0:
                    bot.reply_to(message, f"إجابة خاطئة. لديك {user_info['attempts_left']} محاولات متبقية.")
                else:
                    bot.reply_to(message, "لقد استنفدت جميع محاولاتك.")
                    punishment = captcha_settings.get('punishment', 'mute')
                    execute_punishment(chat_id, user_id, punishment, message.from_user.first_name)
                    bot.delete_message(chat_id, user_info['message_id'])
                    if captcha_settings.get('delete_service_message') and 'service_message_id' in user_info:
                        bot.delete_message(chat_id, user_info['service_message_id'])
                    del UNVERIFIED_USERS[chat_id][user_id]
            try: bot.delete_message(chat_id, message.message_id)
            except: pass
        else:
            try: bot.delete_message(chat_id, message.message_id)
            except: pass
        return
    if message.text:
        repeat_settings = db[chat_id].get('anti_repeat', {})
        if repeat_settings.get('enabled'):
            last_msg = last_message_tracker.get((chat_id, user_id))
            if last_msg and last_msg == message.text:
                punishment = repeat_settings.get('punishment', 'mute')
                reason = "تكرار نفس الرسالة"
                apply_punishment(chat_id, user_id, punishment, message.from_user.first_name, reason)
                try:
                    bot.delete_message(chat_id, message.message_id)
                except:
                    pass
                last_message_tracker.pop((chat_id, user_id), None)
                return
            last_message_tracker[(chat_id, user_id)] = message.text
        long_msg_settings = db[chat_id].get('long_messages', {})
        if long_msg_settings.get('enabled'):
            msg_len = len(message.text)
            min_len = long_msg_settings.get('min_chars', 0)
            max_len = long_msg_settings.get('max_chars', 0)
            violation = False
            reason = ""
            if min_len > 0 and msg_len < min_len:
                violation = True
                reason = f"إرسال رسالة أقصر من الحد الأدنى ({min_len} حرف)"
            if max_len > 0 and msg_len > max_len:
                violation = True
                reason = f"إرسال رسالة أطول من الحد الأقصى ({max_len} حرف)"
            if violation:
                if long_msg_settings.get('delete', False):
                    try: bot.delete_message(chat_id, message.message_id)
                    except: pass
                punishment = long_msg_settings.get('punishment', 'none')
                apply_punishment(chat_id, user_id, punishment, message.from_user.first_name, reason)
                return
        forbidden_settings = db[chat_id].get('forbidden_words', {})
        punishment = forbidden_settings.get('punishment', 'none')
        if punishment != 'none':
            words_to_check = forbidden_settings.get('words', [])
            message_text_lower = message.text.lower()
            for word in words_to_check:
                if word in message_text_lower:
                    if forbidden_settings.get('delete_message', False):
                        try:
                            bot.delete_message(chat_id, message.message_id)
                        except Exception as e:
                            print(f"Could not delete forbidden word message: {e}")
                    reason = "استخدام كلمة محظورة"
                    if punishment == 'warn':
                        handle_warning(chat_id, user_id, message.from_user.first_name, reason)
                    else:
                        execute_punishment(chat_id, user_id, punishment, message.from_user.first_name)
                    return
    if check_and_apply_restrictions(message.from_user, chat_id, message=message):
        return
    media_restrictions = db[chat_id].get('media_restrictions', {})
    for key, setting in media_restrictions.items():
        punishment = setting.get('punishment', 'none')
        if punishment == 'none':
            continue
        detection = MEDIA_TYPES_MAP[key][1]
        triggered = False
        if 'content_types' in detection and message.content_type in detection['content_types']:
            triggered = True
        elif 'func' in detection and detection['func'](message):
            triggered = True
        elif 'entity' in detection:
            all_entities = (message.entities or []) + (message.caption_entities or [])
            if all_entities:
                for entity in all_entities:
                    if entity.type == detection['entity']:
                        triggered = True
                        break
        if triggered:
            if punishment != "none":
                try:
                    bot.delete_message(chat_id, message.message_id)
                except: pass
            if punishment == 'warn':
                reason = f"إرسال وسائط ممنوعة ({MEDIA_TYPES_MAP[key][0]})"
                handle_warning(chat_id, user_id, message.from_user.first_name, reason)
            elif punishment != 'delete':
                execute_punishment(chat_id, user_id, punishment, message.from_user.first_name)
            return
    flood_settings = db[chat_id]['antiflood']
    if flood_settings['enabled']:
        now = time.time()
        user_timestamps = FLOOD_TRACKER[chat_id][user_id]
        user_timestamps.append(now)
        recent_messages = [t for t in user_timestamps if now - t < flood_settings['seconds']]
        if len(recent_messages) >= flood_settings['messages']:
            punishment = flood_settings['punishment']
            duration = flood_settings.get('duration', 0)
            if punishment != 'delete' and punishment != 'none':
                execute_punishment(chat_id, user_id, punishment, message.from_user.first_name, duration)
            if flood_settings['delete_messages']:
                try:
                    bot.delete_message(chat_id, message.message_id)
                except:
                    pass
            FLOOD_TRACKER[chat_id][user_id].clear()
            return
    if message.text:
        alphabet_settings = db[chat_id].get('alphabets', {})
        for lang_key, regex in ALPHABET_REGEX.items():
            lang_settings = alphabet_settings.get(lang_key, {})
            punishment = lang_settings.get('punishment', 'none')
            if punishment != 'none' and regex.search(message.text):
                if lang_settings.get('delete', False):
                    try: bot.delete_message(chat_id, message.message_id)
                    except: pass
                if punishment == 'warn':
                    reason = f"استخدام حروف {LANG_MAP.get(lang_key, lang_key)} بدون تصريح"
                    handle_warning(chat_id, user_id, message.from_user.first_name, reason)
                else:
                    execute_punishment(chat_id, user_id, punishment, message.from_user.first_name)
                break

if __name__ == '__main__':
    night_scheduler_thread = threading.Thread(target=night_mode_scheduler, daemon=True)
    night_scheduler_thread.start()
    repeating_msg_scheduler_thread = threading.Thread(target=repeating_messages_scheduler, daemon=True)
    repeating_msg_scheduler_thread.start()
    print(f"Bot @{bot.get_me().username} is running...")
    bot.polling(none_stop=True)
