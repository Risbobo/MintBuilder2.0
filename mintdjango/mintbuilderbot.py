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
from mintbuilderapp.bot import *

from telegram import Update, KeyboardButton, WebAppInfo, ReplyKeyboardMarkup
from telegram.ext import Application, Updater, ContextTypes, CommandHandler, PollAnswerHandler, CallbackContext
from telegram.constants import ChatType, ReactionType


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
    text = await sync_to_async(bot_generate_teams)(update.effective_chat.id)
    parse_message = update.message.text.split(' ')[1:]
    if len(parse_message) > 0:
        text += ("\n \n(Si vous voulez faire des requêtes, "
                 "vous pouvez utiliser la commande /request avant de lancer cette commande)")
    await update.effective_chat.send_message(text=text, parse_mode='Markdown')


async def create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        poll = await sync_to_async(Poll.objects.get)(chat_id=update.effective_chat.id)
        await context.bot.stop_poll(chat_id=poll.chat_id, message_id=poll.message_id)
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
    poll.poll_id=new_poll.poll.id
    poll.message_id = new_poll.id
    print("new poll id : ", new_poll.id)
    await sync_to_async(poll.save)()


async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer.option_ids
    user = update.effective_user
    poll_id = update.poll_answer.poll_id
    # print(user, type(user), user.first_name)
    # The user comes
    if answer == (0,):
        number_of_participant, max_participant, chat_id = await sync_to_async(participant_coming)(user, poll_id)
        if number_of_participant >= max_participant:
            await context.bot.send_message(chat_id=chat_id,
                                           text="Attention, il y a maintenant {} personnes qui viennent "
                                                "alors que la limite de places est {}".format(number_of_participant,
                                                                                              max_participant))
    # The user don't come
    elif answer == (1,):
        #print("Je viens pas")
        pass
    # The user organises
    elif answer == (2,):
        #print("J'organise")
        pass
    # Vote retracted
    elif answer == ():
        await sync_to_async(participant_notcoming)(user, poll_id)


async def add_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    parse_name = update.message.text.split(' ')[1:]
    if len(parse_name) > 0:
        number_of_participant, max_participant = await sync_to_async(bot_add_participant)(parse_name, chat_id)
        await context.bot.set_message_reaction(chat_id=chat_id,
                                               message_id=update.message.message_id,
                                               reaction=['\U0001F44D'])
        if number_of_participant >= max_participant:
            await update.message.reply_text("Attention, il y a maintenant {} personnes qui viennent "
                                            "alors que la limite de places est {}".format(number_of_participant,
                                                                                          max_participant))
    else:
        await update.message.reply_text("Il n'y a personne à ajouter")


async def remove_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    parse_name = update.message.text.split(' ')[1:]
    if len(parse_name) > 0:
        state = await sync_to_async(bot_remove_participant)(parse_name, chat_id)
        if state == 0:
            await update.message.reply_text("Je n'ai trouvé personne avec ce nom")
        elif state == 1:
            await context.bot.set_message_reaction(chat_id=chat_id,
                                                   message_id=update.message.message_id,
                                                   reaction=['\U0001F44D'])
        elif state == 2:
            await update.message.reply_text("J'ai trouvé trop de personne avec ce nom")
    else:
        await update.message.reply_text("Il n'y a personne à retirer")


async def participant_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = await sync_to_async(bot_participant_list)(chat_id)
    await update.effective_chat.send_message(text=text, parse_mode='Markdown')


