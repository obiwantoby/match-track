# Application Functions

This document provides a map of the key functions in the Match Score Tracker application, organized by component and purpose.

## Authentication Functions

- `login(email, password)`: Authenticates a user and returns a JWT token
- `register(email, username, password, role)`: Creates a new user account
- `changePassword(oldPassword, newPassword)`: Updates a user's password
- `isAdmin()`: Checks if the current user has admin privileges
- `logout()`: Removes authentication token and redirects to login

## Match Management Functions

- `createMatch(matchData)`: Creates a new match with defined structure
- `getMatches(year)`: Retrieves matches, optionally filtered by year
- `getMatchById(matchId)`: Gets detailed information about a specific match
- `getMatchConfig(matchId)`: Gets configuration details for a match
- `getMatchTypes()`: Returns available match types and their templates

## Shooter Management Functions

- `createShooter(shooterData)`: Adds a new shooter to the database
- `getShooters()`: Returns a list of all shooters
- `getShooterById(shooterId)`: Gets detailed shooter information
- `updateShooter(shooterId, shooterData)`: Updates shooter information

## Score Management Functions

- `createScore(scoreData)`: Records a new score for a shooter in a match
- `updateScore(scoreId, scoreData)`: Updates an existing score
- `getScoreById(scoreId)`: Retrieves a specific score record
- `getScoresByMatch(matchId)`: Gets all scores for a specific match
- `getScoresByShooter(shooterId)`: Gets all scores for a specific shooter

## Report Generation Functions

- `getMatchReport(matchId)`: Generates a detailed report for a match
- `getShooterReport(shooterId)`: Generates a report of a shooter's performance
- `getShooterAverages(shooterId, year)`: Calculates shooter average statistics

## Calculation Functions

- `calculateTotals(stages)`: Calculates total score and X count from stages
- `calculateSubtotals(stages, matchType)`: Calculates subtotals for 900pt Aggregates
- `determineWinners(scores)`: Identifies winners by match type and caliber
- `formatCaliber(caliber)`: Standardizes caliber naming for display

## Form Management Functions

- `handleInputChange(e)`: Updates form state based on input changes
- `handleSubmit(e)`: Processes form submission
- `validateForm()`: Checks if form data is valid before submission
- `resetForm()`: Clears form fields

## UI Helper Functions

- `formatDate(date)`: Converts dates to a readable format
- `calculateAggregateScores(shooterScores)`: Calculates 1800 or 2700 Aggregates 
- `toggleView(view)`: Switches between different views in components
- `showToast(message, type)`: Displays notification messages
- `handleFilterChange(filter)`: Updates data filtering options

## Data Management Functions

- `resetDatabase()`: Resets the database to its initial state (admin only)
- `seedDatabase()`: Populates the database with initial data if needed
- `exportData(format)`: Exports data in specified format (not implemented yet)
- `importData(data)`: Imports data from external source (not implemented yet)
