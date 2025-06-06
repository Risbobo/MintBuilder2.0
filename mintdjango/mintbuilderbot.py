import os
import time

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mintdjango.settings')
django.setup()
from asgiref.sync import sync_to_async
from mintbuilderapp.bot import *

from telegram import Update, KeyboardButton, WebAppInfo, ReplyKeyboardMarkup
from telegram.ext import Application, ContextTypes, CommandHandler, PollAnswerHandler
from telegram.constants import ChatType


def command_log(cmd):
    t = time.time()
    lt = time.ctime(t)
    print("{} | Receive command : {}".format(lt, cmd))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command_log("start")
    text = "Hello ! Je suis MintBuilder ! \n" \
           "Je m'occupe de créer des sondages pour organiser des quiz et de tirer les équipes.\n" \
           "Je peux créer un sondage avec la commande /poll et je peux tirer les équipes avec la commande /team. " \
           "Pour plus de détails, vous pouvez utiliser la commande /help.\n" \
           "Amusez-vous bien !"
    await update.message.reply_text(text=text)


async def launch_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_log("app")
    if update.effective_chat.type==ChatType.PRIVATE:
        user_chats = await sync_to_async(get_polls)(update.effective_user.id)
        if user_chats == 0 or len(user_chats) == 0:
            await update.message.reply_text("Tu ne fais partie d'aucun chat")
        else :
            kb = [[KeyboardButton(text=chat_name + "\n{}/{}/new_request".format(os.getenv("WEBAPP_URL"), chat_id),
                                 web_app=WebAppInfo('https://www.google.com/'))
                                #web_app=WebAppInfo("{}/{}/new_request".format(os.getenv("WEBAPP_URL"), chat_id)))
                  for chat_name, chat_id in user_chats.items()]]
            await update.message.reply_text("\U0001F44D \U0001F44D", reply_markup=ReplyKeyboardMarkup(kb))
    else:
        chat_id = await sync_to_async(get_poll)(update.effective_chat.id)
        if chat_id == 0:
            await update.message.reply_text("Ce chat n'a pas de sondage")
        else:
            link = "{}/{}/new_request".format(os.getenv("WEBAPP_URL"), chat_id)
            await update.effective_chat.send_message(text="[Lien vers l'app({})](https://www.google.com/)".format(link), parse_mode='Markdown')


async def generate_teams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_log("team")
    text = await sync_to_async(bot_generate_teams)(update.effective_chat.id)
    parse_message = update.message.text.split(' ')[1:]
    if len(parse_message) > 0:
        text += ("\n \n(Si vous voulez faire des requêtes, "
                 "vous pouvez utiliser la commande /request avant de lancer cette commande)")
    if text == 0:
        await update.message.reply_text("Ce chat n'a pas de sondage")
    else:
        await update.effective_chat.send_message(text=text, parse_mode='Markdown')


async def create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_log("poll")
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
    await sync_to_async(poll.save)()


async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer.option_ids
    user = update.effective_user
    poll_id = update.poll_answer.poll_id
    # The user comes
    if answer == (0,):
        number_of_participant, max_participant, chat_id = await sync_to_async(participant_coming)(user, poll_id)
        if chat_id and number_of_participant >= max_participant:
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
    command_log("add")
    chat_id = update.effective_chat.id
    parse_name = update.message.text.split(' ')[1:]
    if len(parse_name) > 0:
        number_of_participant, max_participant = await sync_to_async(bot_add_participant)(parse_name, chat_id)
        if number_of_participant == 0 and max_participant == 0:
            await update.message.reply_text("Ce chat n'a pas de sondage")
        else:
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
    command_log("remove")
    chat_id = update.effective_chat.id
    parse_name = update.message.text.split(' ')[1:]
    if len(parse_name) > 0:
        state = await sync_to_async(bot_remove_participant)(parse_name, chat_id)
        if state == -1:
            await update.message.reply_text("Ce chat n'a pas de sondage")
        elif state == 0:
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
    command_log("participant")
    chat_id = update.effective_chat.id
    text = await sync_to_async(bot_participant_list)(chat_id)
    await update.effective_chat.send_message(text=text, parse_mode='Markdown')


async def make_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_log("request")
    chat_id = update.effective_chat.id
    message = update.message.text
    command_end = message.find(' ')
    if command_end < 0 or len(message[command_end+1:]) == 0 :
        text = await sync_to_async(print_request)(chat_id=chat_id)
        await update.effective_chat.send_message(text=text, parse_mode='Markdown')
    else:
        participants = [participant.strip() for participant in message[command_end + 1:].split(',')]
        state, arg = await sync_to_async(add_request)(chat_id=chat_id, request_list=participants)
        if state == -1:
            await update.message.reply_text("Ce chat n'a pas de sondage")
        elif state == 0:
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
    command_log("max")
    chat_id = update.effective_chat.id
    parse_number = update.message.text.split(' ')[1:]
    if len(parse_number) > 0:
        try:
            val = int(parse_number[0])
        except ValueError:
            await update.message.reply_text(text="La valeur entrée n'est pas un entier")
        else:
            new_val = await sync_to_async(bot_set_max)(chat_id, val)
            if new_val < 0 :
                await update.message.reply_text("Ce chat n'a pas de sondage")
            elif new_val == val:
                await context.bot.set_message_reaction(chat_id=chat_id,
                                                       message_id=update.message.message_id,
                                                       reaction=['\U0001F44D'])
            else:
                await update.message.reply_text("Le nombre de places disponibles est maintenant {}".format(new_val))
    else:
        await update.message.reply_text("Aucune valeur entrée")


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_log("help")
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
    text = "[Link to GitHub](https://github.com/Risbobo/MintBuilder2.0)"
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