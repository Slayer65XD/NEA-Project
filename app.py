from flask import Flask, render_template
import requests
import pandas as pd
import csv

app = Flask(__name__)

# API details
apiUrl = 'https://api.football-data.org/v2/competitions/PL/matches'
apiKey = 'ya8bbf204c3bd75d784cc0a91a16567ab'

@app.route('/')
def homePage():
    return render_template('index.html')

@app.route('/liveScores')
def liveScoresPage():
    try:
        # Fetch live scores data from the API
        response = requests.get(
            apiUrl,
            headers={'X-Auth-Token': apiKey}
        )
        response.raise_for_status()
        data = response.json()

        # Filter for upcoming matches (SCHEDULED status)
        upcomingMatches = [
            {
                'homeTeam': match['homeTeam']['name'],
                'awayTeam': match['awayTeam']['name'],
                'status': match['status'],
                'date': match['utcDate'],
                'matchday': match['matchday']
            }
            for match in data.get('matches', [])
            if match['status'] == 'SCHEDULED'
        ]

        # Find the next gameweek (matchday)
        if upcomingMatches:
            nextGameweek = min(match['matchday'] for match in upcomingMatches)
            upcomingMatches = [match for match in upcomingMatches if match['matchday'] == nextGameweek]

        # Sort matches by date and time
        upcomingMatches.sort(key=lambda x: x['date'])
    except requests.RequestException as e:
        print(f'Error fetching live scores: {e}')
        upcomingMatches = []

    # Render live scores template with upcoming fixtures
    return render_template('live-scores.html', matches=upcomingMatches)

@app.route('/predictions')
def predictionsPage():
    predictions = {}

    # Load data from CSV
    with open('data/PredictedResults25.csv', 'r') as csvFile:
        csvReader = csv.DictReader(csvFile)
        for row in csvReader:
            roundNumber = int(row['round_number'])
            # Map numerical result to descriptive text
            result = row['predictedResult'].strip()
            if result == '1':
                result = 'Home Win'
            elif result == '0':
                result = 'Draw'
            elif result == '-1':
                result = 'Away Win'

            predictions.setdefault(roundNumber, []).append({
                'homeTeam': row['home_team_name'],
                'awayTeam': row['away_team_name'],
                'result': result
            })

    matchdays = sorted(predictions.keys())  # Sort matchdays in order
    return render_template('predictions.html', predictions=predictions, matchdays=matchdays)



if __name__ == '__main__':
    app.run(debug=True)