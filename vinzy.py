# =========================================================================
# PROJECT: VINZY SMART ADDER V6.0 (ENTERPRISE GOLD)
# AUTHOR: VINZY DIGITAL SERVICES
# ENGINE: ASYNC-TELEBOT + TELETHON INTEGRATION
# PLATFORM: OPTIMIZED FOR KOYEB / HEROKU / VPS
# =========================================================================

import os
import asyncio
import logging
import sys
import time
import signal
import random
import platform
from datetime import datetime

# --- CORE DEPENDENCY CHECK ---
try:
    from telebot.async_telebot import AsyncTeleBot
    from telebot import types as bot_types
    from telethon import TelegramClient, functions, types as tl_types, errors
    from telethon.sessions import StringSession
    from telebot.asyncio_helper import ApiTelegramException
except ImportError as e:
    print(f"CRITICAL ERROR: Missing libraries. Ensure pip install telethon pyTelegramBotAPI aiohttp. Error: {e}")
    sys.exit(1)

# --- 1. CONFIGURATION & SECURE STORAGE ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Validation of Environment Variables
if not all([API_ID, API_HASH, SESSION_STRING, BOT_TOKEN]):
    print("❌ FATAL: One or more Environment Variables (API_ID, API_HASH, SESSION_STRING, BOT_TOKEN) are missing.")
    sys.exit(1)

# --- 2. ADVANCED LOGGING INFRASTRUCTURE ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("vinzy_runtime.log")
    ]
)
logger = logging.getLogger("VinzyGold_V6")

# Global variables for session tracking
vinzy_vault = {}
start_time = datetime.now()
TOTAL_INVITES_EVER = 0

# Initialize Async Components
bot = AsyncTeleBot(BOT_TOKEN)
finder = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- 3. THE FINDER COMMANDER ENGINE (TELETHON) ---

async def get_finder_client():
    """
    Maintains and validates the connection for the worker session.
    Includes auto-reconnect logic if the session drops.
    """
    try:
        if not finder.is_connected():
            logger.info("Attempting to connect Finder Session...")
            await finder.connect()
        
        if not await finder.is_user_authorized():
            logger.error("Finder Session is unauthorized. Please generate a new String Session.")
            return None
            
        return finder
    except Exception as e:
        logger.error(f"Finder Connection Failure: {str(e)}")
        return None

# --- 4. BUSINESS LOGIC & DATA PROCESSING ---

async def scrape_members_advanced(group_link):
    """
    Scrapes members and performs deep-cleaning (Removing bots, deleted accounts).
    """
    client = await get_finder_client()
    if not client:
        return "Finder session offline. Check logs.", None

    try:
        logger.info(f"Starting scrape for: {group_link}")
        entity = await client.get_entity(group_link)
        
        # Pull participants from the resolved entity
        participants = await client.get_participants(entity)
        
        clean_list = []
        stats = {"premium": 0, "normal": 0, "ghosts": 0, "total": 0}
        
        for p in participants:
            stats["total"] += 1
            # Skip bots and deleted profiles to prevent ban-risk
            if p.bot or p.deleted:
                stats["ghosts"] += 1
                continue
            
            is_premium = getattr(p, 'premium', False)
            if is_premium:
                stats["premium"] += 1
            else:
                stats["normal"] += 1
            
            clean_list.append({
                "id": p.id,
                "premium": is_premium,
                "name": p.first_name if p.first_name else "Telegram User",
                "username": p.username if p.username else "NoUsername"
            })
            
        return clean_list, stats
    except Exception as e:
        logger.error(f"Scrape Logic Error: {e}")
        return f"Error: {str(e)}", None

async def calculate_channel_capacity(target_username):
    """
    Determines available slots in the target channel (Strict 200 Limit).
    """
    client = await get_finder_client()
    if not client:
        return "Finder session offline.", 0

    try:
        entity = await client.get_entity(target_username)
        full_info = await client(functions.channels.GetFullChannelRequest(channel=entity))
        current_members = full_info.full_chat.participants_count
        
        # The 200 limit is a hard Telegram restriction for non-organic invites
        slots_remaining = 200 - current_members
        return slots_remaining, current_members
    except Exception as e:
        logger.error(f"Capacity Check Error: {e}")
        return f"Error: {str(e)}", 0

# --- 5. ASYNC STATE-MACHINE HANDLERS ---

