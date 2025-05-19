# Fixing the Cross-Machine Access Issue

## The Problem

You're experiencing the following issues:
1. CORS errors when trying to access the app from a different machine
2. Cookie domain errors
3. Network errors because the frontend is trying to access "localhost" which refers to the client machine, not the server

The key problem is that the frontend code is built with hardcoded references to "localhost" but when you access it from a different machine, these references don't work.

## The Solution

### 1. Update the `docker-compose.yml` file:

```yaml
version: '3'

services:
  app:
    build:
      context: .
      args:
        # Replace with your actual server IP address
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

  # Rest of the configuration remains the same
```

The key changes are:
1. **Use the server's IP address** in the `FRONTEND_ENV` variable instead of localhost
2. **Add multiple origins** to the `ORIGINS` environment variable to support different ways of accessing the app

### 2. Rebuild and restart the containers:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 3. Access the app using the server's IP address:

From your other machine, access the app at:
```
http://192.168.50.167:8080
```

## Why This Works

When the React app is built during the Docker image creation:
1. The environment variable `REACT_APP_BACKEND_URL` will be set to `http://192.168.50.167:8080/api`
2. This value is "baked into" the JavaScript bundle during build time
3. When your browser loads this JavaScript, it will make API calls to the correct IP address

## Testing the Fix

After applying these changes, you should:
1. See no more CORS errors in the browser console
2. Be able to log in successfully
3. Have full functionality of the app when accessed from different machines

## Default Login Credentials

Once the app is working:
- Email: `admin@example.com`
- Password: `password`
