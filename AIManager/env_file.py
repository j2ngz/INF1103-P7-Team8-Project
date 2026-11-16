import os

#This will read the .env file which contains the Gemini API key, so the AI Manager can find the GEMINI_API_KEY
#If the .env file is missing, it wouldnt crash the program
def load_env_file(path, environ=None):
    environ = os.environ if environ is None else environ

    #When no .env file detected 
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            #if key is already set, keep existing and ignore .env file
            environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
