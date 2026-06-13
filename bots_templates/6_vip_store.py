# ====================================================
# حقوق النشر © بوت صانع | جميع الحقوق محفوظة
# صُنع بواسطة بوت المصنع الرسمي
# ====================================================

import telebot
from telebot import types
import sqlite3
from datetime import datetime

bot = telebot.TeleBot("{TOKEN}")
OWNER_ID = {OWNER_ID}






def init_db():
    conn = sqlite3.connect("store.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products 
                 (name TEXT PRIMARY KEY, price INTEGER, stock INTEGER, content TEXT, image_file_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS promo_codes 
                 (code TEXT PRIMARY KEY, points INTEGER, max_uses INTEGER, uses INTEGER DEFAULT 0, active INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS custom_buttons 
                 (button_name TEXT PRIMARY KEY, content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchases 
                 (purchase_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_name TEXT, content TEXT, image_file_id TEXT, 
                 FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('referral_points', '10')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('currency_name', 'نقاط')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('store_name', 'متجري')")
    try:
        c.execute("ALTER TABLE products ADD COLUMN content TEXT")
        c.execute("ALTER TABLE products ADD COLUMN image_file_id TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    return conn

db_conn = init_db()

def get_store_name():
    with db_conn:
        c = db_conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'store_name'")
        return c.fetchone()[0]

def get_currency_name():
    with db_conn:
        c = db_conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'currency_name'")
        return c.fetchone()[0]

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()
    currency = get_currency_name()
    store_name = get_store_name()
    try:
        with db_conn:
            c = db_conn.cursor()
            c.execute("SELECT value FROM settings WHERE key='referral_points'")
            referral_points = int(c.fetchone()[0])
            if len(args) > 1 and args[1].isdigit():
                referrer_id = int(args[1])
                if referrer_id != user_id:
                    c.execute("UPDATE users SET points = points + ?, referrals = referrals + 1 WHERE user_id = ?", 
                              (referral_points, referrer_id))
                    if c.rowcount > 0:
                        bot.send_message(referrer_id, f"**شكرا لدعوتك صديقا جديدا**\n**― تم اضافة {referral_points} {currency} الى رصيدك**", 
                                        parse_mode="Markdown")
            c.execute("INSERT OR IGNORE INTO users (user_id, points) VALUES (?, 0)", (user_id,))
            db_conn.commit()
        markup = get_main_menu(user_id)
        welcome_text = f"**اهلا بك في {store_name}**\n" \
                       f"**― تعليمات الاستخدام:**\n" \
                       f"**• المتجر**: استعرض المنتجات واشتر ما تريد\n" \
                       f"**• نقاطي**: تابع رصيدك من {currency}\n" \
                       f"**• دعوة**: ادع اصدقاءك لربح المزيد\n" \
                       f"**• مشترياتي**: راجع مشترياتك\n" \
                       f"**― اختر خيارا:**"
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, "**حدث خطا، حاول مرة اخرى**", reply_markup=get_main_menu(user_id), parse_mode="Markdown")
        print(f"Error in send_welcome: {e}")

@bot.message_handler(commands=['v'])
def owner_commands(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "**هذا الامر للمالك فقط، تواصل مع الدعم للمساعدة**", parse_mode="Markdown")
        return
    markup = get_owner_menu()
    bot.send_message(message.chat.id, get_owner_menu_text(), reply_markup=markup, parse_mode="Markdown")

def get_main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("› المتجر", callback_data="shop"),
        types.InlineKeyboardButton("› نقاطي", callback_data="points")
    )
    markup.add(
        types.InlineKeyboardButton("› الرصيد", callback_data="balance"),
        types.InlineKeyboardButton("› كود خصم", callback_data="promo")
    )
    markup.add(
        types.InlineKeyboardButton("› دعوة", callback_data="referral"),
        types.InlineKeyboardButton("› مشترياتي", callback_data="purchases")
    )
    markup.add(
        types.InlineKeyboardButton("› تعليمات", callback_data="help")
    )
    with db_conn:
        c = db_conn.cursor()
        c.execute("SELECT button_name FROM custom_buttons")
        custom_buttons = c.fetchall()
        for (button_name,) in custom_buttons:
            markup.add(types.InlineKeyboardButton(f"› {button_name}", callback_data=f"custom_{button_name}"))
    return markup

def get_owner_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("› اضافة منتج", callback_data="add_product"),
        types.InlineKeyboardButton("› انشاء كود", callback_data="create_code")
    )
    markup.add(
        types.InlineKeyboardButton("› المنتجات", callback_data="list_products"),
        types.InlineKeyboardButton("› المستخدمون", callback_data="user_count")
    )
    markup.add(
        types.InlineKeyboardButton("› رسالة عامة", callback_data="broadcast"),
        types.InlineKeyboardButton("› نقاط الدعوة", callback_data="set_ref_points")
    )
    markup.add(
        types.InlineKeyboardButton("› زر مخصص", callback_data="add_custom_button"),
        types.InlineKeyboardButton("› حذف زر", callback_data="delete_custom_button")
    )
    markup.add(
        types.InlineKeyboardButton("› العملة", callback_data="change_currency"),
        types.InlineKeyboardButton("› اسم المتجر", callback_data="change_store_name")
    )
    return markup

def get_main_menu_text():
    store_name = get_store_name()
    currency = get_currency_name()
    return f"**اهلا بك في {store_name}**\n" \
           f"**― تعليمات الاستخدام:**\n" \
           f"**• المتجر**: استعرض المنتجات واشتر ما تريد\n" \
           f"**• نقاطي**: تابع رصيدك من {currency}\n" \
           f"**• دعوة**: ادع اصدقاءك لربح المزيد\n" \
           f"**• مشترياتي**: راجع مشترياتك\n" \

def get_owner_menu_text():
    store_name = get_store_name()
    currency = get_currency_name()
    return f"**لوحة تحكم {store_name}**\n" \
           f"**› اضافة منتج**: اضف منتجا جديدا\n" \
           f"**› انشاء كود**: انشئ كود خصم\n" \
           f"**› المنتجات**: ادارة المنتجات\n" \
           f"**› المستخدمون**: عدد المستخدمين\n" \
           f"**› رسالة عامة**: ارسل اعلانا\n" \
           f"**› نقاط الدعوة**: تعديل النقاط\n" \
           f"**› زر مخصص**: اضافة زر\n" \
           f"**› حذف زر**: ازالة زر مخصص\n" \
           f"**› العملة**: تغيير اسم {currency}\n" \
           f"**› اسم المتجر**: تعديل اسم {store_name}\n" \

@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    user_id = call.from_user.id
    chat_id = call.from_user.id
    message_id = call.message.message_id
    currency = get_currency_name()
    store_name = get_store_name()

    markup = types.InlineKeyboardMarkup(row_width=2)
    text = ""

    try:
        with db_conn:
            c = db_conn.cursor()

            if call.data == "shop":
                c.execute("SELECT name, price, stock FROM products")
                products = c.fetchall()
                text = f"**المنتجات المتوفرة في {store_name}:**"
                if not products:
                    text += f"\n**― لا توجد منتجات حاليا**"
                else:
                    for name, price, stock in products:
                        text += f"\n**› {name}** - **{price} {currency}** (**الكمية: {stock}**)"
                        markup.add(types.InlineKeyboardButton(f"شراء {name}", callback_data=f"buy_{name}"))
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="back"))

            elif call.data == "points":
                c.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
                points = c.fetchone()[0]
                text = f"**رصيدك الحالي:**\n**― {points} {currency}**"
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="back"))

            elif call.data == "balance":
                c.execute("SELECT points, referrals FROM users WHERE user_id = ?", (user_id,))
                points, refs = c.fetchone()
                text = f"**تفاصيل حسابك:**\n**› {currency}: {points}**\n**› المدعوون: {refs}**"
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="back"))

            elif call.data == "promo":
                text = f"**ادخل كود الخصم لاستبداله بـ {currency}:**"
                bot.register_next_step_handler_by_chat_id(chat_id, process_promo_code)
                bot.edit_message_text(text, chat_id, message_id, reply_markup=None, parse_mode="Markdown")
                return

            elif call.data == "referral":
                c.execute("SELECT value FROM settings WHERE key='referral_points'")
                referral_points = int(c.fetchone()[0])
                ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
                text = f"**رابط الدعوة الخاص بك:**\n**― `{ref_link}`**\n**› كل صديق ينضم يكسبك {referral_points} {currency}**"
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="back"))

            elif call.data == "purchases":
                c.execute("SELECT product_name, content, image_file_id FROM purchases WHERE user_id = ?", (user_id,))
                purchases = c.fetchall()
                text = f"**مشترياتك من {store_name}:**"
                if not purchases:
                    text += f"\n**― لم تقم بشراء اي منتجات بعد**"
                else:
                    for product_name, content, image_file_id in purchases:
                        text += f"\n**› {product_name}**"
                        markup.add(types.InlineKeyboardButton(product_name, callback_data=f"view_purchase_{product_name}"))
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="back"))

            elif call.data.startswith("view_purchase_"):
                product_name = call.data.replace("view_purchase_", "")
                c.execute("SELECT content, image_file_id FROM purchases WHERE user_id = ? AND product_name = ? LIMIT 1", (user_id, product_name))
                result = c.fetchone()
                if result:
                    content, image_file_id = result
                    if image_file_id:
                        bot.send_photo(chat_id, image_file_id, caption=f"**محتوى {product_name}:**\n**― {content}**", parse_mode="Markdown")
                    else:
                        bot.send_message(chat_id, f"**محتوى {product_name}:**\n**― {content}**", parse_mode="Markdown")
                return

            elif call.data == "help":
                text = f"**تعليمات استخدام {store_name}:**\n" \
                       f"**› المتجر**: استعرض المنتجات واشتر ما تريد\n" \
                       f"**› نقاطي**: تابع رصيدك من {currency}\n" \
                       f"**› دعوة**: ادع اصدقاءك لربح المزيد\n" \
                       f"**› مشترياتي**: راجع مشترياتك\n" \
                       f"**― للمساعدة، تواصل مع الدعم**"
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="back"))

            elif call.data == "add_product" and user_id == OWNER_ID:
                text = "**ادخل اسم المنتج الجديد:**"
                bot.register_next_step_handler_by_chat_id(chat_id, process_product_name)
                bot.edit_message_text(text, chat_id, message_id, reply_markup=None, parse_mode="Markdown")
                return

            elif call.data == "create_code" and user_id == OWNER_ID:
                text = "**ادخل اسم كود الخصم الجديد:**"
                bot.register_next_step_handler_by_chat_id(chat_id, process_code_name)
                bot.edit_message_text(text, chat_id, message_id, reply_markup=None, parse_mode="Markdown")
                return

            elif call.data == "list_products" and user_id == OWNER_ID:
                c.execute("SELECT name FROM products")
                products = c.fetchall()
                text = f"**المنتجات في {store_name}:**"
                if not products:
                    text += f"\n**― لا توجد منتجات حاليا**"
                else:
                    for (name,) in products:
                        text += f"\n**› {name}**"
                        markup.add(types.InlineKeyboardButton(f"حذف {name}", callback_data=f"delete_{name}"))
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="owner_back"))

            elif call.data == "user_count" and user_id == OWNER_ID:
                c.execute("SELECT COUNT(*) FROM users")
                count = c.fetchone()[0]
                text = f"**عدد المستخدمين في {store_name}:**\n**― {count}**"
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="owner_back"))

            elif call.data == "broadcast" and user_id == OWNER_ID:
                text = "**ادخل الرسالة لارسالها الى جميع المستخدمين:**"
                bot.register_next_step_handler_by_chat_id(chat_id, process_broadcast)
                bot.edit_message_text(text, chat_id, message_id, reply_markup=None, parse_mode="Markdown")
                return

            elif call.data == "set_ref_points" and user_id == OWNER_ID:
                c.execute("SELECT value FROM settings WHERE key='referral_points'")
                current_points = int(c.fetchone()[0])
                text = f"**نقاط الدعوة الحالية:**\n**― {current_points}**\n**› ادخل القيمة الجديدة:**"
                bot.register_next_step_handler_by_chat_id(chat_id, process_ref_points)
                bot.edit_message_text(text, chat_id, message_id, reply_markup=None, parse_mode="Markdown")
                return

            elif call.data == "add_custom_button" and user_id == OWNER_ID:
                text = "**ادخل اسم الزر المخصص الجديد:**"
                bot.register_next_step_handler_by_chat_id(chat_id, process_custom_button_name)
                bot.edit_message_text(text, chat_id, message_id, reply_markup=None, parse_mode="Markdown")
                return

            elif call.data == "delete_custom_button" and user_id == OWNER_ID:
                c.execute("SELECT button_name FROM custom_buttons")
                buttons = c.fetchall()
                text = f"**اختر زرا لحذفه:**"
                if not buttons:
                    text += f"\n**― لا توجد ازرار مخصصة في {store_name}**"
                else:
                    for (button_name,) in buttons:
                        text += f"\n**› {button_name}**"
                        markup.add(types.InlineKeyboardButton(f"حذف {button_name}", callback_data=f"del_custom_{button_name}"))
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="owner_back"))

            elif call.data == "change_currency" and user_id == OWNER_ID:
                text = f"**اسم العملة الحالي:**\n**― {currency}**\n**› ادخل الاسم الجديد:**"
                bot.register_next_step_handler_by_chat_id(chat_id, process_change_currency)
                bot.edit_message_text(text, chat_id, message_id, reply_markup=None, parse_mode="Markdown")
                return

            elif call.data == "change_store_name" and user_id == OWNER_ID:
                text = f"**اسم المتجر الحالي:**\n**― {store_name}**\n**› ادخل الاسم الجديد:**"
                bot.register_next_step_handler_by_chat_id(chat_id, process_change_store_name)
                bot.edit_message_text(text, chat_id, message_id, reply_markup=None, parse_mode="Markdown")
                return

            elif call.data.startswith("custom_"):
                button_name = call.data.replace("custom_", "")
                c.execute("SELECT content FROM custom_buttons WHERE button_name = ?", (button_name,))
                content = c.fetchone()[0]
                text = f"**محتوى الزر {button_name}:**\n**― {content}**"
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="back"))

            elif call.data.startswith("del_custom_") and user_id == OWNER_ID:
                button_name = call.data.replace("del_custom_", "")
                c.execute("DELETE FROM custom_buttons WHERE button_name = ?", (button_name,))
                db_conn.commit()
                text = f"**تم حذف الزر {button_name} بنجاح**"
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="owner_back"))

            elif call.data.startswith("buy_"):
                product = call.data.replace("buy_", "")
                c.execute("SELECT price, stock, content, image_file_id FROM products WHERE name = ?", (product,))
                result = c.fetchone()
                if not result:
                    text = f"**المنتج {product} غير موجود**"
                else:
                    price, stock, content, image_file_id = result
                    c.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
                    points = c.fetchone()[0]
                    if stock <= 0:
                        text = f"**نفدت كمية {product}**"
                    elif points < price:
                        text = f"**رصيدك غير كاف لشراء {product}**"
                    else:
                        c.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (price, user_id))
                        c.execute("UPDATE products SET stock = stock - 1 WHERE name = ?", (product,))
                        c.execute("INSERT INTO purchases (user_id, product_name, content, image_file_id) VALUES (?, ?, ?, ?)", 
                                  (user_id, product, content, image_file_id))
                        db_conn.commit()
                        if image_file_id:
                            bot.send_photo(chat_id, image_file_id, caption=f"**تم شراء {product} بنجاح**\n**› السعر: {price} {currency}**\n**› الوصف: {content}**\n**› رصيدك الجديد: {points - price} {currency}**", parse_mode="Markdown")
                        else:
                            bot.send_message(chat_id, f"**تم شراء {product} بنجاح**\n**› السعر: {price} {currency}**\n**› الوصف: {content}**\n**› رصيدك الجديد: {points - price} {currency}**", parse_mode="Markdown")
                        text = get_main_menu_text()
                    markup.add(types.InlineKeyboardButton("› رجوع", callback_data="back"))

            elif call.data.startswith("delete_") and user_id == OWNER_ID:
                product = call.data.replace("delete_", "")
                c.execute("DELETE FROM products WHERE name = ?", (product,))
                db_conn.commit()
                text = f"**تم حذف {product} من {store_name} بنجاح**"
                markup.add(types.InlineKeyboardButton("› رجوع", callback_data="owner_back"))

            elif call.data == "back":
                text = get_main_menu_text()
                markup = get_main_menu(user_id)

            elif call.data == "owner_back" and user_id == OWNER_ID:
                text = get_owner_menu_text()
                markup = get_owner_menu()

        if text:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text("**حدث خطا، حاول مرة اخرى**", chat_id, message_id, reply_markup=get_main_menu(user_id), parse_mode="Markdown")
        print(f"Error in handle_buttons: {e}")

