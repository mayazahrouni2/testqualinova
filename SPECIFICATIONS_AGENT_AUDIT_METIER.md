# 🛡️ Spécifications Fonctionnelles : L'Agent Evidence Mapper QualiNova

Ce document décrit l'intelligence métier et le fonctionnement interne de l'agent QualiNova, conçu pour agir comme un auditeur certifié senior (ISO 9001, 27001, 14001, etc.).

---

## 1. Vision Métier : Le "Rapprochement de Preuves"
L'Evidence Mapper ne se contente pas de chercher des documents. Il simule le raisonnement d'un auditeur humain qui doit valider si une intention (Procédure/Exigence) est réellement appliquée (Preuve opérationnelle). 

Son but ultime est de fournir un verdict impartial, sans jamais extrapoler ni inventer de contenu.

---

## 2. Le Cycle de Vie de l'Agent (Workflow Décisionnel)

L'agent opère selon un cycle itératif de 7 étapes clés, orchestrées par une logique de graphe cyclique (**LangGraph**) :

### Étape 1 : Analyse de l'Objectif de Contrôle
Au lieu de chercher bêtement l'intitulé de l'exigence, l'agent extrait l'**intention métier**.
*   *Fonctionnalité* : Le LLM décompose l'exigence complexe en un "Objectif de Contrôle" simple (ex: "Trouver la preuve de la revue de direction annuelle").

### Étape 2 : Planification Stratégique & Tactique
L'IA n'est pas figée. Elle choisit ses outils selon le succès des étapes précédentes :
*   **Mode Sémantique** : Recherche par le sens pour trouver des preuves directes.
*   **Mode Gap Analysis** : Recherche active de l'absence de documents obligatoires ou de contradictions.
*   **Mode Absence Confirmation** : Stratégie de dernier recours pour valider qu'aucune preuve n'existe réellement avant de déclarer une Non-Conformité (NC) majeure.

### Étape 3 : Récolte des Faits (Harvesting)
L'IA génère ses propres requêtes de recherche (2 à 4 mots clés) et interroge la base vectorielle (**Qdrant**).
*   *Détail* : Les requêtes sont optimisées pour maximiser la pertinence sémantique.

### Étape 4 : Le "Fidelity Check" (Garde-fou Anti-Hallucination)
C'est le cœur du système de confiance. L'agent évalue la "qualité" de chaque fragment trouvé :
*   **Démontré** : Le texte apporte une preuve concrète (ex: "Le planning a été validé le 12/01").
*   **Déclaratif** : Simple mention dans une procédure sans preuve d'application ("Le planning doit être validé").
*   **Néant** : Hors sujet total.

### Étape 5 : Pivot de Stratégie (Intelligent Pivot)
Si la qualité est jugée insuffisante (`declarative` ou `none`), l'agent **change sa stratégie**. Il passe par exemple d'une recherche de "document" à une recherche de "lacune" pour être certain de son verdict.

### Étape 6 : Arbitrage et Sélection
L'agent compare tous les candidats récoltés lors des itérations et sélectionne celui qui possède le meilleur score de fidélité objective.

### Étape 7 : Verdict Final et Notation ISO
L'agent produit le résultat final structuré selon les standards d'audit :
*   **Statut de Conformité** (Conforme, Partiel, Non-Conforme).
*   **Type de Constat** (Majeure, Mineure, Amélioration, Point Fort).
*   **Niveau de Maîtrise** (Nul, Partiel, Démontré).

---

## 4. 🛠️ Moteur de Détection et Traitement des Non-Conformités (NC)

L'une des forces majeures de l'agent est sa capacité à qualifier précisément les écarts de conformité de manière autonome.

### A. La Stratégie "Gap Search" (Preuve par l'Absence)
Contrairement à un moteur de recherche classique qui s'arrête s'il ne trouve rien, l'agent QualiNova active le mode **Gap Analysis** :
1.  **Recherche Active d'Écart** : L'agent génère des requêtes pour trouver des documents qui *devraient* exister mais ne sont pas là.
2.  **Confirmation d'Absence** : Si après pivotement stratégique, aucune preuve crédible ne remonte, l'agent conclut à une omission structurelle.

### B. Grille de Classification Professionnelle
L'agent utilise les standards ISO pour catégoriser ses constats :

| Typologie | Critère de l'Agent | Impact Audit |
| :--- | :--- | :--- |
| **Major NC (❌)** | Absence totale d'un processus obligatoire ou preuve critique manquante. | Non-conformité Majeure |
| **Minor NC (⚠️)** | Preuve identifiée mais incomplète, périmée ou non signée/validée. | Non-conformité Mineure |
| **OFI (Opportunity for Improvement)** | La preuve existe, mais elle est faible ou la pratique est risquée. | Observation / Piste d'amélioration |
| **Strong Point (⭐)** | Preuves multiples, croisées et parfaitement documentées. | Point Fort |

### C. Analyse de Risque et Justification
Pour chaque NC identifiée, l'agent calcule :
- **Le Niveau de Risque** (Faible, Moyen, Élevé, Critique) basé sur l'importance de l'exigence dans le référentiel.
- **La Justification de l'Écart** : Une explication textuelle listant précisément les "Éléments Manquants" (ex: date de révision absente, manque de signature de la direction).

---

## 5. Fonctionnalités de Transparence "Auditor-Ready"

Pour qu'un auditeur humain ait confiance en l'IA, l'agent expose ses mécanismes internes dans l'interface finale :
- **Queries Log** : Liste des vraies requêtes de recherche utilisées.
- **Reasoning Trace** : Historique complet des décisions stratégiques étape par étape.
- **Confidence Meter** : Score de confiance sur la sélection finale.
- **Justification Factuelle** : L'agent a interdiction d'inventer ; il doit justifier chaque mot par une citation précise.

---

## 4. Capacités Multimodales et Ingestion
L'agent s'appuie sur une pipeline d'ingestion robuste :
- **Support Multi-format** : PDF, Word, Excel et Images (OCR).
- **Enrichissement de Métadonnées** : Chaque fragment de texte (chunk) est marqué avec le nom du document, la date détectée et les responsables cités pour renforcer le "Grounding".

---

## 5. Résumé de la Stack Agentique
- **Cerveau** : LangGraph (Workflow cyclique et décisionnel).
- **Mémoire** : Qdrant (Base vectorielle avec recherche sémantique).
- **Modèle** : Meta Llama-3.1 70B (Expert métier et raisonnement critique).
- **Interface** : Streamlit (Dashboard Premium orienté métier).
