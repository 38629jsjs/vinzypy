# =========================================================================
# PROJECT: VINZY SMART ADDER V5.5 (ULTIMATE ASYNC)
# AUTHOR: VINZY DIGITAL SERVICES
# DESCRIPTION: HIGH-SPEED ASYNC MEMBER ADDER WITH 409 CONFLICT RECOVERY
# PLATFORM: PYTHON 3.10+ | TELETHON | ASYNC-TELEBOT | KOYEB
# =========================================================================

import os
import asyncio
import logging
import sys
import time
import signal
from datetime import datetime

# --- CORE LIBRARIES ---
try:
    from telebot.async_telebot import AsyncTeleBot
    from telebot import types as bot_types
    from telethon import TelegramClient, functions, types as tl_types, errors
    from telethon.sessions import StringSession
    from telebot.asyncio_helper import ApiTelegramException
except ImportError as e:
    print(f"CRITICAL: Missing libraries. Ensure requirements.txt is correct. Error: {e}")
    sys.exit(1)

# --- 1. CONFIGURATION & LOGGING ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Standard logging for Koyeb Console visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VinzyAdder_V5.5")

# Global memory storage for user sessions
vinzy_vault = {}
start_time = datetime.now()

# Initialize Bot & Finder
bot = AsyncTeleBot(BOT_TOKEN)
finder = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- 2. THE FINDER COMMANDER ENGINE ---

async def get_finder_client():
    """Manages the worker session connection and health checks."""
    try:
        if not finder.is_connected():
            await finder.connect()
        
        if not await finder.is_user_authorized():
            logger.error("Finder Session is unauthorized or expired.")
            return None
        return finder
    except Exception as e:
        logger.error(f"Finder Connection Failure: {e}")
        return None

# --- 3. ANALYTICS & SCRAPER LOGIC ---

async def scrape_logic(group_link):
    """Deep scans a group using the Finder session to extract clean member data."""
    client = await get_finder_client()
    if not client: 
        return "Finder session disconnected. Check your SESSION_STRING.", None

    try:
        # Resolve group/channel entity
        entity = await client.get_entity(group_link)
        
        # We target participants specifically for Chats/Megagroups
        participants = await client.get_participants(entity)
        
        clean_list = []
        stats = {"premium": 0, "normal": 0, "ghosts": 0}
        
        for p in participants:
            # Filter out bots and deleted accounts to avoid waste and rate-limits
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
                "name": p.first_name or "Unknown"
            })
            
        return clean_list, stats
    except Exception as e:
        logger.error(f"Scrape Error: {e}")
        return f"Scrape Error: {str(e)}", None

async def check_channel_slots(target_username):
    """Calculates precisely how many slots are left before hitting the 200 limit."""
    client = await get_finder_client()
    if not client: 
        return "Finder session disconnected.", 0

    try:
        entity = await client.get_entity(target_username)
        full = await client(functions.channels.GetFullChannelRequest(channel=entity))
        current_count = full.full_chat.participants_count
        
        # Telegram hard limit for manual/bot-driven invites is 200
        available_slots = 200 - current_count
        return available_slots, current_count
    except Exception as e:
        logger.error(f"Limit Check Error: {e}")
        return f"Limit Check Error: {str(e)}", 0

# --- 4. ASYNC BOT HANDLERS ---

