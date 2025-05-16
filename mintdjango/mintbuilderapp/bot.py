import os

from django.http import HttpResponse
from telegram import Bot
from asgiref.sync import async_to_sync
from .models import Poll, Participant, Team, Group


def post_teams(request, chat_id):
    print("I send a message with the bot")
    token = os.getenv('BOT_TOKEN')
    bot = Bot(token=token)
    chat = -4792114242
    async_to_sync(bot.sendMessage)(chat_id=chat, text='Bonjour')
    return HttpResponse("")