# ====================================================
# حقوق النشر © بوت صانع | جميع الحقوق محفوظة
# صُنع بواسطة بوت المصنع الرسمي
# ====================================================

import asyncio
import json
import logging
import os
import random
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Callable, Coroutine
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from functools import wraps
import aiofiles

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    User, Chat, Message, CallbackQuery, ChatPermissions
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters,
    ChatMemberHandler, ConversationHandler
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ArchitecturalError(Exception):
    pass

class PermissionDenied(ArchitecturalError):
    pass

class ResourceNotFound(ArchitecturalError):
    pass

class Version:
    MAJOR = 0
    MINOR = 1
    PATCH = 0
    
    @classmethod
    def get(cls):
        return f"{cls.MAJOR}.{cls.MINOR}.{cls.PATCH}"

class WhiteWolfManifest:
    ENTITY = "الذئب الأبيض"
    PORTAL = "@j49_c"
    REALM_ALPHA = "@bshshshkk"
    REALM_BETA = "@BQBOOB"
    SIGNATURE = f"☠️ {ENTITY} | Telegram: {PORTAL}"
    ECHOES = [REALM_ALPHA, REALM_BETA]

@dataclass
class WolfMetadata:
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    signature: str = field(default_factory=lambda: WhiteWolfManifest.SIGNATURE)
    version: str = field(default_factory=lambda: Version.get())
    
    def to_dict(self):
        return asdict(self)

class CrypticDialect:
    GREETINGS = [
        "طَلع الفجر وياك، لكن احذر الظل الي يمشي وراك",
        "يا هلا بـ الغريب، شلون الريح اليوم؟",
        "دخلت البوابة... ما في رجوع"
    ]
    
    FAREWELLS = [
        "الظلام يجيك من ورى الكواليس",
        "روح بسلام، بس ترا العيون تراقب",
        "مع السلامة، لا تنسى إن الحيطان لها آذان"
    ]
    
    WARNINGS = [
        "يا بطل، خفف من الهوس شوي",
        "ترا الدنيا دوارة، لا تستعجل",
        "الصبر مفتاح الفرج، بس الفرج بعيد"
    ]
    
    SUCCESS = [
        "تمام التمام، مثل ما يبيه الذيب",
        "نفذت الخطة ببراعة، صح عليك",
        "الظلام يشهد إنك سويتها"
    ]
    
    ERRORS = [
        "صار غلط، بس الذئب ما يموت بسهولة",
        "في شي مو رايح، جرب مرة ثانية وانت هادي",
        "الحظ خانك، بس الصبر زين"
    ]

    @classmethod
    def whisper(cls, category: str) -> str:
        pool = getattr(cls, category, cls.WARNINGS)
        return random.choice(pool)

class SecurityMixin:
    @staticmethod
    def validate_identity(user_id: int, authorized: List[int]) -> bool:
        return user_id in authorized
    
    @staticmethod
    def timestamp_obfuscate() -> str:
        return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

