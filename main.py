import telebot
from telebot import types
import requests
import json
import math
from flask import Flask
from threading import Thread

# --- কনফিগারেশন ---
TOKEN = '8711394676:AAEBWeTTCY9_DqLSBiJWcAvn48qCUPflyUQ'
BIN_ID = '69e1de2a856a68218942e52a'
MASTER_KEY = '$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S.'
ACCESS_KEY = '$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya'
ADMIN_ID = 8194390770
SMM_API_KEY = '43f02c483bae7c3b36a646eb764c54cb'
DOLLAR_RATE = 130
EXTRA_FEE = 0.03

bot = telebot.TeleBot(TOKEN)
app = Flask('')

# --- সার্ভিস লিস্ট (আপনার দেওয়া ডাটা) ---
SERVICES = {
    "Views": [
        {"id": 138, "name": "Telegram Post Views [Instant]", "price": 5, "min": 1000},
        {"id": 823, "name": "Telegram Post Views [Non Drop]", "price": 5, "min": 1000},
        {"id": 100, "name": "Telegram Post Views [1 Post]", "price": 5, "min": 1000},
        {"id": 136, "name": "Telegram Post Views [High Speed]", "price": 5, "min": 1000},
        {"id": 301, "name": "Telegram Post Views [Fast]", "price": 6, "min": 1000},
        {"id": 822, "name": "Telegram Post Views [Real]", "price": 6, "min": 1000},
        {"id": 303, "name": "Telegram Post Views [Last 5]", "price": 12, "min": 1000},
        {"id": 304, "name": "Telegram Post Views [Last 10]", "price": 19, "min": 1000},
    ],
    "Reactions": [
        {"id": 10788, "name": "Positive Mix Reactions", "price": 7, "min": 1000},
        {"id": 10698, "name": "Mix Positive + Bonus", "price": 8, "min": 1000},
        {"id": 10789, "name": "Positive Mix (HQ)", "price": 8, "min": 1000},
        {"id": 284, "name": "Premium Reactions [100]", "price": 24, "min": 1000},
    ],
    "Members": [
        {"id": 2730, "name": "Telegram Members [No Refill]", "price": 20, "min": 1000},
        {"id": 2731, "name": "Telegram Members [Cheap]", "price": 47, "min": 1000},
    ]
}

# --- JSONBin ফাংশনস ---
def get_db():
    url = f'https://api.jsonbin.io/v3/b/{BIN_ID}/latest'
    headers = {'X-Master-Key': MASTER_KEY, 'X-Access-Key': ACCESS_KEY}
    return requests.get(url, headers=headers).json()['record']

def update_db(data):
    url = f'https://api.jsonbin.io/v3/b/{BIN_ID}'
    headers = {'Content-Type': 'application/json', 'X-Master-Key': MASTER_KEY, 'X-Access-Key': ACCESS_KEY}
    requests.put(url, json=data, headers=headers)

# --- কিবোর্ডস ---
def main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🛒 New Order", callback_data="new_order"),
               types.InlineKeyboardButton("💰 Deposit", callback_data="deposit"))
    markup.add(types.InlineKeyboardButton("👤 Profile", callback_data="profile"),
               types.InlineKeyboardButton("📞 Support", callback_data="support"))
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
    return markup

