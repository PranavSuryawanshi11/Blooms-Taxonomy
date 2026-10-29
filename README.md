# BloomCraft AI — Cognitive Examination Engineering System

> University-grade automated examination paper generator adhering to Revised Bloom's Taxonomy, syllabus ingestion, cognitive blueprinting, outcome-based education (OBE) standards, and AICTE examination reform policies.

---

## 🌟 Overview

**BloomCraft AI** is an intelligent, full-stack examination engineering workbench designed for university faculty and academic institutions. It transforms unstructured course syllabi into balanced, high-fidelity examination papers calibrated across cognitive learning tiers (L1 Remember through L6 Create), mapped directly to Course Outcomes (COs), and rendered with technical schematic diagrams and official institutional export formats.

---

## 🚀 Key Capabilities

- **Revised Bloom's Taxonomy Calibration**: Automatically constructs cognitive distributions ensuring balanced assessment across all 6 tiers:
  - **L1** Remember &bull; **L2** Understand &bull; **L3** Apply
  - **L4** Analyze &bull; **L5** Evaluate &bull; **L6** Create
- **Automated Syllabus & PDF Ingestion**: Extracts text, modules, chapters, and course objectives from course syllabi using `pdfplumber`.
- **Outcome-Based Blueprint Builder**: Customizes marks, sections, internal choices, and Course Outcome (CO1–CO6) distributions with real-time cognitive index calibration.
- **Multi-Provider Free-Tier LLM Architecture**: Built-in resilient dynamic failover and discovery across free-tier providers:
  - **Groq Cloud** (Llama 3.3, Mixtral)
  - **OpenRouter** (Free-tier catalog)
  - **Cerebras Cloud** (Ultra-fast Llama models)
  - **Mistral AI** (Mistral Small / Codestral)
- **Technical Figure & Schematic Generator**: Synthesizes algorithmic SVG circuit diagrams, network topologies, architecture diagrams, and scientific schematics with zero external graphic dependencies.
- **University Examination Export**: Generates production-ready Microsoft Word (`.docx`) documents with institutional headers, course outcome mapping matrices, and clean CSS print formatting.
- **Faculty Authentication & Isolated Archive**: Secure faculty login and sign-up with PBKDF2 password hashing and private, per-teacher examination question paper history.

---

## 📁 Systematic Project Structure

```text
├── backend/
│   ├── app.py                         # Flask REST API server and static web host
│   ├── config.py                      # Cognitive presets, Bloom levels, and university templates
│   ├── .env.example                   # Backend environment configuration template
│   ├── core/
│   │   ├── auth_history_service.py    # Faculty authentication, PBKDF2 hashing & history archive
│   │   ├── bloom_engine.py            # Bloom distribution validators and cognitive index calculations
│   │   ├── blueprint_builder.py       # Examination blueprint compiler and section allocation
│   │   ├── diagram_ai.py              # AI-assisted SVG technical diagram synthesis
│   │   ├── export_service.py          # Word DOCX generation with AICTE matrix tables
│   │   ├── figure_generator.py        # Algorithmic SVG diagram rendering engine
│   │   ├── figure_planner.py          # Prompt analysis and diagram candidate identification
│   │   ├── llm_client.py              # Zero-dependency multi-provider LLM client with runtime failover
│   │   ├── question_generator.py      # Prompt builder and question synthesizer
│   │   └── syllabus_parser.py         # PDF syllabus extractor and module segmenter
│   ├── data/
│   │   ├── bloom_stems.json           # Action verbs and stems for each Bloom cognitive level
│   │   ├── custom_templates.json      # User-defined examination templates
│   │   ├── sample_syllabi.json        # Preloaded reference syllabi for quick demonstration
│   │   └── user_question_sets.json    # Question bank sets
│   ├── test_auth_history_integration.py # Auth and history service integration tests
│   ├── test_e2e_live.py               # End-to-end question paper workflow tests
│   └── test_generator.py              # Cognitive paper generation unit tests
│
├── frontend/
│   ├── index.html                     # Single-page application interface and auth portal
│   ├── css/
│   │   ├── components.css             # Component library (badges, modals, form controls, cards)
│   │   ├── main.css                   # Core design system, typography, and color variables
│   │   └── print.css                  # Print-specific styling for clean question paper export
│   └── js/
│       ├── app.js                     # Global state, workflow controller, notifications
│       ├── auth.js                    # Faculty login/signup session controller and history modal
│       ├── blueprint.js               # Blueprint matrix editor and cognitive sliders
│       ├── custom_sets.js             # Custom question sets manager
│       ├── export.js                  # Document export and client-side formatting
│       ├── generator.js               # Question generation and regeneration controller
│       └── syllabus.js                # Syllabus upload and text ingestion handler
│
├── .env.example                       # Root environment variables template
├── .gitignore                         # Comprehensive Git exclusion rules
├── package_project.py                 # Clean distribution zip packaging utility
├── requirements.txt                   # Production Python dependencies
└── README.md                          # Systematic documentation
```

---

## 🛠️ Quick Start & Installation

### 1. Prerequisites
- Python **3.9+** (Python 3.10, 3.11, or 3.12 recommended)
- Git

### 2. Clone the Repository
```bash
git clone <your-repository-url>
cd "Question Paper Generator"
```

### 3. Create and Activate a Virtual Environment
- **Windows (Command Prompt / PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy the template `.env.example` to `.env`:
```bash
# On Windows PowerShell:
Copy-Item .env.example .env

# On macOS / Linux / Bash:
cp .env.example .env
```

Open `.env` and fill in at least one of the supported free-tier API keys:
```ini
# Groq (Recommended - Free Tier, Fast): https://console.groq.com/keys
GROQ_API_KEY=your_groq_api_key_here

# OpenRouter (Optional): https://openrouter.ai/keys
OPENROUTER_API_KEY=

# Cerebras (Optional): https://cloud.cerebras.ai
CEREBRAS_API_KEY=

# Mistral (Optional): https://console.mistral.ai
MISTRAL_API_KEY=
```

> **Security Note:** The `.env` file contains secret credentials and is strictly ignored in `.gitignore`. **Never commit or push `.env` to any public or private Git repository.** Use `.env.example` for all shared configurations.

### 6. Run the Application
```bash
python backend/app.py
```
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 🧪 Running Tests

To verify backend modules, cognitive calibration, and user authentication isolation:
```bash
# Test Faculty Authentication and Isolated Paper History
python backend/test_auth_history_integration.py

# Test Question Generation & Bloom Distribution Validation
python backend/test_generator.py

# Test End-to-End Live Workflow (requires valid API key in .env)
python backend/test_e2e_live.py
```

---

## 🔒 Security & Privacy

- **Faculty Data Isolation**: Faculty accounts and generated history are stored locally in `backend/data/user_store.json` (which is also ignored from version control).
- **PBKDF2 Password Hashing**: Passwords are saved with cryptographically secure salted hashes (`PBKDF2-SHA256` with 120,000 iterations).

---

## 📄 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

