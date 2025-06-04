# MAINTAINER Daniel Kidd, daniel.wayne.kidd@gmail.com

# Use official Python image as base
FROM python:3.11

# Set our timezone.
RUN ln -sf /usr/share/zoneinfo/US/Central /etc/localtime

# Generate App Directory
COPY requirements.txt /app/
RUN mkdir -p /app
WORKDIR /app

# Install packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy our files into our container.
COPY . /app

# Expose our port.
EXPOSE 8080

# Run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers"]