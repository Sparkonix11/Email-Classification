---
title: Email Classification API
emoji: 📧
colorFrom: blue
colorTo: green
sdk: docker
app_file: main.py
pinned: false
---

# Email Classification for Support Team

## Project Overview

This project implements an email classification system that categorizes support emails into predefined categories while ensuring that personal information (PII) is masked before processing. The system uses a combination of Named Entity Recognition (NER) techniques for PII masking and a pre-trained XLM-RoBERTa model for email classification.

## Key Features

1. **Email Classification**: Classifies support emails into four categories:
   - Incident
   - Request
   - Change
   - Problem

2. **Personal Information Masking**: Detects and masks the following types of PII:
   - Full Name ("full_name")
   - Email Address ("email")
   - Phone number ("phone_number")
   - Date of birth ("dob")
   - Aadhar card number ("aadhar_num")
   - Credit/Debit Card Number ("credit_debit_no")
   - CVV number ("cvv_no")
   - Card expiry number ("expiry_no")

3. **API Interface**: Exposes the solution as a RESTful API endpoint.

## Project Structure

```
.
├── classification_model/    # Local model files (not used in deployment)
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Docker configuration
├── main.py                  # Main FastAPI application
├── models.py                # Email classifier model implementation
├── README.md                # Project documentation
├── requirements.txt         # Python dependencies
└── utils.py                 # PII masker implementation
```

## Installation

### Prerequisites

- Python 3.8+
- [Docker](https://www.docker.com/) (optional)
- Hugging Face account for model hosting

### Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd email_classifier_project
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```

### Using Docker

1. Build and run with Docker Compose:
   ```
   docker-compose up
   ```

## Uploading the Model to Hugging Face Hub

Before deploying the application to Hugging Face Spaces, you need to upload the model to the Hugging Face Model Hub:

1. Install the Hugging Face CLI if you haven't already:
   ```
   pip install huggingface_hub
   ```

2. Log in to Hugging Face:
   ```
   huggingface-cli login
   ```

3. Create a new model repository on Hugging Face:
   ```
   huggingface-cli repo create email-classifier-model
   ```

4. Upload the model using Python:
   ```python
   from transformers import XLMRobertaForSequenceClassification, XLMRobertaTokenizer
   
   # Load the local model
   model = XLMRobertaForSequenceClassification.from_pretrained("classification_model")
   tokenizer = XLMRobertaTokenizer.from_pretrained("classification_model")
   
   # Push to Hugging Face Hub
   model.push_to_hub("YourUsername/email-classifier-model")
   tokenizer.push_to_hub("YourUsername/email-classifier-model")
   ```

5. Update the `MODEL_PATH` environment variable in the Dockerfile with your Hugging Face model path:
   ```
   ENV MODEL_PATH="YourUsername/email-classifier-model"
   ```

## API Usage

The API exposes a single endpoint for email classification:

- **Endpoint**: `/classify`
- **Method**: POST
- **Input Format**:
  ```json
  {
    "input_email_body": "string containing the email"
  }
  ```
- **Output Format**:
  ```json
  {
    "input_email_body": "string containing the email",
    "list_of_masked_entities": [
      {
        "position": [start_index, end_index],
        "classification": "entity_type",
        "entity": "original_entity_value"
      }
    ],
    "masked_email": "string containing the masked email",
    "category_of_the_email": "string containing the class"
  }
  ```

## Example

```python
import requests

url = "https://sparkonix-email-classification-model.hf.space/classify"
data = {
    "input_email_body": "Hello, my name is John Doe, and I'm having issues with my account."
}

response = requests.post(url, json=data)
print(response.json())
```

## Deployment to Hugging Face Spaces

1. Create a new Space on Hugging Face:
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Choose a name for your Space
   - Select "Docker" as the Space SDK

2. Connect your GitHub repository to the Space:
   - In the Space settings, go to "Repository"
   - Enter your GitHub repository URL
   - Authenticate with GitHub if prompted

3. Ensure your Hugging Face Space has access to the model:
   - Go to your model on Hugging Face Hub
   - Go to "Settings" > "Collaborators"
   - Add your Space as a collaborator with "Read" access

4. Your API will be available at:
   ```
   https://username-space-name.hf.space/classify
   ```

## Technologies Used

- **FastAPI**: Web framework for building the API
- **SpaCy**: NLP library for PII detection and masking
- **Transformers**: Hugging Face library for the email classification model
- **PyTorch**: Deep learning framework
- **Docker**: Containerization for deployment