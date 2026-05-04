import os
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. الإعدادات ---
TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # آيدي فيصل الشخصي
DATA_CHANNEL_ID = "-1003970062260" # آيدي قناة الأرشيف
PORT = int(os.environ.get('PORT', 8080))

URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "whatsapp_support": "https://wa.me/0554852681", # ⚠️ ضع رقم واتساب فيصل هنا
    "free_channel": "https://t.me/c/3907521588/1",
    "private_channel": "https://t.me/c/3953368081/1"
}

app = Flask(__name__)
bot_instance = Bot(token=TOKEN) if TOKEN else None

# --- 2. واجهة البوت ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX الخاص", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة", callback_data='menu_indicators')],
        [InlineKeyboardButton("✅ تأكيد اشتراك ", callback_data='verify_sub')],
        [InlineKeyboardButton("🆓 القناة المجانية ", url=URLS["free_channel"])],
        [InlineKeyboardButton("💬 الدعم الفني ", url=URLS["whatsapp_support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك في بوت عزيز التجاري! 🚀", reply_markup=main_menu_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("🗓️ باقة شهر - 100 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("🗓️ باقة 3 شهور - 279 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("🗓️ باقة 6 شهور - 549 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر باقة SPX المناسبة للدفع عبر سلة:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("📈 مؤشر Aziz Pro - 399 ريال", url=URLS["ind_1m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اشتراك المؤشرات الخاصة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'verify_sub':
        await query.message.reply_text("أرسل الآن صورة الفاتورة أو رقم الطلب ليقوم فيصل بمراجعته وتفعيل اشتراكك.")

    elif data == 'back_to_main':
        await query.edit_message_text("اختر خدمتك المفضلة:", reply_markup=main_menu_keyboard())

# --- 3. نظام التأكيد اليدوي (يرسل للآدمن فقط) ---
async def handle_verification_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) == str(ADMIN_ID): return
    user = update.effective_user
    keyboard = [[InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user.id}"),
                 InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")]]
    
    # الطلب يذهب لفيصل فقط (ADMIN_ID) للمراجعة
    if update.message.photo:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, 
                                   caption=f"📩 طلب يدوي جديد:\nالاسم: {user.first_name}\nID: `{user.id}`", 
                                   reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await context.bot.send_message(chat_id=ADMIN_ID, 
                                     text=f"📩 طلب يدوي جديد:\nالاسم: {user.first_name}\nالرسالة: {update.message.text}\nID: `{user.id}`", 
                                     reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("✅ تم إرسال طلبك لفيصل. سيصلك الرد هنا فور المراجعة.")

async def admin_decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, user_id = query.data.split("_")
    await query.answer()

    if action == "approve":
        await context.bot.send_message(chat_id=user_id, text=f"🎉 تم قبول طلبك! رابط القناة الخاصة:\n{URLS['private_channel']}")
        await context.bot.send_message(chat_id=DATA_CHANNEL_ID, text=f"✅ تفعيل يدوي: تم قبول اشتراك {user_id}")
        status = "✅ تم القبول"
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ نعتذر، لم يتم التأكد من الدفع. تواصل مع الدعم.")
        status = "❌ تم الرفض"
    
    # تحديث الرسالة عند الأدمن
    if query.message.photo:
        await query.edit_message_caption(caption=query.message.caption + f"\n\n{status}")
    else:
        await query.edit_message_text(text=query.message.text + f"\n\n{status}")

# --- 4. الويب هوك (تأكيد دفع سلة يرسل للأرشيف) ---
@app.route('/webhook', methods=['POST'])
def salla_webhook():
    try:
        data = request.json
        if data.get('event') in ['subscription.created', 'subscription.charged']:
            customer = data['data'].get('customer', {})
            name = f"{customer.get('first_name')} {customer.get('last_name')}"
            msg = f"💰 **دفع مؤكد (سلة)**\n👤 العميل: {name}\n📱 الجوال: {customer.get('mobile', 'N/A')}"
            
            if bot_instance:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # يرسل لقناة الأرشيف فوراً
                loop.run_until_complete(bot_instance.send_message(chat_id=DATA_CHANNEL_ID, text=msg))
                # إشعار لفيصل
                loop.run_until_complete(bot_instance.send_message(chat_id=ADMIN_ID, text=f"🔔 دفع جديد من {name} سجل في الأرشيف."))
                loop.close()
        return jsonify({'status': 'success'}), 200
    except:
        return jsonify({'status': 'error'}), 500

# --- 5. تشغيل النظام ---
def main():
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(admin_decision_handler, pattern="^(approve|reject)_"))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_verification_request))
    application.run_polling()

if __name__ == '__main__':
    main()