def process_product_name(message):
    product_name = message.text
    bot.send_message(message.chat.id, "**ادخل سعر المنتج (رقم):**", parse_mode="Markdown")
    bot.register_next_step_handler(message, lambda m: process_product_price(m, product_name))

def process_product_price(message, product_name):
    try:
        price = int(message.text)
        bot.send_message(message.chat.id, "**ادخل الكمية المتوفرة (رقم):**", parse_mode="Markdown")
        bot.register_next_step_handler(message, lambda m: process_product_stock(m, product_name, price))
    except ValueError:
        bot.send_message(message.chat.id, "**السعر يجب ان يكون رقما، حاول مجددا**", parse_mode="Markdown")

def process_product_stock(message, product_name, price):
    try:
        stock = int(message.text)
        bot.send_message(message.chat.id, "**ادخل محتوى المنتج (نص او صورة مع نص):**", parse_mode="Markdown")
        bot.register_next_step_handler(message, lambda m: process_product_content(m, product_name, price, stock))
    except ValueError:
        bot.send_message(message.chat.id, "**الكمية يجب ان تكون رقما، حاول مجددا**", parse_mode="Markdown")

def process_product_content(message, product_name, price, stock):
    content = message.text or ""
    image_file_id = message.photo[-1].file_id if message.photo else None
    with db_conn:
        c = db_conn.cursor()
        c.execute("INSERT INTO products (name, price, stock, content, image_file_id) VALUES (?, ?, ?, ?, ?)", 
                  (product_name, price, stock, content, image_file_id))
        db_conn.commit()
    bot.send_message(message.chat.id, f"**تم اضافة {product_name} بنجاح**", parse_mode="Markdown")
    if image_file_id:
        bot.send_photo(message.chat.id, image_file_id, caption=f"**تم اضافة {product_name} مع الصورة**", parse_mode="Markdown")

