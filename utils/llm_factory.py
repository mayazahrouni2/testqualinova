import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from config.settings import settings


import httpx

# --- AGENT LLM FACTORY (TOKEN FACTORY ESPRIT ONLY) ---

class LLMFactory:
    """
    Fabrique de LLM centralisée utilisant exclusivement TokenFactory Esprit.
    """

    # Mapping agent → modèle selon complexité
    AGENT_MODEL_MAP = {
        "checklist_manager" : {
            "model": "hosted_vllm/Llama-3.1-70B-Instruct",
            "temperature": 0.1,
            "max_tokens" : 4096,
        },
        "evidence_mapper" : {
            "model": "hosted_vllm/Llama-3.1-70B-Instruct",
            "temperature": 0.0,
            "max_tokens" : 2048,
        }
    }

    def __init__(self):
        # Client HTTP avec SSL désactivé (Requis par Esprit)
        self.http_client = httpx.Client(verify=False)

    def get_llm(self, agent_name: str) -> ChatOpenAI:
        """ Retourne une instance ChatOpenAI configurée pour TokenFactory Esprit. """
        config = self.AGENT_MODEL_MAP.get(agent_name, self.AGENT_MODEL_MAP["evidence_mapper"])
        
        # Lecture dynamique (évite le cache Streamlit sur les modules)
        url = settings.TOKEN_FACTORY_URL
        key = settings.TOKEN_FACTORY_KEY
        
        return ChatOpenAI(
            model       = config["model"],
            base_url    = url,
            api_key     = key,
            temperature = config["temperature"],
            max_tokens  = config["max_tokens"],
            timeout     = 100,
            http_client = self.http_client
        )


llm_factory = LLMFactory()
