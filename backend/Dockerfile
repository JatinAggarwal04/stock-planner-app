# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Install system dependencies (as root)
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (as root initially)
COPY requirements.txt .

# Install dependencies (as root, global install is fine in container)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create models directory and copy app code
COPY . .

# Setup User & Permissions (Still as root)
# 1. Create user
# 2. Create models directory if not copied
# 3. Change ownership of EVERYTHING in /app to user
RUN useradd -m -u 1000 user && \
    mkdir -p models && \
    chown -R user:user /app

# Switch to non-root user for runtime
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose the port
EXPOSE 7860

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
