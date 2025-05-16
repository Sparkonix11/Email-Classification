FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PORT=7860
ENV MODEL_PATH="Sparkonix/email-classifier-model" 

# SQLite database path
ENV DATABASE_PATH="/data/emails.db"

# Global access key for email retrieval
ENV EMAIL_ACCESS_KEY="access_key_123"

# Add this line to set cache location to a writable directory
ENV HF_HOME="/app/.cache/huggingface"

# Create the Hugging Face cache directory and set permissions
RUN mkdir -p /app/.cache/huggingface && chmod -R 777 /app/.cache/huggingface
# Create data directory for SQLite
RUN mkdir -p /data && chmod -R 777 /data

# Expose the port
EXPOSE 7860

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]