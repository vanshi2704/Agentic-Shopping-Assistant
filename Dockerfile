# Dockerfile

# Step 1: Start with a specific, pinned version of the official Playwright image.
# Using a specific version tag (e.g., v1.44.0-jammy) instead of 'latest' ensures
# that your builds are reproducible and won't break unexpectedly when the base image updates.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Step 2: Set environment variables
# PYTHONUNBUFFERED ensures that print statements and logs are sent straight to the
# terminal (and your Railway logs) without being buffered, making debugging easier.
ENV PYTHONUNBUFFERED=1
# Set the working directory before any file operations.
WORKDIR /app

# Step 3: Copy and install dependencies in a separate layer
# This leverages Docker's layer caching. This layer will only be rebuilt if
# requirements.txt changes, making subsequent builds much faster.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 4: Explicitly install Playwright's browsers (Best Practice)
# While the base image includes the browsers, running this command ensures they are
# correctly installed and linked in the container's environment, preventing runtime issues.
RUN playwright install --with-deps

# Step 5: Copy the rest of the application code
# This should be done AFTER installing dependencies.
COPY . .

# Step 6: Create and switch to a non-root user (Security Best Practice)
# Running containers as a non-root user is a critical security measure.
# It limits the potential damage if an attacker were to exploit your application.
RUN groupadd --system app && useradd --system --gid app app
USER app

# Step 7: Expose the port your app will run on
# This is for documentation; Railway will use the PORT environment variable regardless.
EXPOSE 8000

# Step 8: The command to run your application
# The shell form is used so the ${PORT} environment variable is correctly substituted by the shell.
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT:-8000}", "whatsapp_bot:app"]

