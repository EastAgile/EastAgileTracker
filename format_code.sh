#!/bin/bash

# format_code.sh

# Run isort
echo "Running isort..."
isort .

# Run Black
echo "Running Black..."
black .

echo "Code formatting complete!"