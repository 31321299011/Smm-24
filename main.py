import os
import json
import logging
import requests
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# -------------------- কনফিগারেশন (তোর দেওয়া) --------------------
BOT_TOKEN = "8711394676:AAEBWeTTCY9_DqLSBiJWcAvn48qCUPflyUQ"
ADMIN_CHAT_ID = 8194390770
JSONBIN_BIN_ID = "69e1de2a856a68218942e52a"
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
SMM_API_KEY = "43f02c483bae7c3b36a646eb764c54cb"
SMM_API_URL = "https://smmsun.com/api/v2"
BKASH_NAGAD_NUMBER = "01830165894"
SUPPORT_USERNAMES = ["@jhgmaing", "@bot_Developer_io"]

# -------------------- সার্ভিস লিস্ট (ID -> নাম ও প্রতি ১০০০ এর দাম টাকায়) --------------------
SERVICES = {
    # Views
    138:  {"name": "Telegram Post Views [Instant][1 Post]", "rate_tk": 35},
    823:  {"name": "Telegram Post Views [Instant][Non Drop]", "rate_tk": 45},
    100:  {"name": "Telegram Post Views [Instant][1 Post]", "rate_tk": 38},
    136:  {"name": "Telegram Post Views [Instant][1 Post]", "rate_tk": 65},
    301:  {"name": "Telegram Post Views [Instant][1 Post]", "rate_tk": 46},
    822:  {"name": "Telegram Post Views [Real and Active]", "rate_tk": 46},
    199:  {"name": "Telegram Post Views [Instant]", "rate_tk": 39},
    821:  {"name": "Telegram Post Views [Non Drop]", "rate_tk": 39},
    303:  {"name": "Telegram Post Views [Last 5 Post]", "rate_tk": 12},
    304:  {"name": "Telegram Post Views [Last 10 Post]", "rate_tk": 19},
    306:  {"name": "Telegram Post Views [Last 20 Post]", "rate_tk": 32},
    139:  {"name": "Telegram Post Views [Last 50 Post]", "rate_tk": 59},
    # Reactions
    10788: {"name": "Telegram Positive Mix Reactions", "rate_tk": 7},
    335:   {"name": "Telegram Positive Mix Reactions", "rate_tk": 7},
    10698: {"name": "Mix Positive Reactions + Bonus Views", "rate_tk": 8},
    10699: {"name": "Mix Negative Reactions + Bonus Views", "rate_tk": 8},
    10789: {"name": "Positive Mix (High Quality)", "rate_tk": 8},
    10797: {"name": "Reactions (❤️😍👍🥰🔥)", "rate_tk": 19},
    284:   {"name": "Premium Reactions [💯]", "rate_tk": 24},
    330:   {"name": "Like (👍) Reaction + Free Views", "rate_tk": 25},
    281:   {"name": "Premium Reactions (Single Emoji)", "rate_tk": 28},
    291:   {"name": "Premium Positive Mix", "rate_tk": 28},
    # Members
    2730:  {"name": "Telegram Members [No Refill]", "rate_tk": 20},
    2731:  {"name": "Telegram Members [No Refill]", "rate_tk": 47}
}

# Conversation states
DEPOSIT_AMOUNT, DEPOSIT_SCREENSHOT = range(2)

# Flask app for webhook
flask_app = Flask(__name__)

# -------------------- JSONBin Helper Functions --------------------
def get_db():
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Master-Key": JSONBIN_MASTER_KEY, "X-Access-Key": JSONBIN_ACCESS_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()["record"]
        else:
            logging.error(f"JSONBin get error: {resp.text}")
            return {"users": {}, "deposits": [], "orders": [], "settings": {"bkash_nagad": BKASH_NAGAD_NUMBER, "admin_id": ADMIN_CHAT_ID}}
    except Exception as e:
        logging.error(f"JSONBin get exception: {e}")
        return {"users": {}, "deposits": [], "orders": [], "settings": {"bkash_nagad": BKASH_NAGAD_NUMBER, "admin_id": ADMIN_CHAT_ID}}

