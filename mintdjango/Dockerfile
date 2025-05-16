# Use the official Python runtime image
# Stage 1 : Base build stage
FROM python:3.12-slim AS builder

# Create the app directory
RUN mkdir /app

# Set the working directory inside the container
WORKDIR /app

# Set environment variables top optimize Python
# Prevent Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Upgrade pip
RUN pip install --upgrade pip

# Copy the Django project and install all dependencies
COPY requirements.txt /app/

# Run this command to install all dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2 : Production stage
FROM python:3.12-slim

RUN useradd -m -r appuser && \
    mkdir /app && \
    chown -R appuser /app

# Cop the Python dependencies fromthe builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Set working dir
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Set environment variables top optimize Python
# Prevent Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Expose the Django port
EXPOSE 8000

# Run Django's development server
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "mintdjango.wsgi:application"]