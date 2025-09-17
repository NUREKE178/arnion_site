# Telegram Group Mafia Bot (Group part)
# Minimal comments, designed to run with aiogram (>=3.x style adapted for 2.x compatible API)
# Replace BOT_TOKEN and BOT_USERNAME and PHOTO URLs before running.

import asyncio
import json
import logging
import random
import time
from collections import defaultdict
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatType

# CONFIG - replace the placeholders
BOT_TOKEN = "REPLACE_WITH_YOUR_BOT_TOKEN"
BOT_USERNAME = "@REPLACE_WITH_YOUR_BOT_USERNAME"
DAY_PHOTOS = [
    "https://example.com/day1.jpg",
    "https://example.com/day2.jpg",
]
NIGHT_PHOTOS = [
    "https://example.com/night1.jpg",
    "https://example.com/night2.jpg",
]
GAME_SAVE_FILE = "mafia_games_backup.json"
# durations in seconds
NIGHT_DURATION = 35
DAY_DURATION = 60
VOTE_DURATION = 45

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Roles. You can add or remove roles here.
ROLE_LIST = [
    "Buzaky",  # mafia
    "JasyrinBuzaky",  # mafia boss
    "SynypZhetekshi",  # detective
    "Medbike",  # doctor
    "TartiptiOkushy",  # villager
    "UzdikOkushy",  # one-time protect
    "AkterBala",  # can mimic
]

# Player class
class Player:
    def __init__(self, user_id: int, name: str):
        self.user_id = user_id
        self.name = name
        self.role: Optional[str] = None
        self.alive: bool = True
        self.vote_target: Optional[int] = None
        self.night_target: Optional[int] = None
        self.used_ability: bool = False
        self.protected_until_round: int = -1
        self.energy: int = 3
        self.morale: int = 100
        self.items: List[str] = []
        self.disguise: bool = False

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "role": self.role,
            "alive": self.alive,
            "used_ability": self.used_ability,
            "protected_until_round": self.protected_until_round,
            "energy": self.energy,
            "morale": self.morale,
            "items": self.items,
            "disguise": self.disguise,
        }

    @classmethod
    def from_dict(cls, d):
        p = cls(d["user_id"], d["name"])
        p.role = d.get("role")
        p.alive = d.get("alive", True)
        p.used_ability = d.get("used_ability", False)
        p.protected_until_round = d.get("protected_until_round", -1)
        p.energy = d.get("energy", 3)
        p.morale = d.get("morale", 100)
        p.items = d.get("items", [])
        p.disguise = d.get("disguise", False)
        return p


