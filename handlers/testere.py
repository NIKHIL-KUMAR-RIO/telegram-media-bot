from telegram.ext import Application, CommandHandler

async def start(update, context):
    await update.message.reply_text("Hello")

app = Application.builder().token("8871060923:AAH721KatH2rbs6Ec3Tqur7r9daHOm1aOWk").build()
app.add_handler(CommandHandler("start", start))
app.run_polling()  