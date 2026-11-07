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
