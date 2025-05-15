import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Tuple, Optional
import uvicorn

from utils import PIIMasker
from models import EmailClassifier

# Initialize the FastAPI application
app = FastAPI(title="Email Classification API", 
              description="API for classifying support emails and masking PII",
              version="1.0.0")

# Initialize the PII masker and email classifier
pii_masker = PIIMasker()
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
        # Process the email to mask PII
        processed_data = pii_masker.process_email(email_input.input_email_body)
        
        # Classify the masked email
        classified_data = email_classifier.process_email(processed_data)
        
        return classified_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing email: {str(e)}")

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