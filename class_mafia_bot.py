from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import random
from collections import Counter, defaultdict

# ойыншылардың соңғы сөздерін сақтау үшін өзіміз жасаймыз
last_words = {}   # {user_id: (chat_id, task)}

# 🔑 BotFather берген токенді қой
TOKEN = "8498228551:AAGSzFHnY_0G3EjAfZiT3lDDUTEEn2oYhWY"

# /start командасы
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type

    if chat_type == "private":
        username = update.effective_user.username or update.effective_user.first_name

        keyboard = [
            [InlineKeyboardButton("🏫 Группаға қосу", url="https://t.me/kofee_menu_bot?startgroup=true")],
            [InlineKeyboardButton("🎭 Рөлдер", callback_data="roles_info")],
            [InlineKeyboardButton("👤 Профиль", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_photo(
            photo="https://bookshelfbattle.com/wp-content/uploads/2015/08/shutterstock_100111385.jpg",  # сурет сілтемесін өзің қой
            caption=(
                f"Сәлем, @{username}! 👋\n\n"
                "🏫 Бұл — мектеп стиліндегі *МАФИЯ* ойыны!\n\n"
                "Қалай ойнайды:\n"
                "1️⃣ Ботты топқа қос\n"
                "2️⃣ 🌙 Түнде – хулиган қимылдайды\n"
                "3️⃣ ☀️ Күндіз – дауыс беріп, хулигандарды табамыз!\n\n"
                "🎲 Күлкілі, қарапайым және қызық!"
            ),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "Бұл топта *МАФИЯ* ойынын ойнауға дайынбыз! 🎲\n\n/join басып қосылыңдар.",
            parse_mode="Markdown"
        )

# 🎭 Рөлдер түсіндірмесі
async def roles_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "🎭 Рөлдердің анықтамасы:\n\n"
        "😈 Хулиган (Мафия) – түнде құпия біреуді ойыннан шығарады\n"
        "🎒 Оқушы (Мирный) – күндіз талқылап, дауыс береді\n"
        "🏥 Медбике (Доктор) – бір адамды құтқара алады\n"
        "🎓 Директор (Шериф) – біреуін тексереді\n"
        "🧑‍🏫 Староста (Дон) – мафияны басқарады\n"
        "📚 Мұғалім (Мирный) – бейбіт ойыншы\n"
        "🤓 Сыныптас (Мирный) – бейбіт ойыншы"
    )
# 👤 Профиль карточкасы
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    username = user.username or user.first_name

    caption = (
        "✨ *МАФИЯ | Профиль карточкасы*\n\n"
        f"👤 Аты: *{user.first_name}*\n"
        f"🔗 Username: @{username}\n"
        f"🆔 ID: `{user.id}`\n\n"
        "🎲 *Статус:* Ойынға дайын!"
    )

    await query.message.reply_photo(
        photo="https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png",
        caption=caption,
        parse_mode="Markdown"
    )

# /join командасы – топта қолданушыларды тіркеу
players = set()  # қосылған ойыншыларды сақтау үшін

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        user = update.effective_user
        players.add(user.id)

        text = (
            "🎉 *Жаңа ойыншы қосылды!*\n\n"
            f"👤 {user.mention_html()} ойынды бастауға дайын!\n\n"
            f"👥 Қазіргі ойыншылар саны: *{len(players)}*\n\n"
            "⏳ Күтудеміз..."
        )

        keyboard = [
            [InlineKeyboardButton("🚀 Ойынды бастау", callback_data="start_game")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_html(
            text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("Бұл команда тек топта жұмыс істейді 🙂")

# 🚀 Ойынды бастау
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not players:
        await query.message.reply_text("😅 Әзірге ойыншылар жоқ!")
        return

    text = (
        "🎭 *Ойын басталды!*\n\n"
        f"Қатысушылар саны: *{len(players)}*\n"
        "Рөлдер жеке-жеке чатқа жіберіледі 🔒"
    )

    await query.message.reply_text(
        text,
        parse_mode="Markdown"
    )
# --- Осы кодты файлдың соңына қосу (жалғастыру) ---

import asyncio
import random
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

# ----- Ойын күйін сақтайтын кластар -----

class Player:
    def __init__(self, user_id: int, name: str, username: Optional[str]):
        self.id = user_id
        self.name = name
        self.username = username or name
        self.alive = True

    def mention(self):
        # HTML mention
        return f'<a href="tg://user?id={self.id}">{self.username}</a>'


class Game:
    """
    Бір топқа арналған ойын объектісі.
    """
    def __init__(self, chat_id: int, app):
        self.chat_id = chat_id
        self.app = app  # Application объектісін жібереміз, сонда bot арқылы хабарлама жібереді
        self.players: Dict[int, Player] = {}  # user_id -> Player
        self.roles: Dict[int, str] = {}  # user_id -> role
        self.alive: Set[int] = set()
        self.phase: str = "waiting"  # waiting | night | day | voting | ended
        self.mafia_votes: Dict[int, int] = {}  # mafia member id -> target id
        self.doctor_save: Optional[int] = None
        self.sheriff_check: Optional[int] = None
        self.day_votes: Dict[int, int] = {}  # voter id -> target id
        self.vote_message_id: Optional[int] = None
        self.night_task: Optional[asyncio.Task] = None
        self.day_task: Optional[asyncio.Task] = None

    # ---- Player management ----
    def add_player(self, user):
        if user.id in self.players:
            return False
        p = Player(user.id, user.first_name, getattr(user, "username", None))
        self.players[user.id] = p
        self.alive.add(user.id)
        return True

    def remove_player(self, user_id: int):
        if user_id in self.players:
            del self.players[user_id]
            self.alive.discard(user_id)
            self.roles.pop(user_id, None)
            return True
        return False

    def reset_actions(self):
        self.mafia_votes.clear()
        self.doctor_save = None
        self.sheriff_check = None
        self.day_votes.clear()

    # ---- Role assignment ----
    def assign_roles(self):
        """
        Рөлдерді кездейсоқ түрде тағайындайды.
        Логика: өлшемдерге қарай 1-2 мафия, 1 дон мүмкін, 1 доктор, 1 шериф, қалғаны бейбіт.
        """
        ids = list(self.players.keys())
        random.shuffle(ids)
        n = len(ids)
        roles = {}

        # Минимальды рөлдер:
        mafia_count = max(1, n // 4)  # шамамен 1/4 мафия
        # Отырғысы келгендер үшін Дон болу мүмкіндігі:
        mafia_ids = set(random.sample(ids, mafia_count))
        remaining = [i for i in ids if i not in mafia_ids]

        # Доктор
        if remaining:
            doctor = random.choice(remaining)
            remaining.remove(doctor)
        else:
            doctor = None

        # Шериф
        if remaining:
            sheriff = random.choice(remaining)
            remaining.remove(sheriff)
        else:
            sheriff = None

        # Басқа бейбіттер
        for uid in ids:
            if uid in mafia_ids:
                roles[uid] = "mafia"
            elif uid == doctor:
                roles[uid] = "doctor"
            elif uid == sheriff:
                roles[uid] = "sheriff"
            else:
                roles[uid] = "villager"

        # Ерекше: егер екіден көп мафия болса біреуін "don" деп қоя аласың — опция ретінде:
        if mafia_count >= 2:
            don = random.choice(list(mafia_ids))
            roles[don] = "don"

        self.roles = roles
        return roles

    # ---- Helpers ----
    def alive_players(self) -> List[Player]:
        return [self.players[uid] for uid in self.players if uid in self.alive]

    def alive_count(self) -> int:
        return len(self.alive)

    def mafia_members(self) -> List[int]:
        return [uid for uid, r in self.roles.items() if r in ("mafia", "don") and uid in self.alive]

    def is_mafia(self, user_id: int) -> bool:
        return self.roles.get(user_id) in ("mafia", "don")

    def villagers_count(self) -> int:
        return sum(1 for uid in self.alive if not self.is_mafia(uid))

    # ---- Game phases ----
    async def start_game(self):
        if len(self.players) < 3:
            await self.app.bot.send_message(self.chat_id, "Кемінде 3 адам қажет! /join арқылы адамдарды жинаңдар.")
            return

        # Тазалау
        self.reset_actions()
        roles = self.assign_roles()
        self.phase = "night"

        # Рөлдерді жеке хабарлама арқылы жіберу
        for uid, role in roles.items():
            try:
                text = f"🤫 Сенің рөлің: *{role.upper()}*\n\n"
                if role == "mafia":
                    text += "Сен мафиясың — түнде бір адамды таңда. Басқа мафиялармен келісім керек.\n"
                elif role == "don":
                    text += "Сен – Староста (Don). Түнде таңдап, ақпарат аласың.\n"
                elif role == "doctor":
                    text += "Сен – Медбике (Doctor). Әр түнде біреуін сақтай аласың.\n"
                elif role == "sheriff":
                    text += "Сен – Директор (Sheriff). Әр түнде біреуді тексеріп, мафия ма әлде жоқ па білесің.\n"
                else:
                    text += "Сен бейбіт ойыншысы (Villager). Күндіз талқылауда дауыс бересің.\n"

                text += "\n⚠️ Бұл хабарлама құпия — оны чатта жариялама."
                await self.app.bot.send_message(uid, text, parse_mode="Markdown")
            except Exception:
                # Егер приват хабарлама жіберілмесе (пайдаланушы ботқа хабарлама бөгет қойса), чатқа ескерту
                await self.app.bot.send_message(self.chat_id,
                    f"⚠️ @{self.players[uid].username}, маған жеке хабар жіберуге рұқсат беріңіз — рөліңізді жібереді.")

        # Топқа имбовый хабарлама: ойын басталды
        await self.app.bot.send_message(
            self.chat_id,
            self._group_start_message(),
            parse_mode="HTML",
            reply_markup=self._group_start_keyboard()
        )

        # Бастапқы түн фазасын бастау
        await self.start_night_phase()

    def _group_start_message(self):
        return (
            image_url := "https://c.wallhere.com/photos/38/5f/night_city_city_lights_skyscrapers-548880.jpg!d"  # түнгі сурет
            "<b>🎭 Ойын басталды!</b>\n\n"
            "Түн түсті — бәрің тыныш болыңдар. Мафиялар қимылдайды.\n"
            "Түн аяқталған соң, нәтижесін топтан хабарлаймыз."
        )

    def _group_start_keyboard(self):
        kb = [[InlineKeyboardButton("⏭️ Келесі (статус)", callback_data=f"status:{self.chat_id}")]]
        return InlineKeyboardMarkup(kb)

    async def start_night_phase(self, timeout: int = 45):
        self.phase = "night"
        self.reset_actions()
        # Жеке хабарламалар: мафияға, докторға, шерифке — таңдау батырмалары
        alive = self.alive_players()
        if not alive:
            return

        # Суреттер/стиль — имба стильдегі хабарламалар
        # Мафияға жеке хабарлама: кімдерді таңдауға болады
        mafia_ids = self.mafia_members()
        targets_keyboard = self._alive_keyboard(prefix=f"mafia_target:{self.chat_id}:")

        # Егер мафия біреу болса, соған жеке жібереміз; егер бірнеше — әрқайсысы жеке таңдайды (дабағы дауыс)
        for mid in mafia_ids:
            try:
                await self.app.bot.send_message(
                    mid,
                    
                    "🌙 Түн! Маған кімді алып тастағың келеді? Таңдаңыз:",
                    reply_markup=targets_keyboard
                )
            except Exception:
                pass

        # Докторқа
        doc_id = None
        for uid, r in self.roles.items():
            if r == "doctor" and uid in self.alive:
                doc_id = uid
                break
        if doc_id:
            try:
                await self.app.bot.send_message(
                    doc_id,
                    "🏥 Сен — Доктор. Қай адамды сақтағың келеді? (Өзіңді де сақтай аласың)",
                    reply_markup=self._alive_keyboard(prefix=f"doctor_save:{self.chat_id}:")
                )
            except Exception:
                pass

        # Шерифке
        sheriff_id = None
        for uid, r in self.roles.items():
            if r == "sheriff" and uid in self.alive:
                sheriff_id = uid
                break
        if sheriff_id:
            try:
                await self.app.bot.send_message(
                    sheriff_id,
                    "🔎 Сен — Директор (Sheriff). Кімді тексергің келеді?",
                    reply_markup=self._alive_keyboard(prefix=f"sheriff_check:{self.chat_id}:")
                )
            except Exception:
                pass

        # Түннің таймауты — егер әрекеттер болса да, уақыттан кейін шешім қабылданады
        loop = asyncio.get_running_loop()
        if self.night_task and not self.night_task.done():
            self.night_task.cancel()
        self.night_task = loop.create_task(self._night_timeout(timeout))

    async def _night_timeout(self, timeout):
        try:
            await asyncio.sleep(timeout)
            await self.resolve_night()
        except asyncio.CancelledError:
            return

    async def resolve_night(self):
        """
        
        Түн әрекеттерін шешу:
        - Мафия таңдауы (көбіші) vs доктор сақтауы -> өлтіру/құтқару
        - Шериф тексеру нәтижесін жеке хабарлау
        """
        # Мафиалардың қосылған дауыстарын жинау (мафия_votes: mid -> target)
        if not self.phase == "night":
            return
        self.phase = "resolving_night"

        mafia_choice = None
        if self.mafia_votes:
            cnt = Counter(self.mafia_votes.values())
            mafia_choice = cnt.most_common(1)[0][0]  # мақсат user_id
        saved = self.doctor_save
        checked = self.sheriff_check

        # Шерифке тексеру нәтижесін жіберу
        if checked:
            role = self.roles.get(checked, "unknown")
            is_maf = "Иә, бұл мафия" if role in ("mafia", "don") else "Жоқ, бұл бейбіт"
            # Директорға жекеше хабарлау
            try:
                await self.app.bot.send_message(checked, f"🔎 Тексеру: {is_maf}")
            except Exception:
                pass

        # Нәтиже: егер мафия таңдаған адам бар болса және ол доктор сақтаған болмаса - өлтіру
        killed = None
        if mafia_choice and mafia_choice in self.alive:
            if mafia_choice == saved:
                # сақталып қалды
                await self.app.bot.send_message(self.chat_id, f"🌙 Түн: біреу байқалды — бірақ дәрігер құтқарып қалды! 🙏")
            else:
                # өлтіру
                self.alive.discard(mafia_choice)
                self.players[mafia_choice].alive = False
                killed = mafia_choice
                await self.app.bot.send_message(
                    self.chat_id,
                    image_url := "https://c.wallhere.com/photos/38/5f/night_city_city_lights_skyscrapers-548880.jpg!d",  # түнгі сурет
                    f"🌙 Түн нәтиже: {self.players[killed].mention()} тыныштықта қалды... 💀",
                    parse_mode="HTML"
                )
        else:
            await self.app.bot.send_message(self.chat_id, "🌙 Түн өтті: ешкім өлмеді.")

        # Рөлдер/мәліметтерді reset
        self.reset_actions()

        # Соқыр тексеру: кім қалды, кім мафия — тек ойын соңында көрсетіледі
        # Жеңімпазды тексеру
        winner = self.check_win()
        if winner:
            await self.end_game(winner)
            return

        # Күн фазасына ауысу
        await self.start_day_phase()

    async def start_day_phase(self, timeout: int = 60):
        self.phase = "day"
        # Топқа имба хабарлама — талқылау басталдыim

        image_url = "https://avatars.mds.yandex.net/i?id=98bead6b404da6c6eb4de05e08c71b27_l-9271342-images-thumbs&n=13"  # күндізгі сурет
        text = (
            "☀️ <b>Күн шықты!</b>\n\n"
            "Талқылау уақыты басталды — сіздер кімге күдіктенесіздер? Біреуін дауысқа қойып көрейік.\n"
            f"Қатысушылар саны: <b>{self.alive_count()}</b>"
        )
        # Бот топта дауыс беру батырмасын қояды (әр тірі ойыншыға)
        kb = []
        for p in self.alive_players():
            kb.append([InlineKeyboardButton(f"{p.username}", callback_data=f"vote:{self.chat_id}:{p.id}")])
        kb.append([InlineKeyboardButton("🗳️ Қарсыласпау", callback_data=f"vote:{self.chat_id}:0")])
        markup = InlineKeyboardMarkup(kb)

        msg = await self.app.bot.send_message(self.chat_id, text, parse_mode="HTML", reply_markup=markup)
        self.vote_message_id = msg.message_id

        # Күннің таймауты
        loop = asyncio.get_running_loop()
        if self.day_task and not self.day_task.done():
            self.day_task.cancel()
        self.day_task = loop.create_task(self._day_timeout(timeout))

    async def _day_timeout(self, timeout):
        try:
            await asyncio.sleep(timeout)
            await self.resolve_day()
        except asyncio.CancelledError:
            return

    async def resolve_day(self):
        """
        Дауыстарды есептеу — ең көп дауыс алған адам шықпақ.
        """
        if self.phase not in ("day",):
            return
        self.phase = "resolving_day"

        # Ауыстыру: өміршең ойыншылардың дауыстарын тексер
        votes = Counter(self.day_votes.values())
        # егер "0" ең көп дауыс алған болса — қинамау
        if not votes:
            await self.app.bot.send_message(self.chat_id, "🗳️ Күннің соңында дауыс болмады — ешкім еше алмады.")
        else:
            top, cnt = votes.most_common(1)[0]
            # majority талабы керек болса мына блокты қолданың (мысалы жартыдан көп)
            if top == 0:
                await self.app.bot.send_message(self.chat_id, "🗳️ Көпшілік қарсыласпау ұсынды — ешкім шықпады.")
            else:
                # Линчтеу
                if top in self.alive:
                    self.alive.discard(top)
                    self.players[top].alive = False
                    await self.app.bot.send_message(
                        self.chat_id,
                        f"🔨 Күн: {self.players[top].mention()} дауыс көп алып шығарыласа, ойыннан шығарылды.",
                        parse_mode="HTML"
                    )

        # Тексеру: кім қалғанын және жеңімпазды тексеру
        winner = self.check_win()
        if winner:
            await self.end_game(winner)
            return

        # Келесі түні бастау
        await self.start_night_phase()

    def check_win(self) -> Optional[str]:
        """
        Жеңімпаз кім — 'mafia' немесе 'villagers' немесе жоқ
        Мафия саны >= бейбіттер саны -> мафия жеңеді
        Егер барлық мафия өлсе -> бейбіттер жеңеді
        """
        mafia_alive = sum(1 for uid in self.alive if self.roles.get(uid) in ("mafia", "don"))
        villagers_alive = sum(1 for uid in self.alive if self.roles.get(uid) not in ("mafia", "don"))

        if mafia_alive == 0:
            return "villagers"
        if mafia_alive >= villagers_alive:
            return "mafia"
        return None

    async def end_game(self, winner: str):
        self.phase = "ended"
        if winner == "mafia":
            text = "🏴‍☠️ <b>Хулиган жеңді!</b>\n\nҚұттықтаймыз мафияны!"
        else:
            text = "🏅 <b>Бейбіттер жеңді!</b>\n\nҰрлықсыз күндер келсін!"
        # Қайсысы жеңгенін және барлық рөлдерді көрсету
        roles_report = "\n\n<b>Рөлдер:</b>\n"
        for uid, role in self.roles.items():
            alive_mark = "✅" if uid in self.alive else "💀"
            roles_report += f"{alive_mark} {self.players[uid].username} — {role}\n"

        await self.app.bot.send_message(self.chat_id, text + roles_report, parse_mode="HTML")

        # Ресет
        self.players.clear()
        self.roles.clear()
        self.alive.clear()
        self.reset_actions()

    def _alive_keyboard(self, prefix: str = "target:"):
        kb = []
        for p in self.alive_players():
            kb.append([InlineKeyboardButton(p.username, callback_data=f"{prefix}{p.id}")])
        # қосымша "Өзіңді таңдау" батырмасы
        kb.append([InlineKeyboardButton("Өзіңді таңдау", callback_data=f"{prefix}{0}")])
        return InlineKeyboardMarkup(kb)


# ----- Game manager: әрбір топқа жеке Game объектісі -----
GAME_STORE: Dict[int, Game] = {}  # chat_id -> Game


def get_game(chat_id: int, app) -> Game:
    if chat_id not in GAME_STORE:
        GAME_STORE[chat_id] = Game(chat_id, app)
    return GAME_STORE[chat_id]

# 🔻 Ойыншыны шығару
async def eliminate_player(chat_id, user, role, context):
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🚫 *{user.first_name}* ойыннан шығарылды!\n"
            f"🎭 Оның рөлі: *{role}*\n\n"
            "🕊 Соңғы сөзін күтудеміз (30 сек)..."
        ),
        parse_mode="Markdown"
    )

    await context.bot.send_message(
        chat_id=user.id,
        text=(
            "😵 Сіз ойыннан шығарылдыңыз!\n\n"
            "🗣 Соңғы сөзіңізді жазыңыз немесе фото/стикер/GIF жіберіңіз "
            "(30 секунд ішінде). Ол топта жарияланады."
        )
    )

    # 30 секундтық таймер қосу
    task = asyncio.create_task(last_word_timeout(user.id, chat_id, context))
    last_words[user.id] = (chat_id, task)


# 🔻 Таймер
async def last_word_timeout(user_id, chat_id, context):
    await asyncio.sleep(30)
    if user_id in last_words:
        last_words.pop(user_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏳ Соңғы сөзін айтпай кетті..."
        )


# 🔻 Соңғы сөзді қабылдау (кез келген формат)
async def handle_last_word(update, context):
    user = update.effective_user
    if user.id in last_words:
        chat_id, task = last_words.pop(user.id)
        task.cancel()  # таймерді тоқтату

        msg = update.message

        try:
            # Хабарламаны топқа көшіру
            await msg.copy(chat_id=chat_id)

            # Қосымша жазу
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🕊 <b>{user.first_name}</b> соңғы сөзін айтты!",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"❌ Соңғы сөзді көшіруде қате: {e}")
# ----- Хендлерлер (жалғастыру үшін) -----
# Бұл хендлерлерді main() ішіне тірке
# app.add_handler(CommandHandler("join", join))
# app.add_handler(CommandHandler("leave", leave))
# app.add_handler(CommandHandler("startgame", startgame_cmd))
# app.add_handler(CommandHandler("cancelgame", cancel_game_cmd))
# app.add_handler(CommandHandler("status", status_cmd))
# app.add_handler(CallbackQueryHandler(callback_router))  # барлық callback-тарды осы маршрутизатор өңдейді

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /join — топ ішінде ойынға қосылу
    """
    if update.effective_chat.type not in ("group", "supergroup"):
        await update.message.reply_text("Ойынға тек топ ішінде қосыласың. Ботты топқа шақырыңдар және /join деп жазыңдар.")
        return

    chat_id = update.effective_chat.id
    game = get_game(chat_id, context.application)
    added = game.add_player(update.effective_user)
    if added:
        text = (
            f"🎉 {update.effective_user.mention_html()} ойынды бастауға қосылды!\n"
            f"Қазір барлығы: <b>{len(game.players)}</b> ойыншы."
        )
    else:
        text = f"⚠️ {update.effective_user.mention_html()}, сен әлдеқашан қосылғансың."
    await update.message.reply_html(text)

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /leave — топ ішінде ойыннан шығу
    """
    if update.effective_chat.type not in ("group", "supergroup"):
        await update.message.reply_text("Бұл команда тек топта жұмыс істейді.")
        return
    chat_id = update.effective_chat.id
    game = get_game(chat_id, context.application)
    removed = game.remove_player(update.effective_user.id)
    if removed:
        await update.message.reply_text(f"{update.effective_user.mention_html()} ойыннан шықты.", parse_mode="HTML")
    else:
        await update.message.reply_text("Сен ойында жоқсың.", parse_mode="HTML")

async def startgame_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /startgame — топтың админі немесе кім бастамақ болса ойын бастайды.
    """
    if update.effective_chat.type not in ("group", "supergroup"):
        await update.message.reply_text("Ойынды тек топ ішінде бастай аласыз.")
        return

    chat_id = update.effective_chat.id
    game = get_game(chat_id, context.application)
    if game.phase != "waiting":
        await update.message.reply_text("Ойын қазір жүріп жатыр немесе аяқталды.")
        return

    await game.start_game()

async def cancel_game_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        await update.message.reply_text("Команда топ ішінде қолданылады.")
        return
    chat_id = update.effective_chat.id
    if chat_id in GAME_STORE:
        del GAME_STORE[chat_id]
        await update.message.reply_text("Ойын күшін жойды.")
    else:
        await update.message.reply_text("Ойынды таппадым.")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /status — топтағы ағымдағы күй (тек топта)
    """
    chat_id = update.effective_chat.id
    game = GAME_STORE.get(chat_id)
    if not game:
        await update.message.reply_text("Ойын жоқ.")
        return
    text = (
        f"📊 Ойын күйі: {game.phase}\n"
        f"👥 Қатысушылар: {len(game.players)}\n"
        f"🔰 Тірі: {len(game.alive)}\n"
    )
    await update.message.reply_text(text)


# ----- Callback маршрутизаторы (callback_data-лар осы жерде өңделеді) -----
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    callback_data форматтары:
      - mafia_target:<chat_id>:<target_id>
      - doctor_save:<chat_id>:<target_id>
      - sheriff_check:<chat_id>:<target_id>
      - vote:<chat_id>:<target_id>
      - status:<chat_id>
    """
    query = update.callback_query
    data = query.data or ""
    await query.answer()  # қысқа жауап (опционал)

    parts = data.split(":")
    action = parts[0] if parts else ""
    if action == "status":
        # Топтағы жалпы статус көрсетеді
        if len(parts) >= 2:
            chat_id = int(parts[1])
            game = GAME_STORE.get(chat_id)
            if not game:
                await query.message.reply_text("Ойын табылмады.")
                return
            text = (
                f"📊 Ойын күйі: {game.phase}\n"
                f"👥 Қатысушылар: {len(game.players)}\n"
                f"🔰 Тірі: {len(game.alive)}\n"
            )
            await query.message.reply_text(text)
        return

    if action in ("mafia_target", "doctor_save", "sheriff_check", "vote"):
        if len(parts) < 3:
            return
        chat_id = int(parts[1])
        target_id = int(parts[2])
        game = GAME_STORE.get(chat_id)
        user_id = query.from_user.id

        if not game:
            await query.message.reply_text("Ойын табылмады.")
            return

        # ---- Мафия таңдауы ----
        if action == "mafia_target":
            if game.phase != "night":
                await query.message.reply_text("Қазір түн емес.")
                return
            if not game.is_mafia(user_id):
                await query.message.reply_text("Сен мафия емессің.")
                return
            # тірі болу керек
            if target_id != 0 and target_id not in game.alive:
                await query.message.reply_text("Бұл адам өлі немесе жоқ.")
                return
            game.mafia_votes[user_id] = target_id
            await query.message.reply_text("✅ Таңдадың. Сәйкесінше басқа мафиялар да таңдау керек.")
            # егер барлық мафия дауыс берсе, тоқтату (таймерді жойып артық іске қосу)
            mafia_mems = game.mafia_members()
            if all(mid in game.mafia_votes for mid in mafia_mems):
                # жедел шешу
                if game.night_task and not game.night_task.done():
                    game.night_task.cancel()
                await game.resolve_night()
            return

        # ---- Доктор ----
        if action == "doctor_save":
            if game.phase != "night":
                await query.message.reply_text("Қазір түн емес.")
                return
            # Тексер
            role = game.roles.get(user_id)
            if role != "doctor":
                await query.message.reply_text("Сен доктор емессің.")
                return
            if target_id != 0 and target_id not in game.alive:
                await query.message.reply_text("Бұл адам өлі немесе жоқ.")
                return
            game.doctor_save = target_id
            await query.message.reply_text("✅ Тыңда — сақтап қойдың.")
            # егер мафия да дауыс беріп бітсе және доктор бітсе -> шешу
            mafia_mems = game.mafia_members()
            if (not mafia_mems) or all(mid in game.mafia_votes for mid in mafia_mems):
                if game.night_task and not game.night_task.done():
                    game.night_task.cancel()
                await game.resolve_night()
            return

        # ---- Шериф ----
        if action == "sheriff_check":
            if game.phase != "night":
                await query.message.reply_text("Қазір түн емес.")
                return
            role = game.roles.get(user_id)
            if role != "sheriff":
                await query.message.reply_text("Сен шериф емессің.")
                return
            if target_id != 0 and target_id not in game.alive:
                await query.message.reply_text("Бұл адам өлі немесе жоқ.")
                return
            game.sheriff_check = target_id
            await query.message.reply_text("🔎 Жарайды, тексереді. Нәтижесін алғанда хабарлаймын.")
            # егер басқа да әрекеттер бітсе
            mafia_mems = game.mafia_members()
            if (not mafia_mems) or all(mid in game.mafia_votes for mid in mafia_mems):
                if game.night_task and not game.night_task.done():
                    game.night_task.cancel()
                await game.resolve_night()
            return

        # ---- Дауыс беру (күн) ----
        if action == "vote":
            if game.phase != "day":
                await query.message.reply_text("Қазір дауыс беру уақыты емес.")
                return
            if user_id not in game.alive:
                await query.message.reply_text("Өкінішке орай, сен ойыннан шықтың — дауыс бере алмайсың.")
                return
            # target_id == 0 болса — қарсыласпау (абстейн)
            game.day_votes[user_id] = target_id
            # белгілі бір ең көп дауысқа жеткен-жетпегенін тексеру
            # егер дауыс берушілер саны тірі ойыншылар санына тең болса — шешу
            if len(game.day_votes) >= game.alive_count():
                if game.day_task and not game.day_task.done():
                    game.day_task.cancel()
                await game.resolve_day()
            else:
                await query.message.reply_text("✅ Дауысың есептелді.")
            return

    # Егер белгісіз action болса — жайші
    await query.message.reply_text("Белгісіз әрекет.")

# ------ Қосу/Тіркеу нұсқаулары ------
# main() ішінде немесе Application құрғанда төмендегілерді тірке:
#
# app.add_handler(CommandHandler("join", join))
# app.add_handler(CommandHandler("leave", leave))
# app.add_handler(CommandHandler("startgame", startgame_cmd))
# app.add_handler(CommandHandler("cancelgame", cancel_game_cmd))
# app.add_handler(CommandHandler("status", status_cmd))
# app.add_handler(CallbackQueryHandler(callback_router))
#
# Сондай-ақ, сенің бұрынғы /start, profile, roles_info, rules хендлерлерің болса,
# оларды қалдырып, осы қосымшаларды тіркеуді ұмытпа.
#
# ----- Пайдалану бойынша ескертулер -----
# 1) Түн/күннің таймаут уақытын (start_night_phase, start_day_phase функцияларында)
#    қажеттіліктеріне қарай өзгерте аласың (қазір 45s/60s қойылған).
# 2) Егер приват хабарлама жібермейтін қолданушылар болса, оларды топта ескерту мақсатында
#    топқа хабарлама жіберіледі.
# 3) UI-ды "имбовый" ету үшін топ және жеке хабарламалардағы мәтіндерді қалауыңа қарай
#    эмодзи, HTML/Markdown стильдерімен сәнде.
#
# Егер қосып тіркегеннен кейін қателік шықса (callback_pattern, parsing және т.б.) — қазіргідей
# оны түзеп беремін. Қосымша: дауыстарды tie-break ережесін қалай алғың келетінін (тең дауыс,
# 아무кім шығарылмасын немесе рандом) айтсаң соны қосып беремін.
#
# --- Код аяқталды ---

# 🔹 Негізгі функция
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(roles_info, pattern="roles_info"))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CallbackQueryHandler(profile, pattern="profile"))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("startgame", startgame_cmd))
    app.add_handler(CommandHandler("cancelgame", cancel_game_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_last_word))


    print("🤖 Mafia Bot Python арқылы іске қосылды!")
    app.run_polling()

if __name__ == "__main__":
    main()
