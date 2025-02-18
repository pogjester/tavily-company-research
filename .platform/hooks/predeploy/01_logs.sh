#!/bin/bash
# Create log directory if it doesn't exist
mkdir -p /var/log/app_logs
# Set permissions
chmod 777 /var/log/app_logs
# Create log files if they don't exist
touch /var/log/app_logs/application.log
touch /var/log/app_logs/gunicorn.log
# Set permissions
chmod 666 /var/log/app_logs/application.log
chmod 666 /var/log/app_logs/gunicorn.log 