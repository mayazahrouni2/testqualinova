import os
# Désactivation du surveillance de fichiers Streamlit pour éviter les crashs avec Torch 2.4+
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

import streamlit as st
import io
import os
import tempfile
from utils.file_extractor import FileExtractor
from utils.embedding_utils import EmbeddingService
from agents.checklist_manager import ChecklistManager
from agents.evidence_mapper import EvidenceMapper
from orchestrator.langgraph_orchestrator import LangGraphOrchestrator
from database.qdrant_db import qdrant_client_instance as vector_client

# App reloaded with Upstash Redis support

# Titre Premium et Style
st.set_page_config(page_title="QualiNova AI - Evidence Mapper", layout="wide", page_icon="🛡️")

# Custom CSS pour un look moderne (Glassmorphism + Gradients)
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        border: none;
    }
    .stMetric {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ QualiNova - Module Evidence Mapping")
st.markdown("---")

# Variables de session
if "document_chunks" not in st.session_state:
    st.session_state.document_chunks = []
if "checklist_reqs" not in st.session_state:
    st.session_state.checklist_reqs = []
if "user_session" not in st.session_state:
    st.session_state.user_session = None

def save_uploaded_file(uploaded_file):
    """ Sauvegarde temporaire du fichier pour traitement par les librairies natives """
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name

# Sidebar de Navigation
st.sidebar.image("https://via.placeholder.com/150", caption="QualiNova AI Engine")
st.sidebar.markdown("### 🗺️ Pilotage Evidence Mapping")

# Gestion d'un ID de session (pour séparer les tests/documents)
st.sidebar.markdown("### 🔐 Profil Utilisateur (Multi-tenant)")
if st.session_state.user_session is None:
    st.warning("Veuillez vous authentifier pour accéder à l'application.")
    with st.sidebar.form("auth_form"):
        email = st.text_input("Email :")
        company_name = st.text_input("Nom de l'entreprise (Company) :")
        submit_auth = st.form_submit_button("Se connecter")
        
        if submit_auth:
            import re
            def normalize_id(text):
                return re.sub(r'[^a-z0-9]', '_', str(text).lower().strip()).strip('_')
            
            st.session_state.user_session = {
                "user_id": f"u_{normalize_id(email.split('@')[0])}" if email else "u_unknown",
                "email": email,
                "company_name": company_name,
                "company_id": normalize_id(company_name) if company_name else "default_corp"
            }
            st.rerun()
    st.stop()
else:
    user = st.session_state.user_session
    st.sidebar.success(f"🏢 Entreprise : {user['company_name']} ({user['company_id']})")
    st.sidebar.write(f"👤 {user['email']}")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.user_session = None
        st.rerun()

st.sidebar.markdown("---")
audit_id = st.sidebar.text_input("ID de Mission d'Audit :", value="audit_001", help="Changez cet ID pour tester de nouveaux documents sans les mélanger avec les anciens.")

if st.sidebar.button("🗑️ Vider cet Audit"):
    try:
        vector_client.delete_document(st.session_state.user_session["company_id"], audit_id)
        st.sidebar.success(f"Documents de l'audit '{audit_id}' supprimés !")
    except Exception as e:
        st.sidebar.error(f"Erreur : {e}")

selection = st.sidebar.radio("Navigation Phases :", [
    "📦 1. Données Source (Upstash Redis)",
    "📋 2. Analyse de Checklist",
    "🔥 3. Mapping de Preuves"
])
# Phase 1 : Visualisation Redis
if selection.startswith("📦"):
    st.header("📦 Données Source (Upstash Redis)")
    st.info("Flux sans ingestion locale : Les preuves d'audit sont récupérées directement depuis Upstash.")
    
    st.write(f"🏢 Action groupée pour l'entreprise **{user['company_name']}**")
    
    from services.upstash_redis_service import upstash_redis_service
    available_docs = upstash_redis_service.list_all_audits(user["company_id"])
    
    if available_docs:
        st.success(f"📂 {len(available_docs)} documents détectés pour cette entreprise dans Redis.")
        if st.button("🚀 SYNCHRONISER & CHARGER TOUTES LES DONNÉES", use_container_width=True, type="primary"):
            with st.spinner("Synchronisation Redis + Qdrant en cours..."):
                all_data = upstash_redis_service.get_all_company_data(user["company_id"])
                
                if all_data:
                    progress_text = st.empty()
                    progress_bar = st.progress(0)
                    total = len(all_data)
                    
                    for i, doc in enumerate(all_data):
                        doc_name = doc.get('filename', f'Doc_{i}')
                        progress_text.text(f"📥 Indexation sémantique : {doc_name} ({i+1}/{total})")
                        
                        # Extraction texte
                        text_to_index = doc.get("analysis_text", "")
                        if text_to_index.strip():
                            chunks = []
                            words = text_to_index.split()
                            for j in range(0, len(words), 800):
                                chunk_text = " ".join(words[j:j + 800])
                                vector = EmbeddingService.encode(chunk_text).tolist()
                                chunks.append({
                                    "vector": vector,
                                    "text": chunk_text,
                                    "doc_name": doc_name
                                })
                            
                            if chunks:
                                vector_client.insert_chunks(
                                    company_id=user["company_id"],
                                    user_id=user["user_id"],
                                    audit_id=audit_id,
                                    chunks=chunks
                                )
                        
                        progress_bar.progress((i + 1) / total)
                    
                    st.success(f"✅ {total} documents synchronisés et indexés dans Qdrant !")
                    st.session_state.all_audit_data = all_data
                    progress_text.empty()
                    progress_bar.empty()
                else:
                    st.error("Aucune donnée disponible à synchroniser.")
    else:
        st.warning("Aucun document trouvé pour cette entreprise dans Redis.")
        st.info("Utilisez la section d'upload ci-dessous pour ajouter des analyses.")

    st.markdown("---")
    st.subheader("🔍 Testeur de Recherche Sémantique (Diagnostic)")
    with st.expander("🧪 Ouvrir le Laboratoire de Test"):
        st.write("Vérifiez ici que le 'chunking' et les 'embeddings' fonctionnent bien sur vos données.")
        test_query = st.text_input("Saisissez une question ou un concept à tester :", placeholder="Ex: Quelle est la politique de sauvegarde ?")
        if st.button("🧪 Lancer la Simulation"):
            if test_query:
                with st.spinner("Recherche vectorielle dans Qdrant..."):
                    from database.qdrant_db import qdrant_client_instance as vector_client
                    from utils.embedding_utils import EmbeddingService
                    
                    # 1. Vectorisation de la question
                    q_vector = EmbeddingService.encode(test_query).tolist()
                    
                    # 2. Recherche
                    hits = vector_client.search_similar(
                        company_id=user["company_id"],
                        audit_id="global", # On cherche partout pour le test
                        query_vector=q_vector,
                        top_k=3
                    )
                    
                    if hits:
                        st.success(f"🎯 {len(hits)} fragments trouvés dans votre corpus !")
                        for i, hit in enumerate(hits):
                            with st.container():
                                st.markdown(f"**📍 Fragment {i+1}** (Score: `{hit['score']:.3f}`) - Source: `{hit['doc_name']}`")
                                st.code(hit['text'][:1000] + ("..." if len(hit['text']) > 1000 else ""))
                    else:
                        st.warning("❌ Aucun fragment trouvé. Avez-vous cliqué sur 'SYNCHRONISER' plus haut ?")
            else:
                st.error("Veuillez saisir une question.")

    st.markdown("---")
    st.subheader("📤 Upload de données d'audit (Source Finale)")
    st.write("Importez directement votre JSON d'analyse consolidée pour cet audit.")
    
    uploaded_json = st.file_uploader("Fichier JSON d'analyse", type=["json"], key="redis_uploader")
    if uploaded_json is not None:
        if st.button("🚀 Pousser vers Upstash"):
            from services.upstash_redis_service import upstash_redis_service
            import json
            try:
                json_data = json.load(uploaded_json)
                key = upstash_redis_service.set_audit_data(user["company_id"], audit_id, json_data)
                st.success(f"✅ Document enregistré dans Redis !")
                
                # --- NOUVEAU : Indexation automatique dans Qdrant ---
                with st.spinner("Génération des embeddings et indexation Qdrant..."):
                    # Extraction du texte depuis le champ 'analysis' (qui peut être dict ou str)
                    analysis = json_data.get("analysis", "")
                    if isinstance(analysis, dict):
                        text_to_index = "\n".join([f"{k}: {v}" for k, v in analysis.items()])
                    else:
                        text_to_index = str(analysis)
                    
                    if text_to_index.strip():
                        # Chunking simple
                        chunks = []
                        max_chunk = 800
                        words = text_to_index.split()
                        for i in range(0, len(words), max_chunk):
                            chunk_text = " ".join(words[i:i + max_chunk])
                            if chunk_text:
                                vector = EmbeddingService.encode(chunk_text).tolist()
                                chunks.append({
                                    "vector": vector,
                                    "text": chunk_text,
                                    "doc_name": json_data.get("filename", "Upload_Redis")
                                })
                        
                        if chunks:
                            # Log Console pour le terminal
                            print(f"🔍 [DEBUG QDRANT] Upload de {len(chunks)} fragments pour company={user['company_id']}")
                            
                            vector_client.insert_chunks(
                                company_id=user["company_id"],
                                user_id=user["user_id"],
                                audit_id=audit_id,
                                chunks=chunks
                            )
                            st.info(f"🔍 [DEBUG QDRANT] {len(chunks)} fragments vectorisés et envoyés vers le Cloud.")
                            st.success(f"⚡ Indexation Qdrant terminée !")
                        else:
                            st.warning("⚠️ Aucun texte n'a pu être extrait pour Qdrant.")
                
                st.success(f"🎉 Processus complet terminé pour l'entreprise '{user['company_id']}'")
            except Exception as e:
                st.error(f"Erreur lors de l'upload : {e}")

    st.markdown("---")
    st.subheader("🗄️ Audits Disponibles dans Redis")
    from services.upstash_redis_service import upstash_redis_service
    existing_audits = upstash_redis_service.list_all_audits(user["company_id"] if "user_session" in st.session_state and st.session_state.user_session else None)
    if existing_audits:
        cols = st.columns(len(existing_audits) if len(existing_audits) < 4 else 4)
        for i, aid in enumerate(existing_audits):
            with cols[i % 4]:
                if st.button(f"📂 {aid}", key=f"btn_{aid}"):
                    # On ne peut pas changer audit_id directement via session state car c'est un input sidebar
                    # Mais on peut l'indiquer à l'utilisateur
                    st.info(f"Pour utiliser **{aid}**, changez l'ID dans la barre latérale.")
    else:
        st.write("Aucun audit trouvé dans Redis.")

# Phase 2 : Checklist Manager
elif selection.startswith("📋"):
    st.header("2️⃣ Agent Checklist : Extraction des Exigences")
    st.write("Cet Agent convertit vos fichiers de checklist en un format structuré compréhensible par l'IA.")
    f = st.file_uploader("Checklist d'audit (.xlsx, .pdf, .docx)", type=["xlsx", "pdf", "docx"])
    
    if st.button("🤖 Structurer la Checklist"):
        if f:
            tmp_path = save_uploaded_file(f)
            try:
                manager = ChecklistManager()
                reqs = manager.process_checklist(tmp_path)
                
                st.session_state.checklist_reqs = reqs
                if reqs:
                    st.success(f"🎉 {len(reqs)} exigences identifiées !")
                    st.dataframe(reqs, use_container_width=True)
                else:
                    st.error("Échec de l'extraction des exigences.")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            st.warning("Uploadez une checklist !")

# Phase 3 : Orchestrateur Evidence Mapper (LangGraph)
elif selection.startswith("🔥"):
    st.header("🛜 Mapping de Preuves Automatisé")
    st.markdown("Flux Direct : L'Agent utilise les données centralisées d'Upstash Redis (Grounding sans ingestion locale).")
    
    f_check = st.file_uploader("Sélectionnez la Checklist Source", type=["xlsx", "pdf", "docx"])
    
    if st.button("🚀 LANCER LE MAPPING"):
        if not f_check:
            st.warning("Uploadez la checklist pour commencer.")
        else:
            tmp_path = save_uploaded_file(f_check)
            try:
                orchestrator = LangGraphOrchestrator()
                user = st.session_state.user_session
                
                with st.spinner(f"⏳ Recherche de preuves pour '{audit_id}' + Arbitrage IA..."):
                    final_state = orchestrator.run(
                        company_id=user["company_id"],
                        user_id=user["user_id"],
                        audit_id=audit_id, 
                        checklist_path=tmp_path
                    )
                
                if final_state.get("error"):
                    st.error(final_state["error"])
                else:
                    results = final_state["results"]
                    st.success(f"✅ Mapping terminé pour {len(results)} exigences.")
                    
                    c1, c2, c3 = st.columns(3)
                    conform_count = len([r for r in results if r.get("compliance_status") == "conform"])
                    nc_count = len([r for r in results if "nc" in str(r.get("finding_type", "")).lower()])
                    c1.metric("Conformes", f"{conform_count}/{len(results)}")
                    c2.metric("Non-Conformités", f"{nc_count}")
                    avg_score = sum([r["coverage_score"] for r in results]) / len(results) if results else 0
                    c3.metric("Maturité Moyenne", f"{avg_score*100:.1f} %")
                    
                    st.markdown("---")
                    st.subheader("🔍 Détails du Mapping & Audit")
                    
                    import pandas as pd
                    df_res = pd.DataFrame(results)
                    st.dataframe(df_res, use_container_width=True)
                    
                    for res in results:
                        # Définition des libellés et emojis
                        status_map = {"conform": "✅ CONFORME", "partial": "⚠️ PARTIEL", "non_conform": "❌ NON CONFORME"}
                        mastery_labels = {
                            "none": "🔴 Aucune maîtrise démontrée",
                            "partial": "🟠 Maîtrise partielle",
                            "demonstrated": "🟢 Maîtrise démontrée"
                        }
                        
                        status_label = status_map.get(res.get("compliance_status"), "❓ INCONNU")
                        finding_label = str(res.get("finding_type", "")).upper().replace("_", " ")
                        mastery_label = mastery_labels.get(res.get("mastery_level"), "⚪ Niveau non évalué")
                        
                        with st.expander(f"Détail : {res['requirement_id']} - {status_label}"):
                            # Affichage explicite demandé par l'utilisateur
                            st.write(f"### {status_label}")
                            st.write(f"**Typologie :** `{finding_label}`")
                            st.write(f"**Maîtrise :** {mastery_label}")
                            st.markdown("---")
                            
                            st.write("**Exigence :**", res["description"])
                            
                            m_cols = st.columns(4)
                            m_cols[0].write(f"**Statut**\n{res.get('compliance_status', 'N/A').upper()}")
                            m_cols[1].write(f"**Typologie**\n{finding_label}")
                            m_cols[2].write(f"**Risque**\n{str(res.get('risk_level', 'N/A')).upper()}")
                            m_cols[3].write(f"**Niveau Maîtrise**\n{res.get('mastery_level', 'NONE').upper()}")
                            
                            st.info(f"**Document cité :** {res['best_document']}")
                            st.write("**Analyse de l'IA :**", res["justification"])
                            
                            if res.get("elements_manquants") and res["elements_manquants"] not in ["", "Aucun", "None", "N/A"]:
                                st.warning(f"**Éléments manquants :** {res['elements_manquants']}")
                            
                            st.progress(max(0.0, min(1.0, float(res["coverage_score"]))), text=f"Score de couverture : {float(res['coverage_score'])*100:.0f}%")
                            
                            if res.get("explanation_payload"):
                                exp = res["explanation_payload"]
                                st.markdown("---")
                                st.subheader("🧠 Logique Agentique & Grounding")
                                
                                c1, c2, c3 = st.columns(3)
                                c1.metric("Confiance Sélection", exp.get("confidence_in_selection", "N/A").upper())
                                c2.metric("Incertitude", exp.get("uncertainty_level", "N/A").upper())
                                c3.metric("Itérations", exp.get("iterations", 0))
                                
                                st.write(f"**🏢 Thème d'audit :** {exp.get('audit_theme', 'Opérations')}")
                                st.write(f"**🎯 Objectif de contrôle :** {exp.get('control_objective', 'N/A')}")
                                st.write(f"**🚀 Stratégie employée :** `{exp.get('strategy_selected', 'N/A')}`")
                                
                                # Affichage des requêtes réellement utilisées
                                queries = exp.get("queries_used", [])
                                if queries:
                                    st.write("**🔍 Requêtes envoyées au moteur vectoriel (Qdrant) :**")
                                    st.code(" | ".join(queries))
                                
                                # Trace de raisonnement compacte
                                if exp.get("reasoning_trace"):
                                    st.write("**📝 Historique décisionnel (Trace) :**")
                                    for trace in exp["reasoning_trace"]:
                                        with st.container():
                                            st.markdown(f"**Étape {trace['step']}** : `{trace.get('strategy')}` via `{', '.join(trace.get('tools', []))}`")
                                            st.caption(f"↳ *Constat :* {trace.get('outcome')}")
                                
                                st.success(f"**⚖️ Pourquoi ce choix ?** {exp.get('why_selected', 'N/A')}")
                                st.info(f"**🏁 Fin de recherche :** {exp.get('why_stopped', 'Processus terminé')}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
