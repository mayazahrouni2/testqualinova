# 🛡️ Projet QualiNova : Rapport de Développement - Module Evidence Mapping

Ce document retrace les étapes clés, les défis techniques résolus et l'architecture finale du moteur d'audit intelligent développé pour QualiNova.

## 1. 📋 Présentation du Module
Le module **Evidence Mapping** a pour mission de réaliser le rapprochement automatique entre des exigences d'audit (ex: ISO 9001/27001) et des preuves réelles extraites de documents ou de configurations techniques.

---

## 2. 🔧 Résolution des Problématiques d'Infrastructure
Au démarrage, plusieurs obstacles bloquaient l'accès aux LLM via l'infrastructure **Esprit Token Factory** :

- **Correction SSL/TLS** : Mise en place d'un client `httpx` avec `verify=False` pour contourner les restrictions de certificats du réseau interne.
- **Normalisation de l'API OpenAI** : Correction de la `base_url` (ajout du suffixe `/v1`) pour assurer la compatibilité avec la librairie OpenAI officielle et LangChain.
- **Failover & Modèles** : Configuration d'une `llm_factory` robuste capable de basculer entre les modèles **Llama-3.1 8B** (rapide) et **70B** (raisonnement complexe).

---

## 3. 🧠 Architecture Agentique (Le "Cœur" du Système)
La plus grande évolution a consisté à passer d'un simple RAG (Search & Answer) à un véritable **Agent d'Audit** orchestré par **LangGraph**.

### A. Le Concept de "Grounding Agent"
L'agent est conçu pour être "ancré" dans la réalité documentaire. Il suit un workflow rigoureux :
1.  **Analyse Métier** : Extraction de l'objectif de contrôle réel masqué derrière l'exigence.
2.  **Stratégie de Recherche** : Génération de requêtes ciblées pour Qdrant.
3.  **Vérification de Fidélité** : Une étape d'auto-critique où l'IA score la qualité de la preuve trouvée sur une échelle de `none` à `demonstrated`.

### B. Le Pivot Stratégique (Agentic Pivot)
Contrairement à un bot classique, si l'Evidence Mapper ne trouve rien au premier essai, il ne s'arrête pas. Il analyse son échec et **pivote** vers une nouvelle stratégie :
- **Document First** : Recherche sémantique de preuves.
- **Gap Analysis** : Si aucune preuve n'est trouvée, il cherche activement des traces d'absence ou des exceptions.
- **Absence Confirmation** : Si plusieurs itérations échouent, il conclut formellement à une non-conformité avec une justification robuste.

---

## 4. 📊 Transparence et Professionnalisme
Pour répondre aux exigences d'un auditeur humain, nous avons éliminé les champs "N/A" et les boîtes noires :

- **Mastery Level Obligatoire** : Chaque résultat exprime son niveau de maîtrise (`none`, `partial`, `demonstrated`).
- **Traçabilité des Requêtes** : L'interface affiche les requêtes exactes envoyées à la base vectorielle.
- **Reasoning Trace** : L'historique décisionnel de l'agent est affiché étape par étape, montrant son cheminement logique.
- **Confiance & Incertitude** : Ajout de scores de confiance pour identifier les cas nécessitant une revue humaine.

---

## 5. 🛠️ Stack Technique Finalisé
- **Framework** : LangChain / LangGraph.
- **Interface** : Streamlit (Look premium, dashboard interactif).
- **Base Vectorielle** : Qdrant (stockage des fragments documentaires).
- **Embeddings** : BAAI/bge-m3.
- **LLM** : Meta Llama-3.1 (via Esprit Token Factory).

---

## 6. 🚦 Workflow d'Utilisation Standard
1.  **Ingestion** : L'utilisateur uploade les manuels et procédures (PDF, Word, etc.).
2.  **Extraction** : L'IA structure la checklist d'audit à partir d'un fichier Excel ou texte.
3.  **Mapping** : L'agent LangGraph boucle sur chaque exigence, cherche des preuves, pivote stratégiquement si besoin, et rend un verdict d'audit détaillé.

---
*Ce document a été généré pour servir de guide technique et fonctionnel pour le projet QualiNova AI.*
