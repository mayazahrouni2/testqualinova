import os
import re
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from config.settings import settings

class QdrantDBClient:
    """ Client Qdrant robuste pour le stockage vectoriel de l'audit """
    
    def __init__(self):
        self.url = settings.QDRANT_URL
        self.api_key = settings.QDRANT_API_KEY
        self.collection_name = "audit_evidence_m3"
        self.dim = 1024 # Dimension par défaut pour BAAI/bge-m3
        
        self._connect()
        self._setup_collection()

    def _connect(self):
        """ Connexion à Qdrant Cloud ou Local """
        try:
            print(f"📡 Tentative de connexion Qdrant sur : {self.url}")
            if self.url and self.api_key:
                self.client = QdrantClient(url=self.url, api_key=self.api_key)
            elif self.url:
                self.client = QdrantClient(url=self.url)
            else:
                self.client = QdrantClient(":memory:") # Solution de repli locale en mémoire
            print(f"✅ Qdrant initialisé avec succès sur : {self.url}")
            print(f"🏗️ Tentative de configuration de la collection...")
        except Exception as e:
            print(f"❌ Erreur de connexion Qdrant : {e}")
            raise e

    def _setup_collection(self):
        """ Création de la collection si elle n'existe pas """
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            # Création de la collection partagée unique
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )
            print(f"🏗️ Collection Qdrant '{self.collection_name}' créée avec succès.")
            
        # Création d'un index de payload pour optimiser le filtrage par company_id
        from qdrant_client.http.models import PayloadSchemaType
        try:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="company_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="audit_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            print("⚡ Index 'company_id' et 'audit_id' créés ou mis à jour.")
        except Exception as e:
            pass

    def insert_chunks(self, company_id, user_id, audit_id, chunks):
        """ Insertion massive de fragments de documents """
        from datetime import datetime
        points = []
        for c in chunks:
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=c["vector"],
                    payload={
                        "company_id": company_id,
                        "user_id": user_id,
                        "audit_id": audit_id,
                        "document_id": c.get("document_id", str(uuid.uuid4())),
                        "document_name": c["doc_name"],
                        "chunk_index": c.get("chunk_index", 0),
                        "text": c["text"],
                        "document_type": c.get("document_type", "unknown"),
                        "uploaded_at": datetime.utcnow().isoformat(),
                    }
                )
            )
        
        # Qdrant client upsert in batches
        self.client.upload_points(
            collection_name=self.collection_name,
            points=points,
            batch_size=100
        )
        print(f"📦 {len(chunks)} fragments insérés dans Qdrant pour la company '{company_id}'.")

    def search_similar(self, company_id, audit_id, query_vector, top_k=3):
        """ Recherche sémantique par similarité cosinus avec filtrage strict par company_id """
        
        # Filtre par company_id ET optionnellement audit_id
        must_conditions = [
            FieldCondition(key="company_id", match=MatchValue(value=company_id))
        ]
        
        if audit_id and audit_id != "global":
            must_conditions.append(FieldCondition(key="audit_id", match=MatchValue(value=audit_id)))
            
        qdrant_filter = Filter(must=must_conditions)
        
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=10, # On cherche plus pour filtrer la diversité
            with_payload=True
        ).points
        
        formatted_results = []
        seen_docs = set()
        all_hits = []
        
        for hit in results:
            payload = hit.payload
            text = payload.get("text") or ""
            # Filtre : on ignore les chunks trop courts (bruit administratif, signatures...)
            if text.strip():
                all_hits.append({
                    "text": text,
                    "doc_name": payload.get("document_name", payload.get("doc_name")),
                    "score": hit.score
                })
                
        # Reranking : Priorité aux chunks riches (Lexical Scoring)
        def score_chunk_richness(chunk):
            score = 0
            if re.search(r'\d{2}/\d{2}/\d{4}', chunk['text']): score += 2  # Date complète
            if re.search(r'M\.|Mme\.', chunk['text']): score += 2          # Personne / Titre
            if len(chunk['text']) > 300: score += 1                        # Longueur (moins de risques d'être hors contexte)
            if re.search(r'%|objectif|indicateur|revue', chunk['text'], re.IGNORECASE): score += 1
            return score
            
        # On trie les candidats (qui sont déjà sémantiquement pertinents) par leur richesse
        all_hits = sorted(all_hits, key=score_chunk_richness, reverse=True)
                
        # 1. 1 extrait max par document (diversité)
        for hit in all_hits:
            if hit["doc_name"] not in seen_docs:
                formatted_results.append(hit)
                seen_docs.add(hit["doc_name"])
            if len(formatted_results) == top_k:
                break
                
        # 2. Si pas assez (ex. 1 seul document existant), on complète avec les autres
        if len(formatted_results) < top_k:
            for hit in all_hits:
                if hit not in formatted_results:
                    formatted_results.append(hit)
                if len(formatted_results) == top_k:
                    break
                    
        return formatted_results

    def delete_document(self, company_id, audit_id):
        """ Supprimer de manière sécurisée les points liés à une company et un audit donné """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="company_id",
                        match=MatchValue(value=company_id)
                    ),
                    FieldCondition(
                        key="audit_id",
                        match=MatchValue(value=audit_id)
                    )
                ]
            )
        )

qdrant_client_instance = QdrantDBClient()
