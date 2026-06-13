# ====================================================
# حقوق النشر © بوت صانع | جميع الحقوق محفوظة
# صُنع بواسطة بوت المصنع الرسمي
# ====================================================

#الملف اول مرا واول شخص ينزله BBBBYB2 يمنع منعا باتأ بيعه  تم تنزيله  مجانأ


import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, ChatMember
import uuid
import re
import random

API_TOKEN = '{TOKEN}'
bot = telebot.TeleBot(API_TOKEN)

user_states = {}
user_temp_data = {}

bound_channels = {}

active_roulettes = {}

banned_from_creator_roulettes = {}

ROULETTE_TEXT_PROMPT = (
    "أرسل كليشة السحب\n\n"
    "1 - للتشويش: <code>&lt;tg-spoiler&gt;&lt;/tg-spoiler&gt;</code>\n"
    "<tg-spoiler>مثال</tg-spoiler>\n\n"
    "2 - للتعريض: <code>&lt;b&gt;&lt;/b&gt;</code>\n"
    "<b>مثال</b>\n\n"
    "3 - لجعل النص مائل: <code>&lt;i&gt;&lt;/i&gt;</code>\n"
    "<i>مثال</i>\n\n"
    "4 - للاقتباس: <code>&lt;blockquote&gt;&lt;/blockquote&gt;</code>\n"
    "<blockquote>مثال</blockquote>\n\n"
    "🚫 رجاءً عدم إرسال روابط نهائياً"
)

CHANNEL_BINDING_INSTRUCTIONS = (
    "1️⃣ أضف البوت كمشرف في قناتك.\n"
    "2️⃣ قم بإعادة توجيه أي رسالة من قناتك إلى البوت.\n\n"
    "📌 ملاحظة:\n"
    "جميع المشرفين الآخرين في القناة سيتمكنون أيضًا من استخدام البوت بعد إضافته."
)

CONDITIONAL_CHANNEL_QUESTION = "هل تريد إضافة قناة شرط؟\n\nعند إضافة قناة شرط لن يتمكن أحد من المشاركة في السحب قبل الانضمام لقناة الشرط."
SEND_CONDITIONAL_CHANNEL_LINK = "أرسل رابط القناة الشرطية (مثال: @YourChannel / https://t.me/YourChannel)"

NOT_YOUR_COMMAND_MSG = "❗ هذا الأمر مخصص لمنشئ الروليت فقط."

def main_menu_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎯 إنشاء روليت", callback_data="create_roulette"))
    kb.add(InlineKeyboardButton("🔗 ربط قناة", callback_data="bind_main_channel"),
           InlineKeyboardButton("✖️ فصل القناة", callback_data="disconnect_main_channel"))
    kb.add(InlineKeyboardButton("🔔 ذكرني إذا فزت", callback_data="remind_me_global_info"))
    return kb

def channel_binding_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📥 أضفني إلى قناتك", url=f"https://t.me/{bot.get_me().username}?startgroup=true"),
           InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main_menu"))
    return kb

def roulette_creation_options_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎨 تعديل الكليشة", callback_data="choose_style_instructions"))
    kb.add(InlineKeyboardButton("➕ إضافة قناة شرط", callback_data="prompt_conditional_channel"))
    kb.add(InlineKeyboardButton("⏭️ تخطي", callback_data="skip_conditional_channel"))
    return kb

def conditional_channel_choice_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔗 إضافة رابط قناة", callback_data="send_conditional_channel_link_prompt"))
    kb.add(InlineKeyboardButton("⏭️ تخطي", callback_data="skip_conditional_channel"))
    return kb

