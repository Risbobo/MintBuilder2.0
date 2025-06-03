import os

import telegram
from django.core.exceptions import MultipleObjectsReturned
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from telegram import Bot
from asgiref.sync import async_to_sync

from .common.util.homonym import teams_to_string
from .models import Poll, Participant, Group
from .common.util.team import random_team_generator

# Here are functions that interact with the bot from the app's "side"


def print_teams_message(teams_created):
    teams_string = teams_to_string(teams_created)

    team_text = []
    for i, team in enumerate(teams_string):
        team_text.append("*Equipe {}*".format(i + 1))
        for member in team:
            team_text.append('- {}'.format(member))
        team_text.append('')
    team_text.append('Amusez-vous bien !')
    text = '\n'.join(team_text)
    return text


def post_teams(request, chat_id):
    poll = get_object_or_404(Poll, pk=chat_id)
    telegram_id = poll.chat_id
    token = os.getenv('BOT_TOKEN')
    bot = Bot(token=token)
    teams_created = [[participant for participant in team.participant_set.all()] for team in poll.team_set.all()]
    text = print_teams_message(teams_created)
    async_to_sync(bot.sendMessage)(chat_id=telegram_id, text=text, parse_mode='Markdown')
    return HttpResponse("")


def bot_generate_teams(chat_id):
    # poll = await sync_to_async(get_object_or_404)(Poll, chat_id=update.effective_chat)
    #print(chat_id)
    poll = get_object_or_404(Poll, chat_id=chat_id)
    participants = poll.participant_set.all()
    requests = poll.group_set.all()
    requests = [group.request() for group in requests]
    for request in requests:
        if len(request) > poll.team_size:
            return "Une ou plusieurs requêtes sont plus grandes que la taille d'équipe possible"
    teams_created = random_team_generator(participants,
                                          groupements=requests,
                                          max_per_team=poll.team_size)

    return print_teams_message(teams_created)


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


def participant_coming(user:telegram.User, poll_id):
    poll = get_object_or_404(Poll, poll_id=poll_id)
    first_name = user.first_name
    last_name = user.last_name
    username = user.username
    user_id = user.id
    try:
        new_participant = Participant.objects.get(participant_id=user_id)
        poll.participant_set.add(new_participant)
        new_participant.save()
    except Participant.DoesNotExist:
        null_participants = Participant.objects.filter(poll=None)
        if len(null_participants) == 0:
            new_participant = Participant.objects.create(participant_name=first_name,
                                                         surname=last_name,
                                                         username=username,
                                                         participant_id=user_id)
            poll.participant_set.add(new_participant)
        else:
            new_participant = null_participants[0]
            new_participant.poll.clear()
            poll.participant_set.add(new_participant)
            new_participant.participant_name = first_name
            new_participant.surname = last_name
            new_participant.username = username
            new_participant.participant_id = user_id
            new_participant.save()
    return poll.participant_set.count(), poll.max_participant, poll.chat_id


def participant_notcoming(user:telegram.User, poll_id):
    poll = get_object_or_404(Poll, poll_id=poll_id)
    user_id = user.id
    try:
        user_todelete = Participant.objects.get(participant_id=user_id)
    except Participant.DoesNotExist:
        return
    group = user_todelete.group_in_poll(poll)
    user_todelete.group.remove(group)
    team = user_todelete.team_in_poll(poll)
    user_todelete.team.remove(team)
    user_todelete.poll.remove(poll)
    user_todelete.save()


