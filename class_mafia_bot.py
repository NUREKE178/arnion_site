"""
Mafia Telegram Bot — Classroom edition
Features:
- Inline-button driven UI
- Photo at game start (host uploads photo to set mood)
- Role distribution based on player count
- Night and Day phases with button actions
- Private role messages in Kazakh and Russian (both supported)
- Complex flow, logs, persistent stats in JSON
- Commands: /start, /newgame, /join, /leave, /begin, /status, /lang

Requirements:
- python-telegram-bot v20+ (async)
- Python 3.9+

NOTE: This is a single-file example. For production, split into modules and secure token.
"""

import asyncio
import json
import logging
import random
import os
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

from telegram import (
    __version__ as TG_VER,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    InputMediaPhoto,
)
from telegram.constants import ChatAction

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# Basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("8348607898:AAGg8qbGEaSd8EjaeSFchqYg5gzKbA1H_uo", "8348607898:AAGg8qbGEaSd8EjaeSFchqYg5gzKbA1H_uo")
DATA_FILE = "mafia_data.json"

# ---------- Helpers & Data Models ----------

class Lang(Enum):
    KZ = "kz"
    RU = "ru"

# Messages (bilingual). Access with M(msg_key, lang)
MESSAGES = {
    "welcome": {
        Lang.KZ: "Сәлем! Мен — Сыныптық Мафия боты. Ойын жасау үшін /newgame бастаңыз.",
        Lang.RU: "Привет! Я — Бот школьной Мафии. Чтобы создать игру, нажми /newgame.",
    },
    "newgame_started": {
        Lang.KZ: "Жаңа ойын құрылуда. Қосылу үшін /join басыңыз. Хостке фото жүктеп, 'Set Mood' батырмасын басуға болады.",
        Lang.RU: "Создана новая игра. Чтобы присоединиться, нажми /join. Хост может загрузить фото и нажать 'Set Mood'.",
    },
    "joined": {
        Lang.KZ: "%s ойнауға қосылды!",
        Lang.RU: "%s присоединился к игре!",
    },
    "already_joined": {
        Lang.KZ: "%s сен ойындасың!",
        Lang.RU: "%s уже в игре!",
    },
    "not_enough_players": {
        Lang.KZ: "Ойын бастау үшін кемінде 6 адам қажет.",
        Lang.RU: "Для старта игры нужно минимум 6 игроков.",
    },
    "roles_assigned": {
        Lang.KZ: "Рөлдер берілді. Барлығына жеке хабарлама келді.",
        Lang.RU: "Роли распределены. Всем отправлены приватные сообщения.",
    },
    "game_over": {
        Lang.KZ: "Ойын аяқталды. Қорытынды:\n%s",
        Lang.RU: "Игра окончена. Результат:\n%s",
    },
    # more messages used later...
}


def M(key: str, lang: Lang = Lang.KZ) -> str:
    part = MESSAGES.get(key, {})
    return part.get(lang, next(iter(part.values())) if part else "")

# ---------- Persistent Storage ----------

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

DB = load_data()

# ---------- Game State ----------

class Phase(Enum):
    LOBBY = auto()
    NIGHT = auto()
    DAY = auto()
    ENDED = auto()

class Role(Enum):
    HULIGAN = "h"  # mafia
    STUDENT = "s"  # villager
    TEACHER = "t"  # doctor
    SPY = "p"      # detective (shp)
    JOKER = "j"    # clown
    SPORT = "sp"   # optional
    SMART = "sm"   # optional

ROLE_NAMES = {
    Role.HULIGAN: ("Хулиган 😈", "Хулиган 😈"),
    Role.STUDENT: ("Үздік оқушы 📚", "Лучший ученик 📚"),
    Role.TEACHER: ("Сынып жетекші 👩‍🏫", "Классный руководитель 👩‍🏫"),
    Role.SPY: ("Жасырын шпаргалкашы 📝", "Тайный списывальщик 📝"),
    Role.JOKER: ("Қалжыңбас 🤡", "Шутник 🤡"),
    Role.SPORT: ("Спортшы 🏃", "Спортсмен 🏃"),
    Role.SMART: ("Ақылды қыз 👧", "Умная девочка 👧"),
}

