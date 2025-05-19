# Stage 1: Build React App
FROM node:20 AS frontend-build
ARG FRONTEND_ENV
ENV FRONTEND_ENV=${FRONTEND_ENV}
WORKDIR /app
COPY frontend/ /app/
RUN rm /app/.env
RUN touch /app/.env
RUN echo "${FRONTEND_ENV}" | tr ',' '\n' > /app/.env
RUN cat /app/.env
RUN yarn install --frozen-lockfile && yarn build

# Stage 2: Install Python Backend
FROM python:3.11-slim as backend
WORKDIR /app
COPY backend/ /app/
RUN rm -f /app/.env
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Final Image
FROM nginx:stable-alpine
# Copy built frontend
COPY --from=frontend-build /app/build /usr/share/nginx/html
# Copy backend
COPY --from=backend /app /backend
# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Fix proxy_pass to ensure it uses 127.0.0.1 instead of localhost
RUN sed -i 's|proxy_pass http://localhost:8001/;|proxy_pass http://127.0.0.1:8001/;|g' /etc/nginx/nginx.conf

# Install Python and dependencies
RUN apk add --no-cache python3 py3-pip mongodb-tools \
    && pip3 install --break-system-packages pymongo \
    && pip3 install --break-system-packages -r /backend/requirements.txt

# Add env variables if needed
ENV PYTHONUNBUFFERED=1

# Start both services: Uvicorn and Nginx
CMD ["/entrypoint.sh"]