# Use the official Microsoft Playwright base image
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Default port for local development, Railway will override this
ENV PORT=8000

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium --with-deps

# Copy project files
COPY . .

# Expose port (Railway will inject its own PORT)
EXPOSE ${PORT}

# Create directory for any temporary files
RUN mkdir -p /app/tmp && chmod 777 /app/tmp

# Start command using Gunicorn
# The $PORT variable will be provided by Railway
CMD gunicorn --workers=2 --threads=4 --worker-class=gthread --bind 0.0.0.0:${PORT} agent:app
