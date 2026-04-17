import os
from dotenv import load_dotenv

class Settings:
    def __init__(self):
        load_dotenv()
        # Supabase
        self.SUPABASE_URL = os.getenv("SUPABASE_URL", "")
        self.SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
        
        # Redis
        self.REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        self.REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
        
        # Qdrant
        self.QDRANT_URL = os.getenv("QDRANT_URL", "")
        self.QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
        
        # TokenFactory Esprit (Unique Provider)
        self.TOKEN_FACTORY_URL = os.getenv("TOKEN_FACTORY_URL", "https://tokenfactory.esprit.tn/v1")
        self.TOKEN_FACTORY_KEY = os.getenv("TOKEN_FACTORY_KEY", "")
        
        self.EMBEDDING_MODEL = "BAAI/bge-m3"

settings = Settings()
