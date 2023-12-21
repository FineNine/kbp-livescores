from django.shortcuts import render
from django.http import HttpResponse

import numpy as np
import pandas as pd
import os
import json

# Create your views here.
def test(request):
    print(os.getcwd())
    payload = pd.read_csv('data/final.csv', index_col=0)
    return HttpResponse(payload.to_html())

def index(request):
    test = ['401551470','401551733','401551746']
    scores = load_scores()
    games_to_update = create_update_list(scores)

    game_data = fake_request(test)

    for game in game_data:
        teams = get_teams(scores, convert_to_utf(game['header']['id']), test[0])
        scores = updated_scores(scores, game, teams)
        # CHECK IF FINAL

    margins = compute_margins(scores)
    picks = load_picks()

    print(len(picks)/len(scores))
    assert len(picks)/len(scores) ==1 

    kbp_scores = compute_kbp_scores(picks, margins)

    return HttpResponse(kbp_scores.to_html(index=False))

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
    loser_scores = scores.groupby('Bowl')['Points'].min().reset_index()
    loser_scores.columns = ['Bowl','LoserPoints']
    margins = scores.merge(loser_scores, on='Bowl')
    margins['Margin'] = margins['Points'] - margins['LoserPoints']
    print(margins[margins['Margin'] != 0])
    return margins[margins['Margin'] != 0]

def compute_kbp_scores(picks, margins):
    picks = picks.merge(margins[['Bowl','Team','Margin']], on=['Bowl','Team'])
    print(picks.head())
    picks['Diff'] = picks['Points'] - picks['Margin']
    picks['Diff'] = picks['Diff'].abs()
    picks['Score'] = picks.Diff.apply(scoring_alg)
    final_scores = picks.groupby('Name')['Score'].sum().reset_index()
    final_scores['Rank'] = final_scores.Score.rank(method='min', ascending=False).astype(int)

    names = load_nicknames()
    final_scores = final_scores.merge(names, on='Name')
    return final_scores[['Rank','Nickname','Score']].sort_values('Rank')


def convert_to_utf(string):
    print(string)
    new_str = string.encode('utf-8', errors='backslashreplace').decode('utf-8')
    print(new_str)
    return new_str
    return bytes(string, 'latin-1').decode('utf-8')

def get_teams(scores, id: str, test):
    assert id in scores['ESPN Game ID'].astype(str).to_list()
    return scores[scores['ESPN Game ID'].astype(str) == id]['ESPN Team Name'].to_list()

def fake_request(game_ids):
    game_data = []
    for id in game_ids:
        temp = int(id)
        game_data.append(read_json(f"data/{temp}.json"))
    return game_data

def load_scores():
    return pd.read_csv('data/scores.csv', index_col=0)

def load_picks():
    return pd.read_csv('data/picks.csv')

def load_nicknames():
    return pd.read_csv('data/nicknames.csv')

def create_update_list(scores):
    return scores[scores['isFinal'] == 0]['ESPN Game ID']

def read_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


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