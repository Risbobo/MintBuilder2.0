import os
import time
from html.parser import HTMLParser

import django
from django.shortcuts import get_object_or_404
from mintdjango.settings import DATABASES, INSTALLED_APPS
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mintdjango.settings')
django.setup()
from asgiref.sync import sync_to_async, async_to_sync
from mintbuilderapp.models import Poll, Participant, Group
from mintbuilderapp.common.util.team import random_team_generator
from mintbuilderapp.bot import bot_generate_teams, clear_poll

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


async def generate_teams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO : request are larger than team size control
    text = await sync_to_async(bot_generate_teams)(update.effective_chat)
    # TODO : if args, invite to go to the app
    await update.effective_chat.send_message(text=text, parse_mode='Markdown')


async def create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        poll = await sync_to_async(Poll.objects.get)(chat_id=update.effective_chat.id)
        await context.bot.stop_poll(chat_id=poll.chat_id, message_id=poll.poll_id)
        await sync_to_async(clear_poll)(chat_id=poll.chat_id)
    except Poll.DoesNotExist:
        name = update.effective_chat.first_name if update.effective_chat.type==ChatType.PRIVATE \
            else update.effective_chat.title
        poll = await sync_to_async(Poll.objects.create)(chat_id=update.effective_chat.id,
                                                        chat_name=name,
                                                        is_telegram=True)
    new_poll = await context.bot.send_poll(
        chat_id=update.effective_chat.id,
        question='Prochain quiz, qui vient ?',
        options=['Let\'s go \U0001F44D !', 'Non... \U0001F614', "J'organise \U0001F60E !"],
        is_anonymous=False
    )
    poll.poll_id=new_poll.id
    await sync_to_async(poll.save)()


def main() -> None:
    #load_dotenv()
    token = os.getenv('BOT_TOKEN')
    bot = Application.builder().token(token=token).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("app", launch_app))
    bot.add_handler(CommandHandler("team", generate_teams))
    bot.add_handler(CommandHandler("poll", create_poll))

    print("I'm listening")
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()