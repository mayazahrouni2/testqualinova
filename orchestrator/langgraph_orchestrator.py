from typing import Annotated, List, TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from agents.checklist_manager import ChecklistManager
from agents.evidence_mapper import EvidenceMapper
import json

# Définition de l'état du GRAPH
class AuditState(TypedDict):
    company_id: str
    user_id: str
    audit_id: str
    checklist_path: str
    requirements: List[dict]
    current_idx: int
    results: List[dict]
    error: Optional[str]

class LangGraphOrchestrator:
    """ Orchestrateur intelligent focalisé sur le Evidence Mapping via LangGraph """
    
    def __init__(self):
        # Initialisation des Agents
        self.checklist_agent = ChecklistManager()
        self.mapper_agent = EvidenceMapper()
        
        # Construction du Graphe
        self.workflow = self._create_workflow()

    def _create_workflow(self):
        graph = StateGraph(AuditState)

        # Ajout des Nœuds Simplifiés pour le Mapping Uniquement
        graph.add_node("extract_checklist", self.node_extract_checklist)
        graph.add_node("map_evidence_loop", self.node_map_evidence_loop)

        # Définition des Chemins (Edges)
        graph.add_edge(START, "extract_checklist")
        
        graph.add_conditional_edges(
            "extract_checklist",
            self.should_continue_after_extraction,
            {
                "continue": "map_evidence_loop",
                "end": END
            }
        )

        graph.add_conditional_edges(
            "map_evidence_loop",
            self.should_continue_processing,
            {
                "loop": "map_evidence_loop",
                "finish": END
            }
        )

        return graph.compile()

    # --- LOGIQUE DES NŒUDS ---

    def node_extract_checklist(self, state: AuditState):
        """ Étape 1 : Extraction de la checklist """
        print(f"--- [LANGGRAPH] Node: Extract Checklist ---")
        reqs = self.checklist_agent.process_checklist(state["checklist_path"])
        return {
            "requirements": reqs, 
            "current_idx": 0,
            "error": None if reqs else "La checklist est vide ou n'a pas pu être extraite."
        }

    def node_map_evidence_loop(self, state: AuditState):
        """ Étape 2 : Uniquement le Mapping de Preuves via Qdrant """
        idx = state["current_idx"]
        req = state["requirements"][idx]
        audit_id = state["audit_id"]
        company_id = state["company_id"]
        
        print(f"--- [LANGGRAPH] Node: Evidence Search [{idx+1}/{len(state['requirements'])}] : {req.get('id')} ---")

        # 1. Recherche sémantique dans Qdrant + Arbitrage IA
        mapping_res = self.mapper_agent.map_evidence(
            company_id=company_id,
            audit_id=audit_id,
            requirement_desc=req["description"]
        )

        new_result = {
            "requirement_id": req.get("id", f"REQ-{idx+1}"),
            "description": req["description"],
            "best_document": mapping_res["best_document"] if mapping_res else "AUCUNE PREUVE TROUVÉE",
            "justification": mapping_res["justification"] if mapping_res else "Le moteur vectoriel n'a trouvé aucun fragment pertinent.",
            "elements_manquants": mapping_res.get("elements_manquants", "") if mapping_res else "",
            "is_valid": mapping_res.get("is_valid", False) if mapping_res else False,
            "coverage_score": mapping_res.get("coverage_score", 0.0) if mapping_res else 0.0,
            "similarity": mapping_res.get("similarity_score", 0.0) if mapping_res else 0.0,
            "compliance_status": mapping_res.get("compliance_status", "non_conform") if mapping_res else "non_conform",
            "finding_type": mapping_res.get("finding_type", "major_nc") if mapping_res else "major_nc",
            "risk_level": mapping_res.get("risk_level", "high") if mapping_res else "high",
            "strength_of_evidence": mapping_res.get("strength_of_evidence", "weak") if mapping_res else "weak",
            "evidence_source": mapping_res.get("evidence_source", "document") if mapping_res else "document",
            "technical_evidence_used": mapping_res.get("technical_evidence_used", False) if mapping_res else False,
            "conflict_detected": mapping_res.get("conflict_detected", False) if mapping_res else False,
            "mastery_level": mapping_res.get("mastery_level", "none"),
            "explanation_payload": mapping_res.get("explanation_payload", {}) if mapping_res else {},
        }

        # Mise à jour des résultats
        updated_results = state["results"] + [new_result]

        return {
            "results": updated_results,
            "current_idx": idx + 1
        }

    # --- LOGIQUE CONDITIONNELLE ---

    def should_continue_after_extraction(self, state: AuditState):
        if state["error"] or not state["requirements"]:
            return "end"
        return "continue"

    def should_continue_processing(self, state: AuditState):
        if state["current_idx"] < len(state["requirements"]):
            return "loop"
        return "finish"

    def run(self, company_id: str, user_id: str, audit_id: str, checklist_path: str):
        """ Lance l'exécution asynchrone du graphe """
        initial_state = {
            "company_id": company_id,
            "user_id": user_id,
            "audit_id": audit_id,
            "checklist_path": checklist_path,
            "requirements": [],
            "current_idx": 0,
            "results": [],
            "error": None
        }
        
        final_state = self.workflow.invoke(initial_state)
        return final_state
