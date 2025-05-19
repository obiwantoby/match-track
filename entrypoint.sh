#!/bin/sh
set -e

# Function to check if MongoDB is ready
check_mongodb() {
  echo "Checking MongoDB connection..."
  python3 -c "
import sys
import time
import pymongo
from pymongo.errors import ConnectionFailure

mongo_url = '$MONGO_URL'
max_retries = 30
retry_interval = 5

for i in range(max_retries):
    try:
        client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print('MongoDB connection successful!')
        sys.exit(0)
    except (ConnectionFailure, pymongo.errors.ServerSelectionTimeoutError) as e:
        print(f'Attempt {i+1}/{max_retries}: MongoDB not available yet: {e}')
        if i < max_retries - 1:
            print(f'Retrying in {retry_interval} seconds...')
            time.sleep(retry_interval)
        else:
            print('Max retries reached. MongoDB is not available.')
            sys.exit(1)
" || return 1
}

# Function to check if admin user is created
check_admin_user() {
  echo "Checking if the admin user is created..."
  python3 -c "
import sys
import time
import pymongo
from pymongo.errors import ConnectionFailure

mongo_url = '$MONGO_URL'
db_name = '$DB_NAME'
max_retries = 10
retry_interval = 2

for i in range(max_retries):
    try:
        client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        admin_user = db.users.find_one({'email': 'admin@example.com'})
        
        if admin_user:
            print('Admin user found!')
            sys.exit(0)
        else:
            print(f'Attempt {i+1}/{max_retries}: Admin user not found yet')
            if i < max_retries - 1:
                print(f'Retrying in {retry_interval} seconds...')
                time.sleep(retry_interval)
            else:
                print('Max retries reached. Admin user not created.')
                # Continue anyway
                sys.exit(0)
    except Exception as e:
        print(f'Attempt {i+1}/{max_retries}: Error checking admin user: {e}')
        if i < max_retries - 1:
            print(f'Retrying in {retry_interval} seconds...')
            time.sleep(retry_interval)
        else:
            print('Max retries reached. Error checking admin user.')
            # Continue anyway
            sys.exit(0)
" || return 0
}

# Wait for MongoDB to be ready
check_mongodb

# Start the FastAPI backend
cd /backend || { echo "Backend directory not found"; exit 1; }

echo "Starting FastAPI backend"
# Start Uvicorn with proper host binding
uvicorn server:app --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!

echo "Waiting for backend to start..."
sleep 10

# Wait for admin user to be created
check_admin_user

if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Backend failed to start at initialization, exiting"
    exit 1
fi

# Start Nginx
nginx -g 'daemon off;' &
NGINX_PID=$!

# Handle termination signals
trap 'kill $BACKEND_PID $NGINX_PID; exit 0' SIGTERM SIGINT

# Check if processes are still running
while kill -0 $BACKEND_PID 2>/dev/null && kill -0 $NGINX_PID 2>/dev/null; do
    sleep 1
done

# If we get here, one of the processes died
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Nginx died, shutting down backend..."
    kill $BACKEND_PID
else
    echo "Backend died, shutting down nginx..."
    kill $NGINX_PID
fi

exit 1
