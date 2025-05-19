# How to Fix the Nginx Configuration in Docker

The root cause of your login issue is that the Nginx configuration in the Docker container is incorrectly forwarding API requests. Here's how to fix it:

## The Problem

In your current Nginx configuration, the `location /api/` block has:

```nginx
location /api/ {
  proxy_pass http://localhost:8001/;  # This STRIPS the /api prefix!
}
```

When a request comes in for `/api/auth/token`, this configuration forwards it to the backend as just `/auth/token` (without the `/api` prefix). However, your FastAPI backend expects requests to include the `/api` prefix, causing a 404 error.

## The Solution

Modify the Nginx configuration to preserve the `/api` prefix when forwarding:

```nginx
location /api/ {
  proxy_pass http://localhost:8001/api/;  # This PRESERVES the /api prefix!
}
```

## Steps to Fix

1. Edit your `nginx.conf` file:
   ```bash
   # Inside your project directory
   nano nginx.conf
   ```

2. Find the `location /api/` block and change the proxy_pass line:
   ```nginx
   location /api/ {
     proxy_pass http://localhost:8001/api/;
     # Other settings remain the same
   }
   ```

3. Rebuild and restart your Docker container:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

## Login Credentials

Once fixed, use these credentials to log in:
- Email: `admin@example.com`
- Password: `password`

## Technical Explanation

The issue is related to how Nginx handles URL path mapping in the `proxy_pass` directive:

1. When `proxy_pass` includes a URI (e.g., `http://backend/some/path/`), Nginx **replaces** the matched location part with this URI.
2. When `proxy_pass` doesn't include a URI (e.g., just `http://backend`), Nginx **appends** the whole request URI to it.

In your case, you need to maintain the `/api` prefix in the forwarded path, so the proxy_pass should include the complete prefix.
