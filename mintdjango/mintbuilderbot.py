import os
import time
from html.parser import HTMLParser

import django
from mintdjango.settings import DATABASES, INSTALLED_APPS
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mintdjango.settings')
django.setup()
from asgiref.sync import sync_to_async
from mintbuilderapp.models import Poll, Participant
from telegram import Update, KeyboardButton, WebAppInfo, ReplyKeyboardMarkup
from telegram.ext import Application, Updater, ContextTypes, CommandHandler, CallbackContext
from telegram.constants import ChatType
from dotenv import load_dotenv


def command_log(cmd):
    t = time.time()
    lt = time.ctime(t)
    print("{} | Receive command : {}".format(lt, cmd))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command_log("start")
    user = await sync_to_async(Participant.objects.get)(participant_name='user3')
    #user = update.effective_user
    #print(user)
    chat_id = update.effective_chat
    #print(chat_id)
    #users = await sync_to_async(Participant.objects.all)()
    #random_user = list(users)[0]
    await update.message.reply_text(f"Here is a user from the database : {user}")


async def launch_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type==ChatType.PRIVATE:
        kb = [
            [KeyboardButton(
                "Let's Mint some Teams!",
                web_app=WebAppInfo('https://www.google.com/')
                #web_app=WebAppInfo(os.getenv("WEBAPP_URL"))
            )],
            [KeyboardButton(
                "Let's Mint some Teams but other!",
                web_app=WebAppInfo('https://www.google.com/')
                # web_app=WebAppInfo(os.getenv("WEBAPP_URL"))
            )]
        ]
        await update.message.reply_text("Ok", reply_markup=ReplyKeyboardMarkup(kb))
    else:
        #await update.message.reply_text(text=f"<a href='{os.getenv("WEBAPP_URL")}'> Link </>", parse_mode='HTML')
        #await update.effective_chat.send_message(text=f"<a href='{os.getenv("WEBAPP_URL")}'> Link </>", parse_mode='HTML')
        await update.effective_chat.send_message(text=f"link : https://www.google.com/", parse_mode='HTML')


def main() -> None:
    #load_dotenv()
    token = os.getenv('BOT_TOKEN')
    bot = Application.builder().token(token=token).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("app", launch_app))

    print("I'm listening")
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()