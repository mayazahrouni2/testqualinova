import os
from upstash_redis import Redis
from dotenv import load_dotenv
import json

load_dotenv()

class UpstashRedisService:
    def __init__(self):
        url = os.getenv("UPSTASH_REDIS_REST_URL")
        token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.redis = Redis(url=url, token=token)

    def get_audit_data(self, company_id: str, audit_id: str):
        """
        Récupère les données d'audit filtrées par entreprise.
        Clés : 'audit:{company_id}:{audit_id}'
        """
        # 1. Tentative par clé structurée (Priorité)
        structured_key = f"audit:{company_id}:{audit_id}"
        data = self.redis.get(structured_key)
        if data:
            print(f"✅ [REDIS] Données trouvées pour l'entreprise '{company_id}' : '{structured_key}'")
            return self._parse_data(data)

        # 2. Backwards compatibility : Tentative sans company_id si rien n'est trouvé
        legacy_keys = [f"audit:{audit_id}", audit_id]
        for key in legacy_keys:
            data = self.redis.get(key)
            if data:
                print(f"⚠️ [REDIS] Données trouvées via clé héritée : '{key}'")
                return self._parse_data(data)

        # 3. Recherche floue dans les clés de l'entreprise
        all_company_keys = self.redis.keys(f"audit:{company_id}:*")
        potential = [k for k in all_company_keys if audit_id in k]
        if potential:
            print(f"🔎 [REDIS] Match partiel trouvé pour l'entreprise : '{potential[0]}'")
            return self._parse_data(self.redis.get(potential[0]))

        print(f"❌ [REDIS] Aucune donnée pour l'audit '{audit_id}' et l'entreprise '{company_id}'")
        return None


    def set_audit_data(self, company_id: str, audit_id: str, data: dict):
        """
        Stocke les données d'audit sous une clé isolée par entreprise.
        """
        key = f"audit:{company_id}:{audit_id}"
        data["company_id"] = company_id
        data["audit_id"] = audit_id
        self.redis.set(key, json.dumps(data, ensure_ascii=False))
        print(f"✅ [REDIS] Données stockées pour {company_id} -> {key}")
        return key

    def _parse_data(self, data):

        if isinstance(data, str):
            try:
                return json.loads(data)
            except:
                return data
        return data

    def get_all_data(self, key_pattern: str = "*"):
        """Récupère toutes les données correspondant à un pattern."""
        keys = self.redis.keys(key_pattern)
        results = {}
        for key in keys:
            results[key] = self.redis.get(key)
        return results

    def list_all_audits(self, company_id: str = None):
        """
        Liste les documents appartenant à une entreprise.
        Scanne les clés audit:* et analysis:*
        """
        all_keys = self.redis.keys("audit:*") + self.redis.keys("analysis:*")
        
        valid_docs = []
        for k in all_keys:
            try:
                raw = self.redis.get(k)
                data = self._parse_data(raw)
                if isinstance(data, dict):
                    # Vérification du tag company_id à l'intérieur du JSON
                    if not company_id or str(data.get("company_id")) == str(company_id):
                        # On utilise le filename ou la clé comme identifiant
                        name = data.get("filename") or k
                        valid_docs.append(name)
            except:
                continue
                
        return list(set(valid_docs))

    def get_audit_data_by_name(self, company_id: str, name: str):
        """Récupère un document par son nom/clé pour une entreprise donnée."""
        all_keys = self.redis.keys("audit:*") + self.redis.keys("analysis:*")
        for k in all_keys:
            try:
                data = self._parse_data(self.redis.get(k))
                if isinstance(data, dict) and str(data.get("company_id")) == str(company_id):
                    if data.get("filename") == name or k == name:
                        # Extraction texte si c'est un dictionnaire d'analyse
                        if isinstance(data.get("analysis"), dict):
                            data["analysis"] = "\n".join([f"{k}: {v}" for k, v in data["analysis"].items()])
                        return data
            except: continue
        return None

    def get_all_company_data(self, company_id: str):
        """Récupère l'intégralité des documents d'une entreprise."""
        all_keys = self.redis.keys("audit:*") + self.redis.keys("analysis:*")
        results = []
        for k in all_keys:
            try:
                data = self._parse_data(self.redis.get(k))
                if isinstance(data, dict) and str(data.get("company_id")) == str(company_id):
                    # Extraction texte
                    if isinstance(data.get("analysis"), dict):
                        data["analysis_text"] = "\n".join([f"{k}: {v}" for k, v in data["analysis"].items()])
                    else:
                        data["analysis_text"] = str(data.get("analysis", ""))
                    results.append(data)
            except: continue
        return results

    def delete_audit_data(self, company_id: str, name: str):
        """Supprime un document par son nom/clé."""
        all_keys = self.redis.keys("audit:*") + self.redis.keys("analysis:*")
        for k in all_keys:
            try:
                data = self._parse_data(self.redis.get(k))
                if isinstance(data, dict) and data.get("company_id") == company_id:
                    if data.get("filename") == name or k == name:
                        return self.redis.delete(k)
            except: continue
        return 0

upstash_redis_service = UpstashRedisService()