def bot_add_participant(parse_name, chat_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    first_name = parse_name[0]
    last_name = " ".join(parse_name[1:])
    null_participants = Participant.objects.filter(poll=None)
    if len(null_participants) == 0:
        new_participant = Participant.objects.create(participant_name=first_name, participant_id=0)
        if last_name:
            new_participant.surname = last_name
        else:
            homonyms = Participant.objects.filter(participant_name=first_name)
            for i in range(1, homonyms.count() + 1):
                default_name = '#' + str(i)
                if homonyms.filter(surname=default_name).count() == 0:
                    new_participant.surname = default_name
                    break
        poll.participant_set.add(new_participant)
        new_participant.save()
    else:
        new_participant = null_participants[0]
        new_participant.poll.clear()
        poll.participant_set.add(new_participant)
        new_participant.participant_name = first_name
        if last_name:
            new_participant.surname = last_name
        else:
            homonyms = Participant.objects.filter(participant_name=first_name)
            for i in range(homonyms.count() + 1):
                default_name = '#' + str(i)
                if homonyms.filter(surname=default_name).count() == 0:
                    new_participant.surname = default_name
        new_participant.participant_id = 0
        new_participant.save()
    return poll.participant_set.count(), poll.max_participant


def bot_remove_participant(parse_name, chat_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    first_name = parse_name[0]
    last_name = " ".join(parse_name[1:])
    participant_query = Participant.objects.filter(poll=poll, participant_name=first_name)
    try:
        user_todelete = participant_query.get()
        if last_name and user_todelete.surname != last_name:
            return 0
    except Participant.DoesNotExist:
        return 0
    except MultipleObjectsReturned:
        if not last_name:
            return 2
        else:
            participant_query = participant_query.filter(surname=last_name)
            try:
                user_todelete = participant_query.get()
            except Participant.DoesNotExist:
                return 0
            except MultipleObjectsReturned:
                return 2
    group = user_todelete.group_in_poll(poll)
    user_todelete.group.remove(group)
    team = user_todelete.team_in_poll(poll)
    user_todelete.team.remove(team)
    user_todelete.poll.remove(poll)
    user_todelete.save()
    return 1


def bot_participant_list(chat_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    #print(poll.pk)
    participant_dict = poll.participants_to_string()
    text = ["Il y a actuellement {} personnes qui viennent \U0001F44D \n"
                    "(La limite de places est {})\n"
                    "\n*Liste des participant-e-s*".format(poll.number_of_participants(), poll.max_participant)]
    for participant in participant_dict.values():
        text.append("- {}".format(participant))
    return '\n'.join(text)


def add_request(chat_id, request_list):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    participants_list = []
    groups = set()
    for participant in request_list:
        parse_name = participant.split(' ')
        first_name = parse_name[0]
        last_name = " ".join(parse_name[1:])
        participant_query = Participant.objects.filter(poll=poll, participant_name=first_name)
        try:
            user_request = participant_query.get()
            if last_name and user_request.surname != last_name:
                return 0, participant
        except Participant.DoesNotExist:
            return 0, participant
        except MultipleObjectsReturned:
            if not last_name:
                return 2, participant
            else:
                participant_query = participant_query.filter(surname=last_name)
                try:
                    user_request = participant_query.get()
                except Participant.DoesNotExist:
                    return 0, participant
                except MultipleObjectsReturned:
                    return 2, participant
        participants_list.append(user_request)
        group = user_request.group_in_poll(poll)
        if group:
            groups.add(group)
    if len(groups) > 1:
        return 3, groups
    elif len(groups) == 0:
        if poll.group_set.count() > 17:
            return 4, groups
        else:
            empty_groups = poll.group_set.filter(color='zinc')
            if len(empty_groups) == 0:
                new_group = Group.objects.create(poll=poll, tab_position=poll.last_group() + 1)
            else:
                new_group = empty_groups[0]
            new_group.pick_color(poll.group_set.all())
            for participant in participants_list:
                participant.group.add(new_group)
                participant.save()
            return 1, new_group
    else:
        new_group = groups.pop()
        for participant in participants_list:
            if participant.group is None:
                participant.group.add(new_group)
        return 1, new_group


def print_request(chat_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    participants_list = []
    if poll.group_set.count() == 0:
        return "Il n'y a aucune requête"
    for group in poll.group_set.all():
        if group.participant_set.count() > 0:
            participants_list.append(group.participant_set.all())
    groups_string = teams_to_string(participants_list)
    team_text = []
    for i, team in enumerate(groups_string):
        team_text.append("*Requête {}*".format(i + 1))
        for member in team:
            team_text.append('- {}'.format(member))
        team_text.append('')
    text = '\n'.join(team_text)
    return text


def bot_set_max(chat_id, max_val):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    poll.max_participant = max_val
    poll.save()
    return poll.max_participant