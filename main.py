import os
import json
import logging
import requests
from datetime import datetime
from flask import Flask, request
import telebot
from telebot import types

# -------------------- কনফিগারেশন --------------------
BOT_TOKEN = "8711394676:AAEBWeTTCY9_DqLSBiJWcAvn48qCUPflyUQ"
ADMIN_CHAT_ID = 8194390770
JSONBIN_BIN_ID = "69e1de2a856a68218942e52a"
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
SMM_API_KEY = "43f02c483bae7c3b36a646eb764c54cb"
SMM_API_URL = "https://smmsun.com/api/v2"
BKASH_NAGAD_NUMBER = "01830165894"
SUPPORT_USERNAMES = ["@jhgmaing", "@bot_Developer_io"]

# -------------------- সার্ভিস লিস্ট --------------------
SERVICES = {
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
    2730:  {"name": "Telegram Members [No Refill]", "rate_tk": 20},
    2731:  {"name": "Telegram Members [No Refill]", "rate_tk": 47}
}

# Flask app
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# State management
user_states = {}   # user_id -> state
user_temp = {}     # user_id -> temporary data

# -------------------- JSONBin Helpers --------------------
def get_db():
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Master-Key": JSONBIN_MASTER_KEY, "X-Access-Key": JSONBIN_ACCESS_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()["record"]
    except:
        pass
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
    except:
        return False

def get_user_balance(user_id):
    db = get_db()
    uid = str(user_id)
    return float(db["users"].get(uid, {}).get("balance", 0.0))

def update_user_balance(user_id, amount, operation="add"):
    db = get_db()
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {"balance": 0.0, "join_date": datetime.now().isoformat()}
    if operation == "add":
        db["users"][uid]["balance"] = db["users"][uid].get("balance", 0.0) + amount
    elif operation == "set":
        db["users"][uid]["balance"] = amount
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
    return len(db["deposits"]) - 1

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

# -------------------- Helper: Main Menu Keyboard --------------------
def main_menu_markup(user_id):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🛒 সার্ভিস সমূহ", callback_data="menu_services"),
        types.InlineKeyboardButton("👤 প্রোফাইল", callback_data="menu_profile")
    )
    kb.add(
        types.InlineKeyboardButton("💳 ব্যালেন্স যোগ করুন", callback_data="menu_deposit"),
        types.InlineKeyboardButton("📞 সাপোর্ট", callback_data="menu_support")
    )
    kb.add(types.InlineKeyboardButton("📋 অর্ডার হিস্টোরি", callback_data="menu_history"))
    if user_id == ADMIN_CHAT_ID:
        kb.add(types.InlineKeyboardButton("🔐 অ্যাডমিন প্যানেল", callback_data="admin_panel"))
    return kb

def back_button(callback_data="back_to_main"):
    return types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 ফিরুন", callback_data=callback_data))

# -------------------- /start Command --------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    welcome = f"👋 স্বাগতম, {message.from_user.first_name}!\n\n✨ SMM প্যানেল বটে আপনাকে স্বাগতম। নিচের মেনু থেকে অপশন নির্বাচন করুন।"
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu_markup(user_id))

