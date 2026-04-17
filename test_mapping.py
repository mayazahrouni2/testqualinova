from database.qdrant_db import qdrant_client_instance as vector_client
from agents.evidence_mapper import EvidenceMapper
from utils.embedding_utils import EmbeddingService
import os

def test_evidence_mapping():
    print("--- TEST MAPPING DE PREUVES HYBRIDE (MCP / QDRANT) ---")
    
    # 1. Vérification Connexion Qdrant
    try:
        from database.qdrant_db import qdrant_client_instance
        print(f"Connexion Qdrant active : {bool(qdrant_client_instance.client)}")
    except Exception as e:
        print(f"Erreur Connexion Qdrant : {e}")
        return

    # 2. Insertion de fragments de Test (RAG Simulé)
    test_chunks = [
        {
            "doc_name": "Manuel Qualité.pdf",
            "text": "La politique qualité de l'entreprise est définie par la direction et revue annuellement lors de la revue de direction.",
            "vector": EmbeddingService.encode("La politique qualité de l'entreprise est définie par la direction.")
        },
        {
            "doc_name": "Procédure Sécurité.pdf",
            "text": "Il est recommandé que l'authentification MFA soit activée mais ce n'est pas strict.",
            "vector": EmbeddingService.encode("MFA est recommandé mais pas obligatoire.")
        }
    ]
    
    print("⏳ Insertion de fragments dans Qdrant...")
    company_id = "test_company"
    user_id = "u_test_user"
    vector_client.insert_chunks(company_id, user_id, "audit_test_001", test_chunks)
    print("✅ Fragments insérés.")

    # 3. Test de Mapping avec EvidenceMapper
    mapper = EvidenceMapper()
    
    # Nos exigeances tests:
    # 1. Exigence documentaire pure
    # 2. Exigence technique pure
    # 3. Exigence contradictoire (MFA documentaire vs technique)
    
    exigences = [
        "La direction doit-elle définir une politique qualité ?",
        "L'accès au repository doit être protégé par un système de sécurité MFA.",
        "Le repository backend est-il protégé et revu correctement avant déploiement ?"
    ]
    
    for exigence in exigences:
        print(f"\n🔍 Mapping pour l'exigence : '{exigence}'")
        result = mapper.map_evidence(company_id, "audit_test_001", exigence)
        
        if result:
            print("--- RÉSULTAT MAPPING ---")
            print(f"Source   : {result.get('evidence_source')}")
            print(f"Tech?    : {result.get('technical_evidence_used')}")
            print(f"Conflit? : {result.get('conflict_detected')}")
            print(f"Document : {result.get('best_document')}")
            print(f"Texte    : {result.get('best_text')}")
            print(f"Valide   : {result.get('is_valid')}")
            print(f"Justif   : {result.get('justification')}")
        else:
            print("❌ Aucun résultat trouvé par le mapper.")

if __name__ == "__main__":
    test_evidence_mapping()
