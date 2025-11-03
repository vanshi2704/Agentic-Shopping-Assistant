# Dockerfile

# Step 1: Start with a specific, pinned version of the official Playwright image.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Step 2: Set environment variables for better logging and path management.
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Step 3: Copy and install dependencies in a separate layer for build caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 4: Explicitly install Playwright's browsers to ensure they are available.
RUN playwright install --with-deps

# Step 5: Copy the rest of the application code.
COPY . .

# Step 6: Create and switch to a non-root user for better security.
RUN groupadd --system app && useradd --system --gid app app
USER app

# Step 7: Expose the port for documentation purposes.
EXPOSE 8000

# Step 8: The command to run your application.
# --- THIS IS THE CRITICAL FIX ---
# This "shell form" correctly processes the ${PORT} environment variable.
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} whatsapp_bot:app
