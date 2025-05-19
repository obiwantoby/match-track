# Match Score Tracker

A comprehensive web application for managing and scoring shooting matches with support for different match types, score aggregates, and detailed reporting.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Data Structure](#data-structure)
- [Score Calculation and Aggregates](#score-calculation-and-aggregates)
- [Installation and Setup](#installation-and-setup)
- [Usage](#usage)
- [Components](#components)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)

## Overview

Match Score Tracker is a specialized application designed for shooting sports competitions, particularly focused on pistol shooting matches like the National Match Course (NMC), 600pt and a 900pt Aggregates, and Presidents Course matches. It provides comprehensive tools for managing shooters, defining match structures, recording scores, and generating reports.

## Features

- **User Management**: Admin and Reporter roles with appropriate permissions
- **Shooter Management**: Track shooter details including NRA and CMP numbers
- **Match Definition**: Define complex match structures with multiple match types and calibers
- **Score Entry**: Record detailed scores by stage with automatic subtotal calculations
- **Score Editing**: Update recorded scores with automatic recalculation
- **Reporting**:
  - Match Reports: View all scores for a specific match with subtotals
  - Shooter Reports: Track individual shooter performance across all matches
  - Average Statistics: Calculate performance averages by caliber and match type
  - Year-based Filtering: Filter match lists and statistics by year
- **Aggregation**: Support for standard aggregate scores (1800, 2700, etc.)
- **Password Management**: Users can change their passwords
- **Database Management**: Administrators can reset the database when needed

## System Architecture

The application follows a modern full-stack architecture:

### Frontend
- **React**: Single-page application with component-based structure
- **React Router**: Client-side routing
- **Axios**: HTTP client for API requests
- **Context API**: State management for authentication
- **Tailwind CSS**: Utility-first CSS framework for styling

### Backend
- **FastAPI**: High-performance Python web framework
- **MongoDB**: NoSQL database for flexible data storage
- **Motor**: Asynchronous MongoDB driver for Python
- **JWT Authentication**: Secure token-based authentication
- **Pydantic**: Data validation and settings management

## Data Structure

The application's data model is structured around the following key entities:

### Users
- Manage authentication and authorization
- Support for admin and reporter roles

### Shooters
- Basic information (name, ID)
- Shooting organization IDs (NRA, CMP)

### Matches
- Configuration (name, date, location)
- Structure definition (match types, calibers)
- Aggregate type designation

### Scores
- Individual scores by shooter, match, caliber, and stage
- Automatic calculation of subtotals and aggregates

## Score Calculation and Aggregates

### Match Types
1. **NMC (National Match Course)** - 300pt Aggregate
   - Stages: SF, TF, RF
   - Each stage is worth 100 points

2. **600pt Aggregate**
   - Stages: SF1, SF2, TF1, TF2, RF1, RF2
   - Each stage is worth 100 points

3. **900pt Aggregate**
   - Stages: SF1, SF2, TF1, TF2, RF1, RF2
   - Subtotals: SFNMC (SF1+SF2), TFNMC (TF1+TF2), RFNMC (RF1+RF2)
   - Total is calculated from subtotals

4. **Presidents Course** - 400pt Aggregate
   - Stages: SF1, SF2, TF, RF

### Automatic Calculations
- The application automatically calculates subtotals for 900pt Aggregates
- For each match type, total scores and X counts are automatically computed
- When scores are edited, all calculations are updated automatically

### Match Aggregates
Support for standard match aggregates:
- **1800 Aggregate**: Either two 900pt matches or three 600pt matches
- **2700 Aggregate**: Three 900pt matches

## Installation and Setup

### Prerequisites
- Node.js (v14 or later)
- Python (v3.9 or later)
- MongoDB

### Backend Setup
1. Navigate to the backend directory
   ```
   cd backend
   ```

2. Install Python dependencies
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env` file
   ```
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=shooting_matches_db
   SECRET_KEY=your_secret_key_here
   ```

4. Start the backend server
   ```
   uvicorn server:app --reload --host 0.0.0.0 --port 8001
   ```

### Frontend Setup
1. Navigate to the frontend directory
   ```
   cd frontend
   ```

2. Install Node.js dependencies
   ```
   yarn install
   ```

3. Set up environment variables in `.env` file
   ```
   REACT_APP_BACKEND_URL=http://localhost:8001
   ```

4. Start the frontend development server
   ```
   yarn start
   ```

## Usage

### User Management
- **Default Admin**: The system creates a default admin user (admin@example.com / admin123)
- **User Registration**: New users can register but will have the Reporter role
- **Role Management**: Admin users can manage other users

### Match Management
1. **Create Match**: Define match structure with match types and calibers
2. **Add Scores**: Record scores for each shooter by match type and caliber
3. **View Reports**: Generate match and shooter reports with detailed statistics

### Year-based Filtering
- Filter match lists by year to focus on specific time periods
- View shooter statistics for specific years to track improvement

## Components

### Frontend Components
- **App**: Main application component with routing and authentication
- **ChangePassword**: User password management
- **EditScore**: Score editing interface with automatic recalculation
- **MatchReport**: Detailed match results with multiple views
- **ScoreEntry**: Score entry interface with dynamic form generation
- **ShooterDetail**: Individual shooter details and performance history
- **UserManagement**: User administration and database management

### Backend Components
- **Authentication**: User management and security
- **Data Models**: Pydantic models for validation
- **API Endpoints**: FastAPI routes for all operations
- **Database Interface**: MongoDB integration
- **Calculation Logic**: Score aggregation and statistics computation

## API Endpoints

### Authentication
- `POST /api/auth/token`: Login and get access token
- `POST /api/auth/register`: Register new user
- `GET /api/auth/me`: Get current user information
- `POST /api/auth/change-password`: Update user password

### Shooters
- `POST /api/shooters`: Create new shooter
- `GET /api/shooters`: Get all shooters
- `GET /api/shooters/{shooter_id}`: Get shooter details

### Matches
- `POST /api/matches`: Create new match
- `GET /api/matches`: Get all matches
- `GET /api/matches/{match_id}`: Get match details
- `GET /api/match-types`: Get available match types
- `GET /api/match-config/{match_id}`: Get match configuration

### Scores
- `POST /api/scores`: Create new score
- `PUT /api/scores/{score_id}`: Update existing score
- `GET /api/scores`: Get scores (filtered by match/shooter)
- `GET /api/scores/{score_id}`: Get specific score

### Reports
- `GET /api/match-report/{match_id}`: Get detailed match report
- `GET /api/shooter-report/{shooter_id}`: Get shooter performance report
- `GET /api/shooter-averages/{shooter_id}`: Get shooter average statistics

### System Management
- `POST /api/reset-database`: Reset database (admin only)

## Authentication

The application uses JWT (JSON Web Token) for authentication:

1. User login generates a token with role information
2. Token is stored in local storage and included in API requests
3. Backend validates token and checks permissions
4. Protected routes check user role before allowing access

### Role-based Access Control
- **Admin**: Full access to all features
- **Reporter**: Read-only access to reports
