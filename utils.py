import re
import spacy
from typing import List, Dict, Tuple, Any, Optional
from database import EmailDatabase

class Entity:
    def __init__(self, start: int, end: int, entity_type: str, value: str):
        self.start = start
        self.end = end
        self.entity_type = entity_type
        self.value = value

    def to_dict(self):
        return {
            "position": [self.start, self.end],
            "classification": self.entity_type,
            "entity": self.value
        }

    def __repr__(self): # Added for easier debugging
        return f"Entity(type='{self.entity_type}', value='{self.value}', start={self.start}, end={self.end})"

class PIIMasker:
    def __init__(self, spacy_model_name: str = "xx_ent_wiki_sm", db_path: str = None): # Allow model choice
        # Load SpaCy model
        try:
            self.nlp = spacy.load(spacy_model_name)
        except OSError:
            print(f"SpaCy model '{spacy_model_name}' not found. Downloading...")
            try:
                spacy.cli.download(spacy_model_name)
                self.nlp = spacy.load(spacy_model_name)
            except Exception as e:
                print(f"Failed to download or load {spacy_model_name}. Error: {e}")
                print("Attempting to load 'en_core_web_sm' as a fallback for English.")
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                except OSError:
                    print("Downloading 'en_core_web_sm'...")
                    spacy.cli.download("en_core_web_sm")
                    self.nlp = spacy.load("en_core_web_sm")

        # Initialize database connection with SQLite path
        self.db = EmailDatabase(connection_string=db_path)
        
        # Initialize regex patterns
        self._initialize_patterns()

    def _initialize_patterns(self):
        # Define regex patterns for different entity types
        self.patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # More precise phone number regex that handles international formats while avoiding false positives
            "phone_number": r'\b(?:(?:\+|00)[1-9]\d{0,3}[-\s.]?)(?:\(?\d{1,5}\)?[-\s.]?)?(?:\d{1,5}[-\s.]?){1,4}\d{1,5}\b',
            # Card number regex: common formats, allows optional spaces/hyphens
            "credit_debit_no": r'\b(?:(?:\d{4}[\s-]?){3}\d{4}|\d{13,19})\b',
            # CVV: 3 or 4 digits, ensuring it's a standalone number (word boundary)
            "cvv_no": r'\b\d{3,4}\b',
            # Expiry: MM/YY or MM/YYYY, common separators
            "expiry_no": r'\b(0[1-9]|1[0-2])[/\s-]([0-9]{2}|20[0-9]{2})\b',
            "aadhar_num": r'\b\d{4}\s?\d{4}\s?\d{4}\b',
            # DOB: DD/MM/YYYY or DD-MM-YYYY etc.
            "dob": r'\b(0[1-9]|[12][0-9]|3[01])[/\s-](0[1-9]|1[0-2])[/\s-](?:19|20)\d\d\b'
        }

    def detect_regex_entities(self, text: str) -> List[Entity]:
        """Detect entities using regex patterns"""
        entities = []

        for entity_type, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                start, end = match.span()
                value = match.group()

                # Specific verifications for each entity type
                if entity_type == "credit_debit_no":
                    if not self.verify_credit_card(text, match):
                        continue
                elif entity_type == "cvv_no":
                    if not self.verify_cvv(text, match):
                        continue
                elif entity_type == "phone_number":
                    if not self.verify_phone_number(text, match):
                        continue
                elif entity_type == "dob":
                    if not self._verify_with_context(text, start, end, ["birth", "dob", "born"]):
                        continue

                # Avoid detecting parts of already matched longer entities (e.g. year within a DOB)
                # This is a simple check; more robust overlap handling is done later
                is_substring_of_existing = False
                for existing_entity in entities:
                    if existing_entity.start <= start and existing_entity.end >= end and existing_entity.value != value:
                        is_substring_of_existing = True
                        break
                if is_substring_of_existing:
                    continue

                entities.append(Entity(start, end, entity_type, value))
        return entities

    def _verify_with_context(self, text: str, start: int, end: int, keywords: List[str], window: int = 50) -> bool:
        """Verify an entity match using surrounding context"""
        context_before = text[max(0, start - window):start].lower()
        context_after = text[end:min(len(text), end + window)].lower()

        for keyword in keywords:
            if keyword in context_before or keyword in context_after:
                return True
        return False

    def verify_credit_card(self, text: str, match: re.Match) -> bool:
        """Verify if a match is actually a credit card number using contextual clues"""
        context_window = 50
        start, end = match.span()

        context_before = text[max(0, start - context_window):start].lower()
        context_after = text[end:min(len(text), end + context_window)].lower()

        card_keywords = ["card", "credit", "debit", "visa", "mastercard", "payment", "amex", "account no", "card no"]
        for keyword in card_keywords:
            if keyword in context_before or keyword in context_after:
                return True
        # Basic Luhn algorithm check (optional, can be computationally more intensive)
        # For simplicity, we'll rely on context here. If needed, Luhn can be added.
        return False


    def verify_cvv(self, text: str, match: re.Match) -> bool:
        """Verify if a 3-4 digit number is actually a CVV using contextual clues"""
        context_window = 30
        start, end = match.span()
        value = match.group()

        # If it's part of a longer number sequence (like a phone number or ID), it's likely not a CVV
        # Check character immediately before and after
        char_before = text[start-1:start] if start > 0 else ""
        char_after = text[end:end+1] if end < len(text) else ""
        if char_before.isdigit() or char_after.isdigit():
            return False # It's part of a larger number

        context_before = text[max(0, start - context_window):start].lower()
        context_after = text[end:min(len(text), end + context_window)].lower()

        cvv_keywords = ["cvv", "cvc", "csc", "security code", "card verification", "verification no"]
        date_keywords = ["date", "year", "/", "-", "born", "age", "since", "established", "version", "model", "grade"] # More exhaustive

        is_cvv_context = any(keyword in context_before or keyword in context_after for keyword in cvv_keywords)

        # If it looks like a year in common contexts, it's probably not a CVV
        # e.g. "since 2023", "class of 99", "born 1990"
        if value.isdigit() and (1900 <= int(value) <= 2100 if len(value) == 4 else False):
            year_context_keywords = ["year", "born", "fiscal", "established", "since", "class of", "ended", "began", "joined"]
            if any(kw in context_before for kw in year_context_keywords):
                return False # Likely a year
            # If it's MM/YY or MM/YYYY context, it's expiry, not CVV
            if re.search(r'\b(0[1-9]|1[0-2])[/\s-]$', context_before.strip()): # Ends with MM/
                 return False # Part of an expiry date

        is_date_context = any(keyword in context_before or keyword in context_after for keyword in date_keywords)

        # Check if the number itself looks like a year in typical CVV lengths
        looks_like_year = False
        if len(value) == 2 and value.isdigit(): # e.g. "23" for year in expiry
            if any(k in context_before for k in ["expiry", "exp", "valid thru", "good thru"]) or \
               re.search(r'\b(0[1-9]|1[0-2])[/\s-]$', context_before.strip()):
                looks_like_year = True # It's the YY part of an expiry
        elif len(value) == 4 and value.isdigit() and (1900 <= int(value) <= 2100):
             if any(k in (context_before + context_after) for k in ["year", "born", "fiscal"]):
                 looks_like_year = True


        return is_cvv_context and not (is_date_context and looks_like_year)

    def verify_phone_number(self, text: str, match: re.Match) -> bool:
        """
        Verify if a match is actually a phone number using validation rules and context.
        
        This helps prevent:
        1. CVV numbers being detected as phone numbers
        2. Parts of a phone number being detected as separate numbers
        3. Random digit sequences being detected as phone numbers
        """
        value = match.group()
        start, end = match.span()
        
        # 1. Minimum digit count check (excluding formatting chars)
        digit_count = sum(1 for c in value if c.isdigit())
        if digit_count < 6:
            return False  # Too few digits to be a valid phone number
        
        if digit_count > 15:
            return False  # Too many digits to be a realistic phone number
            
        # 2. Context check for phone numbers
        context_window = 50
        context_before = text[max(0, start - context_window):start].lower()
        context_after = text[end:min(len(text), end + context_window)].lower()
        
        phone_keywords = [
            "phone", "call", "tel", "telephone", "contact", "dial", 
            "mobile", "cell", "number", "direct", "office", "fax"
        ]
        
        # If phone context keywords are found, increase confidence
        has_phone_context = any(kw in context_before or kw in context_after for kw in phone_keywords)
        
        # 3. Check if this is likely part of a larger number or another entity
        # Look for specific formatted patterns that indicate complete phone numbers
        is_clean_formatted = bool(re.search(r'(?:\+\d{1,4}[-\s])?(?:\(\d+\)[-\s]?)?\d+(?:[-\s]\d+)+', value))
        
        # If not properly formatted but has a plus sign, it's likely an international number
        has_intl_prefix = value.startswith('+') or value.startswith('00')
        
        # If it has at least some formatting and reasonable digit count, or has clear phone context,
        # we'll consider it a valid phone number
        return (is_clean_formatted and digit_count >= 7) or (has_intl_prefix and digit_count >= 8) or (has_phone_context and digit_count >= 7)

    def detect_name_entities(self, text: str) -> List[Entity]:
        """Detect name entities using SpaCy NER"""
        entities = []
        doc = self.nlp(text)

        for ent in doc.ents:
            # Use PER for person, common in many models like xx_ent_wiki_sm
            # Also checking for PERSON as some models might use it.
            if ent.label_ in ["PER", "PERSON"]:
                entities.append(Entity(ent.start_char, ent.end_char, "full_name", ent.text))
        return entities

    def detect_all_entities(self, text: str) -> List[Entity]:
        """Detect all types of entities in the text"""
        # Get regex-based entities first
        entities = self.detect_regex_entities(text)

        # Add SpaCy-based name entities
        # We add them second and let overlap resolution handle conflicts
        # This is because NER for names can be more reliable than a generic regex
        name_entities = self.detect_name_entities(text)
        entities.extend(name_entities)

        # Sort entities by their starting position
        entities.sort(key=lambda x: x.start)

        # Resolve overlaps: prioritize NER entities (like names) or longer regex matches
        entities = self._resolve_overlaps(entities)
        return entities

    def _resolve_overlaps(self, entities: List[Entity]) -> List[Entity]:
        """Resolve overlapping entities.
        Prioritize:
        1. NER entities (e.g., "full_name") if they overlap with regex.
        2. Longer entities over shorter ones.
        3. If same length and type, no change (first one encountered).
        """
        if not entities:
            return []

        # A simple greedy approach: iterate and remove/adjust overlaps
        # This can be made more sophisticated
        resolved_entities: List[Entity] = []
        for current_entity in sorted(entities, key=lambda e: (e.start, -(e.end - e.start))): # Process by start, then by longest
            is_overlapped_or_contained = False
            temp_resolved = []
            for i, res_entity in enumerate(resolved_entities):
                # Check for overlap:
                # Current: |----|
                # Res:         |----|   or |----| or   |--|  or  |------|
                overlap = max(0, min(current_entity.end, res_entity.end) - max(current_entity.start, res_entity.start))

                if overlap > 0:
                    is_overlapped_or_contained = True
                    # Preference:
                    # 1. NER names often trump regex if they are the ones causing overlap
                    # 2. Longer entity wins
                    current_len = current_entity.end - current_entity.start
                    res_len = res_entity.end - res_entity.start

                    # If current is a name and overlaps, and previous is not a name, prefer current if it's not fully contained
                    if current_entity.entity_type == "full_name" and res_entity.entity_type != "full_name":
                        if not (res_entity.start <= current_entity.start and res_entity.end >= current_entity.end): # current not fully contained by res
                             # remove res_entity, current will be added later
                            continue # go to next res_entity, this one is marked for removal
                    elif res_entity.entity_type == "full_name" and current_entity.entity_type != "full_name":
                         # res_entity is a name, current is not. Prefer res_entity if it's not fully contained
                        if not (current_entity.start <= res_entity.start and current_entity.end >= res_entity.end):
                            # current entity is subsumed or less important, so don't add current
                            # and keep res_entity
                            temp_resolved.append(res_entity)
                            is_overlapped_or_contained = True # Mark current as handled
                            break # Current is dominated

                    # General case: longer entity wins
                    if current_len > res_len:
                        # current is longer, res_entity is removed from consideration for this current_entity
                        pass # res_entity will not be added to temp_resolved if it's fully replaced
                    elif res_len > current_len:
                        # res is longer, current is dominated
                        temp_resolved.append(res_entity)
                        is_overlapped_or_contained = True # Mark current as handled
                        break # Current is dominated
                    else: # Same length, keep existing one (res_entity)
                        temp_resolved.append(res_entity)
                        is_overlapped_or_contained = True # Mark current as handled
                        break
                else: # No overlap
                    temp_resolved.append(res_entity)

            if not is_overlapped_or_contained:
                temp_resolved.append(current_entity)

            resolved_entities = sorted(temp_resolved, key=lambda e: (e.start, -(e.end - e.start)))


        # Final pass to remove fully contained entities if a larger one exists
        final_entities = []
        if not resolved_entities:
            return []

        for i, entity in enumerate(resolved_entities):
            is_contained = False
            for j, other_entity in enumerate(resolved_entities):
                if i == j:
                    continue
                # If 'entity' is strictly contained within 'other_entity'
                if other_entity.start <= entity.start and other_entity.end >= entity.end and \
                   (other_entity.end - other_entity.start > entity.end - entity.start):
                    is_contained = True
                    break
            if not is_contained:
                final_entities.append(entity)

        return final_entities


    def mask_text(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Mask PII entities in the text and return masked text and entity information
        """
        entities = self.detect_all_entities(text)
        entity_info = [entity.to_dict() for entity in entities]

        # Sort entities by start position to ensure correct masking,
        # longest first at same start to prevent partial masking by shorter entities
        entities.sort(key=lambda x: (x.start, -(x.end - x.start)))

        new_text_parts = []
        current_pos = 0

        for entity in entities:
            # Add text before the entity
            if entity.start > current_pos:
                new_text_parts.append(text[current_pos:entity.start])

            # Add the mask with entity type in uppercase for better visibility
            mask = f"[{entity.entity_type.upper()}]"
            new_text_parts.append(mask)

            current_pos = entity.end

        # Add any remaining text after the last entity
        if current_pos < len(text):
            new_text_parts.append(text[current_pos:])

        return "".join(new_text_parts), entity_info


    def process_email(self, email_text: str) -> Dict[str, Any]:
        """
        Process an email by detecting and masking PII entities.
        The original email is stored in the database for later retrieval if needed.
        """
        # Mask the email
        masked_email, entity_info = self.mask_text(email_text)
        
        # Store the email in the SQLite database - only get back email_id now
        email_id = self.db.store_email(
            original_email=email_text,
            masked_email=masked_email,
            masked_entities=entity_info
        )
        
        # Return the processed data with just the email_id
        return {
            "input_email_body": email_text,  # Return original input for API compatibility
            "list_of_masked_entities": entity_info,
            "masked_email": masked_email,
            "category_of_the_email": "",
            "email_id": email_id
        }
    
    def get_original_email(self, email_id: str, access_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the original email with PII using the email ID and access key.
        
        Args:
            email_id: The ID of the stored email
            access_key: The security key for accessing the original email
            
        Returns:
            The original email data or None if not found or access_key is invalid
        """
        return self.db.get_original_email(email_id, access_key)
    
    def get_masked_email_by_id(self, email_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a masked email by its ID (without the original PII-containing email).
        
        Args:
            email_id: The ID of the stored email
            
        Returns:
            The masked email data or None if not found
        """
        return self.db.get_email_by_id(email_id)
        
    def get_original_by_masked_email(self, masked_email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the original unmasked email using the masked email content.
        
        Args:
            masked_email: The masked version of the email to search for
            
        Returns:
            The original email data or None if not found
        """
        return self.db.get_email_by_masked_content(masked_email)