class DataPersistenceMixin:
    def __init__(self):
        self._vault = "white_wolf_vault.json"
        self._cache: Dict[str, Any] = {}
        self._load_vault()
    
    def _load_vault(self):
        try:
            if os.path.exists(self._vault):
                with open(self._vault, 'r', encoding='utf-8') as stream:
                    self._cache = json.load(stream)
            else:
                self._cache = {
                    "souls": {},
                    "territories": {},
                    "ledger": {},
                    "manifest": WolfMetadata().to_dict()
                }
                self._commit()
        except Exception as e:
            logger.error(f"Vault corruption: {e}")
            self._cache = {"souls": {}, "territories": {}, "ledger": {}}
    
    def _commit(self):
        try:
            with open(self._vault, 'w', encoding='utf-8') as stream:
                json.dump(self._cache, stream, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Commit failed: {e}")
    
    def _extract(self, path: str, default: Any = None) -> Any:
        keys = path.split('.')
        current = self._cache
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def _inject(self, path: str, value: Any):
        keys = path.split('.')
        current = self._cache
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self._commit()

class EconomyEngine:
    def __init__(self, persistence: DataPersistenceMixin):
        self._persistence = persistence
        self._rates = {
            "daily_base": 1000,
            "bonus_multiplier": 1.5,
            "tax": 0.05
        }
    
    def mint_currency(self, soul_id: int, amount: int, reason: str = "unknown"):
        current = self._persistence._extract(f"souls.{soul_id}.wallet", 0)
        self._persistence._inject(f"souls.{soul_id}.wallet", current + amount)
        self._log_transaction(soul_id, amount, reason, "credit")
    
    def burn_currency(self, soul_id: int, amount: int, reason: str = "unknown") -> bool:
        current = self._persistence._extract(f"souls.{soul_id}.wallet", 0)
        if current < amount:
            return False
        self._persistence._inject(f"souls.{soul_id}.wallet", current - amount)
        self._log_transaction(soul_id, amount, reason, "debit")
        return True
    
    def get_balance(self, soul_id: int) -> int:
        return self._persistence._extract(f"souls.{soul_id}.wallet", 0)
    
    def _log_transaction(self, soul_id: int, amount: int, reason: str, tx_type: str):
        tx_id = f"TX-{SecurityMixin.timestamp_obfuscate()}-{random.randint(1000, 9999)}"
        self._persistence._inject(f"ledger.{tx_id}", {
            "soul": soul_id,
            "amount": amount,
            "type": tx_type,
            "reason": reason,
            "timestamp": SecurityMixin.timestamp_obfuscate()
        })

class GamingProtocol:
    def __init__(self, economy: EconomyEngine):
        self._economy = economy
        self._active_sessions: Dict[int, Dict] = {}
        self._riddles = [
            {"puzzle": "شي يمشي بلا رجول، ويتكلم بلا لسان", "solution": "الساعة", "reward": 500},
            {"puzzle": "أنا ابن الماء، فإن تركوني في الماء متُّ", "solution": "الثلج", "reward": 400},
            {"puzzle": "رأسه في السماء ورجله في الأرض", "solution": "النخلة", "reward": 600},
            {"puzzle": "ما هو الشيء الذي كلما أخذت منه كبُر؟", "solution": "الحفرة", "reward": 700}
        ]
        self._math_challenges = [
            {"question": "15 × 15 + 25", "answer": "250", "reward": 300},
            {"question": "√144 × 3", "answer": "36", "reward": 350},
            {"question": "2^8 - 56", "answer": "200", "reward": 400}
        ]
    
    def summon_riddle(self, territory_id: int) -> Optional[Dict]:
        if territory_id in self._active_sessions:
            return None
        riddle = random.choice(self._riddles)
        self._active_sessions[territory_id] = {
            "type": "riddle",
            "data": riddle,
            "attempts": 0,
            "max_attempts": 3,
            "born_at": datetime.now()
        }
        return riddle
    
    def summon_math(self, territory_id: int) -> Optional[Dict]:
        if territory_id in self._active_sessions:
            return None
        challenge = random.choice(self._math_challenges)
        self._active_sessions[territory_id] = {
            "type": "math",
            "data": challenge,
            "attempts": 0,
            "max_attempts": 3,
            "born_at": datetime.now()
        }
        return challenge
    
    def resolve_attempt(self, territory_id: int, attempt: str, soul_id: int) -> Dict:
        if territory_id not in self._active_sessions:
            return {"status": "expired", "message": "اللعبة انتهت يا ذكي"}
        
        session = self._active_sessions[territory_id]
        session["attempts"] += 1
        
        correct_answer = session["data"]["solution"] if session["type"] == "riddle" else session["data"]["answer"]
        
        if attempt.lower().strip() == correct_answer.lower():
            reward = session["data"]["reward"]
            self._economy.mint_currency(soul_id, reward, f"game_{session['type']}_won")
            del self._active_sessions[territory_id]
            return {
                "status": "victory",
                "reward": reward,
                "message": CrypticDialect.whisper("SUCCESS")
            }
        
        if session["attempts"] >= session["max_attempts"]:
            del self._active_sessions[territory_id]
            return {
                "status": "defeat",
                "message": "خسرت يا بطل، جرب حظك مرة ثانية"
            }
        
        return {
            "status": "retry",
            "remaining": session["max_attempts"] - session["attempts"],
            "message": CrypticDialect.whisper("WARNINGS")
        }
    
    def purge_session(self, territory_id: int):
        if territory_id in self._active_sessions:
            del self._active_sessions[territory_id]

class AgriculturalComplex:
    def __init__(self, economy: EconomyEngine):
        self._economy = economy
        self._seeds = {
            "shadow_potato": {"name": "بطاطس الظلام", "cost": 100, "growth": 300, "yield": 250},
            "golden_corn": {"name": "ذرة الفراعنة", "cost": 200, "growth": 600, "yield": 500},
            "moon_strawberry": {"name": "فراولة القمر", "cost": 500, "growth": 900, "yield": 1200}
        }
    
    def plant_crop(self, soul_id: int, crop_type: str) -> Dict:
        if crop_type not in self._seeds:
            return {"success": False, "message": "هالمحصول ما يزرع عندنا"}
        
        seed = self._seeds[crop_type]
        balance = self._economy.get_balance(soul_id)
        
        if balance < seed["cost"]:
            return {"success": False, "message": "فلوسك ما تكفي، روح اشتغل شوي"}
        
        active_plots = self._get_active_plots(soul_id)
        if len(active_plots) >= 5:
            return {"success": False, "message": "حقولك ممتلية، احصد شي قبل لا تزرع"}
        
        self._economy.burn_currency(soul_id, seed["cost"], "planting")
        plot_id = f"plot_{soul_id}_{SecurityMixin.timestamp_obfuscate()}_{random.randint(1000, 9999)}"
        
        self._economy._persistence._inject(f"souls.{soul_id}.farm.{plot_id}", {
            "crop": crop_type,
            "planted_at": SecurityMixin.timestamp_obfuscate(),
            "ready_at": (datetime.now() + timedelta(seconds=seed["growth"])).isoformat(),
            "yield_value": seed["yield"]
        })
        
        return {
            "success": True,
            "message": f"زرعت {seed['name']}، ارجع بعد {seed['growth']//60} دقيقة"
        }
    
    def harvest_all(self, soul_id: int) -> Dict:
        plots = self._get_active_plots(soul_id)
        if not plots:
            return {"success": False, "message": "ما في شي تنحصد يا الفلاح"}
        
        total_yield = 0
        harvested = 0
        now = datetime.now()
        
        for plot_id, plot_data in list(plots.items()):
            ready_time = datetime.fromisoformat(plot_data["ready_at"])
            if now >= ready_time:
                total_yield += plot_data["yield_value"]
                self._economy._persistence._inject(f"souls.{soul_id}.farm.{plot_id}", None)
                harvested += 1
        
        if harvested == 0:
            return {"success": False, "message": "محاصيلك لسه صغار، استنى شوي"}
        
        self._economy.mint_currency(soul_id, total_yield, "harvest")
        return {
            "success": True,
            "harvested": harvested,
            "total": total_yield,
            "message": f"حصدت {harvested} محاصيل وجبت {total_yield} درهم"
        }
    
    def _get_active_plots(self, soul_id: int) -> Dict:
        return self._economy._persistence._extract(f"souls.{soul_id}.farm", {})

class AuthorizationDecorator:
    @staticmethod
    def require_admin(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not update.effective_user or not update.effective_chat:
                return
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            if user_id in self._alphas:
                return await handler(self, update, context, *args, **kwargs)
            
            try:
                member = await context.bot.get_chat_member(chat_id, user_id)
                if member.status in ["administrator", "creator"]:
                    return await handler(self, update, context, *args, **kwargs)
                else:
                    await update.message.reply_text("هالأمر بس للكبار، انقلع")
            except Exception:
                pass
        return wrapper
    
    @staticmethod
    def require_private(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if update.effective_chat and update.effective_chat.type == "private":
                return await handler(self, update, context, *args, **kwargs)
            else:
                if update.message:
                    await update.message.reply_text("هالأمر بس في الخاص، تعال هناك")
        return wrapper

class ButtonStyler:
    """Simple button factory — no KeyboardButtonStyle needed (standard python-telegram-bot)."""

    @staticmethod
    def forge(text: str, callback: str, style=None, emoji_icon=None) -> InlineKeyboardButton:
        return InlineKeyboardButton(text, callback_data=callback)

    @staticmethod
    def forge_danger(text: str, callback: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text, callback_data=callback)

    @staticmethod
    def forge_success(text: str, callback: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text, callback_data=callback)

    @staticmethod
    def forge_primary(text: str, callback: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text, callback_data=callback)

class WhiteWolfCore(SecurityMixin, DataPersistenceMixin):
    def __init__(self):
        super().__init__()
        self._token = "{TOKEN}"
        self._alphas = [{OWNER_ID}]
        self._app = Application.builder().token(self._token).build()
        self._economy = EconomyEngine(self)
        self._gaming = GamingProtocol(self._economy)
        self._farming = AgriculturalComplex(self._economy)
        self._active_territories: Dict[int, bool] = {}
        
        self._initialize_routes()
    
    def _initialize_routes(self):
        self._app.add_handler(CommandHandler("start", self._route_start))
        self._app.add_handler(CommandHandler("help", self._route_help))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._route_text))
        self._app.add_handler(CallbackQueryHandler(self._route_callback))
        self._app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self._route_new_soul))
        self._app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self._route_lost_soul))
        self._app.add_error_handler(self._route_error)
    
    async def _route_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.effective_chat:
            return
        
        user = update.effective_user
        chat = update.effective_chat
        
        self._enlist_soul(user)
        
        if chat.type == "private":
            await self._initiate_private_greeting(update, user)
        else:
            if not self._is_territory_active(chat.id):
                await self._request_territory_activation(update, chat)
    
    async def _initiate_private_greeting(self, update: Update, user: User):
        greeting = random.choice(CrypticDialect.GREETINGS)
        text = f"""╭─◇「 بداية الرحيل 」◇─╮
│
├ ⚡ {greeting}
├ 👤 نورتنا يا: {user.first_name}
├ 🔮 الإصدار: {Version.get()}
├ 🐺 {WhiteWolfManifest.SIGNATURE}
│
├ 📜 الوصايا الثلاث:
├ 1️⃣ أضفني لمجموعتك كـ "مشرف"
├ 2️⃣ اكتب "فعل" في المجموعة
├ 3️⃣ استمتع بالظلام المليء بالذهب
│
├ 🌐 القنوات:
├ {WhiteWolfManifest.REALM_ALPHA}
├ {WhiteWolfManifest.REALM_BETA}
│
╰─◇「 المالك الوحيد: {WhiteWolfManifest.PORTAL} 」◇─╯"""
        
        keyboard = [
            [ButtonStyler.forge_success("➕ اضفني لمجموعتك", "add_to_group")],
            [ButtonStyler.forge_primary("📢 القناة الأولى", "channel_alpha"),
             ButtonStyler.forge_primary("📢 القناة الثانية", "channel_beta")],
            [ButtonStyler.forge_danger("💰 فلوسي", "wallet_status"),
             ButtonStyler.forge("🎮 العب", "games_hub", ButtonStyler.PRIMARY)]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _request_territory_activation(self, update: Update, chat: Chat):
        text = f"""╭─◇「 إذن الدخول 」◇─╮
│
├ ⚠️ أنا نايم هنا، ما أشتغل إلا إذا فعلتني
├ 📝 اكتب "فعل" إذا كنت من المشرفين
├ 🔒 أوامري بس للي له كِلمة
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        if update.message:
            await update.message.reply_text(text)
    
    async def _route_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        
        text = f"""╭─◇「 شريعة الذئب 」◇─╮
│
├ 💀 الأوامر العامة:
├ هويتي - تعرف على نفسك
├ فلوسي - كم معك من الدراهم
├ راتب - استلم مرتبك اليومي
├ العاب - قائمة التسلية
├ مزرعتي - حقولك الخاصة
├ فعل - تفعيل البوت (للمشرفين)
│
├ 🎮 الألعاب:
├ لغز - فزّر مخك
├ رياضة - حسابات سريعة
├ صراحة - جاوب ولا تنحرج
├ تحدي - جرأة أو جبان
│
├ 🚜 المزرعة:
├ ازرع [المحصول] - اشتغل يا فلاح
├ احصد - جني ثمارك
├ سوق - تسوق للبذور
│
├ 👑 خاص بالمشرفين:
├ اكتم - كتم عضو
├ اطرد - طرد فوري
├ نظف - تنظيف الرسائل
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        await update.message.reply_text(text)
    
    async def _route_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text or not update.effective_user or not update.effective_chat:
            return
        
        text = update.message.text.strip()
        user = update.effective_user
        chat = update.effective_chat
        
        self._record_presence(user.id, chat.id)
        
        if chat.type != "private" and not self._is_territory_active(chat.id):
            if text in ["فعل", "تفعيل", "شغل"]:
                await self._activate_territory(update, user, chat)
            return
        
        await self._process_command(update, text, user, chat)
    
    async def _process_command(self, update: Update, text: str, user: User, chat: Chat):
        text_lower = text.lower()
        
        command_map = {
            r'^هويتي$': self._cmd_identity,
            r'^فلوسي$|^رصيدي$': self._cmd_wallet,
            r'^راتب$|^يوميه$': self._cmd_daily,
            r'^العاب$|^الالعاب$': self._cmd_games_menu,
            r'^لغز$': self._cmd_riddle,
            r'^رياضة$|^رياضه$': self._cmd_math,
            r'^صراحة$|^صراحه$': self._cmd_truth,
            r'^تحدي$|^جرأة$|^جرأه$': self._cmd_dare,
            r'^مزرعتي$|^مزرعة$': self._cmd_farm,
            r'^ازرع\s+(\w+)$': self._cmd_plant,
            r'^احصد$': self._cmd_harvest,
            r'^سوق$': self._cmd_shop,
        }
        
        for pattern, handler in command_map.items():
            match = re.match(pattern, text_lower)
            if match:
                if pattern.startswith(r'^ازرع'):
                    await handler(update, user, match.group(1))
                else:
                    await handler(update, user)
                return
        
        if await self._is_guardian(user.id, chat.id):
            await self._process_guardian_commands(update, text, user, chat)
    
    async def _cmd_identity(self, update: Update, user: User):
        soul_data = self._extract(f"souls.{user.id}", {})
        wallet = self._economy.get_balance(user.id)
        messages = soul_data.get("messages", 0)
        join_date = soul_data.get("born", "مجهول")
        
        rank = "عادي"
        if user.id in self._alphas:
            rank = "الذئب الأبيض"
        elif wallet > 50000:
            rank = "ثري"
        elif wallet > 10000:
            rank = "ميسور"
        
        text = f"""╭─◇「 هوية الروح 」◇─╮
│
├ 🏷️ الاسم: {user.first_name}
├ 🆔 الرقم: {user.id}
├ 👤 الرتبة: {rank}
├ 💰 الرصيد: {wallet:,} درهم
├ 💬 الرسائل: {messages}
├ 📅 الانضمام: {join_date[:10] if len(join_date) > 10 else join_date}
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [
            [ButtonStyler.forge_primary("💰 البنك", "bank_hub"),
             ButtonStyler.forge_success("🎮 العب", "games_hub")]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _cmd_wallet(self, update: Update, user: User):
        balance = self._economy.get_balance(user.id)
        text = f"""╭─◇「 خزانتك 」◇─╮
│
├ 💰 {balance:,} درهم
├ 📊 الحالة: {"ميسور" if balance > 10000 else "فقير" if balance < 1000 else "متوسط"}
│
├ 💡 تقدر تستثمر أو تزرع وتكبر فلوسك
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [
            [ButtonStyler.forge_success("📊 استثمر", "invest_dialog"),
             ButtonStyler.forge_danger("💸 حوّل فلوس", "transfer_dialog")]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _cmd_daily(self, update: Update, user: User):
        today = datetime.now().strftime('%Y-%m-%d')
        last = self._extract(f"souls.{user.id}.last_salary")
        
        if last == today:
            text = "⏰ خذيت راتبك اليوم، روح نام واجهز لبكرة"
            if update.message:
                await update.message.reply_text(text)
            return
        
        base = 1000
        bonus = min(self._extract(f"souls.{user.id}.messages", 0) * 2, 2000)
        total = base + bonus
        
        self._economy.mint_currency(user.id, total, "daily_salary")
        self._inject(f"souls.{user.id}.last_salary", today)
        
        text = f"""╭─◇「 الراتب اليومي 」◇─╮
│
├ ✅ خذيت: {total:,} درهم
├ 💵 الأساسي: {base:,}
├ 🎁 البونص: {bonus:,}
├ 💰 صار معك: {self._economy.get_balance(user.id):,}
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        if update.message:
            await update.message.reply_text(text)
    
    async def _cmd_games_menu(self, update: Update, user: User):
        text = f"""╭─◇「 ساحة اللعب 」◇─╮
│
├ 🧩 لغز - أحجيات تفجر مخك
├ 🔢 رياضة - حسابات بسرعة البرق
├ 💭 صراحة - اسأل واجب
├ ⚡ تحدي - جرأة أو انسحب
│
├ 🎯 اختر لعبتك واربح ذهب
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [
            [ButtonStyler.forge_primary("🧩 لغز", "play_riddle"),
             ButtonStyler.forge_success("🔢 رياضة", "play_math")],
            [ButtonStyler.forge_danger("💭 صراحة", "play_truth"),
             ButtonStyler.forge("⚡ تحدي", "play_dare", ButtonStyler.DANGER)]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _cmd_riddle(self, update: Update, user: User):
        if not update.effective_chat:
            return
        
        riddle = self._gaming.summon_riddle(update.effective_chat.id)
        if not riddle:
            if update.message:
                await update.message.reply_text("في لعبة شغالة، خلصها الأول")
            return
        
        text = f"""╭─◇「 اللغز 」◇─╮
│
├ ❓ {riddle['puzzle']}
│
├ ⏱️ عندك 3 محاولات
├ 💰 الجائزة: {riddle['reward']} درهم
│
╰─◇「 جاوب بسرعة 」◇─╯"""
        
        if update.message:
            await update.message.reply_text(text)
        
        asyncio.create_task(self._game_timer(update.effective_chat.id, 60))
    
    async def _cmd_math(self, update: Update, user: User):
        if not update.effective_chat:
            return
        
        challenge = self._gaming.summon_math(update.effective_chat.id)
        if not challenge:
            if update.message:
                await update.message.reply_text("في لعبة شغالة، خلصها الأول")
            return
        
        text = f"""╭─◇「 معادلة 」◇─╮
│
├ 🔢 {challenge['question']} = ؟
│
├ ⏱️ عندك 3 محاولات
├ 💰 الجائزة: {challenge['reward']} درهم
│
╰─◇「 احسبها صح 」◇─╯"""
        
        if update.message:
            await update.message.reply_text(text)
        
        asyncio.create_task(self._game_timer(update.effective_chat.id, 45))
    
    async def _cmd_truth(self, update: Update, user: User):
        questions = [
            "آخر كذبة قلتها وش كانت؟",
            "أكثر شخص تكرهه في المجموعة؟",
            "وش أكثر شي ندمان عليه؟",
            "لو ترجع بالزمن وين تروح؟",
            "سرك الي ما يعرفه أحد؟"
        ]
        question = random.choice(questions)
        
        text = f"""╭─◇「 صراحة 」◇─╮
│
├ 💭 {question}
│
├ 😈 قول الحق ولا أبلعك الظلام
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        if update.message:
            await update.message.reply_text(text)
            self._economy.mint_currency(user.id, 50, "truth_participation")
    
    async def _cmd_dare(self, update: Update, user: User):
        dares = [
            "اكتب منشور في حسابك: أنا جبان وأحب الظلام",
            "ارسل صورة وجهك الحقيقية للمجموعة",
            "اتصل على أول واحد في قائمة جهاتك وقله أحبك",
            "اكتب اسمك مقلوب لمدة ساعة",
            "اعترف لـ @someone إنك تقلده"
        ]
        dare = random.choice(dares)
        
        text = f"""╭─◇「 تحدي 」◇─╮
│
├ ⚡ {dare}
│
├ 🎁 إذا نفذتها: 200 درهم
├ 💀 إذا جبت العيد: الكل يضحك عليك
│
╰─◇「 تقدر تهرب بس هذا مو ذوق الذئاب 」◇─╯"""
        
        if update.message:
            await update.message.reply_text(text)
            self._economy.mint_currency(user.id, 100, "dare_accepted")
    
    async def _cmd_farm(self, update: Update, user: User):
        plots = self._farming._get_active_plots(user.id)
        total_plots = len(plots)
        ready = sum(1 for p in plots.values() if datetime.now() >= datetime.fromisoformat(p["ready_at"]))
        
        text = f"""╭─◇「 مزرعتك 」◇─╮
│
├ 🌱 الحقول: {total_plots}/5
├ ✅ جاهزة للحصاد: {ready}
├ ⏳ تحت النمو: {total_plots - ready}
│
├ 🚜 ازرع شي جديد أو احصد اللي نضج
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [
            [ButtonStyler.forge_success("🌱 ازرع بطاطس", "plant_potato"),
             ButtonStyler.forge_primary("🌽 ازرع ذرة", "plant_corn")],
            [ButtonStyler.forge_danger("🍓 ازرع فراولة", "plant_strawberry"),
             ButtonStyler.forge_success("🌾 احصد كل شي", "harvest_all")]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _cmd_plant(self, update: Update, user: User, crop_type: str):
        result = self._farming.plant_crop(user.id, f"shadow_{crop_type}" if crop_type == "بطاطس" else f"golden_{crop_type}" if crop_type == "ذرة" else f"moon_{crop_type}")
        if update.message:
            await update.message.reply_text(result["message"])
    
    async def _cmd_harvest(self, update: Update, user: User):
        result = self._farming.harvest_all(user.id)
        if update.message:
            await update.message.reply_text(result["message"])
    
    async def _cmd_shop(self, update: Update, user: User):
        text = f"""╭─◇「 سوق البذور 」◇─╮
│
├ 🥔 بطاطس الظلام - 100 درهم
├ 🌽 ذرة الفراعنة - 200 درهم  
├ 🍓 فراولة القمر - 500 درهم
│
├ 💰 رصيدك: {self._economy.get_balance(user.id):,} درهم
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [
            [ButtonStyler.forge_success("اشتري بطاطس", "buy_potato"),
             ButtonStyler.forge_primary("اشتري ذرة", "buy_corn")],
            [ButtonStyler.forge_danger("اشتري فراولة", "buy_strawberry")]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _route_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query or not query.data:
            return
        
        await query.answer()
        data = query.data
        user = query.from_user
        
        if not user:
            return
        
        if data == "wallet_status":
            await self._show_wallet_callback(query, user)
        elif data == "games_hub":
            await self._show_games_callback(query, user)
        elif data == "add_to_group":
            await query.edit_message_text("روح للمجموعة واضفني من هناك يا ذكي")
        elif data == "channel_alpha":
            await query.edit_message_text(f"روح للقناة: {WhiteWolfManifest.REALM_ALPHA}")
        elif data == "channel_beta":
            await query.edit_message_text(f"روح للقناة: {WhiteWolfManifest.REALM_BETA}")
        elif data == "bank_hub":
            await self._show_bank_callback(query, user)
        elif data == "invest_dialog":
            await self._show_invest_callback(query, user)
        elif data == "transfer_dialog":
            await self._show_transfer_callback(query, user)
        elif data.startswith("play_"):
            await self._handle_game_callback(query, user, data.replace("play_", ""))
        elif data.startswith("plant_"):
            crop = data.replace("plant_", "")
            await self._handle_plant_callback(query, user, crop)
        elif data == "harvest_all":
            await self._handle_harvest_callback(query, user)
        elif data.startswith("buy_"):
            await self._handle_buy_callback(query, user, data.replace("buy_", ""))
    
    async def _show_wallet_callback(self, query: CallbackQuery, user: User):
        balance = self._economy.get_balance(user.id)
        text = f"""╭─◇「 خزانتك 」◇─╮
│
├ 💰 {balance:,} درهم
├ 📊 الحالة: {"ميسور" if balance > 10000 else "فقير" if balance < 1000 else "متوسط"}
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [
            [ButtonStyler.forge_success("📊 استثمر", "invest_dialog"),
             ButtonStyler.forge_danger("💸 حوّل", "transfer_dialog")],
            [ButtonStyler.forge_primary("🔙 رجوع", "back_main")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _show_games_callback(self, query: CallbackQuery, user: User):
        text = f"""╭─◇「 ساحة اللعب 」◇─╮
│
├ اختر لعبتك يا {user.first_name}
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [
            [ButtonStyler.forge_primary("🧩 لغز", "play_riddle"),
             ButtonStyler.forge_success("🔢 رياضة", "play_math")],
            [ButtonStyler.forge_danger("💭 صراحة", "play_truth"),
             ButtonStyler.forge("⚡ تحدي", "play_dare", ButtonStyler.DANGER)],
            [ButtonStyler.forge_primary("🔙 رجوع", "back_main")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _show_bank_callback(self, query: CallbackQuery, user: User):
        balance = self._economy.get_balance(user.id)
        text = f"""╭─◇「 البنك 」◇─╮
│
├ 💰 رصيدك: {balance:,} درهم
├ 📈 الفائدة: 5% يومياً
│
├ اختار الخدمة:
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [
            [ButtonStyler.forge_success("استثمار", "invest_dialog"),
             ButtonStyler.forge_primary("تحويل", "transfer_dialog"),
             ButtonStyler.forge_danger("قرض", "loan_dialog")],
            [ButtonStyler.forge_primary("🔙 رجوع", "back_main")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _show_invest_callback(self, query: CallbackQuery, user: User):
        text = f"""╭─◇「 الاستثمار 」◇─╮
│
├ 💡 اكتب في الشات:
├ استثمر [المبلغ]
│
├ مثال: استثمر 5000
│
├ 📈 العائد: 5% يومياً
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [[ButtonStyler.forge_primary("🔙 رجوع", "bank_hub")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _show_transfer_callback(self, query: CallbackQuery, user: User):
        text = f"""╭─◇「 التحويل 」◇─╮
│
├ 💡 اكتب في الشات:
├ حول [المبلغ] @المستخدم
│
├ مثال: حول 1000 @username
│
├ ⚠️ العمولة: 1%
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [[ButtonStyler.forge_primary("🔙 رجوع", "bank_hub")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _handle_game_callback(self, query: CallbackQuery, user: User, game_type: str):
        if game_type == "riddle":
            await query.edit_message_text("اكتب 'لغز' في الشات عشان تلعب")
        elif game_type == "math":
            await query.edit_message_text("اكتب 'رياضة' في الشات عشان تلعب")
        elif game_type == "truth":
            await query.edit_message_text("اكتب 'صراحة' في الشات")
        elif game_type == "dare":
            await query.edit_message_text("اكتب 'تحدي' في الشات")
    
    async def _handle_plant_callback(self, query: CallbackQuery, user: User, crop: str):
        result = self._farming.plant_crop(user.id, f"shadow_{crop}" if crop == "potato" else f"golden_{crop}" if crop == "corn" else f"moon_{crop}")
        await query.edit_message_text(result["message"])
    
    async def _handle_harvest_callback(self, query: CallbackQuery, user: User):
        result = self._farming.harvest_all(user.id)
        await query.edit_message_text(result["message"])
    
    async def _handle_buy_callback(self, query: CallbackQuery, user: User, item: str):
        await query.edit_message_text(f"اكتب 'ازرع {item}' في الشات عشان تشتري وتزرع")
    
    async def _route_new_soul(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                continue
            
            greeting = random.choice(CrypticDialect.GREETINGS)
            text = f"""╭─◇「 عضو جديد 」◇─╮
│
├ 🎉 {greeting}
├ 👋 أهلاً {member.first_name}
├ 🎁 مكافأة الترحيب: 500 درهم
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
            
            keyboard = [
                [ButtonStyler.forge_success("📜 الأوامر", "help_menu"),
                 ButtonStyler.forge_primary("💰 فلوسي", "wallet_status")]
            ]
            
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            self._economy.mint_currency(member.id, 500, "welcome_bonus")
    
    async def _route_lost_soul(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.left_chat_member:
            return
        
        member = update.message.left_chat_member
        farewell = random.choice(CrypticDialect.FAREWELLS)
        
        text = f"""╭─◇「 غياب 」◇─╮
│
├ 👋 {member.first_name} غادر
├ 💀 {farewell}
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        await update.message.reply_text(text)
    
    async def _route_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        if update and update.message:
            await update.message.reply_text("صار غلط في النظام، جرب بعدين")
    
    def _enlist_soul(self, user: User):
        if str(user.id) not in self._cache.get("souls", {}):
            self._inject(f"souls.{user.id}", {
                "id": user.id,
                "first_name": user.first_name,
                "username": user.username,
                "born": SecurityMixin.timestamp_obfuscate(),
                "wallet": 1000,
                "messages": 0
            })
    
    def _record_presence(self, soul_id: int, territory_id: int):
        current = self._extract(f"souls.{soul_id}.messages", 0)
        self._inject(f"souls.{soul_id}.messages", current + 1)
    
    def _is_territory_active(self, territory_id: int) -> bool:
        return self._extract(f"territories.{territory_id}.activated", False)
    
    async def _activate_territory(self, update: Update, user: User, chat: Chat):
        if not await self._is_guardian(user.id, chat.id):
            if update.message:
                await update.message.reply_text("بس المشرفين يقدرون يفعلوني")
            return
        
        self._inject(f"territories.{chat.id}", {
            "activated": True,
            "title": chat.title,
            "activated_by": user.id,
            "activated_at": SecurityMixin.timestamp_obfuscate()
        })
        
        text = f"""╭─◇「 تفعيل ناجح 」◇─╮
│
├ ✅ تم تفعيل البوت في {chat.title}
├ 👤 المفعل: {user.first_name}
├ 📅 {SecurityMixin.timestamp_obfuscate()}
│
├ 🚀 جرب الأوامر:
├ هويتي - فلوسي - العاب
│
╰─◇「 {WhiteWolfManifest.SIGNATURE} 」◇─╯"""
        
        keyboard = [
            [ButtonStyler.forge_success("📜 قائمة الأوامر", "help_menu"),
             ButtonStyler.forge_primary("🎮 العب الآن", "games_hub")]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _is_guardian(self, user_id: int, chat_id: int) -> bool:
        if user_id in self._alphas:
            return True
        
        try:
            member = await self._app.bot.get_chat_member(chat_id, user_id)
            return member.status in ["administrator", "creator"]
        except:
            return False
    
    async def _game_timer(self, territory_id: int, seconds: int):
        await asyncio.sleep(seconds)
        self._gaming.purge_session(territory_id)
    
    async def _process_guardian_commands(self, update: Update, text: str, user: User, chat: Chat):
        pass
    
    def run(self):
        logger.info(f"🐺 {WhiteWolfManifest.ENTITY} v{Version.get()} يستيقظ...")
        self._cache["awakened"] = SecurityMixin.timestamp_obfuscate()
        self._commit()
        
        self._app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

if __name__ == "__main__":
    try:
        core = WhiteWolfCore()
        core.run()
    except KeyboardInterrupt:
        logger.info("🛑 توقف بالأمر")
    except Exception as e:
        logger.error(f"💥 سقط الذئب: {e}")
