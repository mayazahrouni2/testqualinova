from sentence_transformers import SentenceTransformer
from config.settings import settings

class EmbeddingService:
    """ Singleton Statique (Code) + Dynamique (Vecteurs) """
    _instance = None
    
    @classmethod
    def get_model(cls):
        if cls._instance is None:
            cls._instance = SentenceTransformer(settings.EMBEDDING_MODEL)
        return cls._instance

    @classmethod
    def encode(cls, text: str):
        model = cls.get_model()
        return model.encode(text)
