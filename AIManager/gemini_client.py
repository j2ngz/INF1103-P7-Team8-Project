import logging
import os

from AIManager.ai_client import AIClient
from AIManager.ai_configuration_error import AIConfigurationError
from AIManager.no_resumes_uploaded_error import NoResumesUploadedError

logger = logging.getLogger("AIManager")

#Model selected for the API call
MODEL_NAME = "gemini-3.5-flash-lite" 

#if a request that takes longer that the "SET" timing means it fails and AIManager will retry it
REQUEST_TIMEOUT_SECONDS = 120  

#This is the Real AIClient that talks to the gemini API.
class GeminiClient(AIClient):

    def __init__(self, api_key=None, model_name=MODEL_NAME, timeout_seconds=REQUEST_TIMEOUT_SECONDS):
        self._api_key = api_key
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        #it will stay empty until "get_client()"" creates it on the first scan, then reuses it for future scans
        self.__client = None  

    def get_client(self):
        if self.__client is None:
            api_key = self._api_key or os.environ.get("GEMINI_API_KEY", "")
            #If no api key is detect. app.py will show this message to the user
            if not api_key:
                raise AIConfigurationError(
                    "GEMINI_API_KEY is not set. Put it in the .env file")
            #imported here so tests and CI do not need the SDK (easier for us)
            from google import genai 
            try:
                from google.genai import types
                options = types.HttpOptions(timeout=int(self._timeout_seconds * 1000))
                self.__client = genai.Client(api_key=api_key, http_options=options)
            except (ImportError, AttributeError, TypeError, ValueError):
                logger.warning("This google-genai version has no request timeout option LOL using the default...")
                self.__client = genai.Client(api_key=api_key)
        return self.__client

    def upload_resumes(self, resume_paths):
        #upload every PDF to the API, Failed files are skipped, other will continue
        client = self.get_client()
        uploaded = []
        for path in resume_paths:
            try:
                uploaded.append(client.files.upload(file=path))
            except Exception as e:
                logger.error(f"Failed to upload {path}: {e}")
        return uploaded

    def generate_json(self, prompt, resume_paths):
        client = self.get_client()
        uploaded = self.upload_resumes(resume_paths)
        #Error handling: if nothing is uploaded, raise an error 
        if not uploaded:
            raise NoResumesUploadedError("No resumes were uploaded.")
        #if everything is upload semd the prompt and resume, and ask for the reply as "JSON"
        response = client.models.generate_content(
            model=self._model_name,
            contents=[prompt, *uploaded],
            config={"response_mime_type": "application/json"},
        )
        return response.text