@bot.message_handler(commands=['start'])
async def cmd_start(m):
    """Wipes session memory and starts fresh."""
    vinzy_vault[m.chat.id] = {
        "scraped": [],
        "filtered": [],
        "target": None,
        "logs": []
    }
    
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚀 Start Smart Scan", "📊 System Status")
    
    welcome = (
        "👑 <b>Vinzy Smart Adder V5.5</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Status:</b> 🟢 Online\n"
        "<b>Conflict Fix:</b> 🛡️ Enabled\n"
        "<b>Engine:</b> Async Enterprise\n\n"
        "System has been <b>Reset</b>. Previous data cleared.\n"
        "What is your next command, Overlord?"
    )
    await bot.send_message(m.chat.id, welcome, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 System Status")
async def cmd_status(m):
    """Diagnostics command to check server and session health."""
    uptime = datetime.now() - start_time
    finder_status = "✅ Connected" if finder.is_connected() else "❌ Offline"
    
    status_text = (
        "🌡️ <b>System Health Report</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Uptime:</b> {str(uptime).split('.')[0]}\n"
        f"<b>Finder Session:</b> {finder_status}\n"
        f"<b>Active Users:</b> {len(vinzy_vault)}\n"
        f"<b>Server:</b> Koyeb Cloud\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Everything is running optimally.</i>"
    )
    await bot.send_message(m.chat.id, status_text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🚀 Start Smart Scan")
async def start_scan_prompt(m):
    """Phase 1: Get source group link."""
    msg = await bot.send_message(m.chat.id, "📥 <b>Step 1:</b> Paste the <b>Source Group Link</b>:")
    bot.register_next_step_handler(msg, execute_scrape_phase)

async def execute_scrape_phase(m):
    """Handles the heavy scraping and stats generation."""
    if not m.text.startswith(('http', '@')):
        return await bot.send_message(m.chat.id, "❌ Error: Invalid format. Send a link or @username.")

    status = await bot.send_message(m.chat.id, "🛰️ <b>Finder</b> is scanning the group... please wait.")
    members, stats = await scrape_logic(m.text)
    
    if isinstance(members, str):
        return await bot.edit_message_text(f"❌ <b>Error:</b>\n{members}", m.chat.id, status.message_id)

    # Store in Vault
    vinzy_vault[m.chat.id]["scraped"] = members
    
    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("👤 Normal Only", callback_data="type_normal"),
               bot_types.InlineKeyboardButton("💎 Premium Only", callback_data="type_premium"))
    markup.add(bot_types.InlineKeyboardButton("✅ All (Mixed)", callback_data="type_all"))
    
    report = (
        f"📊 <b>Scrape Report</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 Normal: {stats['normal']}\n"
        f"💎 Premium: {stats['premium']}\n"
        f"👻 Filtered: {stats['ghosts']}\n\n"
        f"<b>Choose member type to extract:</b>"
    )
    await bot.edit_message_text(report, m.chat.id, status.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("type_"))
async def filter_handler(call):
    """Filters the huge member list based on button selection."""
    mode = call.data.split("_")[1]
    raw_data = vinzy_vault.get(call.message.chat.id, {}).get("scraped", [])
    
    if not raw_data:
        return await bot.answer_callback_query(call.id, "Session expired. Use /start.", show_alert=True)

    if mode == "premium":
        filtered = [u for u in raw_data if u["premium"]]
    elif mode == "normal":
        filtered = [u for u in raw_data if not u["premium"]]
    else:
        filtered = raw_data
        
    vinzy_vault[call.message.chat.id]["filtered"] = filtered
    
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = await bot.send_message(call.message.chat.id, "📤 <b>Step 2:</b> Send target <b>Channel @Username</b>:")
    bot.register_next_step_handler(msg, execute_limit_check)

async def execute_limit_check(m):
    """Phase 2: Verifies target channel capacity."""
    target = m.text.replace("https://t.me/", "@")
    status = await bot.send_message(m.chat.id, f"📡 Checking capacity for {target}...")
    
    slots, current = await check_channel_slots(target)
    
    if isinstance(slots, str):
        return await bot.edit_message_text(f"❌ <b>Error:</b>\n{slots}", m.chat.id, status.message_id)
    
    if slots <= 0:
        return await bot.edit_message_text(f"❌ <b>Limit Reached:</b>\n{target} has {current}/200 members.", m.chat.id, status.message_id)

    # Filtered list logic
    all_filtered = vinzy_vault[m.chat.id].get("filtered", [])
    final_to_add = all_filtered[:slots]
    
    vinzy_vault[m.chat.id].update({"final_list": final_to_add, "target": target})

    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("🚀 CONFIRM & START", callback_data="run_invite"))
    
    await bot.edit_message_text(
        f"🎯 <b>Slots Available:</b> {slots}\n"
        f"✅ Adding <b>{len(final_to_add)}</b> members to reach limit.\n"
        f"🛡️ Safety Protocol: 45s Delay active.\n\n"
        f"Do you want to proceed?",
        m.chat.id, status.message_id, parse_mode="HTML", reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "run_invite")
