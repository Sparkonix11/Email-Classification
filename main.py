import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Tuple, Optional
import uvicorn
from dotenv import load_dotenv

from utils import PIIMasker
from models import EmailClassifier

# Load environment variables from .env file if available
try:
    load_dotenv()
except ImportError:
    pass  # dotenv might not be installed in production

# Set database path for Hugging Face, using persistent storage
if os.path.exists('/data'):
    db_path = "/data/emails.db"
else:
    db_path = "emails.db"  # Fallback to local directory

# Initialize the FastAPI application
app = FastAPI(title="Email Classification API", 
              description="API for classifying support emails and masking PII",
              version="1.0.0")

# Initialize the PII masker and email classifier
pii_masker = PIIMasker(db_path=db_path)
email_classifier = EmailClassifier()

class EmailInput(BaseModel):
    """Input model for the email classification endpoint"""
    input_email_body: str

class EntityInfo(BaseModel):
    """Model for entity information"""
    position: Tuple[int, int]
    classification: str  
    entity: str

class EmailOutput(BaseModel):
    """Output model for the email classification endpoint"""
    input_email_body: str
    list_of_masked_entities: List[EntityInfo]
    masked_email: str
    category_of_the_email: str

class MaskedEmailInput(BaseModel):
    """Input model for retrieving original email by masked email content"""
    masked_email: str
    access_key: str

@app.post("/classify", response_model=EmailOutput)
async def classify_email(email_input: EmailInput) -> Dict[str, Any]:
    """
    Classify an email into a support category while masking PII
    
    Args:
        email_input: The input email data
        
    Returns:
        The classified email data with masked PII
    """
    try:
        # Process the email to mask PII and store original in database
        processed_data = pii_masker.process_email(email_input.input_email_body)
        
        # Classify the masked email
        classified_data = email_classifier.process_email(processed_data)
        
        # Make sure we return only the fields expected in the response model
        return {
            "input_email_body": email_input.input_email_body,
            "list_of_masked_entities": classified_data["list_of_masked_entities"],
            "masked_email": classified_data["masked_email"],
            "category_of_the_email": classified_data["category_of_the_email"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing email: {str(e)}")

@app.post("/api/v1/unmask-email", response_model=Dict[str, Any])
async def unmask_email(masked_email_input: MaskedEmailInput) -> Dict[str, Any]:
    """
    Retrieve the original unmasked email using the masked email content from the classify response.
    
    Args:
        masked_email_input: Contains the masked email and access key
        
    Returns:
        The original email data with PII information
    """
    try:
        # Verify access key matches the global access key
        if masked_email_input.access_key != os.environ.get("EMAIL_ACCESS_KEY", "default_secure_access_key"):
            raise HTTPException(status_code=401, detail="Invalid access key")
        
        # Retrieve the original email using the masked content
        email_data = pii_masker.get_original_by_masked_email(masked_email_input.masked_email)
        
        if not email_data:
            raise HTTPException(status_code=404, detail="Original email not found for the provided masked email")
        
        return {
            "status": "success",
            "data": {
                "id": email_data["id"],
                "original_email": email_data["original_email"],
                "masked_email": email_data["masked_email"],
                "masked_entities": email_data["masked_entities"],
                "category": email_data.get("category", ""),
                "created_at": email_data.get("created_at", "")
            },
            "message": "Original email retrieved successfully"
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error retrieving original email: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Status message indicating the API is running
    """
    return {"status": "healthy", "message": "Email classification API is running"}

# For local development and testing
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)