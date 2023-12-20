# Stage 1: Build environment
FROM python:3.9 AS builder

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Stage 2: Runtime environment
FROM python:3.9-slim

WORKDIR /app

# Install libgomp1 for LightGBM
RUN apt-get update && apt-get install -y libgomp1

# Copy the requirements.txt file
COPY requirements.txt .
# Install all dependencies listed in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the built application from the previous stage
COPY --from=builder /app /app

# Expose the necessary port (replace 5000 with the actual port number used by your Flask app)
EXPOSE 3000

# Set the entrypoint command to run the Flask app
CMD ["python", "server.py"]