# -------------------- Callback Query Handler (সব ইনলাইন বাটন) --------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    data = call.data

    # ডিবাগ: callback answer
    bot.answer_callback_query(call.id)

    # মেনু নেভিগেশন
    if data == "menu_services":
        show_service_categories(call.message)
    elif data == "menu_profile":
        show_profile(call.message, user_id)
    elif data == "menu_deposit":
        start_deposit(call.message, user_id)
    elif data == "menu_support":
        show_support(call.message)
    elif data == "menu_history":
        show_history(call.message, user_id)
    elif data == "back_to_main":
        edit_to_main_menu(call.message, user_id)
    elif data == "admin_panel":
        if user_id == ADMIN_CHAT_ID:
            show_admin_panel(call.message)
        else:
            bot.answer_callback_query(call.id, "⛔ অননুমোদিত", show_alert=True)

    # ক্যাটাগরি
    elif data.startswith("cat_"):
        category = data.split("_")[1]
        show_services_by_category(call.message, category)
    
    # সার্ভিস সিলেক্ট
    elif data.startswith("service_"):
        service_id = int(data.split("_")[1])
        select_service(call.message, user_id, service_id)

    # অ্যাডমিন একশন
    elif data == "admin_users":
        if user_id == ADMIN_CHAT_ID:
            admin_show_users(call.message)
    elif data == "admin_deposits":
        if user_id == ADMIN_CHAT_ID:
            admin_show_pending_deposits(call.message)
    elif data.startswith("approve_"):
        if user_id == ADMIN_CHAT_ID:
            idx = int(data.split("_")[1])
            admin_approve_deposit(call.message, idx)
    elif data.startswith("reject_"):
        if user_id == ADMIN_CHAT_ID:
            idx = int(data.split("_")[1])
            admin_reject_deposit(call.message, idx)
    elif data.startswith("addbal_"):
        # admin wants to add balance: addbal_<target_user_id>
        if user_id == ADMIN_CHAT_ID:
            target_uid = data.split("_")[1]
            user_states[user_id] = {"state": "admin_addbal", "target": target_uid}
            bot.edit_message_text(
                f"💲 ইউজার {target_uid} এর জন্য কত টাকা যোগ/কাট করবেন? (নেগেটিভ সংখ্যা দিন কাটতে)",
                chat_id, call.message.message_id,
                reply_markup=back_button("admin_panel")
            )
    elif data == "admin_back":
        show_admin_panel(call.message)

# -------------------- Category and Service Display --------------------
def show_service_categories(message):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👁️ টেলিগ্রাম পোস্ট ভিউজ", callback_data="cat_views"),
        types.InlineKeyboardButton("❤️ টেলিগ্রাম রিঅ্যাকশন", callback_data="cat_reactions"),
        types.InlineKeyboardButton("👥 টেলিগ্রাম মেম্বার", callback_data="cat_members"),
        types.InlineKeyboardButton("🔙 মেইন মেনু", callback_data="back_to_main")
    )
    bot.edit_message_text("📂 ক্যাটাগরি নির্বাচন করুন:", message.chat.id, message.message_id, reply_markup=kb)

def show_services_by_category(message, category):
    services = []
    if category == "views":
        ids = [138,823,100,136,301,822,199,821,303,304,306,139]
    elif category == "reactions":
        ids = [10788,335,10698,10699,10789,10797,284,330,281,291]
    elif category == "members":
        ids = [2730,2731]
    else:
        ids = []
    for sid in ids:
        if sid in SERVICES:
            services.append((sid, SERVICES[sid]))
    kb = types.InlineKeyboardMarkup(row_width=1)
    for sid, info in services:
        btn_text = f"{info['name']} - {info['rate_tk']}৳/1000"
        kb.add(types.InlineKeyboardButton(btn_text, callback_data=f"service_{sid}"))
    kb.add(types.InlineKeyboardButton("🔙 ক্যাটাগরিতে ফিরুন", callback_data="menu_services"))
    bot.edit_message_text("🛍️ একটি সার্ভিস নির্বাচন করুন:", message.chat.id, message.message_id, reply_markup=kb)

def select_service(message, user_id, service_id):
    service = SERVICES[service_id]
    text = f"📌 *{service['name']}*\n💰 দাম: {service['rate_tk']} টাকা প্রতি ১০০০\n\n🔗 পোস্টের লিংক পাঠান:"
    user_states[user_id] = {"state": "awaiting_link", "service_id": service_id}
    bot.edit_message_text(text, message.chat.id, message.message_id, parse_mode="Markdown")
    bot.send_message(message.chat.id, "👉 টেলিগ্রাম পোস্টের লিংকটি এখানে লিখুন:", reply_markup=types.ForceReply(selective=True))

# -------------------- Profile, Support, History --------------------
def show_profile(message, user_id):
    bal = get_user_balance(user_id)
    text = f"👤 ইউজার আইডি: `{user_id}`\n💰 বর্তমান ব্যালেন্স: {bal:.2f} টাকা"
    kb = back_button()
    bot.edit_message_text(text, message.chat.id, message.message_id, parse_mode="Markdown", reply_markup=kb)