# Game object to hold state per chat
class MafiaGame:
    def __init__(self, chat_id: int, host_id: int, lang: Lang = Lang.KZ):
        self.chat_id = chat_id
        self.host_id = host_id
        self.lang = lang
        self.phase = Phase.LOBBY
        self.players: List[int] = []
        self.player_usernames: Dict[int, str] = {}
        self.roles: Dict[int, Role] = {}
        self.alive: Set[int] = set()
        self.night_actions: Dict[str, Dict] = {}  # action_type -> {actor: target}
        self.logs: List[str] = []
        self.photo_file_id: Optional[str] = None
        self.vote_map: Dict[int, int] = {}  # voter -> voted
        self.stats: Dict[str, int] = {}

    def to_dict(self):
        return {
            "chat_id": self.chat_id,
            "host_id": self.host_id,
            "lang": self.lang.value,
            "phase": self.phase.name,
            "players": self.players,
            "player_usernames": self.player_usernames,
            "roles": {str(k): v.value for k, v in self.roles.items()},
            "alive": list(self.alive),
            "photo_file_id": self.photo_file_id,
            "logs": self.logs,
            "stats": self.stats,
        }

    @staticmethod
    def from_dict(d):
        g = MafiaGame(d["chat_id"], d["host_id"], Lang(d.get("lang", "kz")))
        g.phase = Phase[d.get("phase", "LOBBY")]
        g.players = d.get("players", [])
        g.player_usernames = d.get("player_usernames", {})
        g.roles = {int(k): Role(v) for k, v in d.get("roles", {}).items()}
        g.alive = set(d.get("alive", g.players[:]))
        g.photo_file_id = d.get("photo_file_id")
        g.logs = d.get("logs", [])
        g.stats = d.get("stats", {})
        return g

GAMES: Dict[int, MafiaGame] = {}

# Load saved games
if DB.get("games"):
    for cid, gd in DB.get("games", {}).items():
        GAMES[int(cid)] = MafiaGame.from_dict(gd)

# ---------- Utilities ----------

async def send_lang_text(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, key: str):
    lang = Lang.KZ
    if chat_id in GAMES:
        lang = GAMES[chat_id].lang
    await ctx.bot.send_message(chat_id, M(key, lang))

def pick_roles_for_count(n: int) -> List[Role]:
    # Rules from user's spec
    roles: List[Role] = []
    if n < 6:
        # fallback
        roles = [Role.HULIGAN, Role.SPY] + [Role.STUDENT] * (n - 2)
    elif 6 <= n <= 8:
        # 2 huligans, 1 spy, 1 teacher, rest students
        roles = [Role.HULIGAN, Role.HULIGAN, Role.SPY, Role.TEACHER] + [Role.STUDENT] * (n - 4)
    elif 9 <= n <= 15:
        # 3 huligans, 1 spy, 1 teacher, 1 joker, rest students
        roles = [Role.HULIGAN, Role.HULIGAN, Role.HULIGAN, Role.SPY, Role.TEACHER, Role.JOKER] + [Role.STUDENT] * (n - 6)
    else:
        # 20+ case sample: 4-5 huligans, extras
        hul_count = 4 if n < 25 else 5
        roles = [Role.HULIGAN] * hul_count + [Role.SPY, Role.TEACHER, Role.SPORT, Role.SMART] + [Role.STUDENT] * (n - (hul_count + 4))
    random.shuffle(roles)
    return roles

def role_name(role: Role, lang: Lang) -> str:
    kz, ru = ROLE_NAMES[role]
    return kz if lang == Lang.KZ else ru

# ---------- Command Handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(M("welcome", Lang.KZ))

