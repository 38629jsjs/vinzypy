# =========================================================================
# PROJECT: VINZY SMART ADDER V5.2 (ENTERPRISE ASYNC)
# AUTHOR: VINZY DIGITAL SERVICES
# DESCRIPTION: FULL-FEATURED ASYNC MEMBER ADDER WITH LIMIT TRACKING
# FEATURES: RESET LOGIC, FINDER ENGINE, ANTI-BAN, ERROR REPORTING
# =========================================================================

import os
import asyncio
import logging
import sys
import time
from datetime import datetime

# --- ASYNC LIBRARIES ---
try:
    from telebot.async_telebot import AsyncTeleBot
    from telebot import types as bot_types
    from telethon import TelegramClient, functions, types as tl_types, errors
    from telethon.sessions import StringSession
except ImportError as e:
    print(f"CRITICAL: Missing libraries. Make sure aiohttp, telethon, and pyTelegramBotAPI are installed. Error: {e}")
    sys.exit(1)

# --- 1. CONFIGURATION & LOGGING ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Logging setup for Koyeb Console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VinzyAdder_V5")

# Validation
if not all([API_ID, API_HASH, SESSION_STRING, BOT_TOKEN]):
    logger.critical("MISSING ENV VARS: Please check API_ID, API_HASH, SESSION, and TOKEN.")
    sys.exit(1)

# --- 2. INITIALIZATION ---
bot = AsyncTeleBot(BOT_TOKEN)
finder = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Isolated memory vault for multi-user handling
vinzy_vault = {}

# --- 3. THE COMMANDER ENGINE (TELETHON) ---

async def get_finder_client():
    """Maintains the connection for the Finder session."""
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

# --- 4. ANALYTICS & LOGIC MODULES ---

async def scrape_members(group_link):
    """Scrapes and cleans member list using the Finder session."""
    client = await get_finder_client()
    if not client: return "Finder session disconnected.", None

    try:
        # Resolve group/channel entity
        entity = await client.get_entity(group_link)
        
        # We only want members from Chats or Megagroups
        participants = await client.get_participants(entity)
        
        clean_list = []
        stats = {"premium": 0, "normal": 0, "ghosts": 0}
        
        for p in participants:
            # Automatic ghost/bot filtering
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
                "name": p.first_name or "User"
            })
            
        return clean_list, stats
    except Exception as e:
        return f"Scrape Error: {str(e)}", None

async def verify_channel_limit(target_username):
    """Calculates remaining slots for the 200 member limit."""
    client = await get_finder_client()
    if not client: return "Finder session disconnected.", 0

    try:
        # Resolve target channel
        entity = await client.get_entity(target_username)
        full = await client(functions.channels.GetFullChannelRequest(channel=entity))
        current_count = full.full_chat.participants_count
        
        # Telegram logic: 200 is the limit for manual bot/user invites
        remaining = 200 - current_count
        return remaining, current_count
    except Exception as e:
        return f"Limit Check Error: {str(e)}", 0

# --- 5. BOT INTERFACE & HANDLERS ---

@bot.message_handler(commands=['start'])
async def handle_start(m):
    """Resets the state and shows the main menu."""
    # RESET LOGIC: Ensure a clean slate every time /start is used
    vinzy_vault[m.chat.id] = {
        "scraped": [],
        "filtered": [],
        "target": None,
        "start_time": datetime.now()
    }
    
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚀 Start Smart Scan")
    
    welcome_text = (
        "👑 <b>Vinzy Smart Adder V5.2</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Status:</b> 🟢 Connected to Koyeb\n"
        "<b>Reset Logic:</b> 🔄 Session Cleared\n\n"
        "This bot is just the commander. The <b>Finder Session</b> "
        "will handle the scraping and adding processes.\n\n"
        "<i>Ready for instructions, Overlord.</i>"
    )
    await bot.send_message(m.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 Start Smart Scan")
async def ask_source_group(m):
    """Step 1: Get the source group."""
    prompt = await bot.send_message(m.chat.id, "📥 <b>Step 1:</b> Paste the <b>Source Group Link</b> to scrape from:")
    bot.register_next_step_handler(prompt, process_scrape_execution)

async def process_scrape_execution(m):
    """Execution of Step 1: Scrape & Report."""
    if not m.text.startswith(('http', '@')):
        return await bot.send_message(m.chat.id, "❌ Error: Invalid link format.")

    status_msg = await bot.send_message(m.chat.id, "🛰️ <b>Finder</b> is scanning the source... please wait.")
    
    members, stats = await scrape_members(m.text)
    
    if isinstance(members, str):
        return await bot.edit_message_text(f"❌ <b>Finder Error:</b>\n<code>{members}</code>", m.chat.id, status_msg.message_id, parse_mode="HTML")

    # Store in Vault
    vinzy_vault[m.chat.id]["scraped"] = members
    
    # Selection Menu
    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("👤 Normal Only", callback_data="type_normal"),
               bot_types.InlineKeyboardButton("💎 Premium Only", callback_data="type_premium"))
    markup.add(bot_types.InlineKeyboardButton("✅ All (Mixed)", callback_data="type_all"))
    
    report = (
        f"📊 <b>Finder Scrape Report</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 Normal Users: {stats['normal']}\n"
        f"💎 Premium Users: {stats['premium']}\n"
        f"👻 Ghosts Filtered: {stats['ghosts']}\n\n"
        f"<b>Choose member type to proceed:</b>"
    )
    await bot.edit_message_text(report, m.chat.id, status_msg.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("type_"))
