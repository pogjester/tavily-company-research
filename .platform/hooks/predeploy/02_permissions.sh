#!/bin/bash
# Give execution permissions to the application directory
chmod 755 /var/app/current -R

# Create a directory for the socket if using Unix socket
mkdir -p /var/run/gunicorn
chmod 777 /var/run/gunicorn

# Ensure Apache has permission to proxy
setsebool -P httpd_can_network_connect 1

# Restart Apache to pick up new configurations
service httpd restart 