import os
import torch
from transformers import XLMRobertaForSequenceClassification, XLMRobertaTokenizer
from typing import Dict, Any

class EmailClassifier:
    """
    Email classification model to categorize emails into different support categories
    """
    
    CATEGORIES = ['Change', 'Incident', 'Problem', 'Request']
    
    def __init__(self, model_path: str = None):
        """
        Initialize the email classifier with a pre-trained model
        
        Args:
            model_path: Path or Hugging Face Hub model ID
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Use environment variable for model path or fall back to Hugging Face Hub model
        # This allows for flexibility in deployment
        model_path = model_path or os.environ.get("MODEL_PATH", "Sparkonix11/email-classifier-model")
        
        # Load the tokenizer and model from Hugging Face Hub or local path
        self.tokenizer = XLMRobertaTokenizer.from_pretrained(model_path)
        self.model = XLMRobertaForSequenceClassification.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()
    
    def classify(self, masked_email: str) -> str:
        """
        Classify a masked email into one of the predefined categories
        
        Args:
            masked_email: The email content with PII masked
            
        Returns:
            The predicted category as a string
        """
        # Tokenize the masked email
        inputs = self.tokenizer(
            masked_email, 
            return_tensors="pt",
            padding="max_length",
            truncation=True,
            max_length=512
        )
        
        inputs = {key: val.to(self.device) for key, val in inputs.items()}
        
        # Perform inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            predicted_class_idx = torch.argmax(logits, dim=1).item()
        
        # Map the predicted class index to the category
        return self.CATEGORIES[predicted_class_idx]
    
    def process_email(self, masked_email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an email by classifying it into a category
        
        Args:
            masked_email_data: Dictionary containing the masked email and other data
            
        Returns:
            The input dictionary with the classification added
        """
        # Extract masked email content
        masked_email = masked_email_data["masked_email"]
        
        # Classify the masked email
        category = self.classify(masked_email)
        
        # Add the classification to the data
        masked_email_data["category_of_the_email"] = category
        
        return masked_email_data