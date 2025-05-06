from models.openai_model import OpenAIModel
from models.local_model import LocalLLM

def get_model(use_openai: bool = False):
    return OpenAIModel() if use_openai else LocalLLM()
