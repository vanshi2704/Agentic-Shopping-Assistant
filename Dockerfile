# Dockerfile

# Step 1: Start with a specific, pinned version of the official Playwright image.
# This ensures your builds are reproducible and won't break unexpectedly.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Step 2: Set environment variables for better logging and path management.
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Step 3: Copy and install dependencies in a separate layer for build caching.
# This step is only re-run if requirements.txt changes, making builds faster.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 4: Explicitly install Playwright's browsers to ensure they are available.
RUN playwright install --with-deps

# Step 5: Copy the rest of the application source code into the container.
COPY . .

# Step 6: Create a non-root user and give it ownership of the app directory.
# This fixes the '[Errno 13] Permission denied' error and is a critical security practice.
RUN groupadd --system app && \
    useradd --system --gid app app && \
    chown -R app:app /app

# Step 7: Switch to the non-root user.
USER app

# Step 8: Expose the port your app will run on for documentation.
EXPOSE 8000

# Step 9: The command to run your application when the container starts.
# The "shell form" (without brackets) correctly processes the ${PORT} environment variable.
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} whatsapp_bot:app
