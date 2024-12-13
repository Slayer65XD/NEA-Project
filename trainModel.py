import os
os.environ["LOKY_MAX_CPU_COUNT"] = '1'

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import lightgbm as lgb
from sklearn.metrics import accuracy_score

# Load data from the Premier League seasons 2014/15 to 2023/24
filePath15 = 'data\PremierLeague15.csv'
filePath16 = 'data\PremierLeague16.csv'
filePath17 = 'data\PremierLeague17.csv'
filePath18 = 'data\PremierLeague18.csv'
filePath19 = 'data\PremierLeague19.csv'
filePath20 = 'data\PremierLeague20.csv'
filePath21 = 'data\PremierLeague21.csv'
filePath22 = 'data\PremierLeague22.csv'
filePath23 = 'data\PremierLeague23.csv'
filePath24 = 'data\PremierLeague24.csv'

# 23/24 Data sourced from Kaggle and 14/15 to 22/23 Data sourced from ChatGPT formatted in the same way as the Kaggle csv file.
data15 = pd.read_csv(filePath15)
data16 = pd.read_csv(filePath16)
data17 = pd.read_csv(filePath17)
data18 = pd.read_csv(filePath18)
data19 = pd.read_csv(filePath19)
data20 = pd.read_csv(filePath20)
data21 = pd.read_csv(filePath21)
data22 = pd.read_csv(filePath22)
data23 = pd.read_csv(filePath23)
data24 = pd.read_csv(filePath24)

# Combine the datasets
data = pd.concat([data15, data16, data17, data18, data19, data20, data21, data22, data23, data24], ignore_index=True)

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
fixturesPath = 'data\PremierLeagueFixtures25.csv'
fixtures = pd.read_csv(fixturesPath)

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
accuracy = accuracy_score(yTest, yPred)
print(f'Model Accuracy: {accuracy:.2f}')

# Encode the 2024/25 fixtures
fixtures['homeTeamEncoded'] = le.transform(fixtures['home_team_name'])
fixtures['awayTeamEncoded'] = le.transform(fixtures['away_team_name'])

# Predict the results for the 2024/25 season fixtures
fixtures['predictedResult'] = model.predict(fixtures[['homeTeamEncoded', 'awayTeamEncoded']])

# Save predictions to a new CSV file
outputPath = 'data/PredictedResults25.csv'
fixtures[['round_number', 'home_team_name', 'away_team_name', 'predictedResult']].to_csv(outputPath, index=False)
print('Predictions saved to:', outputPath)

# Print a preview of the predictions
print(fixtures.head())
