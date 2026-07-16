FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy repository files into the container
COPY . /app

# Expose port
EXPOSE 8080

# Run the python server script
CMD ["python3", "server.py"]
