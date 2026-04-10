# =========================================================================
# PROJECT: VINZY SMART ADDER V4.8 (ENTERPRISE ASYNC)
# AUTHOR: VINZY DIGITAL SERVICES
# DESCRIPTION: HIGH-SPEED ASYNC MEMBER ADDER WITH 200-LIMIT TRACKING
# PLATFORM: PYTHON 3.10+ | TELETHON | ASYNC-TELEBOT | KOYEB
# =========================================================================

import os
import asyncio
import logging
import sys
import time
from datetime import datetime
from telebot.async_telebot import AsyncTeleBot
from telebot import types as bot_types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.sessions import StringSession

# --- 1. CONFIGURATION & ENVIRONMENT ---
# Ensure these are set in your Koyeb environment variables.
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Logging setup for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VinzyAdder")

if not all([API_ID, API_HASH, SESSION_STRING, BOT_TOKEN]):
    logger.critical("FATAL: Missing environment variables! Check API_ID, API_HASH, SESSION, and TOKEN.")
    sys.exit(1)

# Initialize Async Bot and Telethon Finder
bot = AsyncTeleBot(BOT_TOKEN)
finder = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Global Memory for Session Data (Isolated per user chat)
vinzy_vault = {}

# --- 2. THE COMMANDER: FINDER SESSION MANAGEMENT ---

async def get_finder_client():
    """Ensures the Finder session is connected and authorized."""
    if not finder.is_connected():
        await finder.connect()
    
    if not await finder.is_user_authorized():
        logger.error("Finder Session is invalid or expired.")
        return None
    return finder

# --- 3. CORE LOGIC MODULES ---

async def scrape_group_logic(group_link):
    """Deep scans a group using the Finder session to extract clean member data."""
    client = await get_finder_client()
    if not client: return "Finder Session Dead", None

    try:
        # Resolve group entity
        entity = await client.get_entity(group_link)
        if not isinstance(entity, (tl_types.Chat, tl_types.Channel)):
            return "Invalid Group Link. Must be a Chat or Channel.", None

        participants = await client.get_participants(entity)
        
        clean_list = []
        stats = {"premium": 0, "normal": 0, "ghosts": 0}
        
        for p in participants:
            # Filter out bots and deleted accounts to avoid waste
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
                "access_hash": getattr(p, 'access_hash', 0)
            })
            
        return clean_list, stats
    except Exception as e:
        logger.error(f"Scrape Error: {e}")
        return str(e), None

async def check_channel_limit(channel_username):
    """Calculates precisely how many slots are left before hitting the 200 limit."""
    client = await get_finder_client()
    if not client: return "Finder Session Dead", 0

    try:
        entity = await client.get_entity(channel_username)
        full = await client(functions.channels.GetFullChannelRequest(channel=entity))
        current_count = full.full_chat.participants_count
        
        # Telegram's hard limit for manual/bot invites is 200
        slots_left = 200 - current_count
        return slots_left, current_count
    except Exception as e:
        logger.error(f"Limit Check Error: {e}")
        return str(e), 0

# --- 4. BOT INTERFACE & HANDLERS ---

@bot.message_handler(commands=['start'])
async def handle_start(m):
    """Resets all session data and provides the main interface."""
    # RESET LOGIC: Purge the vault for this user
    vinzy_vault[m.chat.id] = {}
    
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚀 Start Smart Scan")
    
    welcome = (
        "👑 <b>Vinzy Smart Adder V4.8</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Status:</b> 🟢 Ready\n"
        "<b>Mode:</b> Async High-Speed\n\n"
        "System has been <b>Reset</b>. Previous data cleared.\n"
        "Using <b>Finder Session</b> for scraping/adding."
    )
    await bot.send_message(m.chat.id, welcome, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 Start Smart Scan")
async def initiate_scan(m):
    """First step of the workflow."""
    msg = await bot.send_message(m.chat.id, "📥 <b>Step 1:</b> Paste the <b>Source Group Link</b>:")
    bot.register_next_step_handler(msg, process_scrape_step)

async def process_scrape_step(m):
    """Handles the heavy lifting of group analysis."""
    if not m.text.startswith(('http', '@')):
        return await bot.send_message(m.chat.id, "❌ Invalid link. Send a link starting with @ or https://")

    status_msg = await bot.send_message(m.chat.id, "🛰️ <b>Finder</b> is analyzing group quality...")
    
    members, stats = await scrape_group_logic(m.text)
    
    if isinstance(members, str):
        return await bot.edit_message_text(f"❌ <b>Error:</b> {members}", m.chat.id, status_msg.message_id)

    # Save to user-specific vault
    vinzy_vault[m.chat.id] = {"scraped": members}
    
    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("👤 Normal Users", callback_data="type_normal"),
               bot_types.InlineKeyboardButton("💎 Premium Only", callback_data="type_premium"))
    markup.add(bot_types.InlineKeyboardButton("✅ All (Best Mix)", callback_data="type_all"))
    
    report = (
        f"📊 <b>Finder Scrape Report</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 Normal: {stats['normal']}\n"
        f"💎 Premium: {stats['premium']}\n"
        f"👻 Ghosts: {stats['ghosts']} (Filtered)\n\n"
        f"<b>Choose user type to add:</b>"
    )
    await bot.edit_message_text(report, m.chat.id, status_msg.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("type_"))
