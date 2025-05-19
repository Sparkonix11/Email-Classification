# Email Classification and PII Masking System - Technical Report

## 1. Introduction to the Problem Statement

The goal of this project is to design and implement an email classification system for a company's support team. The system categorizes incoming support emails into predefined categories while ensuring that personal information (PII) is masked before processing. After classification, the masked data is restored to its original form.

This workflow addresses two critical requirements:

1. **Privacy-Preserving Processing**: Support emails often contain sensitive personal information that must be protected during the classification process. The system temporarily masks PII during analysis to ensure compliance with data protection regulations.

2. **Accurate Classification with Data Restoration**: The system categorizes emails into predefined classes (Incident, Request, Change, Problem) for efficient ticket routing, while ensuring that the original, unmasked data is available to support agents after classification.

The solution provides an API-based system with a secure PII masking and restoration mechanism, enabling support teams to efficiently route requests while maintaining data integrity and privacy compliance.

## 2. Approach Taken for PII Masking and Classification

### 2.1 PII Masking Approach

The system employs a hybrid approach to detect and mask PII, combining rule-based pattern matching and machine learning:

1. **Regular Expression Pattern Matching**: 
   - Implemented regex patterns to identify structured PII such as:
     - Email addresses
     - Phone numbers 
     - Credit/debit card numbers
     - CVV codes
     - Expiry dates
     - Aadhar card numbers (Indian national ID)
     - Date of birth

2. **Named Entity Recognition (NER)**:
   - Utilized SpaCy NLP models (xx_ent_wiki_sm) to detect unstructured PII, particularly personal names
   - Selected multilingual models to handle emails in different languages

3. **Contextual Verification**:
   - Implemented contextual verification to reduce false positives (e.g., verifying that a 3-digit number is a CVV by examining surrounding text)
   - Employed sliding window approach to analyze text segments around potential PII

4. **Entity Overlap Resolution**:
   - Developed a sophisticated algorithm to handle overlapping entities 
   - Prioritized NER-detected entities over regex matches
   - Preferred longer entities over shorter ones when overlaps occurred

5. **Secure Storage**:
   - Created a SQLite database to securely store original emails
   - Implemented access-key authentication for retrieving unmasked content
   - Structured database with appropriate indexes for efficient retrieval

### 2.2 Classification Approach

The classification system follows a standard NLP pipeline for text classification:

1. **Preprocessing**: 
   - Tokenization of masked email text
   - Special token handling for masked PII entities
   - Context preservation during masking to maintain classification accuracy

2. **Model Application**:
   - Feeding masked emails into the fine-tuned XLM-RoBERTa model
   - Mapping prediction outputs to the four support categories

3. **Post-processing**:
   - Structuring response with classification and masked content
   - Attaching metadata about identified PII entities

## 3. Model Selection and Training Details

### 3.1 Model Selection Rationale

After analyzing the email dataset, I observed significant language diversity in the support emails. Using `langdetect`, I determined that emails were written in multiple languages, making a multilingual model essential. I selected **XLM-RoBERTa-base** for the following reasons:

1. **Multilingual Capabilities**: Pre-trained on 100 languages, making it ideal for diverse support emails
2. **Strong Contextual Understanding**: Captures semantic meanings across language boundaries
3. **Transfer Learning Potential**: Excellent base model for fine-tuning with limited labeled data
4. **State-of-the-Art Performance**: Demonstrated superior performance on cross-lingual text classification tasks

### 3.2 Training Process and Hyperparameter Tuning

The training process consisted of multiple phases:

1. **Initial Data Preparation**:
   - Collected and labeled support emails into the four categories
   - Applied PII masking to training data to match inference conditions
   - Split data into training (80%), validation (10%), and test (10%) sets

2. **Wide-Range Hyperparameter Exploration**:
   - Learning rates: [1e-5, 3e-5, 5e-5, 1e-4]
   - Batch sizes: [8, 16, 32]
   - Weight decay: [0.01, 0.001, 0.0001]
   - Warmup steps: [0, 100, 500]
   - Maximum sequence length: [128, 256, 512]

3. **Focused Hyperparameter Optimization**:
   - After identifying the most promising parameter ranges, performed a more granular search
   - Fine-tuned with:
     - Learning rate: 2.3983474850766225e-05
     - Batch size: 16
     - Weight decay: 0.07212037354713949
     - Maximum sequence length: 512
     - Epochs: 3 with early stopping

4. **Final Training**:
   - Trained on the full training set with optimal hyperparameters
   - Implemented gradient accumulation for stable training
   - Applied early stopping based on validation performance

### 3.3 Model Performance

The final model achieved:
- 79% weighted F1 score


## 4. Challenges Faced and Solutions Implemented

### 4.1 PII Detection Challenges

1. **False Positives in PII Detection**
   - **Challenge**: Regular expressions frequently identified numbers and patterns that weren't actually PII
   - **Solution**: Implemented contextual verification by examining text surrounding potential PII; added specific rule-based filters for common false positives

2. **Overlapping Entities**
   - **Challenge**: Different detection methods identified overlapping entities (e.g., a name within an email address)
   - **Solution**: Developed a sophisticated resolution algorithm that prioritizes entities based on type, length, and detection method

3. **Multilingual Name Detection**
   - **Challenge**: Names in non-Latin scripts were frequently missed
   - **Solution**: Integrated xx_ent_wiki_sm model with language-specific fallbacks for better cross-lingual name detection

### 4.2 Classification Challenges

1. **Maintaining Classification Accuracy with Masked Text**
   - **Challenge**: Masking PII reduced contextual information needed for classification
   - **Solution**: Used semantic replacement tokens that preserved entity type information; optimized masking to retain surrounding context

2. **Class Imbalance**
   - **Challenge**: Training data had significantly more "Incident" and "Request" emails than "Change" and "Problem"
   - **Solution**: Implemented class weighting during training; used data augmentation techniques for underrepresented classes

3. **Context Length Limitations**
   - **Challenge**: Some emails exceeded the maximum context length of the model
   - **Solution**: Implemented intelligent truncation that preserved the most relevant parts of the email; retained subject lines and key paragraphs

### 4.3 System Integration Challenges


1. **Deployment Complexity**
   - **Challenge**: Ensuring consistent environment across development and Hugging Face Spaces deployment
   - **Solution**: Created comprehensive Docker configuration with appropriate volume mounts for persistent storage and cache

2. **Error Handling**
   - **Challenge**: Robust error handling for various edge cases (empty emails, malformed inputs)
   - **Solution**: Implemented comprehensive exception handling with meaningful error messages; added fallback mechanisms for component failures

## 5. Conclusion

The Email Classification and PII Masking System successfully addresses the dual challenges of privacy protection and efficient ticket routing. By leveraging advanced NLP techniques and a multilingual model, the system provides robust performance across diverse email content.

The system is deployed as a Docker container on Hugging Face Spaces, providing a scalable, secure API endpoint that can be integrated into existing support workflows.