def get_channel_roulette_markup(roulette_id: str, is_active: bool):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎁 المشاركة في السحب", callback_data=f"join_roulette_{roulette_id}"))
    kb.add(InlineKeyboardButton("🔔 ذكرني إذا فزت", callback_data=f"remind_me_roulette_{roulette_id}"))
    kb.add(InlineKeyboardButton("▶️ تشغيل المشاركة" if not is_active else "⏸️ إيقاف المشاركة",
                                callback_data=f"toggle_participation_{roulette_id}"),
           InlineKeyboardButton("🏁 ابدأ السحب", callback_data=f"start_draw_{roulette_id}"))
    kb.add(InlineKeyboardButton("📊 عرض المشاركين", callback_data=f"view_participants_{roulette_id}"))
    return kb

def creator_exclude_kb(roulette_id: str, participant_id: int):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ استبعاد هذا المشارك", callback_data=f"exclude_participant_{roulette_id}_{participant_id}"))
    return kb

def is_channel_member(channel_id, user_id):
    try:
        member = bot.get_chat_member(channel_id, user_id)
        return member.status not in ['left', 'kicked']
    except Exception:
        return False

def get_channel_info_from_link(link: str):
    match_username = re.match(r"^(?:https?://t\.me/)?@?([a-zA-Z0-9_]+)$", link)
    if match_username:
        return "@" + match_username.group(1)
    return None

def update_roulette_message(roulette_id: str):
    r = active_roulettes.get(roulette_id)
    if not r:
        return

    try:
        participants_count = len(r['participants'])
        updated_text = f"{r['text']}\n\n👥 عدد المشاركين: {participants_count}"
        if not r['active']:
            updated_text += "\n⛔ المشاركة متوقفة حالياً."
        if r['winners']:
            winners_usernames = []
            for winner_id in r['winners']:
                try:
                    winner_info = bot.get_chat(winner_id)
                    winners_usernames.append(f"@{winner_info.username}" if winner_info.username else f"المستخدم {winner_id}")
                except Exception:
                    winners_usernames.append(f"المستخدم {winner_id}")
            updated_text += "\n\n🏆 الفائزون:\n" + "\n".join(winners_usernames)

        bot.edit_message_text(
            chat_id=r['main_channel_id'],
            message_id=r['channel_message_id'],
            text=updated_text,
            parse_mode="HTML",
            reply_markup=get_channel_roulette_markup(roulette_id, r['active'])
        )
    except Exception:
        pass

@bot.message_handler(commands=['start'])
def start_cmd(message: Message):
    user_states.pop(message.from_user.id, None)
    user_temp_data.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "👋 أهلاً بك في بوت الروليت!\nاضغط الزر أدناه لإنشاء روليت:",
        reply_markup=main_menu_kb()
    )

@bot.callback_query_handler(func=lambda c: c.data == "back_to_main_menu")
def handle_back_to_main_menu(call):
    user_states.pop(call.from_user.id, None)
    user_temp_data.pop(call.from_user.id, None)
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👋 أهلاً بك في بوت الروليت!\nاضغط الزر أدناه لإنشاء روليت:",
        reply_markup=main_menu_kb()
    )

@bot.callback_query_handler(func=lambda c: c.data == "create_roulette")
def handle_create_roulette_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    if user_id not in bound_channels:
        bot.send_message(call.message.chat.id, "❗ عليك ربط قناة أولاً قبل إنشاء الروليت.", reply_markup=channel_binding_kb())
        user_states[user_id] = 'awaiting_main_channel_forward'
        return

    user_temp_data[user_id] = {
        'main_channel_id': bound_channels[user_id]['channel_id'],
        'main_channel_username': bound_channels[user_id]['channel_username']
    }
    bot.send_message(call.message.chat.id, ROULETTE_TEXT_PROMPT, parse_mode="HTML")
    user_states[user_id] = 'awaiting_roulette_text'

@bot.callback_query_handler(func=lambda c: c.data == "bind_main_channel")
def handle_bind_main_channel_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, CHANNEL_BINDING_INSTRUCTIONS, reply_markup=channel_binding_kb())
    user_states[user_id] = 'awaiting_main_channel_forward'