def save_db(data):
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {
        "X-Master-Key": JSONBIN_MASTER_KEY,
        "X-Access-Key": JSONBIN_ACCESS_KEY,
        "Content-Type": "application/json"
    }
    try:
        resp = requests.put(url, json=data, headers=headers, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logging.error(f"JSONBin save exception: {e}")
        return False

# -------------------- Helper Functions --------------------
def get_user_balance(user_id):
    db = get_db()
    user_id_str = str(user_id)
    if user_id_str in db["users"]:
        return float(db["users"][user_id_str].get("balance", 0.0))
    else:
        # নতুন ইউজার অ্যাড করব না এখনই, শুধু 0 রিটার্ন করব
        return 0.0

def update_user_balance(user_id, amount, operation="add"):  # operation: "add" or "set"
    db = get_db()
    user_id_str = str(user_id)
    if user_id_str not in db["users"]:
        db["users"][user_id_str] = {"balance": 0.0, "join_date": datetime.now().isoformat()}
    if operation == "add":
        db["users"][user_id_str]["balance"] = float(db["users"][user_id_str].get("balance", 0.0)) + amount
    elif operation == "set":
        db["users"][user_id_str]["balance"] = amount
    return save_db(db)

def add_deposit_request(user_id, amount, screenshot_id):
    db = get_db()
    deposit = {
        "user_id": user_id,
        "amount": amount,
        "screenshot_id": screenshot_id,
        "status": "pending",
        "timestamp": datetime.now().isoformat()
    }
    db["deposits"].append(deposit)
    save_db(db)
    return len(db["deposits"]) - 1  # deposit index

def add_order(user_id, service_id, quantity, link, cost, api_order_id):
    db = get_db()
    order = {
        "user_id": user_id,
        "service_id": service_id,
        "service_name": SERVICES[service_id]["name"],
        "quantity": quantity,
        "link": link,
        "cost": cost,
        "api_order_id": api_order_id,
        "status": "submitted",
        "timestamp": datetime.now().isoformat()
    }
    db["orders"].append(order)
    save_db(db)

# -------------------- SMM API Call --------------------
def place_order_to_api(service_id, link, quantity):
    params = {
        "key": SMM_API_KEY,
        "action": "add",
        "service": service_id,
        "link": link,
        "quantity": quantity
    }
    try:
        resp = requests.get(SMM_API_URL, params=params, timeout=30)
        data = resp.json()
        if "order" in data:
            return data["order"], None
        else:
            return None, data.get("error", "Unknown API error")
    except Exception as e:
        return None, str(e)

# -------------------- Bot Handlers --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"👋 স্বাগতম, {user.first_name}!\n\n"
        "✨ এটি SMM প্যানেল বট। এখানে আপনি টেলিগ্রামের ভিউ, রিঅ্যাকশন, মেম্বার কিনতে পারবেন।\n\n"
        "💰 নিচের মেনু থেকে কাজ নির্বাচন করুন।"
    )
    keyboard = [
        [InlineKeyboardButton("🛒 সার্ভিস সমূহ", callback_data="menu_services")],
        [InlineKeyboardButton("👤 আমার প্রোফাইল", callback_data="menu_profile"),
         InlineKeyboardButton("💳 ব্যালেন্স যোগ করুন", callback_data="menu_deposit")],
        [InlineKeyboardButton("📞 সাপোর্ট", callback_data="menu_support"),
         InlineKeyboardButton("📋 অর্ডার হিস্টোরি", callback_data="menu_history")]
    ]
    # অ্যাডমিন বাটন শুধু অ্যাডমিনের জন্য
    if user.id == ADMIN_CHAT_ID:
        keyboard.append([InlineKeyboardButton("🔐 অ্যাডমিন প্যানেল", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "menu_services":
        await show_services(query)
    elif data == "menu_profile":
        await show_profile(query, user_id)
    elif data == "menu_deposit":
        await start_deposit(query, context)
    elif data == "menu_support":
        await show_support(query)
    elif data == "menu_history":
        await show_history(query, user_id)
    elif data == "admin_panel":
        if user_id == ADMIN_CHAT_ID:
            await show_admin_panel(query)
        else:
            await query.edit_message_text("⛔ অননুমোদিত অ্যাক্সেস।")
    elif data.startswith("service_"):
        service_id = int(data.split("_")[1])
        context.user_data["selected_service"] = service_id
        await ask_for_link(query)
    elif data == "back_to_main":
        await start(update, context)
    elif data == "admin_users":
        if user_id == ADMIN_CHAT_ID:
            await admin_list_users(query)
        else:
            await query.answer("অ্যাক্সেস নেই", show_alert=True)
    elif data == "admin_deposits":
        if user_id == ADMIN_CHAT_ID:
            await admin_list_deposits(query)
        else:
            await query.answer("অ্যাক্সেস নেই", show_alert=True)
    elif data.startswith("approve_"):
        if user_id == ADMIN_CHAT_ID:
            deposit_index = int(data.split("_")[1])
            await admin_approve_deposit(query, deposit_index)
    elif data.startswith("reject_"):
        if user_id == ADMIN_CHAT_ID:
            deposit_index = int(data.split("_")[1])
            await admin_reject_deposit(query, deposit_index)
    elif data.startswith("addbal_"):
        # admin add balance to user: format addbal_<user_id>
        parts = data.split("_")
        target_user = parts[1]
        context.user_data["admin_addbal_user"] = target_user
        await query.edit_message_text(
            f"💲 {target_user} ইউজারের জন্য কত টাকা যোগ করতে চান?\n"
            "শুধু সংখ্যা লিখুন (কাটতে চাইলে নেগেটিভ সংখ্যা দিন যেমন -100):"
        )
        return  # conversation-এ যাবে না, এক্ষেত্রে আমরা আলাদা handler দিব
    elif data.startswith("userorders_"):
        if user_id == ADMIN_CHAT_ID:
            target = data.split("_")[1]
            await show_history_for_admin(query, target)
    elif data == "admin_back":
        await show_admin_panel(query)
    else:
        await query.edit_message_text("❌ অজানা কমান্ড। /start দিয়ে আবার শুরু করুন।")

# -------------------- Service Display --------------------
async def show_services(query):
    # Category selection
    keyboard = [
        [InlineKeyboardButton("👁️ টেলিগ্রাম পোস্ট ভিউজ", callback_data="cat_views")],
        [InlineKeyboardButton("❤️ টেলিগ্রাম রিঅ্যাকশন", callback_data="cat_reactions")],
        [InlineKeyboardButton("👥 টেলিগ্রাম মেম্বার", callback_data="cat_members")],
        [InlineKeyboardButton("🔙 মেইন মেনু", callback_data="back_to_main")]
    ]
    await query.edit_message_text("📂 ক্যাটাগরি নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(keyboard))

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.split("_")[1]
    services = []
    for sid, info in SERVICES.items():
        if cat == "views" and sid in [138,823,100,136,301,822,199,821,303,304,306,139]:
            services.append((sid, info))
        elif cat == "reactions" and sid in [10788,335,10698,10699,10789,10797,284,330,281,291]:
            services.append((sid, info))
        elif cat == "members" and sid in [2730,2731]:
            services.append((sid, info))
    if not services:
        await query.edit_message_text("কোনো সার্ভিস পাওয়া যায়নি।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরুন", callback_data="menu_services")]]))
        return
    keyboard = []
    for sid, info in services:
        btn = InlineKeyboardButton(f"{info['name']} - {info['rate_tk']}৳/1000", callback_data=f"service_{sid}")
        keyboard.append([btn])
    keyboard.append([InlineKeyboardButton("🔙 ক্যাটাগরিতে ফিরুন", callback_data="menu_services")])
    await query.edit_message_text("🛍️ একটি সার্ভিস নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_for_link(query):
    service_id = query.data.split("_")[1]
    service = SERVICES[int(service_id)]
    text = (
        f"📌 সার্ভিস: {service['name']}\n"
        f"💰 দাম: {service['rate_tk']} টাকা প্রতি ১০০০\n\n"
        "🔗 পোস্টের লিংক দিন (যেমন https://t.me/username/123):\n"
        "⏳ অর্ডার কনফার্ম করতে লিংক পাঠানোর পর পরিমাণ জিজ্ঞেস করা হবে।"
    )
    context = query._bot.callback_query_data.get('context')  # tricky but we'll store in user_data
    # Actually we'll use a MessageHandler to catch the link
    await query.edit_message_text(text)
    # Set state for conversation
    context.user_data["awaiting_link_for_service"] = int(service_id)
    return "WAITING_LINK"

# -------------------- Profile, History, Support --------------------
async def show_profile(query, user_id):
    balance = get_user_balance(user_id)
    text = f"👤 ইউজার আইডি: `{user_id}`\n💰 বর্তমান ব্যালেন্স: {balance:.2f} টাকা"
    keyboard = [[InlineKeyboardButton("🔙 মেইন মেনু", callback_data="back_to_main")]]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_support(query):
    text = "📞 সাপোর্ট কন্টাক্ট:\n" + "\n".join(SUPPORT_USERNAMES)
    keyboard = [[InlineKeyboardButton("🔙 মেইন মেনু", callback_data="back_to_main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_history(query, user_id):
    db = get_db()
    user_orders = [o for o in db["orders"] if o["user_id"] == user_id]
    if not user_orders:
        text = "আপনার কোনো অর্ডার নেই।"
    else:
        text = "📋 আপনার শেষ ১০টি অর্ডার:\n\n"
        for o in user_orders[-10:][::-1]:
            text += f"🔹 {o['service_name']}\n📦 পরিমাণ: {o['quantity']}\n💰 খরচ: {o['cost']} টাকা\n🆔 API ID: {o.get('api_order_id','N/A')}\n📅 {o['timestamp'][:10]}\n\n"
    keyboard = [[InlineKeyboardButton("🔙 মেইন মেনু", callback_data="back_to_main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_history_for_admin(query, target_user_id):
    db = get_db()
    user_orders = [o for o in db["orders"] if str(o["user_id"]) == target_user_id]
    if not user_orders:
        text = f"ইউজার {target_user_id} এর কোনো অর্ডার নেই।"
    else:
        text = f"📋 ইউজার {target_user_id} এর অর্ডারসমূহ:\n\n"
        for o in user_orders[-15:][::-1]:
            text += f"🔹 {o['service_name']}\n📦 {o['quantity']} | 💰 {o['cost']}৳\n🔗 {o['link']}\n🆔 {o.get('api_order_id','N/A')}\n\n"
    keyboard = [[InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# -------------------- Deposit Flow (Conversation) --------------------
async def start_deposit(query, context):
    await query.edit_message_text(
        "💵 কত টাকা ডিপোজিট করতে চান?\n"
        "শুধু সংখ্যা লিখুন (ন্যূনতম ১০ টাকা):"
    )
    return DEPOSIT_AMOUNT

async def deposit_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
        if amount < 10:
            await update.message.reply_text("❌ ন্যূনতম ডিপোজিট ১০ টাকা। আবার চেষ্টা করুন।")
            return DEPOSIT_AMOUNT
        context.user_data["deposit_amount"] = amount
        await update.message.reply_text(
            f"📱 {BKASH_NAGAD_NUMBER} (বিকাশ/নগদ)\n\n"
            f"উপরের নম্বরে {amount} টাকা সেন্ড করে স্ক্রিনশট পাঠান।"
        )
        return DEPOSIT_SCREENSHOT
    except ValueError:
        await update.message.reply_text("❌ দয়া করে বৈধ সংখ্যা লিখুন।")
        return DEPOSIT_AMOUNT

async def deposit_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ দয়া করে একটি স্ক্রিনশট ইমেজ পাঠান।")
        return DEPOSIT_SCREENSHOT
    user_id = update.effective_user.id
    amount = context.user_data["deposit_amount"]
    photo_file_id = update.message.photo[-1].file_id
    deposit_index = add_deposit_request(user_id, amount, photo_file_id)
    # অ্যাডমিনকে নোটিফাই
    await context.bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=photo_file_id,
        caption=f"🆕 ডিপোজিট রিকোয়েস্ট #{deposit_index}\n👤 ইউজার: {user_id}\n💰 পরিমাণ: {amount} টাকা",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ অনুমোদন", callback_data=f"approve_{deposit_index}"),
             InlineKeyboardButton("❌ বাতিল", callback_data=f"reject_{deposit_index}")]
        ])
    )
    await update.message.reply_text(
        "✅ আপনার ডিপোজিট রিকোয়েস্ট জমা হয়েছে। অ্যাডমিন অনুমোদন করলেই ব্যালেন্স যোগ হবে।"
    )
    # End conversation
    return ConversationHandler.END

async def cancel_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ ডিপোজিট প্রক্রিয়া বাতিল করা হয়েছে।")
    return ConversationHandler.END

# -------------------- Admin Handlers --------------------
async def show_admin_panel(query):
    keyboard = [
        [InlineKeyboardButton("👥 সকল ইউজার", callback_data="admin_users")],
        [InlineKeyboardButton("💰 পেন্ডিং ডিপোজিট", callback_data="admin_deposits")],
        [InlineKeyboardButton("➕ ইউজার ব্যালেন্স যোগ/কাট", callback_data="admin_addbal")],
        [InlineKeyboardButton("🔙 মেইন মেনু", callback_data="back_to_main")]
    ]
    await query.edit_message_text("🔐 অ্যাডমিন প্যানেল", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_list_users(query):
    db = get_db()
    users = db["users"]
    if not users:
        text = "কোনো ইউজার নেই।"
    else:
        text = "👥 নিবন্ধিত ইউজারগণ:\n\n"
        for uid, data in users.items():
            bal = data.get("balance", 0.0)
            text += f"🆔 {uid} : {bal:.2f} টাকা\n"
    keyboard = [
        [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_panel")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_list_deposits(query):
    db = get_db()
    pending = [d for d in db["deposits"] if d["status"] == "pending"]
    if not pending:
        await query.edit_message_text("✅ কোনো পেন্ডিং ডিপোজিট নেই।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরুন", callback_data="admin_panel")]]))
        return
    # প্রতিটি পেন্ডিং দেখানো হবে, কিন্তু এখানে আমরা শুধু মেসেজ দিব যে নিচে বাটন থেকে অ্যাকশন নিতে হবে।
    # তবে ইতিমধ্যে অ্যাডমিন নোটিফিকেশন পেয়েছে, তাই এখানে শুধু লিস্ট
    text = "📥 পেন্ডিং ডিপোজিটসমূহ:\n"
    for idx, d in enumerate(pending):
        if d["status"] == "pending":
            text += f"#{db['deposits'].index(d)}: ইউজার {d['user_id']} - {d['amount']} টাকা\n"
    text += "\nঅনুমোদন/বাতিল করতে সংশ্লিষ্ট নোটিফিকেশন মেসেজের বাটন ব্যবহার করুন।"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরুন", callback_data="admin_panel")]]))

async def admin_approve_deposit(query, deposit_index):
    db = get_db()
    if deposit_index >= len(db["deposits"]):
        await query.answer("রেকর্ড পাওয়া যায়নি", show_alert=True)
        return
    deposit = db["deposits"][deposit_index]
    if deposit["status"] != "pending":
        await query.answer("ইতিমধ্যে প্রসেস করা হয়েছে", show_alert=True)
        return
    deposit["status"] = "approved"
    user_id = deposit["user_id"]
    amount = deposit["amount"]
    update_user_balance(user_id, amount, "add")
    save_db(db)
    # ইউজারকে নোটিফাই
    try:
        await query.bot.send_message(user_id, f"✅ আপনার {amount} টাকার ডিপোজিট অনুমোদিত হয়েছে। নতুন ব্যালেন্স: {get_user_balance(user_id):.2f} টাকা")
    except:
        pass
    await query.edit_message_caption(caption=query.message.caption + "\n\n✅ অনুমোদিত")
    await query.answer("ডিপোজিট অনুমোদিত হয়েছে।")

async def admin_reject_deposit(query, deposit_index):
    db = get_db()
    if deposit_index >= len(db["deposits"]):
        await query.answer("রেকর্ড পাওয়া যায়নি", show_alert=True)
        return
    deposit = db["deposits"][deposit_index]
    deposit["status"] = "rejected"
    save_db(db)
    try:
        await query.bot.send_message(deposit["user_id"], f"❌ আপনার {deposit['amount']} টাকার ডিপোজিট রিকোয়েস্ট বাতিল করা হয়েছে।")
    except:
        pass
    await query.edit_message_caption(caption=query.message.caption + "\n\n❌ বাতিল করা হয়েছে")
    await query.answer("ডিপোজিট বাতিল করা হয়েছে।")

# -------------------- Order Placement Flow --------------------
async def handle_link_for_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    service_id = context.user_data.get("awaiting_link_for_service")
    if not service_id:
        await update.message.reply_text("দয়া করে প্রথমে সার্ভিস নির্বাচন করুন।")
        return
    link = update.message.text.strip()
    if not link.startswith("https://t.me/"):
        await update.message.reply_text("❌ দয়া করে বৈধ টেলিগ্রাম পোস্ট লিংক দিন।")
        return
    context.user_data["order_link"] = link
    service = SERVICES[service_id]
    await update.message.reply_text(
        f"📦 আপনি কত পরিমাণ চান? (ন্যূনতম 1000, এবং 1000 এর গুণিতক)\n"
        f"উদাহরণ: 1000, 5000, 10000\n"
        f"💰 দাম: {service['rate_tk']} টাকা প্রতি 1000"
    )
    context.user_data["order_service_id"] = service_id
    return "WAITING_QUANTITY"

async def handle_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    service_id = context.user_data["order_service_id"]
    link = context.user_data["order_link"]
    try:
        qty = int(update.message.text.strip())
        if qty < 1000:
            await update.message.reply_text("❌ ন্যূনতম পরিমাণ 1000। আবার চেষ্টা করুন।")
            return "WAITING_QUANTITY"
        if qty % 1000 != 0:
            await update.message.reply_text("❌ পরিমাণ 1000 এর গুণিতক হতে হবে।")
            return "WAITING_QUANTITY"
    except ValueError:
        await update.message.reply_text("❌ দয়া করে সংখ্যা লিখুন।")
        return "WAITING_QUANTITY"

    service = SERVICES[service_id]
    cost = (qty / 1000) * service["rate_tk"]
    balance = get_user_balance(user_id)
    if balance < cost:
        await update.message.reply_text(
            f"❌ অপর্যাপ্ত ব্যালেন্স।\n"
            f"আপনার ব্যালেন্স: {balance:.2f} টাকা\n"
            f"প্রয়োজন: {cost:.2f} টাকা\n"
            f"দয়া করে ডিপোজিট করুন।"
        )
        return ConversationHandler.END

    # Place order via API
    api_order_id, error = place_order_to_api(service_id, link, qty)
    if error:
        await update.message.reply_text(f"❌ অর্ডার সাবমিট করতে সমস্যা হয়েছে:\n{error}")
        return ConversationHandler.END

    # Deduct balance
    update_user_balance(user_id, -cost, "add")
    add_order(user_id, service_id, qty, link, cost, api_order_id)

    await update.message.reply_text(
        f"✅ অর্ডার সফলভাবে সাবমিট হয়েছে!\n"
        f"🆔 অর্ডার আইডি: {api_order_id}\n"
        f"📦 সার্ভিস: {service['name']}\n"
        f"🔢 পরিমাণ: {qty}\n"
        f"💰 খরচ: {cost:.2f} টাকা\n"
        f"🔗 লিংক: {link}\n\n"
        f"ধন্যবাদ!"
    )
    # Clear user_data
    context.user_data.pop("order_service_id", None)
    context.user_data.pop("order_link", None)
    context.user_data.pop("awaiting_link_for_service", None)
    return ConversationHandler.END

# -------------------- Main Application Setup --------------------
def main():
    logging.basicConfig(level=logging.INFO)
    # Create Application
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for deposit
    deposit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_deposit, pattern="^menu_deposit$")],
        states={
            DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount_input)],
            DEPOSIT_SCREENSHOT: [MessageHandler(filters.PHOTO, deposit_screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel_deposit)],
    )

    # Conversation handler for order (link -> quantity)
    order_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link_for_order)],
        states={
            "WAITING_QUANTITY": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity_input)],
        },
        fallbacks=[],
    )

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(menu_|service_|admin_|approve_|reject_|addbal_|userorders_|back_to_main|admin_back|cat_).*"))
    app.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    app.add_handler(deposit_conv)
    app.add_handler(order_conv)
    # Fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: u.message.reply_text("দয়া করে মেনু থেকে বাটন ব্যবহার করুন। /start")))

    return app

# -------------------- Flask Webhook for Render --------------------
app_bot = main()

@flask_app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), app_bot.bot)
        app_bot.process_update(update)
    return "ok"

@flask_app.route("/set_webhook", methods=["GET"])
def set_webhook():
    url = request.args.get("url")
    if not url:
        return "Please provide 'url' query parameter"
    webhook_url = f"{url}/webhook"
    success = app_bot.bot.set_webhook(webhook_url)
    if success:
        return f"Webhook set to {webhook_url}"
    else:
        return "Failed to set webhook"

if __name__ == "__main__":
    # Render will use PORT env variable
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
