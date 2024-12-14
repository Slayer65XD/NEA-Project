from flask import Flask, render_template
import requests
import csv
import os
import json
from datetime import datetime

app = Flask(__name__)

# API details
apiUrl = 'https://api.football-data.org/v4/competitions/PL/matches'
apiKey = '9ca47c095388418992b1fa8b56265aba'

@app.route('/')
def homePage():
    results = {}
    jsonFilePath = 'matches.json'

    # Check when cache was last updated
    fileModTime = os.path.getmtime(jsonFilePath)
    fileModDatetime = datetime.fromtimestamp(fileModTime)

    todayStart = datetime.combine(datetime.today(), datetime.min.time())

    cacheExpired = fileModDatetime < todayStart

    if cacheExpired: 
        print('Cache expired, fetching data...')

        # Fetch live scores data from the API
        try:
            response = requests.get(
                apiUrl,
                headers={'X-Auth-Token': apiKey}
            )
        except requests.RequestException as e:
            print(f'Error fetching live scores: {e}')
            
        response.raise_for_status()

        if response.text:
            print('updating cache')
            f = open(jsonFilePath, "w")
            f.write(response.text)
            f.close()

    with open(jsonFilePath) as f:
        data = json.load(f)

    predictions = {}

    # Load data from CSV
    with open('data/PredictedResults24.csv', 'r') as csvFile:
        
        teams = {}

        csvReader = csv.DictReader(csvFile)
        for row in csvReader:
            roundNumber = int(row['round_number'])

            teams[row['home_team_name']] = teams.get(row['home_team_name'], 0) 
            teams[row['away_team_name']] = teams.get(row['away_team_name'], 0) 

            # Map numerical result to descriptive text
            result = row['predictedResult'].strip()
            if result == '1':
                result = 'Home Win'
                teams[row['home_team_name']] += 3
            elif result == '0':
                result = 'Draw'
                teams[row['home_team_name']] += 1
                teams[row['away_team_name']] += 1
            elif result == '-1':
                result = 'Away Win'
                teams[row['away_team_name']] += 3                

            predictions.setdefault(roundNumber, []).append({
                'homeTeam': row['home_team_name'],
                'awayTeam': row['away_team_name'],
                'result': result
            })

    predictionsTable = dict(sorted(teams.items(), key=lambda item: item[1], reverse=True))
    
    teams = {}

    complete = 0
    correct = 0

    for match in data.get('matches', []):
        roundNumber = int(match['matchday'])

        homeTeamName = match['homeTeam']['shortName']
        awayTeamName = match['awayTeam']['shortName']

        teams[homeTeamName] = teams.get(homeTeamName, { 'points': 0, 'data': match['homeTeam'] }) 
        teams[awayTeamName] = teams.get(awayTeamName, { 'points': 0, 'data': match['awayTeam'] }) 

        # Map numerical result to descriptive text
        result = match['score']['winner']
        if result == 'HOME_TEAM':
            result = 'Home Win'
            teams[homeTeamName]['points'] += 3
        elif result == 'DRAW':
            result = 'Draw'
            teams[homeTeamName]['points'] += 1
            teams[awayTeamName]['points'] += 1
        elif result == 'AWAY_TEAM':
            result = 'Away Win'
            teams[awayTeamName]['points'] += 3
        else:
            result = 'None'

        results.setdefault(roundNumber, []);

        prediction = predictions[roundNumber][len(results[roundNumber])]["result"]
        
        if result != 'None':
            print(result)
            complete = complete + 1

            if result == prediction :
                correct = correct + 1            

        results[roundNumber].append({
            'homeTeam': homeTeamName,
            'awayTeam': awayTeamName,
            'result': result,
            'prediction': prediction,
        })

    table = dict(sorted(teams.items(), key=lambda item: item[1]['points'], reverse=True))

    accuracy = round((correct / complete) * 100)

    # Render results template with upcoming fixtures
    matchdays = sorted(results.keys())  # Sort matchdays in order
    return render_template('index.html', results=results, matchdays=matchdays, table=table, predictionsTable=predictionsTable, complete=complete, correct=correct, accuracy=accuracy)

