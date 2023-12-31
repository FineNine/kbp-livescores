from django.shortcuts import render
from django.http import HttpResponse

import numpy as np
import pandas as pd
import os
import json
import requests
import datetime

# Create your views here.
def kbp_scores(response):
    return HttpResponse(pd.read_csv('kbp/data/kbp.csv').to_html(index=False))

def test(request):
    scores = load_scores()

    scores = update_scores(scores)
    scores.to_csv('kbp/data/scores_new.csv', index=False)

    margins = compute_margins(scores)
    picks = load_picks()
    kbp_scores = compute_kbp_scores(picks, margins)

    return HttpResponse(kbp_scores.to_html(index=False))

def test_update(request):
    return HttpResponse(create_update_list(pd.read_csv('kbp/data/scores_new.csv')))

def index(request):
    # DEV DATA
    test = ['401551470','401551733','401551746']


    scores = load_scores()
    games_to_update = create_update_list(scores)

    game_data = fake_request(test)

    for game in game_data:
        teams = get_teams(scores, convert_to_utf(game['header']['id']), test[0])
        scores = update_scores(scores, game, teams)
        # CHECK IF FINAL

    margins = compute_margins(scores)
    picks = load_picks()


    kbp_scores = compute_kbp_scores(picks, margins)

    return HttpResponse(kbp_scores.to_html(index=False))

def update_scores(scores):
    game_ids = create_update_list(scores)
    # game_ids = ['401551470','401551733','401551746']

    # game_data = request_live_score(game_ids[0])
    data = []
    for id in game_ids:
        game_data = fake_request(id)
        # game_data = request_live_score(id)
        # print(game_data)
        # print(dict(game_data))
        data += format_game_data(id, game_data)
        # print(data)
    data = pd.DataFrame(data, columns = ['ESPN Game ID','ESPN Team Name','ESPN Team ID','Points','State','isFinal','date'])



    data['index'] = data['ESPN Game ID'].astype(str) + data['ESPN Team Name']
    scores['index'] = scores['ESPN Game ID'].astype(str) + scores['ESPN Team Name']

    data.set_index('index', inplace=True)
    scores.set_index('index', inplace=True)

    temp_scores = scores[scores.columns.difference(data.columns)]
    print(data)
    data = temp_scores.merge(data, left_index=True, right_index=True, how='left')
    scores.update(data, overwrite=True)
    print(scores)
    # scores.set_index('index', inplace=True)
    # print(scores[['Bowl','Team','Points']])

    # print(game_data)

    # game_data = 
    return scores

def format_game_data(id, response):
    team_data = response['header']['competitions'][0]['competitors']
    date = response['header']['competitions'][0]['date']
    state = response['header']['competitions'][0]['status']['type']['state']
    is_final = response['header']['competitions'][0]['status']['type']['completed']

    if state == 'pre':
        team0_points = 0
        team1_points = 0
    else:
        team0_points = int(convert_to_utf(team_data[0]['score']))
        team1_points = int(convert_to_utf(team_data[1]['score']))

    team0 = convert_to_utf(team_data[0]['team']['displayName'])
    if team0 == "TBD":
        team0 = "TBD1"
        team1 = "TBD2"
    else:
        team1 = convert_to_utf(team_data[1]['team']['displayName'])
    return [
        (
            id,
            team0,
            int(convert_to_utf(team_data[0]['id'])),
            team0_points,
            state,
            is_final,
            date
        ),
        (
            id,
            team1,
            int(convert_to_utf(team_data[1]['id'])),
            team1_points,
            state,
            is_final,
            date
        ),
    ]

