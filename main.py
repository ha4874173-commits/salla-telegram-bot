import os
import asyncio
import threading
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. الإعدادات ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
DATA_CHANNEL_ID = "-1003846832363"
PORT = int(os.environ.get('PORT', 8080))

# مخزن مؤقت لحفظ بيانات العملاء (رقم الجوال : الاسم)
paid_customers = {} 

URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "whatsapp_support": "https://wa.me/966541234567",
    "free_channel": "https://t.me/c/3907521588/1",
    "private_channel": "https://t.me/c/3953368081/1"
}

app = Flask(__name__)
bot_instance = Bot(token=TOKEN) if TOKEN else None

# --- 2. لوحة الأزرار الرئيسية ---
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
        "مرحباً بك في بوت عزيز التجاري! 🚀\nاشترك الآن عبر سلة، وبعد الدفع اضغط على 'تم الدفع'.",
        reply_markup=main_menu_keyboard()
    )

# --- 3. معالج الويب هوك (سلة) ---
@app.route('/webhook', methods=['POST'])
def salla_webhook():
    data = request.json
    # أحداث الدفع من سلة
    if data.get('event') in ['subscription.created', 'subscription.charged', 'order.paid']:
        customer = data['data'].get('customer', {})
        mobile = customer.get('mobile') # الرقم المسجل في سلة
        name = f"{customer.get('first_name')} {customer.get('last_name')}"
        
        # حفظ في الذاكرة للتحقق لاحقاً
        paid_customers[str(mobile)] = name

        # إرسال للأرشيف مع أزرار التحكم
        keyboard = [
            [InlineKeyboardButton("✅ تفعيل يدوي", callback_data=f"force_approve_{mobile}"),
             InlineKeyboardButton("❌ رفض الطلب", callback_data=f"force_reject_{mobile}")]
        ]
        
        msg = f"💰 **إشعار دفع جديد (سلة)**\n👤 العميل: {name}\n📱 الجوال: `{mobile}`\n⚙️ الحالة: بانتظار العميل يفتح البوت"
        
        if bot_instance:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot_instance.send_message(chat_id=DATA_CHANNEL_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard)))
            loop.close()
            
    return jsonify({'status': 'success'}), 200

# --- 4. معالج الأزرار والتنقل ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    # قائمة اشتراكات SPX (كل الباقات)
    if data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("🗓️ باقة شهر - 100 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("🗓️ باقة 3 شهور - 279 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("🗓️ باقة 6 شهور - 549 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data='back_main')]
        ]
        await query.edit_message_text("اختر مدة اشتراك SPX المناسبة لك:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # قائمة المؤشرات
    elif data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("📈 مؤشر Aziz Pro - 399 ريال", url=URLS["ind_1m"])],
            [InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data='back_main')]
        ]
        await query.edit_message_text("اشتراك المؤشرات الفنية الخاصة:", reply_markup=InlineKeyboardMarkup(keyboard))

    # زر التحقق من الدفع
    elif data == 'check_payment':
        await query.message.reply_text("أرسل الآن رقم الجوال الذي استخدمته في متجر سلة (مثال: 9665xxxxxxxx):")

    # العودة
    elif data == 'back_main':
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=main_menu_keyboard())

# --- 5. التحقق من رقم الجوال بعد الدفع ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # إذا كان الرقم موجود في قائمة المدفوعات من سلة
    if text in paid_customers:
        name = paid_customers[text]
        await update.message.reply_text(
            f"✅ تم التأكد من اشتراكك بنجاح يا {name}!\n\n"
            f"تفضل رابط القناة الخاصة:\n{URLS['private_channel']}\n\n"
            "نتمنى لك تداولاً موفقاً! 📈"
        )
    else:
        await update.message.reply_text(
            "❌ عذراً، هذا الرقم غير مسجل لدينا في قائمة المبيعات الحالية.\n\n"
            "1. تأكد من كتابة الرقم بشكل صحيح (966..).\n"
            "2. تأكد من إتمام الدفع في سلة.\n"
            "3. إذا واجهت مشكلة، تواصل مع الدعم الفني."
        )

# --- 6. التشغيل ---
def main():
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    # استقبال أرقام الجوال من العملاء
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
    
    application.run_polling()

if __name__ == '__main__':
    main()
