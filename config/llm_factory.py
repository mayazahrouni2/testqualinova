from langchain_community.chat_models import ChatOllama
from config.settings import settings

class LLMFactory:
    """ Semi-statique : La config est fixe, mais crée des objets à la demande """
    AGENT_MODEL_MAP = {
        "checklist_manager": {"model": "llama3", "temperature": 0.1},
        "evidence_mapper": {"model": "llama3", "temperature": 0.1},
        "compliance_evaluator": {"model": "llama3", "temperature": 0.05},
        "nc_manager": {"model": "llama3", "temperature": 0.2},
        "capa_manager": {"model": "llama3", "temperature": 0.3},
        "report_generator": {"model": "llama3", "temperature": 0.4}
    }

    @staticmethod
    def get_llm(agent_name: str):
        config = LLMFactory.AGENT_MODEL_MAP.get(agent_name, {"model": "llama3", "temperature": 0.1})
        return ChatOllama(
            model=config["model"],
            temperature=config["temperature"],
            base_url=settings.OLLAMA_URL.replace("/v1", ""),
        )
