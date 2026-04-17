from typing import Annotated, List, TypedDict, Optional, Dict, Any
from langgraph.graph import StateGraph, START, END
from database.qdrant_db import qdrant_client_instance as vector_client
from utils.embedding_utils import EmbeddingService
from utils.llm_factory import llm_factory
from langchain_core.messages import HumanMessage, SystemMessage
from services.mcp.github_mcp_client import github_mcp_client
from services.upstash_redis_service import upstash_redis_service
import json
import re

# --- STRUCTURE DE L'ÉTAT AGENTIQUE BLOQUÉ (FIDÉLITÉ MAXIMALE) ---
class EvidenceState(TypedDict):
    # Identification
    company_id: str
    user_id: str
    audit_id: str
    requirement: str
    
    # Inférence Métier (Grounding)
    audit_theme: str
    control_objective: str
    evidence_nature: str # 'documentary', 'operational', 'technical'
    
    # Stratégie & Tactique
    current_strategy: str # 'document_first', 'gap_first', 'execution_evidence_first', 'absence_confirmation_mode', 'hybrid_document_technical'
    tool_plan: List[str]
    queries: List[str]
    queries_used: List[str] # Historique cumulé des requêtes
    reasoning_trace: List[dict] # Format décisionnel compact
    
    # Collecte
    current_iteration: int
    max_iterations: int
    retrieved_candidates: List[dict]
    selected_candidate: Optional[dict]
    result_quality: str # 'none'|'uncertain'|'declarative'|'partial'|'demonstrated'
    is_from_cache: bool # Si la source principale vient de Redis
    
    # Décision
    next_action: str # 'continue'|'finalize'
    action_reason: str
    why_stopped: str
    fidelity_score: float # Score de grounding pur (0-1)
    confidence_in_selection: str # 'low'|'medium'|'high'
    uncertainty_level: str # 'low'|'medium'|'high'
    
    # Résultats
    coverage_score: float
    compliance_status: str
    finding_type: str
    mastery_level: str
    justification: str
    explanation_payload: Dict[str, Any]
    error: Optional[str]

