#!/bin/bash
service mysql start
sleep 5
mysql -u root -proot_password -e "CREATE DATABASE IF NOT EXISTS dbname;"
uvicorn "main:app" --reload
