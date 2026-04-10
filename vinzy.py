# =========================================================================
# PROJECT: VINZY SMART ADDER V4.5 (KOYEB EDITION)
# AUTHOR: VINZY DIGITAL SERVICES
# DESCRIPTION: ANALYSIS-DRIVEN MEMBER ADDER WITH 200-LIMIT LOGIC
# =========================================================================

import os
import asyncio
import logging
import telebot
from telebot import types as bot_types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.sessions import StringSession

# --- 1. CONFIGURATION (Environment Variables) ---
# When hosting on Koyeb, set these in the "Environment Variables" section.
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VinzyAdder")

bot = telebot.TeleBot(BOT_TOKEN)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Global storage for session data
vinzy_vault = {}

# --- 2. TELETHON LOGIC MODULES ---

async def analyze_group(group_link):
    """Scans group members and filters out bots and deleted accounts."""
    async with client:
        try:
            entity = await client.get_entity(group_link)
            participants = await client.get_participants(entity)
            
            clean_list = []
            stats = {"premium": 0, "normal": 0, "ghosts": 0}
            
            for p in participants:
                if p.bot or p.deleted:
                    stats["ghosts"] += 1
                    continue
                
                is_premium = getattr(p, 'premium', False)
                if is_premium: stats["premium"] += 1
                else: stats["normal"] += 1
                
                clean_list.append({
                    "id": p.id,
                    "premium": is_premium,
                    "name": p.first_name or "User"
                })
            return clean_list, stats
        except Exception as e:
            return str(e), None

async def get_channel_slots(channel_username):
    """Calculates how many spaces are left before the 200 member limit."""
    async with client:
        try:
            entity = await client.get_entity(channel_username)
            full = await client(functions.channels.GetFullChannelRequest(channel=entity))
            current_count = full.full_chat.participants_count
            
            slots_left = 200 - current_count
            return slots_left, current_count
        except Exception as e:
            return str(e), 0

# --- 3. BOT INTERFACE & HANDLERS ---

@bot.message_handler(commands=['start'])
def cmd_start(m):
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚀 Start Smart Scan")
    welcome_text = (
        "<b>Vinzy Smart Manager v4.5</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Ready to fill your channel to the 200 limit.\n"
        "Status: 🟢 Connected to Koyeb"
    )
    bot.send_message(m.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 Start Smart Scan")
def ask_group(m):
    msg = bot.send_message(m.chat.id, "📥 <b>Step 1:</b> Send the <b>Group Link</b> to scan members from:")
    bot.register_next_step_handler(msg, perform_analysis)

def perform_analysis(m):
    bot.send_message(m.chat.id, "🔍 Analyzing group quality... This may take a moment.")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    members, stats = loop.run_until_complete(analyze_group(m.text))
    
    if isinstance(members, str):
        return bot.send_message(m.chat.id, f"❌ <b>Error:</b> {members}")

    vinzy_vault[m.chat.id] = {"scraped": members}
    
    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("👤 Normal Only", callback_data="type_normal"))
    markup.add(bot_types.InlineKeyboardButton("💎 Premium Only", callback_data="type_premium"))
    markup.add(bot_types.InlineKeyboardButton("✅ All (Best Mix)", callback_data="type_all"))
    
    text = (
        f"📊 <b>Scrape Report</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 Normal Users: {stats['normal']}\n"
        f"💎 Premium Users: {stats['premium']}\n"
        f"👻 Ghosts/Bots: {stats['ghosts']} (Filtered)\n\n"
        f"Pick the type of members to add:"
    )
    bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("type_"))
def handle_filter(call):
    mode = call.data.split("_")[1]
    all_m = vinzy_vault[call.message.chat.id]["scraped"]
    
    if mode == "premium":
        filtered = [x for x in all_m if x["premium"]]
    elif mode == "normal":
        filtered = [x for x in all_m if not x["premium"]]
    else:
        filtered = all_m
        
    vinzy_vault[call.message.chat.id]["filtered"] = filtered
    msg = bot.send_message(call.message.chat.id, "📤 <b>Step 2:</b> Send the target <b>Channel Username</b> (@...):")
    bot.register_next_step_handler(msg, process_channel_check)

def process_channel_check(m):
    channel = m.text
    bot.send_message(m.chat.id, f"📡 Checking subscribers in {channel}...")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    slots, current = loop.run_until_complete(get_channel_slots(channel))
    
    if isinstance(slots, str):
        return bot.send_message(m.chat.id, f"❌ <b>Error:</b> {slots}")
    
    if slots <= 0:
        return bot.send_message(m.chat.id, f"❌ <b>Limit Reached!</b>\n{channel} already has {current} members.")

    to_add = vinzy_vault[m.chat.id]["filtered"][:slots]
    vinzy_vault[m.chat.id]["final_list"] = to_add
    vinzy_vault[m.chat.id]["target"] = channel

    text = (
        f"📈 <b>Status:</b> {current}/200 Members\n"
        f"🎯 <b>Action:</b> Adding <b>{len(to_add)}</b> members to reach 200.\n\n"
        f"Click below to start adding slowly (Anti-Ban active)."
    )
    markup = bot_types.InlineKeyboardMarkup()
    markup.add(bot_types.InlineKeyboardButton("🚀 START ADDING", callback_data="execute_add"))
    bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "execute_add")
def final_trigger(call):
    bot.edit_message_text("🎬 <b>Process Started.</b>\nAdding 1 person every 45s...", 
                          call.message.chat.id, call.message.message_id, parse_mode="HTML")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(invite_engine(call.message.chat.id))

async def invite_engine(chat_id):
    members = vinzy_vault[chat_id]["final_list"]
    target = vinzy_vault[chat_id]["target"]
    
    async with client:
        try:
            channel_entity = await client.get_entity(target)
            success = 0
            
            for u in members:
                try:
                    await client(functions.channels.InviteToChannelRequest(channel_entity, [u["id"]]))
                    success += 1
                    if success % 5 == 0:
                        bot.send_message(chat_id, f"⏳ <b>Update:</b> Added {success}/{len(members)}...")
                    
                    await asyncio.sleep(45) # Critical delay to prevent ban
                    
                except errors.UserPrivacyRestrictedError:
                    continue # Skips users who blocked invites
                except errors.FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                except Exception:
                    continue
            
            bot.send_message(chat_id, f"🏁 <b>Done!</b>\nAdded: {success} members.\nChannel: {target}")
        except Exception as e:
            bot.send_message(chat_id, f"❌ <b>Critical Error:</b> {str(e)}")

# --- START ---
if __name__ == "__main__":
    print("Vinzy Smart Adder V4.5 is active.")
    bot.infinity_polling()
