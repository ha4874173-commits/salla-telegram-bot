import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# 1. إعدادات البوت (التوكن الصحيح)
TOKEN = '8232201715:AAFEvsg1y3tD8_CXOXx0NT2CsdZU_jw9sN8'
SALLA_TOKEN = 'حط_هنا_التوكن_اللي_هيبعته_فيصل' 
CHANNEL_ID = '-1002462310103'

# 2. روابط المنتجات (الـ 8 روابط كاملة)
URLS = {
    # روابط تحليل SPX
    "spx_1m": "https://salla.sa/spx-1-month",
    "spx_3m": "https://salla.sa/spx-3-months",
    "spx_6m": "https://salla.sa/spx-6-months",
    "spx_1y": "https://salla.sa/spx-1-year",
    
    # روابط المؤشرات الفنية
    "ind_1m": "https://salla.sa/indicators-1-month",
    "ind_3m": "https://salla.sa/indicators-3-months",
    "ind_6m": "https://salla.sa/indicators-6-months",
    "ind_1y": "https://salla.sa/indicators-1-year",
    
    "support": "https://t.me/your_support_username"
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# دالة القائمة الرئيسية
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليل SPX", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية", callback_data='menu_indicators')],
        [InlineKeyboardButton("✅ تأكيد الدفع (إرسال رقم الطلب)", callback_data='verify_payment')],
        [InlineKeyboardButton("💬 الدعم الفني", url=URLS["support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- دالة التحقق من سلة ---
def verify_salla_order(order_id):
    if SALLA_TOKEN == 'حط_هنا_التوكن_اللي_هيبعته_فيصل':
        return False
    headers = {'Authorization': f'Bearer {SALLA_TOKEN}', 'Content-Type': 'application/json'}
    try:
        response = requests.get(f'https://api.salla.dev/admin/v2/orders/{order_id}', headers=headers)
        if response.status_code == 200:
            data = response.json()
            status = data['data']['status']['id']
            return status in ['completed', 'delivered']
        return False
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في بوت خدماتنا التقنية! 🚀\nالرجاء اختيار الخدمة المطلوبة:",
        reply_markup=main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # قسم تحليل SPX (4 اشتراكات)
    if query.data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("شهر - 150 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("3 شهور - 400 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("6 شهور - 750 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("سنة - 1300 ريال", url=URLS["spx_1y"])],
            [InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر مدة اشتراك تحليل SPX:", reply_markup=InlineKeyboardMarkup(keyboard))

    # قسم المؤشرات الفنية (4 اشتراكات)
    elif query.data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("شهر - 200 ريال", url=URLS["ind_1m"])],
            [InlineKeyboardButton("3 شهور - 550 ريال", url=URLS["ind_3m"])],
            [InlineKeyboardButton("6 شهور - 1000 ريال", url=URLS["ind_6m"])],
            [InlineKeyboardButton("سنة - 1800 ريال", url=URLS["ind_1y"])],
            [InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر مدة اشتراك المؤشرات الفنية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'verify_payment':
        context.user_data['waiting_for_order'] = True
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data='back_to_main')]]
        await query.edit_message_text(
            "من فضلك، قم بإرسال **رقم الطلب** من سلة للتحقق من اشتراكك.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == 'back_to_main':
        context.user_data['waiting_for_order'] = False
        await query.edit_message_text(
            "مرحباً بك في بوت خدماتنا التقنية! 🚀\nالرجاء اختيار الخدمة المطلوبة:",
            reply_markup=main_menu_keyboard()
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_order'):
        order_id = update.message.text.strip()
        if not order_id.isdigit():
            await update.message.reply_text("الرجاء إرسال رقم طلب صحيح (أرقام فقط).")
            return

        await update.message.reply_text("جاري التحقق من الطلب في سلة... ⏳")
        if verify_salla_order(order_id):
            invite_link = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
            await update.message.reply_text(f"✅ تم التحقق بنجاح!\nتفضل برابط الدخول للقناة:\n{invite_link.invite_link}")
        else:
            await update.message.reply_text("❌ لم يتم العثور على طلب مدفوع. تأكد من الرقم أو تواصل مع الدعم.")
        context.user_data['waiting_for_order'] = False

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
