import os

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from telegram import Bot
from asgiref.sync import async_to_sync
from .models import Poll, Participant, Team, Group
from .common.util.team import random_team_generator

# Here are functions that interact with the bot from the app's "side"


def post_teams(request, chat_id):
    print("I send a message with the bot")
    token = os.getenv('BOT_TOKEN')
    bot = Bot(token=token)
    chat = -4792114242
    async_to_sync(bot.sendMessage)(chat_id=chat, text='Bonjour')
    return HttpResponse("")


def bot_generate_teams(chat_id):
    # poll = await sync_to_async(get_object_or_404)(Poll, chat_id=update.effective_chat)
    print(chat_id)
    poll = get_object_or_404(Poll, chat_id=3)
    participants = poll.participant_set.all()
    requests = poll.group_set.all()
    # TODO : request are larger than team size control
    requests = [group.request() for group in requests]
    teams_created = random_team_generator(participants,
                                          groupements=requests,
                                          max_per_team=poll.team_size)
    team_text = []
    for i, team in enumerate(teams_created):
        team_text.append("*Equipe {}*".format(i + 1))
        for member in team:
            team_text.append('- {}'.format(member))
        team_text.append('')
    team_text.append('Amusez-vous bien !')
    text = '\n'.join(team_text)
    #async_to_sync(bot.sendMessage)(chat_id=chat, text=text, parse_mode='Markdown')
    #await update.effective_chat.send_message(teams_created)
    return text


def clear_poll(chat_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    for team in poll.team_set.all():
        team.participant_set.clear()
        #team.save()
    for group in poll.group_set.all():
        group.participant_set.clear()
        #group.save()
    poll.participant_set.clear()
    #poll.save()
