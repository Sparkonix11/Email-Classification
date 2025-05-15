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
# Replace YOUR_ACTUAL_USERNAME with your Hugging Face username after uploading the model

# Add this line to set cache location to a writable directory
ENV HF_HOME="/app/.cache/huggingface"

# Create the Hugging Face cache directory and set permissions
RUN mkdir -p /app/.cache/huggingface && chmod -R 777 /app/.cache/huggingface

# Expose the port
EXPOSE 7860

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]