@bot.message_handler(commands=['start', 'reset'])
async def handle_start_command(m):
    """
    Initializes/Resets the user session vault.
    """
    vinzy_vault[m.chat.id] = {
        "state": "IDLE",
        "scraped_data": [],
        "filtered_data": [],
        "target_channel": None,
        "session_start": datetime.now()
    }
    
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Start Smart Scan", "📊 System Status", "⚙️ Help & FAQ")
    
    welcome_msg = (
        "👑 <b>Vinzy Smart Adder V6.0</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Status:</b> 🟢 Enterprise Gold\n"
        "<b>Engine:</b> Async State-Machine\n"
        "<b>Security:</b> Anti-Ban Enabled\n\n"
        "Welcome back. All previous session data has been purged. "
        "Select an option from the menu to begin."
    )
    await bot.send_message(m.chat.id, welcome_msg, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 System Status")
async def handle_status_check(m):
    """
    Displays technical health metrics of the bot and server.
    """
    uptime = datetime.now() - start_time
    mem_vaults = len(vinzy_vault)
    py_ver = platform.python_version()
    
    status_report = (
        "🌡️ <b>Advanced System Diagnostics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Uptime:</b> {str(uptime).split('.')[0]}\n"
        f"<b>Python Version:</b> {py_ver}\n"
        f"<b>Active Vaults:</b> {mem_vaults}\n"
        f"<b>Finder Link:</b> {'Connected ✅' if finder.is_connected() else 'Disconnected ❌'}\n"
        f"<b>Server Time:</b> {datetime.now().strftime('%H:%M:%S')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>All systems nominal. Ready for high-load.</i>"
    )
    await bot.send_message(m.chat.id, status_report, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🚀 Start Smart Scan")
async def initiate_scrape_sequence(m):
    """
    Moves user to the Scrape input state.
    """
    vinzy_vault[m.chat.id]["state"] = "AWAITING_SOURCE_LINK"
    prompt = (
        "📥 <b>Step 1: Identify Source</b>\n\n"
        "Please send the <b>@Username</b> or the <b>Public Link</b> of the group "
        "you wish to analyze for members."
    )
    await bot.send_message(m.chat.id, prompt, parse_mode="HTML")

@bot.message_handler(func=lambda m: vinzy_vault.get(m.chat.id, {}).get("state") == "AWAITING_SOURCE_LINK")
async def process_scrape_input(m):
    """
    Validates link and executes the scraping logic.
    """
    source = m.text.strip()
    if not source.startswith(('@', 'http', 't.me/')):
        return await bot.send_message(m.chat.id, "❌ Invalid input. Please send a valid @Username or Link.")

    vinzy_vault[m.chat.id]["state"] = "PROCESSING_SCRAPE"
    progress_msg = await bot.send_message(m.chat.id, "🛰️ <b>Finder session</b> is establishing connection to source...")
    
    # Executing the scrape
    data, stats = await scrape_members_advanced(source)
    
    if isinstance(data, str):
        vinzy_vault[m.chat.id]["state"] = "IDLE"
        return await bot.edit_message_text(f"❌ <b>Scrape Failed:</b>\n<code>{data}</code>", m.chat.id, progress_msg.message_id, parse_mode="HTML")

    vinzy_vault[m.chat.id]["scraped_data"] = data
    
    # Building Selection Menu
    markup = bot_types.InlineKeyboardMarkup(row_width=2)
    btn_normal = bot_types.InlineKeyboardButton("👤 Normal Only", callback_data="filter_normal")
    btn_premium = bot_types.InlineKeyboardButton("💎 Premium Only", callback_data="filter_premium")
    btn_all = bot_types.InlineKeyboardButton("✅ Add All Mixed", callback_data="filter_all")
    markup.add(btn_normal, btn_premium)
    markup.add(btn_all)
    
    report = (
        f"📊 <b>Scrape Results for {source}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 Normal Members: {stats['normal']}\n"
        f"💎 Premium Members: {stats['premium']}\n"
        f"👻 Inactive/Bots: {stats['ghosts']}\n\n"
        f"<b>Grand Total:</b> {len(data)} valid users.\n\n"
        f"Which group of users should we target for invitation?"
    )
    await bot.edit_message_text(report, m.chat.id, progress_msg.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("filter_"))
async def handle_filter_selection(call):
    """
    Filters the scraped data based on user button choice.
    """
    mode = call.data.split("_")[1]
    raw_list = vinzy_vault.get(call.message.chat.id, {}).get("scraped_data", [])
    
    if not raw_list:
        return await bot.answer_callback_query(call.id, "Session timeout. Please /start over.", show_alert=True)

    if mode == "premium":
        filtered = [u for u in raw_list if u["premium"]]
    elif mode == "normal":
        filtered = [u for u in raw_list if not u["premium"]]
    else:
        filtered = raw_list
        
    vinzy_vault[call.message.chat.id]["filtered_data"] = filtered
    vinzy_vault[call.message.chat.id]["state"] = "AWAITING_TARGET_CHANNEL"
    
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    target_prompt = (
        "📤 <b>Step 2: Define Target</b>\n\n"
        "Send the <b>@Username</b> of the channel/group where you want to "
        "invite these members into."
    )
    await bot.send_message(call.message.chat.id, target_prompt, parse_mode="HTML")

@bot.message_handler(func=lambda m: vinzy_vault.get(m.chat.id, {}).get("state") == "AWAITING_TARGET_CHANNEL")
async def process_target_input(m):
    """
    Validates target and checks capacity.
    """
    target = m.text.strip().replace("https://t.me/", "@")
    if not target.startswith('@'): target = f"@{target}"
    
    status_check = await bot.send_message(m.chat.id, f"📡 Checking slots in {target}...")
    
    slots, current = await calculate_channel_capacity(target)
    
    if isinstance(slots, str):
        return await bot.edit_message_text(f"❌ <b>Error:</b> {slots}", m.chat.id, status_check.message_id)
    
    if slots <= 0:
        vinzy_vault[m.chat.id]["state"] = "IDLE"
        return await bot.edit_message_text(f"❌ <b>Limit Reached:</b> {target} already has {current}/200 members.", m.chat.id, status_check.message_id)

    # Prep final list
    ready_list = vinzy_vault[m.chat.id].get("filtered_data", [])[:slots]
    vinzy_vault[m.chat.id].update({
        "final_list": ready_list,
        "target_channel": target,
        "state": "READY_FOR_INVITE"
    })

    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("🚀 EXECUTE INVITATIONS", callback_data="start_worker"))
    
    confirmation = (
        f"🎯 <b>Ready for Execution</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📍 Target: {target}\n"
        f"📈 Current: {current}/200\n"
        f"✅ Adding: <b>{len(ready_list)}</b> new members\n\n"
        f"🛡️ <b>Anti-Ban Delay:</b> 40s - 60s (Randomized)\n"
        f"Proceed with the automated worker?"
    )
    await bot.edit_message_text(confirmation, m.chat.id, status_check.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "start_worker")
async def trigger_async_worker(call):
    """
    Launches the invite worker in the background.
    """
    chat_id = call.message.chat.id
    data = vinzy_vault.get(chat_id)
    
    if not data or "final_list" not in data:
        return await bot.answer_callback_query(call.id, "Session Error. Restarting.")

    vinzy_vault[chat_id]["state"] = "WORKING"
    await bot.edit_message_text("🎬 <b>Worker Status:</b> Active\nStarting human-simulated invitations...", chat_id, call.message.message_id)
    
    # Task fire-and-forget
    asyncio.create_task(background_invite_worker(chat_id, data["final_list"], data["target_channel"]))

async def background_invite_worker(chat_id, user_list, target):
    """
    The main invitation loop. Optimized for safety.
    """
    global TOTAL_INVITES_EVER
    client = await get_finder_client()
    success = 0
    fail = 0
    total = len(user_list)
    
    try:
        target_entity = await client.get_entity(target)
        
        for index, user_data in enumerate(user_list):
            try:
                # Execution
                await client(functions.channels.InviteToChannelRequest(
                    target_entity, 
                    [user_data["id"]]
                ))
                success += 1
                TOTAL_INVITES_EVER += 1
                
                # Logic: Notify user every 5 success
                if success % 5 == 0 or success == total:
                    perc = int((success/total)*100)
                    progress_bar = "🟩" * (perc//10) + "⬜" * (10 - (perc//10))
                    await bot.send_message(chat_id, f"⏳ <b>Live Progress:</b>\n{progress_bar} {perc}%\nAdded {success}/{total} to {target}")
                
                # HUMAN SIMULATION DELAY (Critical for ban prevention)
                wait_time = random.randint(40, 65)
                await asyncio.sleep(wait_time)
                
            except errors.FloodWaitError as e:
                await bot.send_message(chat_id, f"⚠️ <b>Flood Alert:</b> Telegram forced a pause. Sleeping {e.seconds}s.")
                await asyncio.sleep(e.seconds)
            except errors.UserPrivacyRestrictedError:
                fail += 1
                continue
            except Exception:
                fail += 1
                continue
        
        final_summary = (
            f"🏁 <b>Invitation Campaign Finished</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ Successfully Added: {success}\n"
            f"❌ Failed/Privacy: {fail}\n"
            f"📍 Target Group: {target}\n"
            f"📊 Total Session Invites: {success + fail}"
        )
        await bot.send_message(chat_id, final_summary, parse_mode="HTML")
        vinzy_vault[chat_id]["state"] = "IDLE"
        
    except Exception as e:
        logger.error(f"Worker Fatal Error: {e}")
        await bot.send_message(chat_id, f"❌ <b>Critical Worker Error:</b>\n<code>{str(e)}</code>", parse_mode="HTML")

# --- 6. CORE STARTUP & CONFLICT RESOLUTION ---

async def startup_sequence():
    """
    The main bootstrapper for the application.
    Handles the 409 Conflict logic and loop monitoring.
    """
    print("="*50)
    print("VINZY SMART ADDER V6.0 - INITIALIZING...")
    print(f"BOOT TIME: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    # Pre-boot Finder connection
    await get_finder_client()
    
    while True:
        try:
            logger.info("Connecting to Telegram Bot Polling...")
            await bot.infinity_polling(skip_pending=True, timeout=90)
        except ApiTelegramException as e:
            if e.error_code == 409:
                logger.warning("Conflict (409) detected. Old instance still active. Waiting 15s...")
                await asyncio.sleep(15)
            else:
                logger.error(f"Telegram API Exception: {e}")
                await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Global System Exception: {e}")
            await asyncio.sleep(10)

# --- 7. CLEAN EXIT HANDLER ---
def stop_instance(*args):
    """Ensures everything closes neatly when the server stops."""
    print("\n[!] Vinzy Gold V6 is shutting down. Cleaning up sessions...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop_instance)
    try:
        asyncio.run(startup_sequence())
    except KeyboardInterrupt:
        print("\n[!] Manual shutdown initiated.")
