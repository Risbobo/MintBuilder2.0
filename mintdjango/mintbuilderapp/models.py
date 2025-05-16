import random
import math

from django.db import models
from django.contrib import admin

# Create your models here.


class Poll(models.Model):
    chat_id = models.IntegerField()
    poll_id = models.IntegerField(default=0)
    chat_name = models.CharField(max_length=200)
    team_size = models.IntegerField(default=6)
    max_participant = models.IntegerField(default=12)
    is_telegram =models.BooleanField(default=False)

    def last_group(self):
        groups = list(self.group_set.all().order_by('tab_position'))
        if len(groups) == 0:
            return 0
        else:
            return groups[-1].tab_position

    def teams_created(self):
        for team in self.team_set.all():
            if team.number_of_participants() > 0:
                return True
        return False

    def teamsize_respected(self):
        if self.team_set.count() > math.ceil(self.participant_set.count() / self.team_size):
            return False
        for team in self.team_set.all():
            if team.number_of_participants() > self.team_size:
                return False
        return True

    def request_respected(self):
        for group in self.group_set.all():
            request = list(group.participant_set.all())
            for i, part1 in enumerate(request):
                for part2 in request[i:]:

                    if part1.team_in_poll(self) != part2.team_in_poll(self):
                        return False
        return True

    def check_homonym(self, participant):
        participant.verbose = False
        for other_participant in self.participant_set.all():
            if participant.participant_name == other_participant.participant_name:
                participant.verbose = True
                other_participant.verbose = True

    def inner_check_homonym(self):
        participant_list = self.participant_set.all()
        for i in range(len(participant_list)):
            participant = participant_list[i]
            participant.verbose = False
            for other_participant in participant_list[i:]:
                if participant.participant_name == other_participant.participant_name:
                    participant.verbose = True
                    other_participant.verbose = True

    @admin.display(
        ordering='chat_name',
        description="Number of participants"
    )
    def number_of_participants(self):
        return self.participant_set.count()

    def __str__(self):
        return self.chat_name


class Team(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    @admin.display(
        description="Number of participants"
    )
    def number_of_participants(self):
        return self.participant_set.count()


class Group(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    color = models.CharField(max_length=20, default='zinc')
    tab_position = models.IntegerField(default=0)

    def pick_color(self, other_groups):
        cols = ['red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal', 'cyan', 'sky',
                'blue', 'indigo', 'violet', 'purple', 'fuchsia', 'pink', 'rose']
        random.shuffle(cols)
        while True:
            col = cols.pop(0)
            other_cols = [other_group.color for other_group in other_groups]
            if col not in other_cols:
                break
            if len(cols) == 0:
                col = 'slate'
                break
        self.color = col
        self.save()

    def request(self):
        return list(self.participant_set.all())

    @admin.display(
        ordering='color',
        description="Number of participants"
    )
    def number_of_participants(self):
        return self.participant_set.count()

    def __str__(self):
        return self.color


class Participant(models.Model):
    poll = models.ManyToManyField(Poll)
    team = models.ManyToManyField(Team)
    group = models.ManyToManyField(Group)
    participant_name = models.CharField(max_length=200)
    participant_id = models.IntegerField(default=0)
    surname = models.CharField(max_length=200, default=None, null=True)
    username = models.CharField(max_length=200, default=None, null=True)
    verbose = models.BooleanField(default=False)

    @admin.display(
        ordering='participant_name',
        description="Number of poll answered"
    )
    def number_of_polls(self):
        return self.poll.count()

    def group_in_poll(self, poll: Poll):
        group = filter(lambda gr: gr in poll.group_set.all(), self.group.all())
        l = list(group)
        if len(l) == 0:
            return None
        else:
            assert len(l) == 1
            return l[0]

    def team_in_poll(self, poll: Poll):
        team = filter(lambda t: t in poll.team_set.all(), self.team.all())
        l = list(team)
        if len(l) == 0:
            return None
        else:
            assert len(l) == 1
            return l[0]

    def is_telegram(self):
        return self.participant_id != 0

    def __str__(self):
        if not self.verbose:
            return self.participant_name
        else:
            if self.surname:
                return str(self.participant_name) + " " + str(self.surname)
            else:
                return str(self.participant_name) + " '" + str(self.username) + "'"