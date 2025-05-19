# Fixed Application Setup Guide

## Understanding the Application Architecture

The application has a complex architecture that involves several components:

1. **Frontend**: A React application served on port 3000 during development or port 8080 when running in the Docker container
2. **Backend**: A FastAPI application running on port 8001
3. **Nginx**: In the Docker setup, an Nginx reverse proxy handles routing, serving the frontend on port 8080 and redirecting `/api/*` requests to the backend

## Issue #1: Nginx Proxy Configuration

The key issue was in the Nginx configuration. The proxy was incorrectly redirecting requests from `/api/*` to the backend's root endpoint (`/`) instead of keeping the `/api` prefix.

**Fixed:**
```
# Before
location /api/ {
  proxy_pass http://localhost:8001/;  # This strips the /api prefix
}

# After
location /api/ {
  proxy_pass http://localhost:8001/api/;  # This preserves the /api prefix
}
```

## Issue #2: CORS Configuration

The backend's CORS middleware wasn't configured to accept requests from your local IP address.

**Fixed:**
- Added your IP (`192.168.50.167:8080`) to the allowed origins
- Enhanced the backend to read allowed origins from an environment variable
- Updated Docker Compose to provide this environment variable

## Running Locally with Docker Compose

To run the application locally with Docker Compose:

1. Make sure your `docker-compose.yml` looks like this:
```yaml
version: '3'

services:
  app:
    build:
      context: .
      args:
        FRONTEND_ENV: "REACT_APP_BACKEND_URL=http://localhost:8080/api"
    ports:
      - "8080:8080"
    environment:
      - MONGO_URL=mongodb://mongodb:27017
      - ORIGINS=http://localhost:8080,http://192.168.50.167:8080
      - DB_NAME=shooting_matches_db
    depends_on:
      mongodb:
        condition: service_healthy
    networks:
      - app-network

  mongodb:
    image: mongo:latest
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - app-network

volumes:
  mongodb_data:

networks:
  app-network:
    driver: bridge
```

2. Rebuild and restart your containers:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## How the App URL Structure Works

1. In the Docker setup:
   - Frontend is accessible at: `http://192.168.50.167:8080/`
   - API endpoints should be accessed at: `http://192.168.50.167:8080/api/*`
   
2. Frontend is configured with: `REACT_APP_BACKEND_URL=http://localhost:8080/api`
   - This environment variable is set during the Docker build
   - The React app uses this to make API calls

3. Inside the Docker container:
   - Nginx listens on port 8080
   - Requests to `/api/*` are proxied to the backend on port 8001
   - Other requests are served from the React build

## Default Admin User

The application creates a default admin user:
- Email: `admin@example.com`
- Password: `password`

You can use these credentials to log in.

## Technical Details: How Routing Works

1. User accesses `http://192.168.50.167:8080/` (frontend)
2. User attempts to log in, which makes a POST request to `/api/auth/token`
3. Nginx receives this request and forwards it to `http://localhost:8001/api/auth/token`
4. The FastAPI backend handles the request and returns the response
5. The response is sent back through Nginx to the browser

The issue was that the Nginx configuration was incorrectly forwarding `/api/auth/token` to `http://localhost:8001/auth/token` (without the `/api` prefix), causing a 404 error because the backend router expects the `/api` prefix.