def show_support(message):
    text = "📞 সাপোর্ট কন্টাক্ট:\n" + "\n".join(SUPPORT_USERNAMES)
    bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=back_button())

def show_history(message, user_id):
    db = get_db()
    orders = [o for o in db["orders"] if o["user_id"] == user_id]
    if not orders:
        text = "❌ কোনো অর্ডার পাওয়া যায়নি।"
    else:
        text = "📋 আপনার শেষ ১০টি অর্ডার:\n\n"
        for o in orders[-10:][::-1]:
            text += f"🔹 {o['service_name']}\n📦 {o['quantity']} | 💰 {o['cost']}৳\n🆔 {o.get('api_order_id','N/A')}\n\n"
    bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=back_button())

def edit_to_main_menu(message, user_id):
    bot.edit_message_text("🔽 মেইন মেনু:", message.chat.id, message.message_id, reply_markup=main_menu_markup(user_id))

# -------------------- Deposit Flow --------------------
def start_deposit(message, user_id):
    user_states[user_id] = {"state": "deposit_amount"}
    bot.edit_message_text(
        "💵 কত টাকা ডিপোজিট করতে চান?\n(ন্যূনতম ১০ টাকা, শুধু সংখ্যা লিখুন)",
        message.chat.id, message.message_id,
        reply_markup=back_button()
    )

