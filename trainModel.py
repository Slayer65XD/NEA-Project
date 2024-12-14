import os
os.environ["LOKY_MAX_CPU_COUNT"] = '1'

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import lightgbm as lgb
from sklearn.metrics import accuracy_score
import requests
import json
from datetime import datetime

import sqlite3
connection = sqlite3.connect("football.db")
cursor = connection.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round INTEGER NOT NULL,
    home_team VARCHAR NOT NULL,
    away_team VARCHAR NOT NULL,
    result TINYINT NOT NULL
)
""")

apiKey = '9ca47c095388418992b1fa8b56265aba'
currentYear = datetime.now().year

csvData = []

for i in range(10):

    year = str(currentYear - i)

    jsonPath = 'data/' + year + '.json'

    print('season', year)
    
    csvPath = 'data/' + year + '.csv'
    if not os.path.exists(csvPath):

        if not os.path.exists(jsonPath):
            print('downloading data')

            # Load data from api
            apiUrl = 'https://api.football-data.org/v4/competitions/PL/matches?season=2024' + year

            try:
                response = requests.get(
                    apiUrl,
                    headers={'X-Auth-Token': apiKey}
                )
            except requests.RequestException as e:
                print(f'Error fetching data: {e}')

            response.raise_for_status()

            if response.text:
                print('saving file')
                f = open(jsonPath, "w")
                f.write(response.text)
                f.close()

        with open(jsonPath) as f:
            data = json.load(f)

        csvData = 'round_number,home_team_name,away_team_name,home_team_goals,away_team_goals\n'
        for match in data.get('matches', []):
            print(match)
            csvData += str(match['matchday']) + ',' + match['homeTeam']['shortName'] + ',' + match['awayTeam']['shortName'] + ',' + str(match['score']['fullTime']['home']) + ',' + str(match['score']['fullTime']['away']) + "\n"

        # write to csv file
        f = open(csvPath, "w")
        f.write(csvData)
        f.close()

    csvData.append(pd.read_csv(csvPath))

# Combine the datasets
data = pd.concat(csvData, ignore_index=True)

# Create target variable
def determineResult(row):
    if row['home_team_goals'] > row['away_team_goals']:
        return 1  # Home Win
    elif row['home_team_goals'] < row['away_team_goals']:
        return -1  # Away Win
    else:
        return 0  # Draw

data['result'] = data.apply(determineResult, axis=1)

# Encode categorical features
le = LabelEncoder()

# Load 2024/25 fixtures
fixtures = pd.read_csv('data/2024.csv')

# Combine historical teams with current fixtures to include all possible teams
allTeams = pd.concat([
    data['home_team_name'], 
    data['away_team_name'], 
    fixtures['home_team_name'], 
    fixtures['away_team_name']
]).unique()

# Fit LabelEncoder with the complete list of teams
le.fit(allTeams)

# Encode historical data
data['homeTeamEncoded'] = le.transform(data['home_team_name'])
data['awayTeamEncoded'] = le.transform(data['away_team_name'])

# Feature set
features = ['homeTeamEncoded', 'awayTeamEncoded']
target = 'result'

# Train-test split (round_number <= 30 for training and > 30 for testing)
trainData = data[data['round_number'] <= 30]
testData = data[data['round_number'] > 30]

xTrain = trainData[features]
yTrain = trainData[target]
xTest = testData[features]
yTest = testData[target]

# LightGBM model
model = lgb.LGBMClassifier(objective='multiclass', num_class=3, metric='multi_logloss')
model.fit(xTrain, yTrain)

# Predictions
yPred = model.predict(xTest)

# Evaluate
confidence = accuracy_score(yTest, yPred)
print(f'Model Confidence: {confidence:.2f}')

# Encode the 2024/25 fixtures
fixtures['homeTeamEncoded'] = le.transform(fixtures['home_team_name'])
fixtures['awayTeamEncoded'] = le.transform(fixtures['away_team_name'])

# Predict the results for the 2024/25 season fixtures
fixtures['predictedResult'] = model.predict(fixtures[['homeTeamEncoded', 'awayTeamEncoded']])

# Empty table
cursor.execute("""
    DELETE FROM predictions
""")

# Save results to database
for index, row in fixtures[['round_number', 'home_team_name', 'away_team_name', 'predictedResult']].iterrows():
    #print(row)

    cursor.execute("""
    INSERT INTO predictions (round, home_team, away_team, result)
    VALUES (?, ?, ?, ?)
    """, (row['round_number'], row['home_team_name'], row['away_team_name'], row['predictedResult']))

# Save predictions to a new CSV file
outputPath = 'data/PredictedResults24.csv'
fixtures[['round_number', 'home_team_name', 'away_team_name', 'predictedResult']].to_csv(outputPath, index=False)
print('Predictions saved to:', outputPath)

# Print a preview of the predictions
print(fixtures.head())

connection.commit()
connection.close()