@bot.callback_query_handler(func=lambda c: c.data == "disconnect_main_channel")
def handle_disconnect_main_channel_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    if user_id in bound_channels:
        del bound_channels[user_id]
        bot.send_message(call.message.chat.id, "✖️ تم فصل القناة بنجاح.")
    else:
        bot.send_message(call.message.chat.id, "❗ لم يتم تعيين قناة لك مسبقاً.")

@bot.callback_query_handler(func=lambda c: c.data == "choose_style_instructions")
def handle_choose_style_instructions(call):
    user_id = call.from_user.id
    if user_states.get(user_id) != 'awaiting_roulette_options_choice':
        bot.answer_callback_query(call.id, "❗ لا يوجد كليشة سحب حالية لتعديلها.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, ROULETTE_TEXT_PROMPT, parse_mode="HTML")
    user_states[user_id] = 'awaiting_roulette_text_edit'

@bot.callback_query_handler(func=lambda c: c.data == "prompt_conditional_channel")
def handle_prompt_conditional_channel(call):
    user_id = call.from_user.id
    if 'roulette_text' not in user_temp_data.get(user_id, {}):
        bot.answer_callback_query(call.id, "❗ الرجاء إدخال كليشة السحب أولاً.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, CONDITIONAL_CHANNEL_QUESTION, reply_markup=conditional_channel_choice_kb())
    user_states[user_id] = 'awaiting_conditional_channel_choice'

@bot.callback_query_handler(func=lambda c: c.data == "send_conditional_channel_link_prompt")
def handle_send_conditional_channel_link_prompt(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, SEND_CONDITIONAL_CHANNEL_LINK)
    user_states[user_id] = 'awaiting_conditional_channel_link'

@bot.callback_query_handler(func=lambda c: c.data == "skip_conditional_channel")
def handle_skip_conditional_channel(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    user_temp_data[user_id]['conditional_channel_id'] = None
    user_temp_data[user_id]['conditional_channel_username'] = None
    bot.send_message(call.message.chat.id, "📝 كم عدد الفائزين الذين تريد اختيارهم؟")
    user_states[user_id] = 'awaiting_winner_count'

@bot.callback_query_handler(func=lambda c: c.data.startswith("join_roulette_"))
def handle_join_roulette(call):
    roulette_id = call.data.split("_")[2]
    user_id = call.from_user.id
    username = call.from_user.username

    r = active_roulettes.get(roulette_id)
    if not r:
        bot.answer_callback_query(call.id, "❗ السحب غير موجود.", show_alert=True)
        return

    if user_id == r['creator_id']:
        bot.answer_callback_query(call.id, "لا يمكنك المشاركة في سحبك الخاص.", show_alert=True)
        return

    if not r['active']:
        bot.answer_callback_query(call.id, "⛔ المشاركة في هذا السحب متوقفة حالياً.", show_alert=True)
        return

    if user_id in r['participants']:
        bot.answer_callback_query(call.id, "✅ أنت مشارك بالفعل.", show_alert=True)
        return

    if user_id in banned_from_creator_roulettes.get(r['creator_id'], set()):
        bot.answer_callback_query(call.id, "🚫 تم استبعادك من سحوبات هذا المنشئ.", show_alert=True)
        return

    if r['conditional_channel_id']:
        try:
            if not is_channel_member(r['conditional_channel_id'], user_id):
                bot.answer_callback_query(call.id, "📛 عليك الاشتراك في القناة الشرطية أولاً للمشاركة.", show_alert=True)
                conditional_channel_username = r.get('conditional_channel_username')
                if conditional_channel_username:
                    link_to_send = f"https://t.me/{conditional_channel_username}"
                    bot.send_message(user_id, f"الرجاء الانضمام إلى القناة الشرطية للمشاركة في السحب:\n{link_to_send}")
                return
        except Exception:
            bot.answer_callback_query(call.id, "⚠️ خطأ في التحقق من الاشتراك في القناة الشرطية.", show_alert=True)
            return

    r['participants'].add(user_id)
    bot.answer_callback_query(call.id, "✅ تم تسجيل مشاركتك!")
    update_roulette_message(roulette_id)

    try:
        participant_info = f"👤 @{username}" if username else f"المستخدم {user_id}"
        bot.send_message(
            r['creator_id'],
            f"🎉 مشاركة جديدة في سحبك:\n\n{participant_info}\n🆔 {user_id}\n📊 عدد المشاركين الكلي: {len(r['participants'])}",
            reply_markup=creator_exclude_kb(roulette_id, user_id)
        )
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("toggle_participation_"))
def handle_toggle_participation(call):
    roulette_id = call.data.split("_")[2]
    user_id = call.from_user.id
    r = active_roulettes.get(roulette_id)

    if not r or user_id != r['creator_id']:
        bot.answer_callback_query(call.id, NOT_YOUR_COMMAND_MSG, show_alert=True)
        return

    bot.answer_callback_query(call.id)
    r['active'] = not r['active']
    status_text = "✅ تم تشغيل المشاركة." if r['active'] else "⛔ تم إيقاف المشاركة."
    update_roulette_message(roulette_id)
    bot.send_message(user_id, status_text)

@bot.callback_query_handler(func=lambda c: c.data.startswith("start_draw_"))
def handle_start_draw(call):
    roulette_id = call.data.split("_")[2]
    user_id = call.from_user.id
    r = active_roulettes.get(roulette_id)

    if not r or user_id != r['creator_id']:
        bot.answer_callback_query(call.id, NOT_YOUR_COMMAND_MSG, show_alert=True)
        return

    bot.answer_callback_query(call.id)
    if not r['participants']:
        bot.send_message(user_id, "❗ لا يوجد مشاركون في السحب.")
        return

    if r['winners']:
        bot.send_message(user_id, "❗ تم السحب مسبقاً لهذا الروليت.")
        return

    winners = random.sample(list(r['participants']), min(r['winners_count'], len(r['participants'])))
    r['winners'] = winners
    r['active'] = False

    update_roulette_message(roulette_id)
    bot.send_message(user_id, "✅ تم سحب الفائزين بنجاح!")

    for winner_id in winners:
        if winner_id in r['reminders']:
            try:
                bot.send_message(
                    winner_id,
                    f"🎉 تهانينا! لقد فزت في السحب:\n\n{r['text']}\n\n🏆 يمكنك التحقق من الفائزين في القناة: @{r['main_channel_username']}",
                    parse_mode="HTML"
                )
            except Exception:
                pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("exclude_participant_"))
def handle_exclude_participant(call):
    parts = call.data.split("_")
    roulette_id = parts[2]
    participant_id = int(parts[3])
    user_id = call.from_user.id
    r = active_roulettes.get(roulette_id)

    if not r or user_id != r['creator_id']:
        bot.answer_callback_query(call.id, NOT_YOUR_COMMAND_MSG, show_alert=True)
        return

    bot.answer_callback_query(call.id)
    if participant_id in r['participants']:
        r['participants'].discard(participant_id)
        banned_from_creator_roulettes.setdefault(r['creator_id'], set()).add(participant_id)
        update_roulette_message(roulette_id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ تم استبعاد المستخدم {participant_id} من هذا السحب وسحوباتك المستقبلية."
        )
    else:
        bot.send_message(user_id, "❗ هذا المشارك ليس في السحب أو تم استبعاده مسبقاً.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("remind_me_roulette_"))
def handle_remind_me_roulette(call):
    roulette_id = call.data.split("_")[3]
    user_id = call.from_user.id
    r = active_roulettes.get(roulette_id)

    if not r:
        bot.answer_callback_query(call.id, "❗ السحب غير موجود.", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    r['reminders'].add(user_id)
    bot.send_message(user_id, "🔔 سيتم إشعارك إذا فزت في هذا السحب!")

@bot.callback_query_handler(func=lambda c: c.data == "remind_me_global_info")
def handle_remind_me_global_info(call):
    bot.answer_callback_query(call.id, "للتذكير، يجب عليك تفعيل زر التذكير لكل سحب على حدة في رسالة السحب. هذا الزر يعرض معلومات فقط.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("view_participants_"))
def handle_view_participants(call):
    roulette_id = call.data.split("_")[2]
    user_id = call.from_user.id
    r = active_roulettes.get(roulette_id)

    if not r or user_id != r['creator_id']:
        bot.answer_callback_query(call.id, NOT_YOUR_COMMAND_MSG, show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    if not r['participants']:
        bot.send_message(user_id, "لا يوجد مشاركون حالياً في هذا السحب.")
        return
    
    participants_list = []
    for p_id in r['participants']:
        try:
            p_info = bot.get_chat(p_id)
            participants_list.append(f"👤 @{p_info.username} (ID: {p_id})")
        except Exception:
            participants_list.append(f"👤 المستخدم (ID: {p_id})")
    
    message_text = "قائمة المشاركين:\n" + "\n".join(participants_list)
    bot.send_message(user_id, message_text)

@bot.message_handler(content_types=['text', 'audio', 'photo', 'video', 'document'], func=lambda message: True)
def handle_messages_by_state(message: Message):
    user_id = message.from_user.id
    current_state = user_states.get(user_id)

    if current_state == 'awaiting_main_channel_forward':
        if message.forward_from_chat and message.forward_from_chat.type == "channel":
            channel = message.forward_from_chat
            try:
                bot_member = bot.get_chat_member(channel.id, bot.get_me().id)
                if bot_member.status not in ['administrator', 'creator']:
                    bot.send_message(message.chat.id, "❗ البوت ليس مشرفاً في هذه القناة. الرجاء إضافة البوت كمشرف وإعادة التوجيه.")
                    return
            except Exception:
                bot.send_message(message.chat.id, "❗ حدث خطأ أثناء التحقق من صلاحيات البوت في القناة. تأكد من أن القناة عامة وأن البوت مشرف.")
                return

            bound_channels[user_id] = {
                'channel_id': channel.id,
                'channel_username': channel.username
            }
            bot.send_message(message.chat.id, f"✅ تم ربط القناة: @{channel.username or channel.title}")
            user_states.pop(user_id, None)
        else:
            bot.send_message(message.chat.id, "❗ يرجى إعادة توجيه رسالة من قناة عامة أضفت فيها البوت كمشرف.")

    elif current_state == 'awaiting_roulette_text':
        user_temp_data[user_id]['roulette_text'] = message.text
        bot.send_message(message.chat.id, "✅ تم حفظ الكليشة، اختر أحد الخيارات:", reply_markup=roulette_creation_options_kb())
        user_states[user_id] = 'awaiting_roulette_options_choice'
    
    elif current_state == 'awaiting_roulette_text_edit':
        user_temp_data[user_id]['roulette_text'] = message.text
        bot.send_message(message.chat.id, "✅ تم تحديث الكليشة، اختر أحد الخيارات:", reply_markup=roulette_creation_options_kb())
        user_states[user_id] = 'awaiting_roulette_options_choice'

    elif current_state == 'awaiting_conditional_channel_link':
        channel_link = message.text.strip()
        channel_identifier = get_channel_info_from_link(channel_link)

        if not channel_identifier:
            bot.send_message(message.chat.id, "❗ الرابط غير صالح. الرجاء إرسال رابط قناة صحيح (مثال: @YourChannel أو https://t.me/YourChannel).")
            return

        try:
            chat = bot.get_chat(channel_identifier)
            if chat.type != 'channel':
                bot.send_message(message.chat.id, "❗ هذا ليس رابط قناة. الرجاء إرسال رابط قناة.")
                return

            user_temp_data[user_id]['conditional_channel_id'] = chat.id
            user_temp_data[user_id]['conditional_channel_username'] = chat.username
            bot.send_message(message.chat.id, f"✅ تم حفظ القناة الشرطية: @{chat.username or chat.title}")
            bot.send_message(message.chat.id, "📝 كم عدد الفائزين الذين تريد اختيارهم؟")
            user_states[user_id] = 'awaiting_winner_count'

        except telebot.apihelper.ApiTelegramException as e:
            if "chat not found" in str(e).lower() or "bad request" in str(e).lower():
                bot.send_message(message.chat.id, "❗ لم أتمكن من العثور على هذه القناة. تأكد من صحة الرابط وأن البوت مشرف فيها.")
            else:
                bot.send_message(message.chat.id, f"❗ حدث خطأ: {e}")
        except Exception:
            bot.send_message(message.chat.id, "❗ حدث خطأ غير متوقع أثناء التحقق من القناة.")

    elif current_state == 'awaiting_winner_count':
        try:
            count = int(message.text)
            if count <= 0:
                raise ValueError("Positive number required")
            user_temp_data[user_id]['winners_count'] = count
            publish_roulette(user_id)
            user_states.pop(user_id, None)
            user_temp_data.pop(user_id, None)
        except ValueError:
            bot.send_message(message.chat.id, "❗ الرجاء إرسال عدد صحيح موجب للفائزين.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❗ حدث خطأ أثناء نشر الروليت: {e}")
            user_states.pop(user_id, None)
            user_temp_data.pop(user_id, None)
    
    elif not message.text.startswith('/'):
        bot.send_message(message.chat.id, "❗ أمر غير مفهوم. الرجاء استخدام الأزرار أو /start للبدء.", reply_markup=main_menu_kb())

def publish_roulette(user_id: int):
    data = user_temp_data.get(user_id)
    if not data or 'roulette_text' not in data or 'main_channel_id' not in data or 'winners_count' not in data:
        bot.send_message(user_id, "❗ حدث خطأ: بيانات الروليت غير مكتملة. يرجى البدء من جديد عبر /start.")
        return

    roulette_id = str(uuid.uuid4())
    initial_text = f"{data['roulette_text']}\n\n👥 عدد المشاركين: 0"

    try:
        channel_message = bot.send_message(
            chat_id=data['main_channel_id'],
            text=initial_text,
            parse_mode="HTML",
            reply_markup=get_channel_roulette_markup(roulette_id, True)
        )

        bot.send_message(
            user_id,
            f"✅ تم نشر الروليت في القناة: @{data['main_channel_username']}\n\nتحكم بالروليت الخاص بك من خلال رسالة السحب في القناة (ID: {roulette_id})."
        )

        active_roulettes[roulette_id] = {
            'creator_id': user_id,
            'main_channel_id': data['main_channel_id'],
            'main_channel_username': data['main_channel_username'],
            'channel_message_id': channel_message.message_id,
            'text': data['roulette_text'],
            'conditional_channel_id': data.get('conditional_channel_id'),
            'conditional_channel_username': data.get('conditional_channel_username'),
            'winners_count': data['winners_count'],
            'participants': set(),
            'active': True,
            'winners': [],
            'reminders': set()
        }
        bot.send_message(user_id, "🎉 تم إنشاء الروليت بنجاح ونشره!")

    except telebot.apihelper.ApiTelegramException as e:
        bot.send_message(user_id, f"❗ فشل في النشر داخل القناة. تأكد أن البوت مشرف ولديه صلاحية إرسال الرسائل.\nالخطأ: {e}")
        active_roulettes.pop(roulette_id, None)
    except Exception as e:
        bot.send_message(user_id, f"❗ حدث خطأ غير متوقع أثناء نشر الروليت: {e}")
        active_roulettes.pop(roulette_id, None)

bot.infinity_polling()