def process_promo_code(message):
    code = message.text
    user_id = message.from_user.id
    currency = get_currency_name()
    with db_conn:
        c = db_conn.cursor()
        c.execute("SELECT points, max_uses, uses, active FROM promo_codes WHERE code = ?", (code,))
        result = c.fetchone()
        if result:
            points, max_uses, uses, active = result
            if not active:
                bot.send_message(message.chat.id, "**هذا الكود غير نشط حاليا**", parse_mode="Markdown")
            elif uses >= max_uses:
                bot.send_message(message.chat.id, "**تم استنفاد استخدامات هذا الكود**", parse_mode="Markdown")
            else:
                c.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
                c.execute("UPDATE promo_codes SET uses = uses + 1 WHERE code = ?", (code,))
                db_conn.commit()
                bot.send_message(message.chat.id, f"**تم استبدال الكود بـ {points} {currency} بنجاح**", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "**الكود غير صالح او مستخدم**", parse_mode="Markdown")

def process_code_name(message):
    code_name = message.text
    bot.send_message(message.chat.id, "**ادخل عدد النقاط للكود (رقم):**", parse_mode="Markdown")
    bot.register_next_step_handler(message, lambda m: process_code_points(m, code_name))

def process_code_points(message, code_name):
    try:
        points = int(message.text)
        bot.send_message(message.chat.id, "**ادخل الحد الاقصى للاستخدامات (رقم):**", parse_mode="Markdown")
        bot.register_next_step_handler(message, lambda m: process_code_max_uses(m, code_name, points))
    except ValueError:
        bot.send_message(message.chat.id, "**النقاط يجب ان تكون رقما، حاول مجددا**", parse_mode="Markdown")

