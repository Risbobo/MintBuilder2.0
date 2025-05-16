from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseNotFound
from django.template.response import TemplateResponse
from .models import Poll, Participant, Team, Group
from .common.util.team import random_team_generator

# Create your views here.


def index_view(request):
    return render(request, 'mintbuilderapp/index.html', {"name": 'user1', "color": 'teal'})


def select_button_view(request, chat_id, group_id):
    user_id = int(request.POST.get('button_unselected'))
    user = get_object_or_404(Participant, pk=user_id)
    poll = get_object_or_404(Poll, chat_id=chat_id)
    group = get_object_or_404(Group, pk=group_id)
    # Check if user is in no group
    # (important for concurrency i.e. the user has been added in a group by another request)
    if not user.group_in_poll(poll):
        user.group.add(group)
        user.save()
        message = {}
    else:
        message = {'message' : 'Un autre utilisateur a fait une modification qui a annulé la vôtre'}
    to_render = detail(request, chat_id, group_id)
    if message:
        to_render.context_data.update(message)
    # print(to_render.context_data)
    return to_render #detail(request, chat_id, group_id)


def unselect_button_view(request, chat_id, group_id):
    user_id = int(request.POST.get('button_selected'))
    user = get_object_or_404(Participant, pk=user_id)
    poll = get_object_or_404(Poll, chat_id=chat_id)
    # unselect user
    group = get_object_or_404(Group, pk=group_id)
    # Check if user is indeed in the targeted group
    # (important for concurrency i.e. the user has been removed from a group by another request)
    if user.group_in_poll(poll) == group:
        group.participant_set.remove(user)
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
    part_groups = [(participant, participant.group_in_poll(poll))
                   for participant in poll.participant_set.all().order_by('participant_name')]
    return TemplateResponse(request, "mintbuilderapp/detail.html",
                            {"poll": poll, "group": group, "part_groups": part_groups})


def add_participant(request, chat_id, group_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    user_name = request.POST.get('new_participant')
    # TODO : 1st and 2nd name control
    null_participants = Participant.objects.filter(poll=None)#get(chat_id=0).participant_set.all()
    if len(null_participants) == 0:
        new_participant = Participant.objects.create(participant_name=user_name, participant_id=0)
        poll.participant_set.add(new_participant)
    else:
        new_participant = null_participants[0]
        new_participant.poll.clear()
        poll.participant_set.add(new_participant)
        new_participant.participant_name = user_name
        new_participant.save()
    # TODO : add message if more than max size
    return detail(request, chat_id, group_id)


def remove_participant(request, chat_id, group_id):
    user_id = int(request.POST.get("confirm_delete_but"))
    user_todelete = get_object_or_404(Participant, pk=user_id)
    poll = get_object_or_404(Poll, chat_id=chat_id)
    group = user_todelete.group_in_poll(poll)
    user_todelete.group.remove(group)
    team = user_todelete.team_in_poll(poll)
    user_todelete.team.remove(team)
    user_todelete.poll.remove(poll)
    user_todelete.save()
    return detail(request, chat_id, group_id)


def edit_poll_param(request, chat_id, group_id):
    poll = get_object_or_404(Poll, chat_id=chat_id)
    new_max = request.POST.get('max_participant')
    new_size = request.POST.get('team_size')
    poll.max_participant = new_max
    poll.team_size = new_size
    poll.save()
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
    '''
    Generate teams if they don't exist already or if they are not valid
    '''
    poll = get_object_or_404(Poll, chat_id=chat_id)
    teams = poll.team_set.all()
    participants = poll.participant_set.all()
    # If some requests or the teams size are not respected, clear the team then roll them
    if not poll.request_respected() or not poll.teamsize_respected():
        clear_teams(chat_id)
    # If teams are already rolled, show them as is
    # TODO : request are larger than team size control
    if not poll.teams_created():
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
    teams = [team for team in poll.team_set.all() if team.participant_set.count() > 0]
    return render(request, "mintbuilderapp/teams.html", {"poll": poll, "teams": teams})


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
