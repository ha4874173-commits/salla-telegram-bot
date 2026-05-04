import os
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. الإعدادات ---
TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # آيدي فيصل
DATA_CHANNEL_ID = "-1003970062260" # قناة الأرشيف
PORT = int(os.environ.get('PORT', 8080))

# 📍 تم تحديث رابط الدعم الفني لواتساب
URLS = {
    "whatsapp_support": "https://wa.me/0554852681", # ⚠️ ضع رقم واتساب فيصل هنا (مثال: 966500000000)
    "free_channel": "https://t.me/c/3907521588/1",
    "private_channel": "https://t.me/c/3953368081/1"
}

app = Flask(__name__)
bot_instance = Bot(token=TOKEN) if TOKEN else None

# --- 2. واجهة البوت ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك التحليلات (سلة)", url="https://salla.sa/AZIZSPX")],
        [InlineKeyboardButton("✅ تأكيد اشتراك (إرسال فاتورة/صورة)", callback_data='verify_sub')],
        [InlineKeyboardButton("🆓 القناة المجانية", url=URLS["free_channel"])],
        [InlineKeyboardButton("💬 الدعم الفني (واتساب)", url=URLS["whatsapp_support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في نظام عزيز المطور! 🚀\nيمكنك الاشتراك عبر سلة أو إرسال إثبات الدفع للمراجعة اليدوية:",
        reply_markup=main_menu_keyboard()
    )

# --- 3. نظام المراجعة اليدوية (إرسال الإثبات) ---
async def handle_verification_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # نتحقق أن المرسل ليس الأدمن نفسه لتجنب التكرار
    if str(update.effective_user.id) == str(ADMIN_ID):
        return

    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("✅ قبول وإرسال الرابط", callback_data=f"approve_{user.id}")],
        [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_{user.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # إرسال البيانات لفيصل للمراجعة
    if update.message.photo:
        await context.bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=update.message.photo[-1].file_id, 
            caption=f"🔔 طلب تفعيل يدوي من: {user.first_name}\nآيدي: `{user.id}`", 
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text=f"🔔 طلب تفعيل يدوي من: {user.first_name}\nالرسالة: {update.message.text}\nآيدي: `{user.id}`", 
            reply_markup=reply_markup
        )
    
    await update.message.reply_text("✅ تم إرسال إثباتك للإدارة. انتظر الرد هنا فور المراجعة.")

# --- 4. معالجة قرار الأدمن (قبول/رفض) ---
async def admin_decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    action, user_id = data.split("_")

    if action == "approve":
        # إرسال الرابط تلقائياً للعميل
        try:
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"🎉 تم التحقق من طلبك بنجاح!\nتفضل رابط الانضمام للقناة الخاصة:\n{URLS['private_channel']}"
            )
            # تحديث رسالة الإدارة
            status_text = "✅ تم القبول وإرسال الرابط للعميل."
            # تسجيل في الأرشيف
            await context.bot.send_message(chat_id=DATA_CHANNEL_ID, text=f"✅ تفعيل يدوي ناجح للعميل {user_id}")
        except Exception as e:
            status_text = f"⚠️ تمت الموافقة ولكن فشل إرسال الرسالة للعميل: {e}"

    elif action == "reject":
        try:
            await context.bot.send_message(chat_id=user_id, text="❌ نعتذر، لم يتم التأكد من بيانات الدفع. يرجى التواصل مع الدعم الفني.")
            status_text = "❌ تم رفض الطلب."
        except:
            status_text = "❌ تم الرفض (العميل أغلق البوت)."

    # تعديل الرسالة عند فيصل لتوضيح الحالة
    if query.message.photo:
        await query.edit_message_caption(caption=query.message.caption + f"\n\n{status_text}")
    else:
        await query.edit_message_text(text=query.message.text + f"\n\n{status_text}")

# --- 5. نظام الويب هوك (سلة) ---
@app.route('/webhook', methods=['POST'])
def salla_webhook():
    try:
        data = request.json
        if data.get('event') in ['subscription.created', 'subscription.charged']:
            customer = data['data'].get('customer', {})
            name = f"{customer.get('first_name')} {customer.get('last_name')}"
            msg = f"💰 **دفع مؤكد من سلة**\n👤 العميل: {name}\n📱 الجوال: {customer.get('mobile', 'N/A')}"
            if bot_instance:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot_instance.send_message(chat_id=DATA_CHANNEL_ID, text=msg))
                loop.run_until_complete(bot_instance.send_message(chat_id=ADMIN_ID, text=msg))
                loop.close()
        return jsonify({'status': 'success'}), 200
    except:
        return jsonify({'status': 'error'}), 500

# --- 6. التشغيل النهائي ---
def main():
    if not TOKEN: return

    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(admin_decision_handler, pattern="^(approve|reject)_"))
    # استقبال الصور والنصوص للمراجعة
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_verification_request))
    
    print("🚀 البوت يعمل الآن بنظام (سلة + المراجعة اليدوية + واتساب)")
    application.run_polling()

if __name__ == '__main__':
    main()