async def invitation_trigger(call):
    """Launches the background async worker to perform additions."""
    chat_id = call.message.chat.id
    data = vinzy_vault.get(chat_id)
    
    if not data or "final_list" not in data:
        return await bot.answer_callback_query(call.id, "Data lost. Please /start.")

    await bot.edit_message_text("🎬 <b>Invitation Process Started.</b>\nRunning in background...", chat_id, call.message.message_id)
    
    # Run the worker as a task to keep the bot interface responsive
    asyncio.create_task(background_worker(chat_id, data["final_list"], data["target"]))

async def background_worker(chat_id, members, target):
    """The core addition engine with anti-ban logic."""
    client = await get_finder_client()
    success = 0
    fail = 0
    total = len(members)
    
    try:
        channel_entity = await client.get_entity(target)
        for index, user in enumerate(members):
            try:
                # The invite request
                await client(functions.channels.InviteToChannelRequest(
                    channel_entity, 
                    [user["id"]]
                ))
                success += 1
                
                # Feedback every 5 successful adds
                if success % 5 == 0 or success == total:
                    progress = (success / total) * 100
                    bar = "🟩" * int(progress/10) + "⬜" * (10 - int(progress/10))
                    await bot.send_message(chat_id, f"⏳ <b>Progress Update:</b>\n{bar} {int(progress)}%\nAdded: {success}/{total}")
                
                # Critical Anti-Ban Delay
                await asyncio.sleep(45)
                
            except errors.FloodWaitError as e:
                await bot.send_message(chat_id, f"⚠️ <b>Flood Wait:</b> Sleeping for {e.seconds}s.")
                await asyncio.sleep(e.seconds)
            except errors.UserPrivacyRestrictedError:
                fail += 1
                continue
            except Exception as e:
                logger.warning(f"Error for user {user['id']}: {e}")
                fail += 1
                continue
                
        # Final Summary
        summary = (
            f"🏁 <b>Operation Complete!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {fail}\n"
            f"📍 Target: {target}"
        )
        await bot.send_message(chat_id, summary, parse_mode="HTML")
        
    except Exception as e:
        await bot.send_message(chat_id, f"❌ <b>Worker Crash:</b>\n<code>{str(e)}</code>", parse_mode="HTML")

# --- 5. STARTUP & 409 CONFLICT RECOVERY ---

async def startup_sequence():
    """Main execution loop with auto-recovery logic."""
    print("="*50)
    print("VINZY SMART ADDER V5.5 - ULTIMATE EDITION ONLINE")
    print(f"DEPLOYMENT TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    # Ensure Finder Session is initialized
    await get_finder_client()
    
    # Conflict-resistant polling loop
    while True:
        try:
            print("[System] Attempting to connect to Telegram Polling...")
            await bot.infinity_polling(skip_pending=True, timeout=90)
        except ApiTelegramException as e:
            if e.error_code == 409:
                print("[Warning] Conflict (409). Retrying in 15s...")
                await asyncio.sleep(15)
            else:
                print(f"[API Error] Code {e.error_code}: {e}")
                await asyncio.sleep(5)
        except Exception as e:
            print(f"[System Error] {e}")
            await asyncio.sleep(5)

# --- 6. SHUTDOWN HANDLER ---
def handle_sigterm(*args):
    """Ensures clean exit on Koyeb termination."""
    print("\n[!] Shutdown signal received. Closing sessions...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    try:
        asyncio.run(startup_sequence())
    except KeyboardInterrupt:
        print("\n[!] System offline. Goodbye.")
