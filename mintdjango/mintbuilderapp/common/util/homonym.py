def teams_to_string(teams_created):
    '''
    :param teams_created: A list of list of Participants (a list of teams or requests)
    :return: A list of list of string that are the names of the Participants with a homonym check
    '''
    first_names = set()
    homonyms = set()
    for team in teams_created:
        for member in team:
            first_name = member.participant_name
            if first_name in first_names:
                homonyms.add(first_name)
            else:
                first_names.add(first_name)
    teams_string = []
    for team in teams_created:
        team_string = []
        for member in team:
            first_name = member.participant_name
            if first_name in homonyms:
                last_name = member.surname if member.surname else member.username if member.username else "X"
                team_string.append(first_name + " " + last_name)
            else:
                team_string.append(first_name)
        teams_string.append(team_string)
    return teams_string