async def make_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = update.message.text
    command_end = message.find(' ')
    #print(command_end)
    if command_end < 0 or len(message[command_end+1:]) == 0 :
        text = await sync_to_async(print_request)(chat_id=chat_id)
        await update.effective_chat.send_message(text=text, parse_mode='Markdown')
    else:
        participants = [participant.strip() for participant in message[command_end + 1:].split(',')]
        state, arg = await sync_to_async(add_request)(chat_id=chat_id, request_list=participants)
        if state == 0:
            await update.message.reply_text("Je n'ai pas trouvé {}".format(arg))
        elif state == 1:
            await context.bot.set_message_reaction(chat_id=chat_id,
                                                   message_id=update.message.message_id,
                                                   reaction=['\U0001F44D'])
        elif state == 2:
            await update.message.reply_text("J'ai trouvé plusieurs {}".format(arg))
        elif state == 3:
            await update.message.reply_text("Ces participants font déjà parties de requêtes différentes".format())
            print(arg)
        else:
            await update.message.reply_text("Je ne supporte pas d'avoir plus de 17 requête (for... some reason)".format())


async def set_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    parse_number = update.message.text.split(' ')[1:]
    if len(parse_number) > 0:
        try:
            val = int(parse_number[0])
        except ValueError:
            await update.message.reply_text(text="La valeur entrée n'est pas un entier")
        else:
            new_val = await sync_to_async(bot_set_max)(chat_id, val)
            if new_val == val:
                await context.bot.set_message_reaction(chat_id=chat_id,
                                                       message_id=update.message.message_id,
                                                       reaction=['\U0001F44D'])
            else:
                await update.message.reply_text("Le nombre de places disponibles est maintenant {}".format(new_val))
    else:
        await update.message.reply_text("Aucune valeur entrée")


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ["*Voici mes commandes :*", '- /start : Affiche un message d\'introduction',
            '- /poll : Crée un sondage à 3 réponses dont seule la première est positive.',
            '- /add <nom> : Permet d\'ajouter un-e participant-e au prochain quiz.'
            'Il est également possible de forwarder le sondage si la personne possède telegram',
            '- /remove <nom> : Permet de retirer un-e participant-e du prochain quiz.'
            'Il est également possible de se retirer du sondage pour retirer sa participation'
            '(En appuyant sur l\'énoncé du sondage puis \"retract vote\")',
            '- /participants : Permet d\'afficher la liste des participant-e-s au prochain quiz',
            '- /max : Permet de modifier le nombre de places maximales disponibles',
            '- /team : Génère aléatoirement des équipes.',
            '- /request <nom1, nom2, ...> : Ajoute une requête pour le tirage des équipes',
            '- /git : provide the link to the [github](https://github.com/Risbobo/MintBuilderPublic)',
            '\n*Exemples* :',
            '/poll 18 - Crée un sondage qui avertira à partir de 18 participants que la limite de place est atteinte',
            '/add Alice - Alice est ajoutée au prochain quiz',
            '/remove Alice - Alice est retirée du prochain quiz',
            '/request Alice, Bob - Alice et Bob seront dans la même équipe quand /team est utilisé.',
            '/request Alice, Bob, Charlie - Alice, Bob et Charles seront dans la même équipe.',]
    text_to_send = '\n'.join(text)
    await update.message.reply_text(text=text_to_send, parse_mode='Markdown')


async def git_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_log("git")
    text = "[Link to GitHub](https://github.com/Risbobo/MintBuilderPublic)"
    await update.message.reply_text(text=text, parse_mode='Markdown')


def main() -> None:
    #load_dotenv()
    token = os.getenv('BOT_TOKEN')
    bot = Application.builder().token(token=token).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("app", launch_app))
    bot.add_handler(CommandHandler("team", generate_teams))
    bot.add_handler(CommandHandler("poll", create_poll))
    bot.add_handler(PollAnswerHandler(receive_poll_answer))
    bot.add_handler(CommandHandler("add", add_participant))
    bot.add_handler(CommandHandler("remove", remove_participant))
    bot.add_handler(CommandHandler("participant", participant_list))
    bot.add_handler(CommandHandler("request", make_request))
    bot.add_handler(CommandHandler("max", set_max))
    bot.add_handler(CommandHandler("help", help))
    bot.add_handler(CommandHandler("git", git_link))

    print("I'm listening")
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()