# Complete Solution Guide

## Issues Identified and Fixed

This application had several interconnected issues that needed to be addressed:

### 1. Nginx Proxy Configuration Issue

**Problem:** The Nginx reverse proxy in the Docker container was incorrectly stripping the `/api` prefix when forwarding requests to the backend, causing 404 errors.

**Solution:** Modified the nginx.conf to preserve the `/api` prefix:
```nginx
# Changed from:
location /api/ {
  proxy_pass http://localhost:8001/;
}

# To:
location /api/ {
  proxy_pass http://localhost:8001/api/;
}
```

### 2. Cross-Machine Access Issue

**Problem:** The frontend JavaScript was being built with hardcoded references to "localhost" which don't work when accessing from a different machine.

**Solution:** Updated the Docker build to use the actual server IP address:
```yaml
# In docker-compose.yml, changed:
FRONTEND_ENV: "REACT_APP_BACKEND_URL=http://localhost:8080/api"

# To:
FRONTEND_ENV: "REACT_APP_BACKEND_URL=http://192.168.50.167:8080/api"
```

### 3. CORS Configuration Issue

**Problem:** The backend CORS middleware wasn't configured to accept requests from your local IP address.

**Solution:** Added your IP to the allowed origins and made the CORS configuration more flexible:
```yaml
# Added environment variable to docker-compose.yml:
ORIGINS=http://localhost:8080,http://192.168.50.167:8080,https://localhost:8080,https://192.168.50.167:8080,http://127.0.0.1:8080
```

### 4. Authentication Token Handling Issue

**Problem:** API requests in components like UserManagement weren't including the authentication token.

**Solution:** Updated all API calls to include the token:
```javascript
// Get the token from localStorage
const token = localStorage.getItem('token');
if (!token) {
  setError("Authentication required. Please log in again.");
  return;
}

// Set authorization header
const config = {
  headers: { Authorization: `Bearer ${token}` }
};

// Use the config with API calls
const response = await axios.get(`${API}/users`, config);
```

### 5. API URL Formation Issue

**Problem:** Some components were double-adding the "/api" prefix to the backend URL.

**Solution:** Added checking to prevent duplicate "/api" segments:
```javascript
// Check if BACKEND_URL already contains /api to avoid duplication
const API = BACKEND_URL.endsWith('/api') ? BACKEND_URL : `${BACKEND_URL}/api`;
```

## How to Run the Application

### Using Docker Compose

1. In your project directory, ensure your docker-compose.yml looks like:
```yaml
version: '3'

services:
  app:
    build:
      context: .
      args:
        FRONTEND_ENV: "REACT_APP_BACKEND_URL=http://192.168.50.167:8080/api"
    ports:
      - "8080:8080"
    environment:
      - MONGO_URL=mongodb://mongodb:27017
      - ORIGINS=http://localhost:8080,http://192.168.50.167:8080,https://localhost:8080,https://192.168.50.167:8080,http://127.0.0.1:8080
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

3. Access the application:
```
http://192.168.50.167:8080
```

## Login Credentials

Use these default admin credentials to log in:
- Email: `admin@example.com`
- Password: `password`

## Technical Details

### Application Architecture

The application follows a standard three-tier architecture:
1. **Frontend**: React application served by Nginx on port 8080
2. **Backend**: FastAPI application running on port 8001
3. **Database**: MongoDB running on port 27017

### Request Flow

1. User accesses `http://192.168.50.167:8080/` 
2. Authentication request goes to `/api/auth/token`
3. Nginx proxy forwards to `http://localhost:8001/api/auth/token`
4. FastAPI backend processes the request and returns a JWT token
5. Frontend stores the token in localStorage
6. Subsequent API requests include the token in the Authorization header

### Authentication Flow

The application uses JWT (JSON Web Tokens) for authentication:
1. User provides email and password to `/api/auth/token`
2. Backend validates credentials and returns a JWT token
3. Frontend stores this token in localStorage
4. Token is included in the Authorization header for subsequent requests
5. Protected routes on the backend verify this token before processing requests