# --- কমান্ডস ---
@bot.message_handler(commands=['start'])
def start(message):
    db = get_db()
    uid = str(message.from_user.id)
    if uid not in db['users']:
        db['users'][uid] = {"balance": 0, "spend": 0}
        update_db(db)
    
    bot.send_message(message.chat.id, "👋 Welcome to SMM Bot!\nসবচেয়ে কম দামে টেলিগ্রাম সার্ভিস কিনুন।", reply_markup=main_menu(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = str(call.from_user.id)
    if call.data == "new_order":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👁 Views", callback_data="cat_Views"))
        markup.add(types.InlineKeyboardButton("❤️ Reactions", callback_data="cat_Reactions"))
        markup.add(types.InlineKeyboardButton("👥 Members", callback_data="cat_Members"))
        bot.edit_message_text("একটি ক্যাটাগরি সিলেক্ট করুন:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("cat_"):
        cat = call.data.split("_")[1]
        markup = types.InlineKeyboardMarkup()
        for s in SERVICES[cat]:
            markup.add(types.InlineKeyboardButton(f"{s['name']} - {s['price']}৳", callback_data=f"srv_{s['id']}"))
        bot.edit_message_text(f"{cat} সার্ভিস লিস্ট:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("srv_"):
        sid = int(call.data.split("_")[1])
        msg = bot.send_message(call.message.chat.id, "আপনার চ্যানেলের বা পোস্টের লিঙ্কটি দিন:")
        bot.register_next_step_handler(msg, process_link, sid)

    elif call.data == "deposit":
        bot.send_message(call.message.chat.id, "কত টাকা ডিপোজিট করতে চান লিখুন (যেমন: 500):")
        bot.register_next_step_handler(call.message, process_deposit)

    elif call.data == "profile":
        db = get_db()
        user = db['users'].get(uid, {"balance": 0, "spend": 0})
        bot.send_message(call.message.chat.id, f"👤 **ইউজার প্রোফাইল**\n\n🆔 ID: {uid}\n💰 ব্যালেন্স: {user['balance']} ৳\n🛒 মোট খরচ: {user['spend']} ৳")

    elif call.data == "support":
        bot.send_message(call.message.chat.id, "🆘 সাপোর্ট এর জন্য যোগাযোগ করুন:\n@jhgmaing\n@bot_Developer_io")

    elif call.data == "admin_panel" and int(uid) == ADMIN_ID:
        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.add(types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
                         types.InlineKeyboardButton("➕ Add Balance", callback_data="admin_add_bal"))
        bot.send_message(call.message.chat.id, "অ্যাডমিন কন্ট্রোল প্যানেল:", reply_markup=admin_markup)

    elif call.data == "admin_stats" and int(uid) == ADMIN_ID:
        db = get_db()
        total_users = len(db['users'])
        bot.send_message(call.message.chat.id, f"📊 **বট স্ট্যাটিস্টিকস**\n\nমোট ইউজার: {total_users}\nমোট অর্ডার: {len(db['orders'])}")

# --- অর্ডার প্রসেস ---
def process_link(message, sid):
    link = message.text
    msg = bot.send_message(message.chat.id, "অর্ডার কোয়ান্টিটি দিন (মিনিমাম ১০০০):")
    bot.register_next_step_handler(msg, process_order, sid, link)

def process_order(message, sid, link):
    try:
        qty = int(message.text)
        if qty < 1000:
            bot.send_message(message.chat.id, "❌ মিনিমাম ১০০০ দিতে হবে। আবার শুরু করুন।")
            return
        
        # সার্ভিস ডিটেইলস খুঁজে বের করা
        selected_service = None
        for cat in SERVICES:
            for s in SERVICES[cat]:
                if s['id'] == sid:
                    selected_service = s
                    break
        
        cost = math.ceil((qty / 1000) * selected_service['price'])
        db = get_db()
        uid = str(message.from_user.id)
        
        if db['users'][uid]['balance'] < cost:
            bot.send_message(message.chat.id, f"❌ পর্যাপ্ত ব্যালেন্স নেই! প্রয়োজন {cost}৳।")
            return

        # SMM API কল
        api_url = f"https://smmsun.com/api/v2?key={SMM_API_KEY}&action=add&service={sid}&link={link}&quantity={qty}"
        response = requests.get(api_url).json()

        if "order" in response:
            db['users'][uid]['balance'] -= cost
            db['users'][uid]['spend'] += cost
            db['orders'].append({"uid": uid, "order_id": response['order'], "cost": cost})
            update_db(db)
            bot.send_message(message.chat.id, f"✅ অর্ডার সফল!\nঅর্ডার আইডি: {response['order']}\nখরচ হয়েছে: {cost}৳")
        else:
            bot.send_message(message.chat.id, f"❌ API Error: {response.get('error', 'Unknown Error')}")

    except Exception as e:
        bot.send_message(message.chat.id, "❌ ভুল ইনপুট! আবার ট্রাই করুন।")

# --- ডিপোজিট প্রসেস ---
def process_deposit(message):
    amount = message.text
    markup = types.InlineKeyboardMarkup()
    bot.send_message(message.chat.id, f"💵 আপনি {amount} টাকা পাঠাতে চান।\n\nবিকাশ/নগদ (Personal): 01830165894\nটাকা পাঠিয়ে ট্রানজেকশন স্ক্রিনশট দিন।")
    bot.register_next_step_handler(message, confirm_deposit, amount)

def confirm_deposit(message, amount):
    bot.send_message(ADMIN_ID, f"🔔 **নতুন ডিপোজিট রিকোয়েস্ট!**\nইউজার: {message.from_user.id}\nটাকা: {amount}\nব্যালেন্স এড করতে /add {message.from_user.id} {amount} লিখুন।")
    bot.send_message(message.chat.id, "✅ আপনার রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে। ভেরিফাই হলে ব্যালেন্স এড হয়ে যাবে।")

# --- অ্যাডমিন কমান্ড: ব্যালেন্স এড ---
@bot.message_handler(commands=['add'])
def add_balance(message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split()
            target_id = parts[1]
            amount = int(parts[2])
            db = get_db()
            if target_id in db['users']:
                db['users'][target_id]['balance'] += amount
                update_db(db)
                bot.send_message(message.chat.id, f"✅ {target_id} ইউজারকে {amount}৳ এড করা হয়েছে।")
                bot.send_message(target_id, f"💰 অভিনন্দন! আপনার ওয়ালেটে {amount}৳ এড করা হয়েছে।")
        except:
            bot.reply_to(message, "ব্যবহার: /add user_id amount")

# --- Render হোস্টিং হেল্পার ---
@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    bot.infinity_polling()