async def filter_selection_handler(call):
    """Filters the list based on button choice."""
    mode = call.data.split("_")[1]
    raw_list = vinzy_vault.get(call.message.chat.id, {}).get("scraped", [])
    
    if not raw_list:
        return await bot.answer_callback_query(call.id, "Session timed out. Press /start.", show_alert=True)

    if mode == "premium":
        filtered = [u for u in raw_list if u["premium"]]
    elif mode == "normal":
        filtered = [u for u in raw_list if not u["premium"]]
    else:
        filtered = raw_list
        
    vinzy_vault[call.message.chat.id]["filtered"] = filtered
    
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = await bot.send_message(call.message.chat.id, "📤 <b>Step 2:</b> Send the target <b>Channel Username</b> (@...):")
    bot.register_next_step_handler(msg, process_target_channel)

async def process_target_channel(m):
    """Step 2: Check limit and prepare adding list."""
    target_username = m.text.replace("https://t.me/", "@")
    status_msg = await bot.send_message(m.chat.id, f"📡 Checking 200-limit for {target_username}...")
    
    slots, current = await verify_channel_limit(target_username)
    
    if isinstance(slots, str):
        return await bot.edit_message_text(f"❌ <b>Limit Check Error:</b>\n<code>{slots}</code>", m.chat.id, status_msg.message_id, parse_mode="HTML")
    
    if slots <= 0:
        return await bot.edit_message_text(f"❌ <b>Limit Reached!</b>\n{target_username} already has {current}/200 members.", m.chat.id, status_msg.message_id)

    # Prepare final list
    filtered_list = vinzy_vault[m.chat.id].get("filtered", [])
    final_to_add = filtered_list[:slots]
    
    vinzy_vault[m.chat.id]["final_list"] = final_to_add
    vinzy_vault[m.chat.id]["target"] = target_username

    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("🚀 START ADDING", callback_data="execute_final"))
    
    confirm_text = (
        f"🎯 <b>Ready to Add</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📈 Current: {current}/200\n"
        f"✅ Adding: <b>{len(final_to_add)}</b> members\n"
        f"🛡️ Protection: 45s Anti-Ban Delay\n\n"
        f"Confirm to start process?"
    )
    await bot.edit_message_text(confirm_text, m.chat.id, status_msg.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "execute_final")
async def execute_invitation_trigger(call):
    """Triggers the async background worker."""
    chat_id = call.message.chat.id
    data = vinzy_vault.get(chat_id)
    
    if not data or "final_list" not in data:
        return await bot.answer_callback_query(call.id, "Error: Data lost. Please /start over.")

    await bot.edit_message_text("🎬 <b>Process Initiated.</b>\nAdding members one-by-one with safety delays...", chat_id, call.message.message_id, parse_mode="HTML")
    
    # Run the worker in the background so the bot stays responsive
    asyncio.create_task(invitation_worker(chat_id, data["final_list"], data["target"]))

async def invitation_worker(chat_id, members, target_channel):
    """The background engine that performs the invitations."""
    client = await get_finder_client()
    success_count = 0
    total = len(members)
    
    try:
        channel_entity = await client.get_entity(target_channel)
        
        for index, user in enumerate(members):
            try:
                # Execution
                await client(functions.channels.InviteToChannelRequest(
                    channel_entity, 
                    [user["id"]]
                ))
                success_count += 1
                
                # Feedback every 5 users
                if success_count % 5 == 0 or success_count == total:
                    await bot.send_message(chat_id, f"⏳ <b>Update:</b> Added {success_count}/{total} to {target_channel}.")
                
                # Critical delay to prevent Telegram bans
                await asyncio.sleep(45)
                
            except errors.FloodWaitError as e:
                await bot.send_message(chat_id, f"⚠️ <b>Flood Wait:</b> Telegram forced a stop for {e.seconds}s.")
                await asyncio.sleep(e.seconds)
            except errors.UserPrivacyRestrictedError:
                continue # Skip users who don't allow invites
            except Exception as e:
                logger.warning(f"Failed to add {user['id']}: {e}")
                continue
        
        await bot.send_message(chat_id, f"🏁 <b>Process Finished!</b>\nSuccessfully added {success_count} members to <code>{target_channel}</code>.")
        
    except Exception as e:
        await bot.send_message(chat_id, f"❌ <b>Critical Worker Error:</b>\n<code>{str(e)}</code>", parse_mode="HTML")

# --- 6. STARTUP PROTOCOL ---

async def startup_sequence():
    """Starts the Finder and the Bot Polling."""
    print("="*50)
    print("VINZY SMART ADDER V5.2 - BOOTING...")
    print(f"START TIME: {datetime.now().strftime('%H:%M:%S')}")
    print("="*50)
    
    # Initialize Finder Session
    await get_finder_client()
    
    # Start Bot Polling (High Speed)
    await bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    try:
        asyncio.run(startup_sequence())
    except KeyboardInterrupt:
        print("\n[!] Powering down. Goodbye.")
