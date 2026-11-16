from abc import ABC, abstractmethod

#A blueprint for any AI we are going to connect to (E.g. Our AI API (Gemini) or for our test script)
class AIClient(ABC):

    @abstractmethod
    def generate_json(self, prompt, resume_paths):
        """
        Send the built prompt and resumes to the AI, and returns its reply as text.
        No errors will be catched here. The AIManager will handle the errors if it encounters one
        """
        pass
