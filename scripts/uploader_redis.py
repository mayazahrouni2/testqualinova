import sys
import os
import json

# Ajout du chemin racine pour l'import des services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.upstash_redis_service import upstash_redis_service

def upload_json(audit_id, file_path):
    """
    Uploade un fichier JSON local vers Upstash Redis sans aucune ingestion 
    ni traitement de documents locaux (le flux pur).
    """
    if not os.path.exists(file_path):
        print(f"❌ Erreur : Le fichier {file_path} n'existe pas.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Le champ 'analysis' est requis pour le mapping de preuves
        if 'analysis' not in data:
            print("⚠️ Attention : Le JSON ne contient pas de champ 'analysis'.")
            print("L'EvidenceMapper utilise ce champ comme preuve principale.")

        key = upstash_redis_service.set_audit_data(audit_id, data)
        print(f"🚀 Succès ! Données uploadées pour l'audit '{audit_id}' dans Redis.")
        print(f"🔑 Clé créée : {key}")

    except Exception as e:
        print(f"❌ Erreur lors de l'upload : {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/uploader_redis.py <audit_id> <path_to_json>")
        print("Exemple: python scripts/uploader_redis.py audit_test_001 data_audit.json")
    else:
        upload_json(sys.argv[1], sys.argv[2])