@app.route('/results')
def resultsPage():
        results = {}
        jsonFilePath = 'matches.json'

        # Check when cache was last updated
        fileModTime = os.path.getmtime(jsonFilePath)
        fileModDatetime = datetime.fromtimestamp(fileModTime)

        todayStart = datetime.combine(datetime.today(), datetime.min.time())

        cacheExpired = fileModDatetime < todayStart

        if cacheExpired: 
            print('cache expired, fetching data')

            # Fetch live scores data from the API
            try:
                response = requests.get(
                    apiUrl,
                    headers={'X-Auth-Token': apiKey}
                )
            except requests.RequestException as e:
                print(f'Error fetching live scores: {e}')
                
            response.raise_for_status()

            if response.text:
                print('updating cache')
                f = open(jsonFilePath, "w")
                f.write(response.text)
                f.close()

        with open(jsonFilePath) as f:
            data = json.load(f)
        
        teams = {}

        for match in data.get('matches', []):
            roundNumber = int(match['matchday'])

            homeTeamName = match['homeTeam']['shortName']
            awayTeamName = match['awayTeam']['shortName']

            teams[homeTeamName] = teams.get(homeTeamName, { 'points': 0, 'data': match['homeTeam'] }) 
            teams[awayTeamName] = teams.get(awayTeamName, { 'points': 0, 'data': match['awayTeam'] }) 

            # Map numerical result to descriptive text
            result = match['score']['winner']
            if result == 'HOME_TEAM':
                result = 'Home Win'
                teams[homeTeamName]['points'] += 3
            elif result == 'DRAW':
                result = 'Draw'
                teams[homeTeamName]['points'] += 1
                teams[awayTeamName]['points'] += 1
            elif result == 'AWAY_TEAM':
                result = 'Away Win'
                teams[awayTeamName]['points'] += 3

            results.setdefault(roundNumber, []).append({
                'homeTeam': homeTeamName,
                'awayTeam': awayTeamName,
                'result': result
            })

        print(teams)        

        table = dict(sorted(teams.items(), key=lambda item: item[1]['points'], reverse=True))

        # Render results template with upcoming fixtures
        matchdays = sorted(results.keys())  # Sort matchdays in order
        return render_template('results.html', results=results, matchdays=matchdays, table=table)

@app.route('/predictions')
def predictionsPage():
    predictions = {}

    # Load data from CSV
    with open('data/PredictedResults24.csv', 'r') as csvFile:
        
        teams = {}

        csvReader = csv.DictReader(csvFile)
        for row in csvReader:
            roundNumber = int(row['round_number'])

            teams[row['home_team_name']] = teams.get(row['home_team_name'], 0) 
            teams[row['away_team_name']] = teams.get(row['away_team_name'], 0) 

            # Map numerical result to descriptive text
            result = row['predictedResult'].strip()
            if result == '1':
                result = 'Home Win'
                teams[row['home_team_name']] += 3
            elif result == '0':
                result = 'Draw'
                teams[row['home_team_name']] += 1
                teams[row['away_team_name']] += 1
            elif result == '-1':
                result = 'Away Win'
                teams[row['away_team_name']] += 3                

            predictions.setdefault(roundNumber, []).append({
                'homeTeam': row['home_team_name'],
                'awayTeam': row['away_team_name'],
                'result': result
            })

    table = dict(sorted(teams.items(), key=lambda item: item[1], reverse=True))
    
    matchdays = sorted(predictions.keys())  # Sort matchdays in order
    return render_template('predictions.html', predictions=predictions, matchdays=matchdays, table=table)

if __name__ == '__main__':
    app.run(debug=True)