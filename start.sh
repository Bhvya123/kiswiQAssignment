#!/bin/bash
# Wait for MySQL to be ready
while ! mysqladmin ping -h "mysql" --silent; do
    echo "Waiting for MySQL..."
    sleep 2
done

echo "MySQL is up - executing command"
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload