# Match Score Tracker

A comprehensive web application for managing and scoring shooting matches with support for different match types, score aggregates, and detailed reporting.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Data Structure](#data-structure)
- [Score Calculation and Aggregates](#score-calculation-and-aggregates)
- [Installation and Setup](#installation-and-setup)
  - [Manual Setup](#manual-setup)
  - [Docker Setup](#docker-setup)
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

You can set up the application either manually or using Docker. Both methods are described below.

### Manual Setup

#### Prerequisites
- Node.js (v14 or later)
- Python (v3.9 or later)
- MongoDB

#### Backend Setup
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
   ```

4. Start the backend server
   ```
   uvicorn server:app --reload --host 0.0.0.0 --port 8001
   ```

#### Frontend Setup
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

### Docker Setup

#### Prerequisites
- Docker
- Docker Compose (optional, for easier management)

#### Building and Running with Docker

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd match-score-tracker
   ```

2. **Configure Environment Variables**

   Create a file called `.env.frontend` with the following content:
   ```
   REACT_APP_BACKEND_URL=http://localhost:8080/api
   ```

   This environment variable will be injected into the frontend build process.

3. **Build and run with Docker Compose (Recommended)**
   ```bash
   docker-compose up -d
   ```

   This will:
   - Build the application container with proper frontend configuration
   - Start a MongoDB container that the application will connect to
   - Configure all necessary networking between containers
   - Make the application available on port 8080

4. **Access the Application**
   
   Open your browser and navigate to:
   ```
   http://localhost:8080
   ```

   The default admin credentials are:
   - Username: admin@example.com
   - Password: admin123

#### Alternative: Running without Docker Compose

1. **Build the Docker Image**
   ```bash
   docker build -t match-score-tracker:latest --build-arg FRONTEND_ENV="$(cat .env.frontend)" .
   ```

2. **Start MongoDB**
   ```bash
   docker run -d --name mongodb -p 27017:27017 mongo:latest
   ```

3. **Run the Application Container**
   ```bash
   docker run -d -p 8080:8080 \
     -e MONGO_URL="mongodb://host.docker.internal:27017" \
     -e DB_NAME="shooting_matches_db" \
     --name match-tracker \
     match-score-tracker:latest
   ```

   This command:
   - Maps port 8080 to the container's port 8080
   - Sets the MongoDB URL to connect to MongoDB running on your host machine
   - Sets the database name
   - Names the container "match-tracker"

   > Note: `host.docker.internal` is a special Docker DNS name that resolves to the host machine's IP address. This allows the containerized application to connect to services running on the host.

#### Docker Troubleshooting

1. **MongoDB Connection Issues**

   If you encounter MongoDB connection problems:
   
   ```
   pymongo.errors.ServerSelectionTimeoutError: mongodb:27017: [Errno -3] Try again
   ```
   
   Solutions:
   - Ensure MongoDB is running: `docker ps | grep mongodb`
   - If using Docker Compose, try restarting: `docker-compose down && docker-compose up -d`
   - Check logs: `docker-compose logs mongodb`
   - Verify network: `docker network inspect app-network`

2. **Application Startup Issues**

   If the application fails to start:
   
   - Check the logs: `docker-compose logs app`
   - Verify MongoDB connection: `docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"`
   - Restart the service: `docker-compose restart app`

3. **CORS Issues**

   If you encounter CORS errors like:
   
   ```
   Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource
   ```
   
   Solutions:
   - Ensure you're using the correct URL format in your frontend .env file:
     ```
     REACT_APP_BACKEND_URL=http://localhost:8080/api
     ```
   - Check your browser console for the exact request URL - it should NOT have duplicate `/api/api/` in the path
   - Try disabling browser extensions that may be interfering with CORS
   - Make sure the nginx proxy configuration is correct and handling preflight OPTIONS requests

4. **Frontend Not Loading**

   If the frontend doesn't load properly:
   
   - Check Nginx logs: `docker-compose exec app cat /var/log/nginx/error.log`
   - Verify the build: `docker-compose exec app ls -la /usr/share/nginx/html`
   - Ensure the REACT_APP_BACKEND_URL is set correctly

#### Authentication Troubleshooting

1. **Login Issues**

   If you're unable to log in with the default admin account:
   
   - Default credentials: admin@example.com / admin123
   - Check logs: `docker-compose logs app | grep "admin user"`
   - Verify MongoDB connection: `docker-compose exec mongodb mongosh --eval "db.users.find({email:'admin@example.com'}).pretty()"`
   - If the admin user doesn't exist, you can recreate it by resetting your containers:
     ```bash
     docker-compose down -v
     docker-compose up -d
     ```

2. **Registration Issues**

   If you encounter "Email already registered" errors when that's not the case:
   
   - Check backend logs: `docker-compose logs app | grep "Registration"`
   - Verify that the MongoDB connection is stable
   - If problems persist, try with a different browser or clear your browser cache
   - You can also try accessing the API directly with curl:
     ```bash
     curl -X POST http://localhost:8080/api/auth/register \
       -H "Content-Type: application/json" \
       -d '{"username":"testuser","email":"test@example.com","password":"password123","role":"reporter"}'
     ```

## Usage

### User Management
- **Default Admin**: The system creates a default admin user (admin@example.com / admin123)
- **User Registration**: New users can register but will have the Reporter role
- **Role Management**: Admin users can promote other users to Admin or demote them to Reporter

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

## Troubleshooting

### MongoDB Connection
- **Error**: If you see MongoDB connection errors, ensure MongoDB is running and accessible.
- **Solution**: Verify that the MONGO_URL environment variable is correctly set to point to your MongoDB instance.

### Backend API Access
- **Error**: Frontend cannot connect to backend API.
- **Solution**: Check that REACT_APP_BACKEND_URL is correctly set to the backend URL with the /api prefix.

### Docker Networking
- **Error**: Container cannot connect to host MongoDB.
- **Solution**: Use `host.docker.internal` instead of `localhost` in the MONGO_URL when running in Docker.