def process_code_max_uses(message, code_name, points):
    try:
        max_uses = int(message.text)
        with db_conn:
            c = db_conn.cursor()
            c.execute("INSERT INTO promo_codes (code, points, max_uses) VALUES (?, ?, ?)", (code_name, points, max_uses))
            db_conn.commit()
        bot.send_message(message.chat.id, f"**تم انشاء الكود {code_name} بـ {points} {get_currency_name()} وحد اقصى {max_uses} استخدامات**", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "**الحد الاقصى يجب ان يكون رقما، حاول مجددا**", parse_mode="Markdown")
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, "**هذا الكود موجود بالفعل**", parse_mode="Markdown")

def process_ref_points(message):
    try:
        points = int(message.text)
        with db_conn:
            c = db_conn.cursor()
            c.execute("UPDATE settings SET value = ? WHERE key = 'referral_points'", (points,))
            db_conn.commit()
        bot.send_message(message.chat.id, f"**تم تعديل نقاط الدعوة الى {points} لكل دعوة**", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "**ادخل رقما صحيحا**", parse_mode="Markdown")

def process_broadcast(message):
    broadcast_msg = message.text
    with db_conn:
        c = db_conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = c.fetchall()
        for (user_id,) in users:
            try:
                if message.photo:
                    bot.send_photo(user_id, message.photo[-1].file_id, caption=f"**{broadcast_msg}**", parse_mode="Markdown")
                else:
                    bot.send_message(user_id, f"**{broadcast_msg}**", parse_mode="Markdown")
            except:
                pass
    bot.send_message(message.chat.id, "**تم ارسال الرسالة الى جميع المستخدمين بنجاح**", parse_mode="Markdown")

