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

