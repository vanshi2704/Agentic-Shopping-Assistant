# Dockerfile

# Step 1: Start with a specific, pinned version of the official Playwright image.
# This ensures that your builds are reproducible and won't break unexpectedly.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Step 2: Set environment variables for better logging and path management.
# PYTHONUNBUFFERED ensures logs appear in real-time.
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Step 3: Copy and install dependencies in a separate layer.
# This leverages Docker's layer caching, making subsequent builds much faster
# as this step is only re-run if requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 4: Explicitly install Playwright's browsers.
# This is a best practice to ensure browsers are correctly installed and linked.
RUN playwright install --with-deps

# Step 5: Copy the rest of the application source code into the container.
COPY . .

# Step 6: Create a non-root user and give it ownership of the app directory.
# This is the critical fix for the '[Errno 13] Permission denied' error.
# It allows your application, running as the 'app' user, to create .json files.
RUN groupadd --system app && \
    useradd --system --gid app app && \
    chown -R app:app /app

# Step 7: Switch to the non-root user.
# This is a critical security best practice to limit the container's privileges.
USER app

# Step 8: Expose the port your app will run on.
# This is for documentation; Railway uses the PORT environment variable regardless.
EXPOSE 8000

# Step 9: The command to run your application when the container starts.
# This "shell form" (without square brackets) correctly processes the ${PORT}
# environment variable provided by Railway.
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} whatsapp_bot:app
