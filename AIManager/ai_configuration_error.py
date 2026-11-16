
#Error handling: In the event the AI cannot be used at all (e.g API Key missing)
#[Note]: the error message for user to see can be set in gemini_client.py... 
class AIConfigurationError(RuntimeError): 
    """
    Runing into this error means the AI was not setup properly... (No API key)...
    Firstly the AI manager will not retry this and, The app will show a error message 
    to the user and goes back to the menu  
    """
    pass
