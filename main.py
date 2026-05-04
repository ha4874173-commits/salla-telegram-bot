import os
import asyncio
import threading
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. الإعدادات الأساسية (تأكد من وجودها في Railway Variables) ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
DATA_CHANNEL_ID = "--1003846832363"
PORT = int(os.environ.get('PORT', 8080))

# ملف قاعدة البيانات (Database) لضمان عدم ضياع الأرقام عند تحديث البوت
DB_FILE = "orders_db.txt"

def save_to_db(mobile, name):
    """حفظ بيانات العميل في ملف نصي بصيغة دائمية"""
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(f"{mobile}|{name}\n")

def search_in_db(mobile):
    """البحث عن رقم الجوال في قاعدة البيانات"""
    if not os.path.exists(DB_FILE):
        return None
    with open(DB_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                m, n = line.strip().split("|")
                if m == str(mobile):
                    return n
    return None

# روابط القنوات والدعم
URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "whatsapp_support": "https://wa.me/966541234567", # رقم فيصل
    "free_channel": "https://t.me/c/3907521588/1",
    "private_channel": "https://t.me/c/3953368081/1"
}

app = Flask(__name__)
bot_instance = Bot(token=TOKEN) if TOKEN else None

# --- 2. واجهة البوت (الأزرار) ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX العالمية", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة", callback_data='menu_indicators')],
        [InlineKeyboardButton("✅ تم الدفع (استلام الرابط)", callback_data='check_payment')],
        [InlineKeyboardButton("🆓 القناة المجانية (مدى الحياة)", url=URLS["free_channel"])],
        [InlineKeyboardButton("💬 الدعم الفني (واتساب)", url=URLS["whatsapp_support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في بوت عزيز التجاري! 🚀\nبعد إتمام الدفع من المتجر، اضغط على 'تم الدفع' لاستلام رابط القناة.",
        reply_markup=main_menu_keyboard()
    )

# --- 3. معالج الويب هوك (Salla Webhook) ---
@app.route('/webhook', methods=['POST'])
def salla_webhook():
    try:
        data = request.json
        event = data.get('event')
        
        # التقاط كافة أحداث الدفع الممكنة من سلة
        if event in ['subscription.created', 'subscription.charge.succeeded', 'order.paid', 'order.status.updated']:
            order_data = data.get('data', {})
            customer = order_data.get('customer', {})
            mobile = str(customer.get('mobile', '')).replace('+', '').strip()
            name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
            
            if mobile:
                save_to_db(mobile, name)
                # إرسال تنبيه فوري لقناة الأرشيف
                msg = f"💰 **تأكيد عملية دفع**\n👤 العميل: {name}\n📱 الجوال: `{mobile}`\n📝 الحدث: {event}"
                if bot_instance:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(bot_instance.send_message(chat_id=DATA_CHANNEL_ID, text=msg))
                    loop.close()
                
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(f"Webhook Error: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500

# --- 4. معالج الأزرار ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("🗓️ باقة شهر", url=URLS["spx_1m"])],
            [InlineKeyboardButton("🗓️ 3 شهور", url=URLS["spx_3m"])],
            [InlineKeyboardButton("🗓️ 6 شهور", url=URLS["spx_6m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_main')]
        ]
        await query.edit_message_text("اختر باقة اشتراك SPX:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("📈 مؤشر Aziz Pro", url=URLS["ind_1m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_main')]
        ]
        await query.edit_message_text("اشتراك المؤشرات الخاصة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'check_payment':
        await query.message.reply_text("أرسل الآن رقم الجوال الذي استخدمته في سلة (بدون +) للتحقق:")

    elif data == 'back_main':
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=main_menu_keyboard())

# --- 5. معالج الرسائل (التحقق من الدفع) ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace('+', '')
    
    # البحث في الـ Database
    name = search_in_db(text)
    
    if name:
        await update.message.reply_text(
            f"✅ أهلاً {name}! تم التأكد من اشتراكك بنجاح.\n\n"
            f"تفضل رابط القناة الخاصة:\n{URLS['private_channel']}"
        )
    else:
        await update.message.reply_text(
            "❌ عذراً، هذا الرقم غير مسجل في قائمة المدفوعات الحالية.\n\n"
            "تأكد من كتابة الرقم بشكل صحيح (مثال: 9665xxxx)، أو انتظر دقيقة بعد الدفع لتحديث البيانات."
        )

# --- 6. التشغيل النهائي ---
def main():
    # تشغيل سيرفر Flask للويب هوك في الخلفية
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    
    # تشغيل البوت (Polling)
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
    
    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
