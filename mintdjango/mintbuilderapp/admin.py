from django.contrib import admin
from .models import Team, Group, Poll, Participant

# Register your models here.


class ParticipantPollInline(admin.TabularInline):
    model = Participant.poll.through
    extra = 1


class ParticipantTeamInline(admin.TabularInline):
    model = Participant


class PollAdmin(admin.ModelAdmin):
    inlines = [ParticipantPollInline]
    list_display = ["chat_name", "chat_id", "number_of_participants"]
    list_filter = ["chat_name"]
    search_fields = ["chat_name"]


class UserAdmin(admin.ModelAdmin):
    inlines = [ParticipantPollInline]
    list_display = ["participant_name", "participant_id", "number_of_polls"]
    list_filter = ["participant_name"]
    search_fields = ["participant_name"]


class TeamAdmin(admin.ModelAdmin):
    inlines = [ParticipantTeamInline]
    list_display = ["poll"]


class GroupAdmin(admin.ModelAdmin):
    inlines = [ParticipantTeamInline]
    list_display = ["color", "number_of_participants", "poll"]


admin.site.register(Participant, UserAdmin)
admin.site.register(Poll, PollAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Group, GroupAdmin)