# -------------------- Text Message Handler (States) --------------------
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo'])
def handle_messages(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # অ্যাডমিন অ্যাড ব্যালেন্স স্টেট
    if user_id in user_states and user_states[user_id].get("state") == "admin_addbal":
        if user_id != ADMIN_CHAT_ID:
            return
        try:
            amount = float(message.text.strip())
        except:
            bot.reply_to(message, "❌ বৈধ সংখ্যা লিখুন")
            return
        target_uid = user_states[user_id]["target"]
        update_user_balance(int(target_uid), amount, "add")
        new_bal = get_user_balance(int(target_uid))
        bot.send_message(chat_id, f"✅ ইউজার {target_uid} এর ব্যালেন্স আপডেট হয়েছে। বর্তমান ব্যালেন্স: {new_bal:.2f} টাকা")
        # notify target
        try:
            bot.send_message(int(target_uid), f"💰 আপনার ব্যালেন্সে {amount:.2f} টাকা {'যোগ' if amount>0 else 'কাটা'} হয়েছে। বর্তমান ব্যালেন্স: {new_bal:.2f} টাকা")
        except:
            pass
        del user_states[user_id]
        show_admin_panel_by_chat(chat_id)
        return

    # ডিপোজিট এমাউন্ট ইনপুট
    if user_id in user_states and user_states[user_id].get("state") == "deposit_amount":
        try:
            amount = float(message.text.strip())
            if amount < 10:
                bot.reply_to(message, "❌ ন্যূনতম ডিপোজিট ১০ টাকা। আবার চেষ্টা করুন:")
                return
        except:
            bot.reply_to(message, "❌ দয়া করে বৈধ সংখ্যা লিখুন:")
            return
        user_states[user_id] = {"state": "deposit_screenshot", "amount": amount}
        bot.send_message(chat_id,
            f"📱 *{BKASH_NAGAD_NUMBER}* (বিকাশ/নগদ)\n\n"
            f"উপরের নম্বরে *{amount}* টাকা সেন্ড করে স্ক্রিনশট পাঠান।",
            parse_mode="Markdown"
        )
        return

    # ডিপোজিট স্ক্রিনশট
    if user_id in user_states and user_states[user_id].get("state") == "deposit_screenshot":
        if not message.photo:
            bot.reply_to(message, "❌ দয়া করে একটি স্ক্রিনশট ইমেজ পাঠান।")
            return
        amount = user_states[user_id]["amount"]
        photo_id = message.photo[-1].file_id
        deposit_idx = add_deposit_request(user_id, amount, photo_id)
        # অ্যাডমিনকে নোটিফাই
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ অনুমোদন", callback_data=f"approve_{deposit_idx}"),
            types.InlineKeyboardButton("❌ বাতিল", callback_data=f"reject_{deposit_idx}")
        )
        bot.send_photo(
            ADMIN_CHAT_ID,
            photo_id,
            caption=f"🆕 ডিপোজিট #{deposit_idx}\n👤 ইউজার: {user_id}\n💰 পরিমাণ: {amount} টাকা",
            reply_markup=kb
        )
        bot.send_message(chat_id, "✅ আপনার ডিপোজিট রিকোয়েস্ট জমা হয়েছে। অ্যাডমিন অনুমোদন করলে ব্যালেন্স যোগ হবে।")
        del user_states[user_id]
        return

    # অর্ডারের লিংক ইনপুট
    if user_id in user_states and user_states[user_id].get("state") == "awaiting_link":
        link = message.text.strip()
        if not link.startswith("https://t.me/"):
            bot.reply_to(message, "❌ দয়া করে বৈধ টেলিগ্রাম পোস্ট লিংক দিন।")
            return
        service_id = user_states[user_id]["service_id"]
        user_temp[user_id] = {"service_id": service_id, "link": link}
        user_states[user_id] = {"state": "awaiting_quantity", "service_id": service_id}
        service = SERVICES[service_id]
        bot.reply_to(message,
            f"📦 আপনি কত পরিমাণ চান? (ন্যূনতম 1000, 1000 এর গুণিতক)\n"
            f"💰 দাম: {service['rate_tk']} টাকা প্রতি 1000"
        )
        return

    # অর্ডারের পরিমাণ ইনপুট
    if user_id in user_states and user_states[user_id].get("state") == "awaiting_quantity":
        try:
            qty = int(message.text.strip())
        except:
            bot.reply_to(message, "❌ দয়া করে সংখ্যা লিখুন।")
            return
        if qty < 1000:
            bot.reply_to(message, "❌ ন্যূনতম পরিমাণ 1000।")
            return
        if qty % 1000 != 0:
            bot.reply_to(message, "❌ পরিমাণ 1000 এর গুণিতক হতে হবে।")
            return

        service_id = user_states[user_id]["service_id"]
        link = user_temp[user_id]["link"]
        service = SERVICES[service_id]
        cost = (qty / 1000) * service["rate_tk"]
        balance = get_user_balance(user_id)
        if balance < cost:
            bot.reply_to(message,
                f"❌ অপর্যাপ্ত ব্যালেন্স।\nআপনার ব্যালেন্স: {balance:.2f} টাকা\nপ্রয়োজন: {cost:.2f} টাকা"
            )
            del user_states[user_id]
            user_temp.pop(user_id, None)
            return

        api_order_id, error = place_order_to_api(service_id, link, qty)
        if error:
            bot.reply_to(message, f"❌ API সমস্যা: {error}")
            del user_states[user_id]
            user_temp.pop(user_id, None)
            return

        update_user_balance(user_id, -cost, "add")
        add_order(user_id, service_id, qty, link, cost, api_order_id)
        bot.send_message(chat_id,
            f"✅ অর্ডার সাবমিট হয়েছে!\n"
            f"🆔 অর্ডার আইডি: {api_order_id}\n"
            f"📦 {service['name']}\n"
            f"🔢 পরিমাণ: {qty}\n"
            f"💰 খরচ: {cost:.2f} টাকা"
        )
        del user_states[user_id]
        user_temp.pop(user_id, None)
        return

    # যদি কোনো স্টেট না থাকে, তাহলে ইগনোর অথবা হেল্প
    bot.reply_to(message, "দয়া করে মেনু থেকে বাটন ব্যবহার করুন। /start")

# -------------------- Admin Panel Functions --------------------
def show_admin_panel(message):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👥 সকল ইউজার", callback_data="admin_users"),
        types.InlineKeyboardButton("💰 পেন্ডিং ডিপোজিট", callback_data="admin_deposits"),
        types.InlineKeyboardButton("🔙 মেইন মেনু", callback_data="back_to_main")
    )
    bot.edit_message_text("🔐 অ্যাডমিন প্যানেল", message.chat.id, message.message_id, reply_markup=kb)

