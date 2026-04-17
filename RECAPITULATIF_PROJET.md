# 🛡️ Projet QualiNova AI - Module Evidence Mapping

## 📋 Présentation du Projet
**QualiNova AI** est une plateforme d'audit interne augmentée par l'Intelligence Artificielle. Le module **Evidence Mapping** a pour objectif d'automatiser le rapprochement entre les exigences d'audit (checklists ISO, réglementations) et les preuves réelles stockées sous forme documentaire ou technique.

---

## 🚀 Fonctionnalités Clés

### 1. 📂 Ingestion Centralisée (Flux Upstash Redis)
- **Flux Direct** : Récupération des données d'audit et analyses pré-calculées directement depuis Upstash Redis.
- **Zéro Ingestion Locale** : Suppression de la nécessité de découper et vectoriser des documents locaux pour les preuves d'audit.
- **Analyses Consolidées** : Utilisation du champ 'analysis' comme source de vérité Grounding pour l'agent.

### 2. 📋 Gestionnaire de Checklist
- **Extraction Intelligente** : Analyse de fichiers Excel ou PDF complexes pour en extraire une liste structurée d'exigences d'audit.
- **Normalisation** : Conversion des données hétérogènes en un format standard pour l'agent IA.

### 3. 🔥 Moteur de Mapping (Evidence Mapper)
- **Orchestration LangGraph** : Workflow multi-étapes gérant la recherche de preuves, l'analyse critique et la synthèse.
- **Score de Couverture** : Évaluation quantitative (0-100%) du niveau de preuve trouvé pour chaque exigence.
- **Classification ISO** :
    - **Statut** : Conforme, Partiel, Non-Conforme.
    - **Type de Constat** : Observation, Amélioration, NC Mineure, NC Majeure.
    - **Niveau de Risque** : Faible, Moyen, Élevé, Critique.
    - **Force de la Preuve** : Faible, Moyenne, Forte.

### 4. 🌐 Audit Hybride (Intégration MCP)
- **GitHub / GitLab MCP Client** : Capacité de l'agent à interroger directement les dépôts de code pour vérifier des configurations techniques (ex: politiques de branche, secrets branchés, règles de sécurité) en temps réel.
- **Détection de Conflits** : Identification automatique des écarts entre la procédure écrite (document) et la réalité technique (code/config).

---

## 🛠️ Stack Technique

- **Interface** : Streamlit (Look premium, Glassmorphism).
- **Cerveau IA** : LangChain & LangGraph.
- **Modèles (LLM)** : Approche multi-fournisseur (OpenAI, Groq, HuggingFace) avec **failover automatique**.
- **Bases de Données** : 
    - **Upstash Redis** : Stockage centralisé des analyses d'audit (Source de vérité).
    - **Qdrant** : Reste disponible pour le support documentaire optionnel.
- **MCP (Model Context Protocol)** : Connecteurs sécurisés pour GitHub/GitLab.

---

## 🛠️ Travaux Réalisés Récemment

1.  **Robustesse de l'Agent** : Refonte du prompt de l'Evidence Mapper pour éliminer les preuves vagues et imposer une rigueur d'auditeur certifié.
2.  **Failover LLM Cascade** : Mise en place d'une `LLMFactory` capable de basculer automatiquement entre Groq, HuggingFace et des modèles locaux en cas de saturation API ou d'erreur.
3.  **Intégration Technique (MCP)** : Développement des clients GitHub/GitLab pour permettre une validation technique automatique au-delà des simples documents.
4.  **Scoring ISO-Compliant** : Implémentation d'une logique de scoring stricte incluant la détection automatique du niveau de risque et de la force de preuve.
5.  **Interface Utilisateur** : Création d'un dashboard interactif permettant de visualiser les résultats de l'audit avec des métriques claires.

---

## 📈 Prochaines Étapes
- Génération automatique de rapports d'audit au format PDF/Word.
- Dashboard de pilotage multi-audit à l'échelle de l'entreprise.
- Intégration de nouveaux connecteurs MCP (Azure, AWS, JIRA).
