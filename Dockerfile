FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set working directory
WORKDIR /app

# Copy repository files into the container
COPY . /app

# Expose port
EXPOSE 8080

# Run the python server script
CMD ["python3", "server.py"]
