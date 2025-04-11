#!/bin/bash

# Script to prepare Django app for deployment to Railway

# Exit on error
set -e

echo "Starting deployment preparation..."

# Change to the src directory
cd "$(dirname "$0")/../src"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running database migrations..."
python manage.py migrate

echo "Deployment preparation completed successfully!"