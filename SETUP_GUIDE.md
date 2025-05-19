# Application Setup Guide

## Running the Application Locally

### Configuration for Docker Compose

When running the application with Docker Compose, you need to configure your frontend to communicate with the backend correctly:

1. In your `docker-compose.yml` file, ensure the backend service is exposing port 8001:
   ```yaml
   backend:
     # other configuration...
     ports:
       - "8001:8001"
   ```

2. If you're running the frontend container separately, your frontend `.env` file should have:
   ```
   REACT_APP_BACKEND_URL=http://192.168.50.167:8001
   ```
   
   Where `192.168.50.167` is your host machine's IP address.

3. If frontend and backend are both in Docker, your frontend `.env` should use:
   ```
   REACT_APP_BACKEND_URL=http://backend:8001
   ```
   
### Authentication Issues

If you're encountering authentication issues:

1. The API endpoint for login is: `/api/auth/token`
2. It must be accessed with a POST request
3. It expects form data with `username` and `password` fields

### Troubleshooting CORS Issues

If you encounter CORS errors:

1. Ensure the backend's CORS configuration includes your frontend's origin
2. The backend has been updated to include `http://192.168.50.167:8080` in allowed origins
3. Check the browser console for specific CORS error messages

### Default Credentials

The application may have a default admin user. Try:
- Username: `admin@example.com`
- Password: `password`

If these don't work, you'll need to register a new user first.

## Development Environment Notes

- Backend runs on port 8001
- Frontend development server runs on port 3000
- The application's API endpoints are all prefixed with `/api`
- MongoDB runs on the default port 27017