async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    # Create game in chat
    if chat_id in GAMES and GAMES[chat_id].phase != Phase.ENDED:
        await update.message.reply_text("Игра уже запущена в этом чате. /status для состояния.")
        return
    g = MafiaGame(chat_id, user.id, Lang.KZ)
    GAMES[chat_id] = g
    DB.setdefault("games", {})[str(chat_id)] = g.to_dict()
    save_data(DB)

    # Buttons: join, set language, host photo upload
    keyboard = [
        [InlineKeyboardButton("Join / Қосылу", callback_data="join")],
        [InlineKeyboardButton("Set Mood (Host) — Загрузить фото", callback_data="set_mood")],
        [InlineKeyboardButton("Language / Язык: KZ/RU", callback_data="toggle_lang")],
        [InlineKeyboardButton("Begin (assign roles)", callback_data="assign_roles")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(M("newgame_started", g.lang), reply_markup=reply_markup)

async def join_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    uid = query.from_user.id
    if chat_id not in GAMES:
        await query.edit_message_text("No active game. /newgame to create one.")
        return
    g = GAMES[chat_id]
    if uid in g.players:
        await query.message.reply_text(M("already_joined", g.lang) % query.from_user.first_name)
        return
    g.players.append(uid)
    g.player_usernames[uid] = query.from_user.full_name
    g.alive.add(uid)
    g.logs.append(f"{query.from_user.full_name} joined")
    DB["games"][str(chat_id)] = g.to_dict()
    save_data(DB)
    await query.message.reply_text(M("joined", g.lang) % query.from_user.full_name)

async def set_mood_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    g = GAMES.get(chat_id)
    if not g:
        await query.edit_message_text("No game in this chat.")
        return
    if query.from_user.id != g.host_id:
        await query.message.reply_text("Only host can set mood photo / Только хост может загрузить фото.")
        return
    await query.message.reply_text("Please send a photo in chat now. / Отправьте фото в чат сейчас.")
    # User will send photo; photo handler will capture it.

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in GAMES:
        return
    g = GAMES[chat_id]
    # accept only from host
    if update.message.from_user.id != g.host_id:
        return
    photo = update.message.photo
    if not photo:
        return
    file_id = photo[-1].file_id
    g.photo_file_id = file_id
    DB["games"][str(chat_id)] = g.to_dict()
    save_data(DB)
    await update.message.reply_text("Mood photo saved. Host can press 'Begin' to assign roles.")

async def toggle_lang_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    g = GAMES.get(chat_id)
    if not g:
        await query.edit_message_text("No game found.")
        return
    g.lang = Lang.RU if g.lang == Lang.KZ else Lang.KZ
    DB["games"][str(chat_id)] = g.to_dict()
    save_data(DB)
    await query.message.reply_text(f"Language set to: {g.lang.value}")

# Assign roles and DM everyone
async def assign_roles_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    g = GAMES.get(chat_id)
    if not g:
        await query.edit_message_text("No game here.")
        return
    n = len(g.players)
    if n < 6:
        await query.message.reply_text(M("not_enough_players", g.lang))
        return
    roles = pick_roles_for_count(n)
    g.roles = {}
    for uid, role in zip(g.players, roles):
        g.roles[uid] = role
    g.alive = set(g.players[:])
    g.phase = Phase.NIGHT
    # send DMs
    for uid, role in g.roles.items():
        try:
            txt = f"Твоя роль: {role_name(role, g.lang)}\n"
            if role == Role.HULIGAN:
                txt += "Ночью вы будете выбирать жертву.\n"
            if role == Role.TEACHER:
                txt += "Ночью вы можете защитить одного человека.\n"
            if role == Role.SPY:
                txt += "Ночью вы можете проверить одного человека.\n"
            if role == Role.JOKER:
                txt += "Если тебя повысят (голосуют) — ты выиграл.\n"
            await context.bot.send_message(chat_id=uid, text=txt)
        except Exception as e:
            logger.error("Failed to send DM to %s: %s", uid, e)
    g.logs.append("Roles assigned")
    DB["games"][str(chat_id)] = g.to_dict()
    save_data(DB)
    await query.message.reply_text(M("roles_assigned", g.lang))
    # Show start/night controls in group
    await show_night_controls(context, g)

# Show Night controls (buttons in group)
async def show_night_controls(context: ContextTypes.DEFAULT_TYPE, g: MafiaGame):
    chat_id = g.chat_id
    text = "Ночь. Хулиганы — действуйте. / Түн болды."
    # include photo if exists
    if g.photo_file_id:
        try:
            await context.bot.send_photo(chat_id=chat_id, photo=g.photo_file_id, caption=text)
        except Exception as e:
            logger.warning("Failed to send mood photo: %s", e)
            await context.bot.send_message(chat_id=chat_id, text=text)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text)

    # Controls: Next phase, View logs, Force day
    keyboard = [
        [InlineKeyboardButton("Хулиганы — выбрать жертву (Host control)", callback_data="huligans_select")],
        [InlineKeyboardButton("Принудительный день / Күн бастау", callback_data="force_day")],
        [InlineKeyboardButton("View logs / Логи", callback_data="view_logs")],
    ]
    await context.bot.send_message(chat_id=chat_id, text="Нажмите кнопку для действий:", reply_markup=InlineKeyboardMarkup(keyboard))

async def huligans_select_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    g = GAMES.get(chat_id)
    if not g:
        await query.edit_message_text("Game not found.")
        return
    # build inline keyboard with alive players as targets
    buttons = []
    for uid in list(g.alive):
        uname = g.player_usernames.get(uid, str(uid))
        buttons.append([InlineKeyboardButton(uname, callback_data=f"target_{uid}")])
    await query.message.reply_text("Выберите жертву (Host/Group click to pick):", reply_markup=InlineKeyboardMarkup(buttons))

async def target_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("target_"):
        return
    target_id = int(data.split("_")[1])
    chat_id = query.message.chat.id
    g = GAMES.get(chat_id)
    if not g:
        return
    # Record night action as if huligans chose target
    g.night_actions.setdefault("kill", {})["huligans"] = target_id
    g.logs.append(f"Night: huligans chose {g.player_usernames.get(target_id, target_id)}")
    DB["games"][str(chat_id)] = g.to_dict()
    save_data(DB)
    await query.message.reply_text(f"Жертва выбрана: {g.player_usernames.get(target_id)}")

async def force_day_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    g = GAMES.get(chat_id)
    if not g:
        return
    # resolve night actions and go to day
    await resolve_night(context, g)

async def view_logs_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    g = GAMES.get(chat_id)
    if not g:
        return
    txt = "\n".join(g.logs[-20:]) if g.logs else "No logs yet"
    await query.message.reply_text(f"Logs:\n{txt}")

# Resolve night
async def resolve_night(context: ContextTypes.DEFAULT_TYPE, g: MafiaGame):
    # determine target
    kill_target = g.night_actions.get("kill", {}).get("huligans")
    protect = g.night_actions.get("protect", {}).get("teacher")
    checked = g.night_actions.get("check", {}).get("spy")
    # Apply protection
    if kill_target and kill_target == protect:
        # survived
        g.logs.append(f"{g.player_usernames.get(kill_target)} targeted but saved by Teacher")
    elif kill_target:
        # kill
        if kill_target in g.alive:
            g.alive.remove(kill_target)
            g.logs.append(f"{g.player_usernames.get(kill_target)} was removed during the night")
    # send check results privately
    if checked:
        role = g.roles.get(checked)
        spy_actor = None
        for uid, r in g.roles.items():
            if r == Role.SPY:
                spy_actor = uid
                break
        if spy_actor:
            try:
                await context.bot.send_message(chat_id=spy_actor, text=f"Check result: {g.player_usernames.get(checked)} is {role_name(role, g.lang)}")
            except Exception as e:
                logger.warning("Failed to send check result: %s", e)
    # clear night actions
    g.night_actions = {}
    g.phase = Phase.DAY
    DB["games"][str(g.chat_id)] = g.to_dict()
    save_data(DB)
    # announce day
    await context.bot.send_message(chat_id=g.chat_id, text="Утро. Ознакомьтесь с итогом ночи. / Таңертең. Нәтижелер: ")
    # provide voting controls
    await show_day_controls(context, g)

async def show_day_controls(context: ContextTypes.DEFAULT_TYPE, g: MafiaGame):
    # List alive players with vote buttons
    keyboard = []
    for uid in g.alive:
        keyboard.append([InlineKeyboardButton(g.player_usernames.get(uid, str(uid)), callback_data=f"vote_{uid}")])
    keyboard.append([InlineKeyboardButton("Finish vote / Завершить голосование", callback_data="finish_vote")])
    await context.bot.send_message(chat_id=g.chat_id, text="Голосование: выберите, кого исключить.", reply_markup=InlineKeyboardMarkup(keyboard))

async def vote_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("vote_"):
        voted = int(data.split("_")[1])
        chat_id = query.message.chat.id
        g = GAMES.get(chat_id)
        if not g or g.phase != Phase.DAY:
            await query.message.reply_text("Голосование отсутствует.")
            return
        voter = query.from_user.id
        if voter not in g.alive:
            await query.message.reply_text("Вы выбиты или не в игре.")
            return
        g.vote_map[voter] = voted
        DB["games"][str(chat_id)] = g.to_dict()
        save_data(DB)
        await query.message.reply_text(f"{query.from_user.full_name} голосует за {g.player_usernames.get(voted)}")
    elif data == "finish_vote":
        chat_id = query.message.chat.id
        g = GAMES.get(chat_id)
        if not g:
            return
        # count votes
        tally: Dict[int, int] = {}
        for v in g.vote_map.values():
            tally[v] = tally.get(v, 0) + 1
        if not tally:
            await query.message.reply_text("Никто не проголосовал.")
            return
        # find max
        victim, votes = max(tally.items(), key=lambda x: x[1])
        # remove victim
        if victim in g.alive:
            # if victim is JOKER -> joker wins
            if g.roles.get(victim) == Role.JOKER:
                # joker wins immediately
                g.phase = Phase.ENDED
                res = f"JOKER {g.player_usernames.get(victim)} wins!"
                await context.bot.send_message(chat_id=g.chat_id, text=res)
                await end_game(context, g, res)
                return
            g.alive.remove(victim)
            g.logs.append(f"During day {g.player_usernames.get(victim)} was removed by vote (votes={votes})")
        # clear votes
        g.vote_map = {}
        DB["games"][str(chat_id)] = g.to_dict()
        save_data(DB)
        # check end conditions
        await check_end_conditions(context, g)

async def check_end_conditions(context: ContextTypes.DEFAULT_TYPE, g: MafiaGame):
    # count huligans vs others
    hul = [uid for uid in g.alive if g.roles.get(uid) == Role.HULIGAN]
    others = [uid for uid in g.alive if g.roles.get(uid) != Role.HULIGAN]
    if not hul:
        res = "Villagers win / Үздік оқушылар жеңді!"
        g.phase = Phase.ENDED
        await end_game(context, g, res)
        return
    if len(hul) >= len(others):
        res = "Huligans win / Хулигандар жеңді!"
        g.phase = Phase.ENDED
        await end_game(context, g, res)
        return
    # continue to night
    g.phase = Phase.NIGHT
    DB["games"][str(g.chat_id)] = g.to_dict()
    save_data(DB)
    await show_night_controls(context, g)

async def end_game(context: ContextTypes.DEFAULT_TYPE, g: MafiaGame, result_text: str):
    g.phase = Phase.ENDED
    # send final stats
    alive_names = [g.player_usernames.get(x) for x in g.alive]
    summary = f"Result: {result_text}\nAlive: {alive_names}\nLogs:\n" + "\n".join(g.logs[-30:])
    await context.bot.send_message(chat_id=g.chat_id, text=summary)
    # cleanup but keep stats
    DB["games"][str(g.chat_id)] = g.to_dict()
    save_data(DB)

# ---------- Private night action handlers (simulate via DM buttons) ----------
async def dm_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # handle DM from users to bot for night actions
    uid = update.effective_user.id
    # find game where this uid has role
    g = None
    for game in GAMES.values():
        if uid in game.players and game.phase == Phase.NIGHT and uid in game.alive:
            g = game
            break
    if not g:
        await update.message.reply_text("You have no nightly actions right now or you're not in a game.")
        return
    role = g.roles.get(uid)
    if role == Role.HULIGAN:
        # huligans need a communal target; we accept a direct reply: send name or id
        await update.message.reply_text("Вы — Хулиган. Отправьте имя цели (точно как в чате) или нажмите кнопку 'Pick from alive' in group.")
    elif role == Role.TEACHER:
        # show list of alive players
        keyboard = [[InlineKeyboardButton(g.player_usernames[p], callback_data=f"protect_{p}")] for p in g.alive]
        await update.message.reply_text("Выберите, кого защитить:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif role == Role.SPY:
        keyboard = [[InlineKeyboardButton(g.player_usernames[p], callback_data=f"check_{p}")] for p in g.alive]
        await update.message.reply_text("Выберите, кого проверить:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("У вас нет ночных действий.")

async def protect_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("protect_"):
        return
    target = int(data.split("_")[1])
    uid = query.from_user.id
    # find game
    g = None
    for game in GAMES.values():
        if uid in game.players and game.phase == Phase.NIGHT:
            g = game
            break
    if not g:
        await query.message.reply_text("No game or not night.")
        return
    g.night_actions.setdefault("protect", {})["teacher"] = target
    g.logs.append(f"Teacher protected {g.player_usernames.get(target)}")
    DB["games"][str(g.chat_id)] = g.to_dict()
    save_data(DB)
    await query.message.reply_text(f"Вы защитили {g.player_usernames.get(target)}")

async def check_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("check_"):
        return
    target = int(data.split("_")[1])
    uid = query.from_user.id
    g = None
    for game in GAMES.values():
        if uid in game.players and game.phase == Phase.NIGHT:
            g = game
            break
    if not g:
        await query.message.reply_text("No game or not night.")
        return
    g.night_actions.setdefault("check", {})["spy"] = target
    g.logs.append(f"Spy checked {g.player_usernames.get(target)}")
    DB["games"][str(g.chat_id)] = g.to_dict()
    save_data(DB)
    await query.message.reply_text(f"Вы проверили {g.player_usernames.get(target)}")

# ---------- Misc Handlers ----------
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    g = GAMES.get(chat_id)
    if not g:
        await update.message.reply_text("No game active here.")
        return
    txt = f"Phase: {g.phase.name}\nPlayers: {len(g.players)}\nAlive: {len(g.alive)}\nHost: {g.host_id}"
    await update.message.reply_text(txt)

# CallbackQuery router
async def cb_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "join":
        await join_cb(update, context)
    elif data == "set_mood":
        await set_mood_cb(update, context)
    elif data == "toggle_lang":
        await toggle_lang_cb(update, context)
    elif data == "assign_roles":
        await assign_roles_cb(update, context)
    elif data == "huligans_select":
        await huligans_select_cb(update, context)
    elif data.startswith("target_"):
        await target_cb(update, context)
    elif data == "force_day":
        await force_day_cb(update, context)
    elif data == "view_logs":
        await view_logs_cb(update, context)
    elif data.startswith("vote_") or data == "finish_vote":
        await vote_cb(update, context)
    elif data.startswith("protect_"):
        await protect_cb(update, context)
    elif data.startswith("check_"):
        await check_cb(update, context)
    else:
        await update.callback_query.answer("Unknown action")

# ---------- Main ----------

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("newgame", newgame))
    application.add_handler(CommandHandler("status", status))

    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.GROUPS, photo_handler))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL, dm_start))

    application.add_handler(CallbackQueryHandler(cb_router))

    # Run the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