# Game state per chat
class Game:
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.players: Dict[int, Player] = {}
        self.started = False
        self.round = 0
        self.phase = "idle"  # idle, night, day, voting, finished
        self.role_list = []
        self.mafia_ids: List[int] = []
        self.logs: List[str] = []
        self.vote_counts: Dict[int, int] = defaultdict(int)
        self.pending_votes: Dict[int, Optional[int]] = {}
        self.night_actions: Dict[int, Optional[int]] = {}
        self.save_ts = time.time()

    def add_player(self, user_id: int, name: str):
        if user_id in self.players:
            return False
        self.players[user_id] = Player(user_id, name)
        return True

    def remove_player(self, user_id: int):
        if user_id in self.players:
            self.players[user_id].alive = False
            self.players[user_id].quit = True
            return True
        return False

    def assign_roles(self):
        total = len(self.players)
        if total < 5:
            return False
        roles = []
        # Basic balance: ~1 mafia per 4 players
        mafia_count = max(1, total // 4)
        roles.extend(["Buzaky"] * (mafia_count - 1))
        roles.append("JasyrinBuzaky")
        # Add detective and medic
        roles.append("SynypZhetekshi")
        roles.append("Medbike")
        # Add special and villager filler
        roles.append("UzdikOkushy")
        roles.append("AkterBala")
        while len(roles) < total:
            roles.append("TartiptiOkushy")
        random.shuffle(roles)
        self.role_list = roles
        for p, role in zip(self.players.values(), roles):
            p.role = role
        self.mafia_ids = [pid for pid, p in self.players.items() if p.role in ("Buzaky", "JasyrinBuzaky")]
        return True

    def alive_players(self) -> List[Player]:
        return [p for p in self.players.values() if p.alive]

    def alive_count(self) -> int:
        return len(self.alive_players())

    def mafia_count(self) -> int:
        return len([p for p in self.players.values() if p.alive and p.role in ("Buzaky", "JasyrinBuzaky")])

    def check_end(self):
        if self.mafia_count() == 0:
            return "villagers"
        if self.mafia_count() >= (self.alive_count() - self.mafia_count()):
            return "mafia"
        return None

    def to_dict(self):
        return {
            "chat_id": self.chat_id,
            "players": {str(k): v.to_dict() for k, v in self.players.items()},
            "started": self.started,
            "round": self.round,
            "phase": self.phase,
            "role_list": self.role_list,
            "logs": self.logs,
        }

    @classmethod
    def from_dict(cls, d):
        g = cls(d["chat_id"])
        g.started = d.get("started", False)
        g.round = d.get("round", 0)
        g.phase = d.get("phase", "idle")
        g.role_list = d.get("role_list", [])
        g.logs = d.get("logs", [])
        players = d.get("players", {})
        for k, v in players.items():
            g.players[int(k)] = Player.from_dict(v)
        g.mafia_ids = [pid for pid, p in g.players.items() if p.role in ("Buzaky", "JasyrinBuzaky")]
        return g


GAMES: Dict[int, Game] = {}

# Persistence
def save_games():
    try:
        data = {str(chat_id): g.to_dict() for chat_id, g in GAMES.items()}
        with open(GAME_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.exception("Failed to save games: %s", e)


def load_games():
    try:
        with open(GAME_SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for chat_id_str, gd in data.items():
            chat_id = int(chat_id_str)
            GAMES[chat_id] = Game.from_dict(gd)
    except FileNotFoundError:
        return
    except Exception as e:
        logging.exception("Failed to load games: %s", e)


load_games()

# Helpers
def url_bot_button():
    return InlineKeyboardMarkup().add(InlineKeyboardButton("🎮 Ботқа өту", url=f"https://t.me/{BOT_USERNAME.lstrip('@')}"))

def players_keyboard_for_selector(game: Game, callback_prefix: str):
    kb = InlineKeyboardMarkup(row_width=2)
    for pid, p in game.players.items():
        if p.alive:
            kb.insert(InlineKeyboardButton(f"{p.name}", callback_data=f"{callback_prefix}:{pid}"))
    kb.add(InlineKeyboardButton("🔙 Артқа", callback_data="back_to_menu"))
    return kb

async def safe_send_photo(chat_id, photo_url, caption, reply_markup=None):
    try:
        await bot.send_photo(chat_id, photo=photo_url, caption=caption, reply_markup=reply_markup)
    except Exception:
        await bot.send_message(chat_id, caption, reply_markup=reply_markup)

# Group entry point - main menu appears via /newgame or button

@dp.message_handler(commands=["newgame", "startgame"])  # admin can type this in group
async def cmd_newgame(message: types.Message):
    if message.chat.type == ChatType.PRIVATE:
        await message.reply("Ойынды топта бастаңыз.")
        return
    chat_id = message.chat.id
    if chat_id not in GAMES:
        GAMES[chat_id] = Game(chat_id)
    game = GAMES[chat_id]
    if game.started:
        await message.reply("Ойын жүріп жатыр. /stopgame арқылы тоқтатыңыз немесе күтіңіз.")
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Ойынға қосылу", callback_data="join_game"))
    kb.add(InlineKeyboardButton("🧾 Қолданысшы тізімі", callback_data="player_list"))
    kb.add(InlineKeyboardButton("🎮 Бастау (админ)", callback_data="start_game"))
    kb.add(InlineKeyboardButton("🗑 Тазалау", callback_data="reset_game"))
    kb.add(InlineKeyboardButton("🎮 Ботқа өту", url=f"https://t.me/{BOT_USERNAME.lstrip('@')}"))
    await message.reply("🟢 Сынып Мафиясы: Ойын бөлмесі. Төменнен қосылыңыз:", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "join_game")
async def cb_join_game(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user
    game = GAMES.get(chat_id)
    if not game:
        await callback.answer("Ойын бөлмесі табылмаған. /newgame басыңыз.")
        return
    added = game.add_player(user.id, user.full_name)
    save_games()
    if added:
        await callback.answer("Сіз ойынды қосылдыңыз ✔️")
        await callback.message.reply(f"{user.full_name} қосылды. Барлық қатысушылар: {len(game.players)}")
    else:
        await callback.answer("Сіз бұрыннан ойындасыз.")


@dp.callback_query_handler(lambda c: c.data == "player_list")
async def cb_player_list(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    game = GAMES.get(chat_id)
    if not game:
        await callback.answer("Ойын жоқ.")
        return
    text = "📋 Қатысушылар:\n"
    for p in game.players.values():
        status = "✔️" if p.alive else "❌"
        text += f"{status} {p.name} — {p.role or '—'}\n"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Артқа", callback_data="back_to_menu"))
    await callback.message.edit_text(text, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "reset_game")
async def cb_reset_game(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    GAMES.pop(chat_id, None)
    save_games()
    await callback.message.reply("🗑 Ойын бөлмесі тазартылды.")


@dp.callback_query_handler(lambda c: c.data == "start_game")
async def cb_start_game(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    game = GAMES.get(chat_id)
    if not game:
        await callback.answer("Ойын бөлмесі жоқ.")
        return
    if game.started:
        await callback.answer("Ойын бұған дейін басталған.")
        return
    if len(game.players) < 5:
        await callback.answer("Ойын үшін кемінде 5 адам қажет.")
        return
    ok = game.assign_roles()
    if not ok:
        await callback.answer("Рөлдер тағайындау мүмкін болмады.")
        return
    game.started = True
    game.round = 0
    save_games()
    # send private role messages
    for pid, p in game.players.items():
        try:
            text = f"🎭 Сіздің рөліңіз: {p.role}\n\n" \
                   + "Түнде әрекетіңізді жасаңыз. Барлығы тек кнопкалар арқылы."
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🎮 Ботқа өту", url=f"https://t.me/{BOT_USERNAME.lstrip('@')}"))
            await bot.send_message(pid, text, reply_markup=kb)
        except Exception:
            await callback.message.reply(f"Пайдаланушы {p.name} ботқа жеке хат алмады. Олар ботты бастауы тиіс.")
    await callback.message.reply("🎲 Ойын басталды! Түн фазасы қазір басталады...")
    asyncio.create_task(run_game_loop(game))


async def run_game_loop(game: Game):
    while True:
        if game.phase == "finished":
            break
        # night
        game.round += 1
        game.phase = "night"
        photo = random.choice(NIGHT_PHOTOS)
        await safe_send_photo(game.chat_id, photo, f"🌙 Түн {game.round}. Барлық түн әрекеттерін жасаңыз.", reply_markup=url_bot_button())
        # reset night actions
        game.night_actions = {pid: None for pid in game.players.keys() if game.players[pid].alive}
        # notify mafia privately with selector buttons
        mafia_ids = [pid for pid, p in game.players.items() if p.alive and p.role in ("Buzaky", "JasyrinBuzaky")]
        if mafia_ids:
            kb = players_keyboard_for_selector(game, "mafia_kill")
            for mid in mafia_ids:
                try:
                    await bot.send_message(mid, "😈 Бұзақылар қайсысын шабалайды?", reply_markup=kb)
                except Exception:
                    pass
        # notify detective
        for pid, p in game.players.items():
            if p.alive and p.role == "SynypZhetekshi":
                kb = players_keyboard_for_selector(game, "detect_check")
                try:
                    await bot.send_message(pid, "👨‍🏫 Тексеру: кімді тексересіз?", reply_markup=kb)
                except Exception:
                    pass
        # notify medic
        for pid, p in game.players.items():
            if p.alive and p.role == "Medbike":
                kb = players_keyboard_for_selector(game, "med_save")
                try:
                    await bot.send_message(pid, "👩‍⚕️ Құтқару: кімді емдейсіз?", reply_markup=kb)
                except Exception:
                    pass
        # actor gets mimic choice
        for pid, p in game.players.items():
            if p.alive and p.role == "AkterBala":
                kb = players_keyboard_for_selector(game, "actor_mimic")
                try:
                    await bot.send_message(pid, "🎭 Кімді имитациялайсыз?", reply_markup=kb)
                except Exception:
                    pass
        save_games()
        # wait for night duration
        await asyncio.sleep(NIGHT_DURATION)
        # process night actions
        kill_targets = []
        med_saved = None
        detected = None
        # collect mafia majority target (simple: first chosen target or majority)
        mafia_votes = defaultdict(int)
        for pid, action in game.night_actions.items():
            # action stored as tuple (role, target)
            if action and action[0] == "mafia_kill":
                mafia_votes[action[1]] += 1
        if mafia_votes:
            # choose max
            target, cnt = max(mafia_votes.items(), key=lambda x: x[1])
            # require at least 1 vote
            kill_targets.append(target)
        # detect
        for pid, action in game.night_actions.items():
            if action and action[0] == "detect_check":
                detected = action[1]
        for pid, action in game.night_actions.items():
            if action and action[0] == "med_save":
                med_saved = action[1]
        # actor mimic
        for pid, action in game.night_actions.items():
            if action and action[0] == "actor_mimic":
                mimic_target = action[1]
                # actor copies the role for reporting only
                if mimic_target in game.players:
                    mimicked_role = game.players[mimic_target].role
                    try:
                        await bot.send_message(pid, f"🎭 Сіз {game.players[mimic_target].name} рөлін имитациялап, ол: {mimicked_role}")
                    except Exception:
                        pass
        # apply kill (respect medic save and protection)
        killed_names = []
        for t in kill_targets:
            if t in game.players and game.players[t].alive:
                p = game.players[t]
                if med_saved == t or p.protected_until_round >= game.round:
                    # saved
                    pass
                else:
                    p.alive = False
                    killed_names.append(p.name)
        # log and announce night results
        if killed_names:
            await bot.send_message(game.chat_id, f"☠️ Түнде: {' ,'.join(killed_names)} оқушы ойыннан шықты.")
        else:
            await bot.send_message(game.chat_id, "🌙 Түн тыныш өтті. Ешкім өлген жоқ.")
        save_games()
        # check end
        winner = game.check_end()
        if winner:
            await announce_winner(game, winner)
            game.phase = "finished"
            save_games()
            break
        # day phase
        game.phase = "day"
        photo = random.choice(DAY_PHOTOS)
        await safe_send_photo(game.chat_id, photo, f"☀️ Күн {game.round}. Дауыс беру басталады. Талқылаңыз және дауыс беріңіз.", reply_markup=url_bot_button())
        # reset voting
        game.vote_counts = defaultdict(int)
        game.pending_votes = {pid: None for pid in game.players.keys() if game.players[pid].alive}
        # send vote keyboards in group and private
        # group message with buttons opens a vote selector
        kb = InlineKeyboardMarkup(row_width=2)
        for pid, p in game.players.items():
            if p.alive:
                kb.insert(InlineKeyboardButton(p.name, callback_data=f"vote:{pid}"))
        kb.add(InlineKeyboardButton("⏭ Дауыс бермеймін", callback_data="vote:0"))
        kb.add(InlineKeyboardButton("🗳 Қазір дауыс санау", callback_data="tally_votes"))
        await bot.send_message(game.chat_id, "🗳 Дауыс беру: кімге дауыс бересіз? (астындағы кнопкалар)", reply_markup=kb)
        save_games()
        # wait for vote duration
        await asyncio.sleep(VOTE_DURATION)
        # tally
        await tally_and_execute_vote(game)
        # check end again
        winner = game.check_end()
        if winner:
            await announce_winner(game, winner)
            game.phase = "finished"
            save_games()
            break
        # small pause before next night
        await asyncio.sleep(2)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("mafia_kill:"))
async def cb_mafia_kill(callback: types.CallbackQuery):
    data = callback.data.split(":", 1)
    target_id = int(data[1])
    user_id = callback.from_user.id
    game = GAMES.get(callback.message.chat.id)
    if not game:
        # mafia private messages have chat = private, so find game where user is mafia
        game = None
        for g in GAMES.values():
            if user_id in g.players and g.players[user_id].role in ("Buzaky", "JasyrinBuzaky"):
                game = g
                break
    if not game:
        await callback.answer("Ойынды таба алмадым.")
        return
    if user_id not in game.players:
        await callback.answer("Сіз бұл ойынның қатысушысы емессіз.")
        return
    game.night_actions[user_id] = ("mafia_kill", target_id)
    save_games()
    await callback.answer("Сіздің таңдау қабылданды.")


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("detect_check:"))
async def cb_detect(callback: types.CallbackQuery):
    data = callback.data.split(":", 1)
    target_id = int(data[1])
    user_id = callback.from_user.id
    # find game
    game = None
    for g in GAMES.values():
        if user_id in g.players:
            game = g
            break
    if not game:
        await callback.answer("Ойынды таба алмадым.")
        return
    game.night_actions[user_id] = ("detect_check", target_id)
    save_games()
    # send private result immediately
    role = game.players.get(target_id).role if target_id in game.players else None
    is_mafia = role in ("Buzaky", "JasyrinBuzaky") if role else False
    try:
        await bot.send_message(user_id, f"🔎 Тексеру нәтижесі: {game.players[target_id].name} — {'Бұзақы' if is_mafia else 'Қалыпты'}")
    except Exception:
        pass
    await callback.answer("Тексеру жіберілді.")


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("med_save:"))
async def cb_med(callback: types.CallbackQuery):
    data = callback.data.split(":", 1)
    target_id = int(data[1])
    user_id = callback.from_user.id
    game = None
    for g in GAMES.values():
        if user_id in g.players:
            game = g
            break
    if not game:
        await callback.answer("Ойынды таба алмадым.")
        return
    game.night_actions[user_id] = ("med_save", target_id)
    save_games()
    await callback.answer("Сіз құтқаруды таңдадыңыз.")


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("actor_mimic:"))
async def cb_actor(callback: types.CallbackQuery):
    data = callback.data.split(":", 1)
    target_id = int(data[1])
    user_id = callback.from_user.id
    game = None
    for g in GAMES.values():
        if user_id in g.players:
            game = g
            break
    if not game:
        await callback.answer("Ойынды таба алмадым.")
        return
    game.night_actions[user_id] = ("actor_mimic", target_id)
    save_games()
    await callback.answer("Сіз имитацияны таңдадыңыз.")


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("vote:"))
async def cb_vote(callback: types.CallbackQuery):
    data = callback.data.split(":", 1)
    target_id = int(data[1])
    chat_id = callback.message.chat.id
    game = GAMES.get(chat_id)
    if not game:
        await callback.answer("Ойын табылмады.")
        return
    voter = callback.from_user.id
    if voter not in game.players or not game.players[voter].alive:
        await callback.answer("Сіз дауыс бере алмайсыз.")
        return
    # store vote
    game.pending_votes[voter] = target_id if target_id != 0 else None
    save_games()
    await callback.answer("Дауыс қабылданды.")


@dp.callback_query_handler(lambda c: c.data == "tally_votes")
async def cb_tally(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    await tally_and_execute_vote(GAMES.get(chat_id))


async def tally_and_execute_vote(game: Game):
    if not game:
        return
    game.vote_counts = defaultdict(int)
    for voter, target in game.pending_votes.items():
        if target and target in game.players and game.players[voter].alive:
            game.vote_counts[target] += 1
    if not game.vote_counts:
        await bot.send_message(game.chat_id, "🗳 Дауыс бермей-ақ өтті. Кім де болмасын шығарылмады.")
        return
    # find max
    target, cnt = max(game.vote_counts.items(), key=lambda x: x[1])
    # simple majority rule
    alive_count = game.alive_count()
    if cnt >= 1:
        if target in game.players and game.players[target].alive:
            game.players[target].alive = False
            await bot.send_message(game.chat_id, f"🪓 Күн дауысында: {game.players[target].name} ойыннан шығарылды ({cnt} дауыс).")
    else:
        await bot.send_message(game.chat_id, "Көпшілік дауыс табылмады.")
    save_games()


async def announce_winner(game: Game, winner: str):
    if winner == "villagers":
        await bot.send_message(game.chat_id, "🏆 Оқушылар жеңді! Бұзақылар жойылды.")
    else:
        await bot.send_message(game.chat_id, "🏆 Бұзақылар жеңді! Сыныпты жаулап алды.")
    # show final roles
    text = "📜 Соңғы нәтижелер:\n"
    for p in game.players.values():
        text += f"{p.name} — {p.role} — {'тірі' if p.alive else 'өлген'}\n"
    await bot.send_message(game.chat_id, text)
    game.started = False
    save_games()


@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def cb_back(callback: types.CallbackQuery):
    await callback.message.edit_text("🔙 Негізгі мәзірге оралу", reply_markup=None)


# graceful stop
@dp.message_handler(commands=["stopgame"])  # admin
async def cmd_stopgame(message: types.Message):
    chat_id = message.chat.id
    g = GAMES.get(chat_id)
    if not g:
        await message.reply("Ойын табылмады.")
        return
    g.phase = "finished"
    g.started = False
    save_games()
    await message.reply("🛑 Ойын тоқтатылды.")


# fallback handler for group to show main menu with buttons on any message
@dp.message_handler(lambda message: message.chat.type != ChatType.PRIVATE)
async def group_any_message(message: types.Message):
    # show quick join menu if game exists or prompt to create
    chat_id = message.chat.id
    if chat_id not in GAMES or not GAMES[chat_id].started:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("➕ Ойынға қосылу", callback_data="join_game"))
        kb.add(InlineKeyboardButton("🟢 Ойынды бастау (админ)", callback_data="start_game"))
        kb.add(InlineKeyboardButton("🎮 Ботқа өту", url=f"https://t.me/{BOT_USERNAME.lstrip('@')}"))
        await message.reply("🟢 Сынып Мафиясы — ойнағыңыз келе ме?", reply_markup=kb)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
