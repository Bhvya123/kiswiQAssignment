#!/bin/bash

# Start MySQL service
sudo service mysql start

# Wait for MySQL to start
sleep 5

# Set up the database (optional)
mysql -u root -proot_password -e "CREATE DATABASE IF NOT EXISTS dbname;"

# Start your application
uvicorn "main:app" --reload