def process_custom_button_name(message):
    button_name = message.text
    bot.send_message(message.chat.id, "**ادخل محتوى الزر (نص او وصف):**", parse_mode="Markdown")
    bot.register_next_step_handler(message, lambda m: process_custom_button_content(m, button_name))

def process_custom_button_content(message, button_name):
    content = message.text
    with db_conn:
        c = db_conn.cursor()
        c.execute("INSERT INTO custom_buttons (button_name, content) VALUES (?, ?)", (button_name, content))
        db_conn.commit()
    bot.send_message(message.chat.id, f"**تم اضافة الزر {button_name} بنجاح**\n**› المحتوى: {content}**", parse_mode="Markdown")

def process_change_currency(message):
    new_currency = message.text
    with db_conn:
        c = db_conn.cursor()
        c.execute("UPDATE settings SET value = ? WHERE key = 'currency_name'", (new_currency,))
        db_conn.commit()
    bot.send_message(message.chat.id, f"**تم تغيير اسم العملة الى {new_currency} بنجاح**", parse_mode="Markdown")

def process_change_store_name(message):
    new_store_name = message.text
    with db_conn:
        c = db_conn.cursor()
        c.execute("UPDATE settings SET value = ? WHERE key = 'store_name'", (new_store_name,))
        db_conn.commit()
    bot.send_message(message.chat.id, f"**تم تغيير اسم المتجر الى {new_store_name} بنجاح**", parse_mode="Markdown")


bot.remove_webhook()
print(f"البوت جاهز - {datetime.now()}")
bot.polling()
