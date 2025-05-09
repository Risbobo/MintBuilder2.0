import math
import random


def random_team_generator(participants, groupements, max_per_team):
    number_of_teams = math.ceil(len(participants) / max_per_team)
    teams = [[] for _ in range(number_of_teams)]
    teams_size = [math.floor(len(participants) / number_of_teams) for _ in range(number_of_teams)]
    for i in range(len(participants) % number_of_teams):
        teams_size[i] += 1
    # Set up constraints and participants
    groupements.sort(key=len)
    groupements.reverse()
    for u in participants:
        if not any(u in sub_list for sub_list in groupements):
            groupements.append([u])
    # Generate the teams randomly
    for group in groupements:
        possible_team = [x for x in range(number_of_teams)]
        while len(possible_team) > 0:
            random.shuffle(possible_team)
            selected_team = possible_team[0]
            if len(teams[selected_team]) + len(group) > teams_size[selected_team]:
                possible_team.remove(selected_team)
            else:
                teams[selected_team] += group
                break
        if len(possible_team) == 0:
            print('Problem')

    return teams
