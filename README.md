# 🛡️ QualiNova AI - Autonomous Audit Evidence Mapper

QualiNova AI is a high-fidelity, autonomous audit agent designed to function as a strict internal auditor. It evaluates organizational compliance against standards (e.g., ISO 9001) by mapping documentary evidence to specific audit requirements using advanced Agentic AI workflows.

---

## 🚀 Key Features

- **Autonomous Audit Reasoning**: Leverages a disciplined, checklist-based evaluation logic to distinguish between absence of proof (Non-Conformity), incomplete evidence (Partial), and full compliance (Conform).
- **Hybrid Data Grounding**: Combines centralized metadata storage in **Upstash Redis** with high-speed semantic search in **Qdrant Cloud/Local**. 
- **Agentic Orchestration**: Uses **LangGraph** to manage complex audit cycles, including multi-step reasoning, tool usage, and failover chains.
- **Multi-Tenant Architecture**: Ensures strict data isolation by `company_id` and `audit_id`.
- **Intelligent Mastery Scoring**: Implements mandatory mastery levels (`NONE`, `PARTIAL`, `DEMONSTRATED`) and risk assessment for every finding.
- **Explainable AI (XAI)**: Provides full reasoning traces, query logs, and confidence scores for every audit conclusion.

---

## 🛠️ Technical Stack

### **Backend & AI Logic**
- **Orchestration**: `LangGraph`, `LangChain`
- **LLM Engine**: `OpenAI` (GPT-4o or similar)
- **Agent Logic**: Custom decision-based reasoning pipeline with iterative search strategies.

### **Data & Storage**
- **Vector Database**: `Qdrant` (Primary) & `Milvus`/`ChromaDB` (Failover/Alternative).
- **Metadata & State**: `Upstash Redis` (Serverless Redis for multi-tenant data management).
- **Blob Storage**: `MinIO` (for artifact storage in containerized environments).
- **Database Backend**: `Supabase` / `PostgreSQL`.

### **Processing & UI**
- **Frontend**: `Streamlit` (Premium custom CSS with Glassmorphism).
- **OCR & Extraction**: `pytesseract`, `pdfplumber`, `PyMuPDF`, `python-docx`.
- **Embeddings**: `sentence-transformers` (Local) and `OpenAI Embeddings`.

---

## 🏗️ System Architecture

### 1. **Data Ingestion Pipeline**
Documents (PDF, DOCX, XLSX) are uploaded and stored in **Upstash Redis**. Upon synchronization, data is chunked, vectorized, and indexed in **Qdrant** for semantic retrieval.

### 2. **Checklist Manager Agent**
Extracts and structures audit requirements from complex regulatory documents into a normalized internal schema.

### 3. **Evidence Mapper Agent**
The core "Auditor" agent. It takes an audit requirement and:
- Formulates optimized search queries.
- Iteratively searches the vector database.
- Analyzes retrieved fragments for compliance.
- Classifies findings (Major NC, Minor NC, Observation, Conform).
- Assigns a **Mastery Level** and **Coverage Score** (0.0 - 1.0).

### 4. **LangGraph Orchestrator**
Manages the state machine that drives the audit process, ensuring that every requirement is processed and that the agent can "pivot" its strategy (e.g., moving from document search to gap analysis) if initial evidence is lacking.

---

## ⚙️ Setup & Installation

### **Prerequisites**
- Python 3.10+
- Docker & Docker Compose
- API Keys: `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`.

### **Local Deployment**
1. **Clone the repository**:
   ```bash
   git clone https://github.com/mayazahrouni2/testqualinova.git
   ```
2. **Setup environment**:
   Create a `.env` file based on existing templates.
3. **Run Infrastructure**:
   ```bash
   docker-compose up -d
   ```
4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Launch Application**:
   ```bash
   streamlit run app.py
   ```

---

## 📊 Audit Logic & Scoring

The agent follows a strict ISO-compliant scoring system:
- **Major NC**: Critical failure in a required process.
- **Minor NC**: Partial failure or lack of consistent evidence.
- **Observation / Risk**: Compliant but with potential for failure.
- **Conformity**: Full evidence demonstrated.

**Mastery Grid:**
- `NONE (0.0)`: No evidence or contradictory data.
- `PARTIAL (0.5)`: Fragmentary evidence found.
- `DEMONSTRATED (1.0)`: Clear, valid, and recent evidence.

---

## 🛡️ License & Contact
*Project internal for QualiNova.*
Contact: [mayazahrouni2](https://github.com/mayazahrouni2)
