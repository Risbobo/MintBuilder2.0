from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views import generic
from .models import Poll, Participant, Team, Group
from .common.util.team import random_team_generator
from random import shuffle

# Create your views here.


def index_view(request):
    return render(request, 'mintbuilderapp/index.html', {"name": 'user1', "color": 'teal'})


def select_button_view(request, chat_id, group_id):
    value = request.POST.get('button_unselected')
    # state = 0 : delete user | state = 1 : do nothing (canceled delete) | state = 2 : select user button
    user_id, state = eval(value)
    user = get_object_or_404(Participant, pk=user_id)
    # delete user
    if state == 0:
        return remove_participant(request, chat_id, group_id, user)
    # select user
    elif state == 2:
        group = get_object_or_404(Group, pk=group_id)
        # Check if user is in no group
        # (important for concurrency i.e. the user has been added in a group by another request)
        if not user.group:
            user.group = group
            user.save()
            message = {}
        else:
            message = {'message' : 'Un autre utilisateur a fait une modification qui a annulé la vôtre'}
        to_render = detail(request, chat_id, group_id)
        if message:
            to_render.context_data.update(message)
        # print(to_render.context_data)
        return to_render #detail(request, chat_id, group_id)
    # do nothing (state 1)
    else:
        return detail(request, chat_id, group_id)


def unselect_button_view(request, chat_id, group_id):
    value = request.POST.get('button_selected')
    # state = 0 : delete user | state = 1 : do nothing (canceled delete) | state = 2 : unselect user button
    user_id, state = eval(value)
    user = get_object_or_404(Participant, pk=user_id)
    # delete user
    if state == 0:
        return remove_participant(request, chat_id, group_id, user)
    # unselect user
    elif state == 2:
        group = get_object_or_404(Group, pk=group_id)
        # Check if user is indeed in the targeted group
        # (important for concurrency i.e. the user has been removed from a group by another request)
        if user.group == group:
            group.participant_set.remove(user)
        return detail(request, chat_id, group_id)
    # do nothing (state 1)
    else :
        return detail(request, chat_id, group_id)


def select_lock_button_view(request, chat_id, group_id):
    value = request.POST.get('button_selected_locked')
    # state = 0 : delete user | state = 1 : do nothing (canceled delete) | state = 2 : do nothing (locked)
    user_id, state = eval(value)
    user = get_object_or_404(Participant, pk=user_id)
    # delete user
    if state == 0:
        return remove_participant(request, chat_id, group_id, user)
    # do nothing (state 1 and 2)
    else:
        return detail(request, chat_id, group_id)


# group_id is group.pk
def detail(request, chat_id, group_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    # Remove tabs of empty groups by defaulting the group to zinc and putting it at the end of the list of groups
    for group in poll.group_set.all():
        if group.number_of_participants() == 0 and group.color != 'zinc' and group.pk != group_id:
            group.color = 'zinc'
            group.tab_position = poll.last_group() + 1
            group.save()
    groups = poll.group_set.all().order_by('tab_position')
    group = get_object_or_404(Group, pk=group_id)
    # group is the tab on which we are. If it is an empty group, it will be zinc. A color is picked for the group
    if group.color == 'zinc':
        group.pick_color(groups)
    return TemplateResponse(request, "mintbuilderapp/detail.html", {"poll": poll, "group": group, "group_id": group_id})


def add_participant(request, chat_id, group_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    # vvvv This was so hard to find for some reason vvvv
    user_name = request.headers.get('HX-Prompt')
    # TODO : 1st and 2nd name control
    null_participants = Participant.objects.filter(poll=None)#get(chat_id=0).participant_set.all()
    if len(null_participants) == 0:
        print("creating user")
        new_participant = Participant.objects.create(participant_name=user_name, participant_id=0)
        #new_participant.save()
        poll.participant_set.add(new_participant)
    else:
        print("using old user")
        new_participant = null_participants[0]
        new_participant.poll.clear()
        poll.participant_set.add(new_participant)
        new_participant.participant_name = user_name
        new_participant.save()
        print("new participant : ", new_participant)
    print(poll.participant_set.all())
    return detail(request, chat_id, group_id)


def remove_participant(request, chat_id, group_id, user_todelete):
    print('deleting user : ', user_todelete)
    #null_poll = get_object_or_404(Poll, chat_id=0)
    user_todelete.group = None
    user_todelete.team = None
    user_todelete.poll.clear()
    #null_poll.participant_set.add(user_todelete)
    user_todelete.save()
    print("deleted user : ", user_todelete)
    return detail(request, chat_id, group_id)


def new_request(request, chat_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    # Look for first zinc (empty) group
    for group in poll.group_set.all().order_by('tab_position'):
        if group.color == 'zinc':
            return detail(request, chat_id, group.pk)
    if poll.group_set.count() > 17:
        # TODO : something if too many groups
        return HttpResponseNotFound("<h1>Trop de requêtes</h1>")
    else:
        new_group = Group.objects.create(poll=poll, tab_position=poll.last_group() + 1)
        return detail(request, chat_id, new_group.pk)


def initialize(request, chat_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    for i, group in enumerate(poll.group_set.all()):
        group.color = 'zinc'
        group.tab_position = i
        group.participant_set.clear()
        group.save()
    return new_request(request, chat_id)


def generate_teams(request, chat_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    teams = poll.team_set.all()
    participants = poll.participant_set.all()
    # If no team exist, if some requests are not respected or if the teams size is not respected, roll the teams
    # Else show teams as they are
    if not poll.teams_created() or not poll.request_respected() or not poll.teamsize_respected():
        requests = [group.request() for group in poll.group_set.all()]
        teams_created = random_team_generator(participants, groupements=requests, max_per_team=poll.team_size)
        to_create = len(teams_created)-len(teams)
        # Create new teams if there aren't enough
        if to_create > 0:
            for _ in range(to_create):
                Team.objects.create(poll=poll)
        teams = poll.team_set.all() # prob useless with postgres
        # Populate teams with the result of random_team_generator
        for team, team_created in zip(teams, teams_created):
            for team_member in team_created:
                team.participant_set.add(team_member)
            team.save()
    return render(request, "mintbuilderapp/teams.html", {"poll": poll})


def clear_teams(chat_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    teams = poll.team_set.all()
    for team in teams:
        team.participant_set.clear()
        team.save()


def reroll_teams(request, chat_id):
    clear_teams(chat_id)
    return generate_teams(request, chat_id)


def clear_section(request):
    return HttpResponse("")


def result(request, chat_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    return render(request, "mintbuilderapp/result.html", {"poll": poll})