# --- AGENT ÉVIDENCE MAPPER (VERSION FIDÉLITÉ & GROUNDING) ---
class EvidenceMapper:
    def __init__(self):
        self.llm = llm_factory.get_llm("evidence_mapper")
        self.workflow = self._create_graph()

    def _create_graph(self):
        """ Orchestration avec Gating technique et Contrôle de Fidélité """
        workflow = StateGraph(EvidenceState)

        workflow.add_node("analyze_requirement", self.node_analyzer)
        workflow.add_node("decide_strategy", self.node_strategy_planner)
        workflow.add_node("execute_tool_plan", self.node_executor)
        workflow.add_node("verify_fidelity", self.node_fidelity_check) # Nouveau nœud de contrôle
        workflow.add_node("decide_next_action", self.node_reflector)
        
        workflow.add_node("select_evidence", self.node_selector)
        workflow.add_node("evaluate_final", self.node_evaluator)

        workflow.add_edge(START, "analyze_requirement")
        workflow.add_edge("analyze_requirement", "decide_strategy")
        workflow.add_edge("decide_strategy", "execute_tool_plan")
        workflow.add_edge("execute_tool_plan", "verify_fidelity")
        workflow.add_edge("verify_fidelity", "decide_next_action")

        workflow.add_conditional_edges(
            "decide_next_action",
            self.router_workflow,
            {
                "continue": "decide_strategy",
                "finalize": "select_evidence"
            }
        )

        workflow.add_edge("select_evidence", "evaluate_final")
        workflow.add_edge("evaluate_final", END)

        return workflow.compile()

    # --- NŒUDS AGENTIQUES DURCIS ---

    def node_analyzer(self, state: EvidenceState):
        """ Étape 1 : Analyse de la checklist et définition de la preuve cible """
        print(f"🧠 [EvidenceMapper] Node: ChecklistAnalyzer")
        prompt = f"""
        Tâche : Agir en tant qu'Auditeur Interne utilisant une Checklist.
        Exigence : "{state['requirement']}"
        
        RÈGLES :
        - Définis UNIQUEMENT le fait précis à vérifier (la preuve recherchée).
        - Pas d'interprétation globale.
        - Pas de mélange thématique.

        Réponds uniquement en JSON :
        {{
            "audit_theme": "Thème",
            "control_objective": "Preuve spécifique recherchée (ex: Présence d'un calendrier de revues)",
            "evidence_nature": "documentary|operational",
            "strategy": "document_first"
        }}
        """
        try:
            res = self.llm.invoke([HumanMessage(content=prompt)])
            data = self._parse_json(res.content)
            return {
                "audit_theme": data.get("audit_theme", "Opérations"),
                "control_objective": data.get("control_objective", state['requirement'][:100]),
                "evidence_nature": data.get("evidence_nature", "documentary"),
                "current_strategy": data.get("strategy", "document_first"),
                "reasoning_trace": [],
                "queries_used": [],
                "current_iteration": 0,
                "max_iterations": 2, # Redescendu à 2 pour éviter la dispersion
                "retrieved_candidates": [],
                "result_quality": "none",
                "is_from_cache": False
            }
        except Exception as e:
            return {"error": str(e), "audit_theme": "Opérations", "control_objective": "Erreur d'analyse initiale"}

    def node_strategy_planner(self, state: EvidenceState):
        """ Étape 2 : Planification de la recherche (Mots-clés cibles) """
        print(f"🎯 [EvidenceMapper] Node: ChecklistPlanner")
        
        prompt = f"""
        Preuve recherchée : "{state['control_objective']}"
        
        Génère 2 ou 3 mots-clés de recherche précis pour trouver cette preuve exacte dans les documents.
        Format : JSON.
        {{
            "tool_plan": ["redis_upstash", "qdrant_semantic"],
            "queries": ["motclé1 motclé2"]
        }}
        """
        try:
            res = self.llm.invoke([HumanMessage(content=prompt)])
            data = self._parse_json(res.content)
            return {
                "tool_plan": data.get("tool_plan", ["redis_upstash"]),
                "queries": data.get("queries", [state["control_objective"][:50]]),
                "action_reason": "recherche de preuve spécifique"
            }
        except:
            return {"tool_plan": ["redis_upstash"], "queries": [state["control_objective"][:50]]}

    def node_executor(self, state: EvidenceState):
        """ Étape 3 : Exécution multi-sources avec marquage de provenance """
        print(f"🔧 [EvidenceMapper] Node: Executor")
        candidates = state.get("retrieved_candidates", [])
        seen_texts = {c["text"] for c in candidates}
        current_queries = state.get("queries", [])
        all_queries = state.get("queries_used", []) + current_queries
        
        is_redis_used = False
        
        for tool in state["tool_plan"]:
            if tool == "qdrant_semantic":
                for query in state["queries"]:
                    try:
                        query_vector = EmbeddingService.encode(query)
                        hits = vector_client.search_similar(
                            company_id=state["company_id"],
                            audit_id=state["audit_id"],
                            query_vector=query_vector.tolist(),
                            top_k=3
                        )
                        for hit in hits:
                            if hit["text"] not in seen_texts:
                                candidates.append({
                                    "text": hit["text"],
                                    "doc_name": hit["doc_name"],
                                    "source": "qdrant_raw",
                                    "score": hit["score"],
                                    "is_summarized": False
                                })
                                seen_texts.add(hit["text"])
                    except Exception as e:
                        print(f"❌ Erreur Qdrant : {e}")

            elif tool == "github_mcp":
                try:
                    tech = github_mcp_client.get_repo_security_config(state["company_id"])
                    if tech:
                        text = f"--- PREUVE TECHNIQUE (GITHUB) ---\n{json.dumps(tech, indent=2)}"
                        if text not in seen_texts:
                            candidates.append({
                                "text": text, 
                                "doc_name": "GitHub Config", 
                                "source": "technical_mcp", 
                                "score": 1.0,
                                "is_summarized": False
                            })
                            seen_texts.add(text)
                except: pass

            elif tool == "redis_upstash":
                try:
                    all_docs = upstash_redis_service.get_all_company_data(state["company_id"])
                    if all_docs:
                        is_redis_used = True
                    for doc in all_docs:
                        analysis_text = doc.get("analysis_text", "Sans texte.")
                        content = f"--- FICHIER : {doc.get('filename')} (Source Redis) ---\n"
                        content += f"ANALYSE QUALINIVA CC : {analysis_text}\n"
                        
                        if content not in seen_texts:
                            candidates.append({
                                "text": content,
                                "doc_name": doc.get('filename', 'Doc Redis'),
                                "source": "redis_cache",
                                "score": 0.9, # Score de base légèrement réduit pour marquer la source cache/résumée
                                "is_summarized": True
                            })
                            seen_texts.add(content)
                except Exception as e:
                    print(f"❌ Erreur Redis : {e}")

        return {
            "retrieved_candidates": candidates, 
            "queries_used": list(set(all_queries)),
            "current_iteration": state["current_iteration"] + 1,
            "is_from_cache": is_redis_used
        }

    def node_fidelity_check(self, state: EvidenceState):
        """ Étape 4 : Vérification de présence et détection de lacunes (Audit Équilibré) """
        print(f"✅ [EvidenceMapper] Node: PresenceCheck")
        candidates = state["retrieved_candidates"]
        if not candidates: return {"result_quality": "none", "fidelity_score": 0.0, "confidence_in_selection": "low"}

        context = "\n---\n".join([c['text'][:500] for c in candidates[-2:]])
        prompt = f"""
        Preuve recherchée : "{state['control_objective']}"
        Extraits trouvés : {context}
        
        Tâche : Déterminer la qualité de la preuve.
        
        ÉCHELLE :
        - none : AUCUNE mention, aucun document, aucune trace.
        - declarative : Politique ou description de processus trouvée (Intention).
        - partial : Procédure présente ou description avec quelques éléments de preuve mais incomplète.
        - demonstrated : Preuve directe, datée et traçable.
        
        RÈGLE : Si une politique ou une procédure est présente mais manque de preuves d'exécution, la qualité est 'declarative' ou 'partial', JAMAIS 'none'.

        Réponds en JSON : {{ "quality": "none|declarative|partial|demonstrated", "confidence": "low|medium|high", "score": 0.0 }}
        """
        try:
            res = self.llm.invoke([HumanMessage(content=prompt)])
            data = self._parse_json(res.content)
            return {
                "result_quality": data.get("quality", "none"),
                "fidelity_score": data.get("score", 0.0),
                "confidence_in_selection": data.get("confidence", "low")
            }
        except:
            return {"result_quality": "none", "fidelity_score": 0.0, "confidence_in_selection": "low"}

    def node_reflector(self, state: EvidenceState):
        """ Étape 5 : Réflexion stratégique (Décision compacte) """
        print(f"🔎 [EvidenceMapper] Node: Reflector")
        
        action = "finalize"
        stop_reason = "process_completed"
        
        if state["result_quality"] == "demonstrated" and state["fidelity_score"] > 0.8:
            action = "finalize"
            stop_reason = "evidence_demonstrated"
        elif state["current_iteration"] < state["max_iterations"]:
            if state["result_quality"] in ["none", "uncertain", "declarative"]:
                action = "continue"
                stop_reason = "seeking_better_evidence"
            elif state["result_quality"] == "partial" and state["confidence_in_selection"] == "low":
                action = "continue"
                stop_reason = "seeking_depth"
            else:
                action = "finalize"
                stop_reason = "quality_sufficient"
        else:
            action = "finalize"
            stop_reason = "max_iterations_reached"

        trace_entry = {
            "step": state["current_iteration"],
            "strategy": state["current_strategy"],
            "tools": state["tool_plan"],
            "outcome": state.get("action_reason", "search_executed")
        }
        
        return {
            "next_action": action,
            "why_stopped": stop_reason,
            "reasoning_trace": state["reasoning_trace"] + [trace_entry]
        }

    def node_selector(self, state: EvidenceState):
        """ Étape 6 : Sélection multi-sources et comparaison de pertinence """
        print(f"🎯 [EvidenceMapper] Node: Selector")
        candidates = state["retrieved_candidates"]
        if not candidates: return {"selected_candidate": None}

        # On limite pour éviter de surcharger le contexte du sélecteur
        unique_candidates = []
        seen = set()
        for c in reversed(candidates): # On préfère les plus récents (souvent plus précis)
            if c["text"][:200] not in seen:
                unique_candidates.append(c)
                seen.add(c["text"][:200])

        prompt = f"""
        Objectif : "{state['control_objective']}"
        Compare ces {len(unique_candidates)} sources et choisis la plus probante.
        
        CANDIDATS :
        {json.dumps([{ "idx": i, "doc": c["doc_name"], "source": c["source"], "snippet": c["text"][:300]} for i, c in enumerate(unique_candidates)], indent=2)}
        
        RÈGLES :
        - Évite le biais de sélection systématique du même document.
        - Si plusieurs sources se complètent, choisis celle qui contient la PREUVE RÉELLE (faits, dates, noms, chiffres) plutôt que l'intention.
        - Si la source Redis est trop vague par rapport à un extrait brut Qdrant, privilégie le brut.

        JSON : {{ "index": X, "reason": "Pourquoi ce choix précis ?" }}
        """
        try:
            res = self.llm.invoke([HumanMessage(content=prompt)])
            data = self._parse_json(res.content)
            idx = data.get("index", 0)
            selected = unique_candidates[idx] if 0 <= idx < len(unique_candidates) else unique_candidates[0]
            selected["why_selected"] = data.get("reason", "Meilleure correspondance factuelle.")
            return {"selected_candidate": selected}
        except:
            return {"selected_candidate": unique_candidates[0]}

    def node_evaluator(self, state: EvidenceState):
        """ Étape 7 : AuditJudgmentNode (Raisonnement d'Audit Autonome) """
        print(f"🏁 [EvidenceMapper] Node: AuditJudgment")
        
        selected = state.get("selected_candidate")
        quality = state.get("result_quality", "none")
        
        prompt = f"""
        Rôle : Auditeur Interne Senior Expérimenté (Evidence Judge).
        
        Tâche : Réaliser une analyse critique de la valeur probante des éléments retrouvés pour conclure de manière autonome.
        
        CONTEXTE D'AUDIT :
        - Objectif de contrôle : "{state['control_objective']}"
        - Élément source sélectionné : "{selected['text'] if selected else "AUCUNE PREUVE RETROUVÉE"}"
        
        VOTRE MISSION (RAISONNEMENT D'AUDITEUR) :
        Vous devez rejeter toute logique mécanique. Votre conclusion doit découler d'une confrontation intellectuelle :
        1. Preuve IDÉALE : Quelle serait la preuve indiscutable pour cette exigence ?
        2. Analyse RÉELLE : Qu'avons-nous réellement dans les mains ? (Distinguer document de preuve d'action).
        3. Valeur PROBANTE : Cette preuve est-elle crédible et défendable ? Démontre-t-elle le contrôle ou juste l'intention ?
        4. Analyse des GAPS : Quels sont les manques structurels empêchant une évaluation 'conforme' ?
        
        DÉCISION AUTONOME :
        Tranchez entre CONFORME, PARTIEL ou NON CONFORME en fonction de la force de la preuve. Ne vous réfugiez pas dans 'PARTIAL' par défaut si la preuve est inexistante ou non probante.
        
        Réponds en JSON :
        {{
            "audit_reasoning": {{
                "expected_id_proof": "description de la preuve idéale",
                "found_evidence_summary": "faits identifiés",
                "probative_value_assessment": "Analyse critique de la force de la preuve",
                "evidence_gaps": ["gap 1", "gap 2"],
                "audit_thought_process": "Démonstration logique menant à la décision",
                "final_judgment_rationale": "Pourquoi cette conclusion est la plus défendable ?"
            }},
            "conclusion": {{
                "status": "conforme|partiel|non conforme",
                "finding": "conform|ofi|minor_nc|major_nc",
                "score": 0.0,
                "justification_summary": "Conclusion professionnelle percutante."
            }}
        }}
        """
        try:
            res = self.llm.invoke([HumanMessage(content=prompt)])
            data = self._parse_json(res.content)
            
            reasoning = data.get("audit_reasoning", {})
            conclusion = data.get("conclusion", {})
            
            raw_score = float(conclusion.get("score", 0.0))
            if raw_score > 1.0: raw_score = raw_score / 100.0 # Toujours normalisé
            
            status_map = {
                "conforme": "conform",
                "partiel": "partial",
                "non conforme": "non_conform"
            }
            ui_status = status_map.get(conclusion.get("status", "non conforme"), "non_conform")
            
            explanation = {
                "audit_theme": state.get("audit_theme", "Analyse d'Audit"),
                "control_objective": state["control_objective"],
                "reasoning": reasoning,
                "probative_value": reasoning.get("probative_value_assessment", "Non évaluée"),
                "gaps": reasoning.get("evidence_gaps", []),
                "thought_process": reasoning.get("audit_thought_process", ""),
                "iterations": state["current_iteration"],
                "strategy": state["current_strategy"]
            }

            return {
                "compliance_status": ui_status,
                "finding_type": conclusion.get("finding", "major_nc"),
                "coverage_score": raw_score,
                "mastery_level": "demonstrated" if ui_status == "conform" else ("partial" if ui_status == "partial" else "none"),
                "justification": conclusion.get("justification_summary", "Analyse d'audit effectuée."),
                "explanation_payload": explanation,
                "selected_candidate": selected
            }
        except:
            return self._format_empty_final(state)

    # --- ROUTER & HELPERS ---

    def router_workflow(self, state: EvidenceState):
        return state["next_action"]

    def _parse_json(self, content: str) -> dict:
        content = re.sub(r"```json|```", "", content.strip()).strip()
        try: return json.loads(content)
        except:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try: return json.loads(match.group())
                except: pass
        return {}

    def _format_empty_final(self, state: EvidenceState):
        return {
            "best_document": "AUCUNE PREUVE CRÉDIBLE",
            "compliance_status": "non_conform",
            "finding_type": "major_nc",
            "coverage_score": 0.0,
            "mastery_level": "none",
            "justification": "L'absence de preuve crédible a été confirmée après analyse et recherche multi-stratégique.",
            "explanation_payload": {
                "audit_theme": state.get("audit_theme", "Opérations"),
                "control_objective": state.get("control_objective", "Recherche de preuve"),
                "strategy_selected": state.get("current_strategy", "gap_search"),
                "queries_used": state.get("queries_used", []),
                "iterations": state.get("current_iteration", 0),
                "mastery_level": "none",
                "confidence_in_selection": "medium",
                "reasoning_trace": state.get("reasoning_trace", []),
                "why_stopped": state.get("why_stopped", "Aucune preuve trouvée")
            }
        }

    def _format_error_state(self, state: EvidenceState, error_msg: str):
        return {
            "best_document": "ERREUR SYSTÈME",
            "compliance_status": "non_conform",
            "finding_type": "major_nc",
            "coverage_score": 0.0,
            "mastery_level": "none",
            "justification": f"ERREUR CRITIQUE : {error_msg}. L'agent n'a pas pu aboutir à une conclusion fiable.",
            "explanation_payload": {"status": "failed", "reason": error_msg, "mastery_level": "none"}
        }

    def map_evidence(self, company_id, audit_id, requirement_desc, requirement_context=None):
        initial_state = {
            "company_id": company_id, "audit_id": audit_id, "requirement": requirement_desc,
            "current_iteration": 0, "max_iterations": 2, "retrieved_candidates": [], "reasoning_trace": [], 
            "error": None, "current_strategy": "document_first", "result_quality": "none"
        }
        try:
            final_res = self.workflow.invoke(initial_state)
            selected = final_res.get("selected_candidate")
            return {
                "best_document": selected["doc_name"] if selected else "AUCUN",
                "best_text": selected["text"] if selected else "Aucune trace.",
                "similarity_score": selected.get("score", 0.0) if selected else 0.0,
                "coverage_score": final_res.get("coverage_score", 0.0),
                "compliance_status": final_res.get("compliance_status", "non_conform"),
                "finding_type": final_res.get("finding_type", "major_nc"),
                "mastery_level": final_res.get("mastery_level", "none"),
                "justification": final_res.get("justification", ""),
                "explanation_payload": final_res.get("explanation_payload", {}),
                "evidence_source": selected.get("source", "document") if selected else "none",
                "technical_evidence_used": selected.get("source") == "technical" if selected else False,
            }
        except Exception as e:
            return self._format_error_state(initial_state, str(e))