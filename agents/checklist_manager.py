from utils.file_extractor import FileExtractor
from utils.llm_factory import llm_factory
from langchain_core.messages import HumanMessage, SystemMessage
import json

class ChecklistManager:
    """ Agent intelligent : Traduit n'importe quelle checklist brute en JSON Standard """
    
    def __init__(self):
        self.llm = llm_factory.get_llm("checklist_manager")

    def process_checklist(self, file_path):
        """ Extrait et structure la checklist à partir du fichier (PDF, Excel, Word, Image) """
        raw_text = FileExtractor.extract_by_extension(file_path)
        
        if not raw_text.strip():
            return []

        # Construction du prompt pour le parsing intelligent (Phase 3 du document)
        system_prompt = (
            "Tu es un expert en audit. On te fournit du texte brut issue d'un document d'audit "
            "(Excel, PDF ou OCR). Ta mission est d'extraire les éléments de la checklist "
            "en JSON valide. Chaque élément doit avoir : id (exigence), description, impact."
        )
        
        human_prompt = (
            f"TEXTE BRUT DU DOCUMENT :\n{raw_text[:8000]}\n\n"
            "Retourne UNIQUEMENT une liste JSON comme ceci : "
            '[{"id": "...", "description": "...", "impact": "..."}]'
        )

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            
            # Nettoyage de la réponse s'il y a des balises markdown
            content = response.content.strip()
            print(f"DEBUG: Checklist agent response starts with: {content[:100]}...") 
            
            # Extraction plus robuste du JSON (recherche de { ou [)
            if "```json" in content:
                content = content.split("```json")[-1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[-1].split("```")[0].strip()

            # On cherche le premier signe JSON
            start_idx = min([content.find("["), content.find("{")]) if "[" in content and "{" in content else (content.find("[") if "[" in content else content.find("{"))
            end_idx = max([content.rfind("]"), content.rfind("}")]) + 1 if "]" in content and "}" in content else (content.rfind("]") + 1 if "]" in content else content.rfind("}") + 1)
            
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx]
            
            data = json.loads(content)
            
            # Si c'est un dictionnaire qui contient une liste, on l'extrait (ex: {"checklist": [...]})
            if isinstance(data, dict):
                for key in data:
                    if isinstance(data[key], list) and len(data[key]) > 0:
                        return data[key]
                return [] # Dico sans liste
                
            return data if isinstance(data, list) else []
            
        except Exception as e:
            print(f"Erreur lors de l'extraction par l'agent checklist : {str(e)}")
            if 'content' in locals():
                print(f"DEBUG: Contenu brut qui a échoué au parsing JSON : {content}")
            return []