def show_admin_panel_by_chat(chat_id):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👥 সকল ইউজার", callback_data="admin_users"),
        types.InlineKeyboardButton("💰 পেন্ডিং ডিপোজিট", callback_data="admin_deposits"),
        types.InlineKeyboardButton("🔙 মেইন মেনু", callback_data="back_to_main")
    )
    bot.send_message(chat_id, "🔐 অ্যাডমিন প্যানেল", reply_markup=kb)

def admin_show_users(message):
    db = get_db()
    users = db["users"]
    if not users:
        text = "কোনো ইউজার নেই।"
    else:
        text = "👥 নিবন্ধিত ইউজার:\n\n"
        for uid, data in users.items():
            bal = data.get("balance", 0.0)
            text += f"🆔 {uid} : {bal:.2f} টাকা  [➕](callback:addbal_{uid})\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_panel"))
    bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=kb, parse_mode="Markdown")

def admin_show_pending_deposits(message):
    db = get_db()
    pending = [d for d in db["deposits"] if d["status"] == "pending"]
    if not pending:
        bot.edit_message_text("✅ কোনো পেন্ডিং ডিপোজিট নেই।", message.chat.id, message.message_id,
                              reply_markup=back_button("admin_panel"))
        return
    text = "📥 পেন্ডিং ডিপোজিটসমূহ (অনুমোদন করতে নিচের নোটিফিকেশনের বাটন ব্যবহার করুন):\n"
    for idx, d in enumerate(db["deposits"]):
        if d["status"] == "pending":
            text += f"#{idx}: ইউজার {d['user_id']} - {d['amount']} টাকা\n"
    bot.edit_message_text(text, message.chat.id, message.message_id,
                          reply_markup=back_button("admin_panel"))

def admin_approve_deposit(message, idx):
    db = get_db()
    if idx >= len(db["deposits"]):
        bot.answer_callback_query(message.id, "রেকর্ড নেই", show_alert=True)
        return
    deposit = db["deposits"][idx]
    if deposit["status"] != "pending":
        bot.answer_callback_query(message.id, "ইতিমধ্যে প্রসেস করা হয়েছে", show_alert=True)
        return
    deposit["status"] = "approved"
    user_id = deposit["user_id"]
    amount = deposit["amount"]
    update_user_balance(user_id, amount, "add")
    save_db(db)
    try:
        bot.send_message(user_id, f"✅ আপনার {amount} টাকার ডিপোজিট অনুমোদিত হয়েছে। নতুন ব্যালেন্স: {get_user_balance(user_id):.2f} টাকা")
    except:
        pass
    bot.edit_message_caption(
        caption=message.message.caption + "\n\n✅ অনুমোদিত",
        chat_id=message.message.chat.id,
        message_id=message.message.message_id
    )

def admin_reject_deposit(message, idx):
    db = get_db()
    if idx >= len(db["deposits"]):
        bot.answer_callback_query(message.id, "রেকর্ড নেই", show_alert=True)
        return
    deposit = db["deposits"][idx]
    deposit["status"] = "rejected"
    save_db(db)
    try:
        bot.send_message(deposit["user_id"], f"❌ আপনার {deposit['amount']} টাকার ডিপোজিট বাতিল করা হয়েছে।")
    except:
        pass
    bot.edit_message_caption(
        caption=message.message.caption + "\n\n❌ বাতিল",
        chat_id=message.message.chat.id,
        message_id=message.message.message_id
    )

# -------------------- Flask Webhook Routes --------------------
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Bad request', 400

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    url = request.args.get("url")
    if not url:
        return "Missing 'url' parameter"
    webhook_url = f"{url}/webhook"
    bot.remove_webhook()
    success = bot.set_webhook(webhook_url)
    if success:
        return f"Webhook set to {webhook_url}"
    else:
        return "Failed to set webhook"

# -------------------- Run --------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
