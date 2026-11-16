import json

#Checks the API's reply before app.py uses it
class ResponseValidator:

    #The five field we specified that we want from the prompt that every record must have (has to be same name as the prompt and ResumeData)
    REQUIRED_FIELDS = {"filename", "name", "skills", "experience_by_field", "certificates_by_industry"}

    def parse(self, raw_text):
        #Turns the reply into a list of dict (one per resume). Returns nothing if its not a JSON
        if not isinstance(raw_text, str):
            return None
        cleaned = raw_text.strip()
        #removing ``` from the replies as the api sometimes returns it in that format...
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, list) else None

    def is_valid(self, record):
       #True when the record has all five fields with the right types
        if not isinstance(record, dict):
            return False
        if not self.REQUIRED_FIELDS.issubset(record.keys()):
            return False
        if not isinstance(record["filename"], str) or not isinstance(record["name"], str):
            return False
        
        #skills must be a list and every item must be a text...
        skills = record["skills"]
        if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
            return False

        #expericence must be a dict and each field name maps to a number (int)
        experience = record["experience_by_field"]
        if not isinstance(experience, dict):
            return False
        if not all(isinstance(v, (int, float)) for v in experience.values()):
            return False

        #certificates must be a dict, each industry maps to a list of certificate names (text) 
        certificates = record["certificates_by_industry"]
        if not isinstance(certificates, dict):
            return False
        for certs in certificates.values():
            if not isinstance(certs, list) or not all(isinstance(c, str) for c in certs):
                return False
        return True

    def valid_records(self, records):
        #Error handling: Keeps the valid records and count how many were dropped
        valid = [r for r in records if self.is_valid(r)]
        return valid, len(records) - len(valid)