async def handle_member_filter(call):
    """Filters the scraped list based on user choice."""
    mode = call.data.split("_")[1]
    raw_data = vinzy_vault.get(call.message.chat.id, {}).get("scraped", [])
    
    if not raw_data:
        return await bot.answer_callback_query(call.id, "Session expired. Hit /start again.", show_alert=True)

    if mode == "premium":
        filtered = [x for x in raw_data if x["premium"]]
    elif mode == "normal":
        filtered = [x for x in raw_data if not x["premium"]]
    else:
        filtered = raw_data
        
    vinzy_vault[call.message.chat.id]["filtered"] = filtered
    
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = await bot.send_message(call.message.chat.id, "📤 <b>Step 2:</b> Send the target <b>Channel Username</b> (@...):")
    bot.register_next_step_handler(msg, process_channel_limit_step)

async def process_channel_limit_step(m):
    """Checks the target channel and calculates remaining slots."""
    channel_username = m.text.replace("https://t.me/", "@")
    status_msg = await bot.send_message(m.chat.id, f"📡 Checking slots in {channel_username}...")
    
    slots, current = await check_channel_limit(channel_username)
    
    if isinstance(slots, str):
        return await bot.edit_message_text(f"❌ <b>Limit Check Error:</b> {slots}", m.chat.id, status_msg.message_id)
    
    if slots <= 0:
        return await bot.edit_message_text(f"❌ <b>Limit Reached!</b>\n{channel_username} already has {current} members.", m.chat.id, status_msg.message_id)

    # Prepare final list based on slots
    filtered_list = vinzy_vault[m.chat.id].get("filtered", [])
    to_add = filtered_list[:slots]
    
    vinzy_vault[m.chat.id]["final_list"] = to_add
    vinzy_vault[m.chat.id]["target"] = channel_username

    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("🚀 START ADDING NOW", callback_data="execute_add"))
    
    confirm_text = (
        f"📈 <b>Slot Check:</b> {current}/200\n"
        f"🎯 <b>Action:</b> Adding <b>{len(to_add)}</b> members to reach limit.\n"
        f"⚡ <b>Mode:</b> Slow Anti-Ban (45s Delay)\n\n"
        f"Proceed with Finder session?"
    )
    await bot.edit_message_text(confirm_text, m.chat.id, status_msg.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "execute_add")
async def trigger_invite_engine(call):
    """Activates the final invitation loop."""
    chat_id = call.message.chat.id
    data = vinzy_vault.get(chat_id)
    
    if not data or "final_list" not in data:
        return await bot.answer_callback_query(call.id, "Error: Data lost. Restart with /start.")

    await bot.edit_message_text("🎬 <b>Invite Process Started.</b>\nAdding users every 45s...", chat_id, call.message.message_id, parse_mode="HTML")
    
    asyncio.create_task(invite_worker(chat_id, data["final_list"], data["target"]))

async def invite_worker(chat_id, members, target):
    """The actual worker that performs the invites with delays."""
    client = await get_finder_client()
    success = 0
    
    try:
        channel_entity = await client.get_entity(target)
        
        for index, user in enumerate(members):
            try:
                # The Finder performs the invite
                await client(functions.channels.InviteToChannelRequest(
                    channel_entity, 
                    [user["id"]]
                ))
                success += 1
                
                # Update every 5 successful adds
                if success % 5 == 0 or success == len(members):
                    await bot.send_message(chat_id, f"⏳ <b>Progress Update:</b> {success}/{len(members)} added to {target}.")
                
                # Standard Anti-Ban Delay
                await asyncio.sleep(45)
                
            except errors.FloodWaitError as e:
                await bot.send_message(chat_id, f"⚠️ <b>Flood Wait:</b> Sleeping for {e.seconds}s...")
                await asyncio.sleep(e.seconds)
            except errors.UserPrivacyRestrictedError:
                continue # User blocked invites
            except Exception as e:
                logger.warning(f"Invite failed for user {user['id']}: {e}")
                continue
        
        await bot.send_message(chat_id, f"🏁 <b>Operation Complete!</b>\nSuccessfully added {success} members to <code>{target}</code>.")
        
    except Exception as e:
        await bot.send_message(chat_id, f"❌ <b>Critical Worker Error:</b> {str(e)}")

# --- 5. EXECUTION ENTRY POINT ---

async def startup():
    """Main loop initializer."""
    print("="*40)
    print("VINZY SMART ADDER V4.8 IS NOW ONLINE")
    print(f"TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*40)
    
    # Pre-connect the finder
    await get_finder_client()
    
    # Start bot polling
    await bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    try:
        asyncio.run(startup())
    except KeyboardInterrupt:
        print("\nSystem offline. Goodbye, Overlord.")