def updated_scores(scores, game, teams):
    team_data = game['header']['competitions'][0]['competitors']
    assert len(team_data) == 2

    team_one = convert_to_utf(team_data[0]['team']['displayName'])
    team_two = convert_to_utf(team_data[1]['team']['displayName'])
    status = game['header']['competitions'][0]['status']['type']['completed']

    assert team_one in teams
    assert team_two in teams
    
    try:
        scores.loc[scores['ESPN Team Name'] == team_one, ['Points']] = int(convert_to_utf(team_data[0]['score']))
        scores.loc[scores['ESPN Team Name'] == team_two, ['Points']] = int(convert_to_utf(team_data[1]['score']))
    except:
        scores.loc[scores['ESPN Team Name'] == team_one, ['Points']] = 0
        scores.loc[scores['ESPN Team Name'] == team_two, ['Points']] = 0

    scores.loc[scores['ESPN Team Name'] == team_one, ['isFinal']] = status
    scores.loc[scores['ESPN Team Name'] == team_two, ['isFinal']] = status

    return scores.copy()

def compute_margins(scores):
    temp_scores = scores.copy()
    loser_scores = temp_scores.groupby('Bowl')['Points'].min().reset_index()
    loser_scores.columns = ['Bowl','LoserPoints']
    margins = temp_scores.merge(loser_scores, on='Bowl')
    margins['Margin'] = margins['Points'] - margins['LoserPoints']
    return margins[margins['Margin'] != 0]

def compute_kbp_scores(picks, margins):
    temp_picks = picks.copy()
    temp_margins = margins.copy()
    temp_picks = temp_picks.merge(temp_margins[['Bowl','Team','Margin']], on=['Bowl','Team'])
    temp_picks['Diff'] = temp_picks['Points'] - temp_picks['Margin']
    temp_picks['Diff'] = temp_picks['Diff'].abs()
    temp_picks['Score'] = temp_picks.Diff.apply(scoring_alg)
    final_scores = temp_picks.groupby('Name')['Score'].sum().reset_index()
    final_scores['Rank'] = final_scores.Score.rank(method='min', ascending=False).astype(int)

    names = load_nicknames()
    final_scores = final_scores.merge(names, on='Name')
    final_scores = final_scores[['Rank','Nickname','Score']]
    final_scores.columns = ['Rank','Name','Score']
    return final_scores.sort_values('Rank')

def convert_to_utf(string):
    new_str = string.encode('utf-8', errors='backslashreplace').decode('utf-8')
    return new_str
    return bytes(string, 'latin-1').decode('utf-8')

def get_teams(scores, id: str, test):
    assert id in scores['ESPN Game ID'].astype(str).to_list()
    return scores[scores['ESPN Game ID'].astype(str) == id]['ESPN Team Name'].to_list()

def fake_request(id):
    print(f"Getting game {id}")
    return read_json(f"kbp/data/{id}.json")

def request_live_score(id):
    print(f"Getting game {id}")
    data = requests.get(f"http://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={id}").json()
    write_json_to_file(data, id)
    return data

def load_scores():
    return pd.read_csv('kbp/data/scores.csv')

def load_picks():
    return pd.read_csv('kbp/data/picks.csv')

def load_nicknames():
    return pd.read_csv('kbp/data/nicknames.csv')

def create_update_list(scores):
    now = datetime.datetime.now().timestamp()
    # return scores[(scores['isFinal'] == 0) & (scores['date'].apply(lambda x: pd.to_datetime(x).timestamp() > datetime.datetime.now().timestamp()))]['ESPN Game ID'].unique()
    return list(scores[(~scores['isFinal']) & (pd.to_datetime(scores['date']).apply(lambda x: x.timestamp() < now))]['ESPN Game ID'].unique())

def read_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def write_json_to_file(data, id, directory="kbp/data"):
    """
    Writes the given data to a JSON file in the specified directory.
    :param data: The data to write to the file.
    :param filename: The name of the file.
    :param directory: The directory where the file will be saved.
    """
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, f"{id}.json")
    with open(filepath, 'w') as file:
        json.dump(data, file, indent=4)

def scoring_alg(value):
    if np.isnan(value):
        return 0
    elif value == 0:
        return 10
    elif value <= 3:
        return 8
    elif value <= 7:
        return 6
    else:
        return 5 