import random

from django.db import models
from django.contrib import admin

# Create your models here.


class Poll(models.Model):
    # TODO : add question_text to personalise prompt
    chat_id = models.IntegerField()
    chat_name = models.CharField(max_length=200)
    team_size = models.IntegerField(default=6)
    max_participant = models.IntegerField(default=12)

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
        for team in self.team_set.all():
            if team.number_of_participants() > self.team_size:
                return False
        return True

    def request_respected(self):
        for group in self.group_set.all():
            request = list(group.participant_set.all())
            for i, part1 in enumerate(request):
                for part2 in request[i:]:
                    if part1.team != part2.team:
                        return False
        return True

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


#TODO : update model with 1st and 2nd name + homonym control
class Participant(models.Model):
    poll = models.ManyToManyField(Poll)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    participant_id = models.IntegerField()
    participant_name = models.CharField(max_length=200)

    @admin.display(
        ordering='participant_name',
        description="Number of poll answered"
    )
    def number_of_polls(self):
        return self.poll.count()

    def __str__(self):
        return self.participant_name
