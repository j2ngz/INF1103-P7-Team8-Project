import logging
import os
import time

from AIManager.ai_configuration_error import AIConfigurationError
from AIManager.no_resumes_uploaded_error import NoResumesUploadedError
from AIManager.prompt_builder import build_prompt
from AIManager.response_validator import ResponseValidator
from Models.resume_batch import ResumeBatch
from Models.resume_data import ResumeData

logger = logging.getLogger("AIManager")

#How many times the AI will retry and wait if it encounters an error (e.g no internet/high traffic for the API used)
MAX_RETRIES = 5
BACKOFF_SECONDS = 5


# Main class for the AIManager. app.py willl only call this class. It will run the whole AI portion and return a ResumeBatch
class AIManager:
    """
    Uses a client to talk to gemini, build_prompt for the instructions to send and validator to check the reply...
    app.py will give it the real client (GeminiClient), and tests will give it the fake one (FakeAIClient)
    """

    def __init__(self, client, validator=None,
                 max_retries=MAX_RETRIES, backoff_seconds=BACKOFF_SECONDS, sleep=time.sleep):
        self._client = client
        self._validator = validator or ResponseValidator()
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep

    def process_resume_batch(self, resume_paths):
        """
        Will return a ResumeBatch, when 
        1) the records are correct and is ready for the next phase (AI replies with no issues)
        2) it is empty when nothing usable comes back
        3) AI call keeps failing after all retries
        Missing API key which doesnt return anything. (Error is passed to app.py)
        """
        #When there is nothing to scan
        if not resume_paths:
            return ResumeBatch()

        filenames = [os.path.basename(p) for p in resume_paths]
        prompt = build_prompt(filenames)

        for attempt in range(1, self._max_retries + 1):
            try:
                raw = self._client.generate_json(prompt, resume_paths)
                records = self._validator.parse(raw)

                #if the reply is not in JSON, rerun
                if records is None:
                    logger.warning(f"Attempt {attempt}: malformed JSON response detected, retrying...")
                    continue

                #Only keep the records that passed the checks, drops any that fails
                valid, dropped = self._validator.valid_records(records)
                if dropped:
                    logger.warning(
                        f"Attempt {attempt}: {dropped} record(s) failed the schema validation and will be dropped.")
                    
                #ALL correct records will be turned into a ResumeBatch and finish
                if valid:
                    return ResumeBatch(ResumeData.from_dict(r) for r in valid)
                logger.warning(f"Attempt {attempt}: no valid records are parsed, retrying...")

            #Error handling: No API Key (passing the error to app.py...)
            except AIConfigurationError:
                raise
            
            #Error handling: No resumes can be upload, returning empty ResumeBatch...
            except NoResumesUploadedError as e:
                logger.error(str(e))
                return ResumeBatch()
            
            #Error handling: when theres no internet or the API selected is busy, wait and try again...
            except Exception as e:
                logger.error(f"Attempt {attempt}: API call failed: {e}")
                if attempt < self._max_retries:
                    self._sleep(self._backoff_seconds * attempt)

        #Error handling: All attempts used, returning empty ResumeBatch...
        logger.error("All retries exhausted. Returning empty result for this batch.")
        return ResumeBatch()
