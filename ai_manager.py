import json
import logging
import os
import time
from abc import ABC, abstractmethod

from models import ResumeBatch, ResumeData

logger = logging.getLogger("AIManager")

# AI Model, API connection failure
MODEL_NAME = "gemini-3.5-flash-lite"  # Google gemini API
MAX_RETRIES = 5
BACKOFF_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 120 

#Errors
#Custom errors raised by the Gemini, AI manager handle them seperately.
class AIConfigurationError(RuntimeError):
    """The AI cannot be used at all, no API key or model is down)."""


class NoResumesUploadedError(RuntimeError):
    """None of the resume files is uploaded to Gemini."""


#For Key Retreieval in .env
#Loads API key from a .env file into the environment.
def load_env_file(path, environ=None):
    environ = os.environ if environ is None else environ
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

#The AI client interface
class AIClient(ABC):
    """A template for any AI client: it must be able to turn resumes into JSON text."""

    @abstractmethod
    def generate_json(self, prompt, resume_paths):
        """
        Send the built prompt along with resumes files from the /resumes folder to AI API and return the reply as JSON text
        if the connection fail then AIManager will handle the error
        """

#Gemini implementation
class GeminiClient(AIClient):
    def __init__(self, api_key=None, model_name=MODEL_NAME, timeout_seconds=REQUEST_TIMEOUT_SECONDS):
        self._api_key = api_key
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self.__client = None

    def get_client(self):
        if self.__client is None:
            #If there got no connection establish before, build with the .env file API key
            api_key = self._api_key or os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                raise AIConfigurationError("GEMINI_API_KEY is not set...")
            from google import genai
            #Timeout handling every request gets a time limit, so a slow API call fails due to many ppl using the same API call
            try:
                from google.genai import types
                options = types.HttpOptions(timeout=int(self._timeout_seconds * 1000))
                self.__client = genai.Client(api_key=api_key, http_options=options)
            except (ImportError, AttributeError, TypeError, ValueError):
                self.__client = genai.Client(api_key=api_key)
        return self.__client

    def upload_resumes(self, resume_paths):
        #Uploads all the resume files and if a file that fail to upload it is logged and skipped.
        client = self.get_client()
        uploaded = []
        for path in resume_paths:
            try:
                uploaded.append(client.files.upload(file=path))
            except Exception as e:
                logger.error(f"Failed to upload {path}: {e}")
        return uploaded
    
    def generate_json(self, prompt, resume_paths):
        #Send the built prompt with uploaded PDFs to Gemini API and return its reply in JSON text.
        client = self.get_client()
        uploaded = self.upload_resumes(resume_paths)
        #If no PDF could be uploaded, raise an error because there is nothing to read.
        if not uploaded:
            raise NoResumesUploadedError("No resumes were successfully uploaded.")
        response = client.models.generate_content(
            model=self._model_name,
            contents=[prompt, *uploaded],
            config={"response_mime_type": "application/json"},
        )
        return response.text

# Prompt
#Prompt used to send the instruction alongside the uploaded resume files.
def build_prompt(filenames):
    file_list = "\n".join(f"- {name}" for name in filenames)
    return (
        "You are an information extraction engine. You will be given "
        f"{len(filenames)} resumes as attached files:\n{file_list}\n\n"
        "For EACH resume, extract:\n"
        "  - filename: the exact file name of the resume\n"
        "  - name: the candidate's full name as it appears on the resume\n"
        "  - skills: a list of technical/professional skills mentioned\n"
        "  - experience_by_field: an object mapping each professional field/industry the "
        "candidate has worked in to their total years of experience in that field, e.g. "
        '{"IT": 4, "Finance": 1}. Use your best judgement to categorize roles into fields '
        "(e.g. IT, Finance, Marketing, Healthcare, Education, Sales, Engineering, Business). "
        "Software, data, analytics, business intelligence, cloud, cybersecurity and other "
        "technology roles must ALL be filed under the single field name \"IT\" - do not invent "
        "separate names such as \"Data Analytics\" or \"Software\". "
        "If experience is not clearly tied to a field, categorize it under \"General\".\n"
        "  - certificates_by_industry: an object mapping each industry to a LIST of the "
        'exact certificate names the candidate holds in that industry, e.g. '
        '{"IT": ["AWS Certified Solutions Architect", "CompTIA Security+"], "FnB": ["ServSafe"]}. '
        "Certificates in software, data, analytics, business intelligence, cloud or "
        "cybersecurity (for example Tableau, Power BI, AWS, Azure, CompTIA) must be listed under \"IT\". "
        "Use an empty object {} if no certificates are mentioned.\n\n"
        "Return ONLY a JSON array, one object per resume, with exactly these five keys. "
        "Do not include any explanation, markdown formatting, or extra text - JSON only."
    )

#Validations
class ResponseValidator:
    #Read the Gemini API replies and ensure that it has the 5 fields we want
    REQUIRED_FIELDS = {"filename", "name", "skills", "experience_by_field", "certificates_by_industry"}

    def parse(self, raw_text):
        #Change the Gemeni API reply into list of records, or None
        if not isinstance(raw_text, str):
            return None
        cleaned = raw_text.strip()
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
        #True when the record has all 5 fields.
        if not isinstance(record, dict):
            return False
        if not self.REQUIRED_FIELDS.issubset(record.keys()):
            return False
        if not isinstance(record["filename"], str) or not isinstance(record["name"], str):
            return False
        skills = record["skills"]
        if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
            return False

        experience = record["experience_by_field"]
        if not isinstance(experience, dict):
            return False
        if not all(isinstance(v, (int, float)) for v in experience.values()):
            return False

        certificates = record["certificates_by_industry"]
        if not isinstance(certificates, dict):
            return False
        for certs in certificates.values():
            if not isinstance(certs, list) or not all(isinstance(c, str) for c in certs):
                return False
        return True

    def valid_records(self, records):
        #Keeps only the valid records, and count how many failed
        valid = [r for r in records if self.is_valid(r)]
        return valid, len(records) - len(valid)

#The main loop
class AIManager:
    #Runs AI portion of the code which sends the resumes to the AI, checks the reply and retries if it fails.
    def __init__(self, client, validator=None, max_retries=MAX_RETRIES, backoff_seconds=BACKOFF_SECONDS, sleep=time.sleep):
        self._client = client
        self._validator = validator or ResponseValidator()
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep

    def process_resume_batch(self, resume_paths):
        if not resume_paths:
            return ResumeBatch()

        filenames = [os.path.basename(p) for p in resume_paths]
        prompt = build_prompt(filenames)

        for attempt in range(1, self._max_retries + 1):
            try:
                raw = self._client.generate_json(prompt, resume_paths)
                records = self._validator.parse(raw)
                if records is None:
                    logger.warning(f"Attempt {attempt}: malformed JSON response, retrying...")
                    continue

                valid, dropped = self._validator.valid_records(records)
                if dropped:
                    logger.warning(
                        f"Attempt {attempt}: {dropped} record(s) failed schema validation and were dropped.")
                if valid:
                    return ResumeBatch(ResumeData.from_dict(r) for r in valid)
                logger.warning(f"Attempt {attempt}: no valid records parsed, retrying...")

            except AIConfigurationError:
                raise
            except NoResumesUploadedError as e:
                logger.error(str(e))
                return ResumeBatch()
            except Exception as e:
                logger.error(f"Attempt {attempt}: API call failed: {e}")
                if attempt < self._max_retries:
                    self._sleep(self._backoff_seconds * attempt)

        logger.error("All retries exhausted. Returning empty result for this batch.")
        return ResumeBatch()
