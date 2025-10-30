# Dockerfile

# Step 1: Start with the official Microsoft Playwright base image
# This is the most important change. This image comes pre-packaged with all the
# complex system dependencies that Playwright needs to run browsers.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy the requirements file into the container
# We copy only this file first to take advantage of Docker's layer caching.
# This step will only be re-run if requirements.txt changes.
COPY requirements.txt .

# Step 4: Install your Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the rest of your application code into the container
COPY . .

# Step 6: Expose the port your app will run on.
# Railway automatically provides a PORT environment variable.
EXPOSE 8000

# Step 7: The command to run your application when the container starts.
# We use gunicorn to run the 'app' object from the 'whatsapp_bot' module.
# We bind to 0.0.0.0 to make it accessible from outside the container.
# The ${PORT:-8000} syntax uses the PORT variable from Railway, or defaults to 8000.
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT:-8000}", "whatsapp_bot:app"]