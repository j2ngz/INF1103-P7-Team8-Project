
#Error handling: in the event no resumes can be uploaded to the AI
class NoResumesUploadedError(RuntimeError):
    """
    Running into this error means that the resumes failed the upload... (bad file/network issue...)
    Firstly the AI manager will not retry this. It logs the error message and returns an empty ResumeBatch
    The app will then tell the user nothing was saved and goes back to the menu, 
    """
    pass
