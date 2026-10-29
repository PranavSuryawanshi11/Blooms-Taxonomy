# Installation & Local Setup Guide

Follow this guide to deploy BloomCraft AI on Windows, macOS, or Linux.

---

## 💻 1. Prerequisites

- **Python**: Version `3.9` or higher (`python --version` or `python3 --version`).
- **Git**: Version `2.20` or higher (`git --version`).
- No database installation is required (SQLite is included in Python standard library).

---

## 🛠️ 2. Step-by-Step Installation

### Step A: Clone the Repository
```bash
git clone https://github.com/PranavSuryawanshi11/Blooms-Taxonomy.git
cd Blooms-Taxonomy
```

### Step B: Create and Activate Virtual Environment

- **Windows (Command Prompt / PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```

- **macOS / Linux / Bash:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Step C: Install Production Dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ 3. Environment & LLM Providers Configuration

Create a `.env` file in the project root:

```ini
# =========================================================================
# BloomCraft AI - Free-Tier Multi-Provider Configuration
# =========================================================================

# Groq Cloud API Key (Recommended - fast inference)
# Free Key: https://console.groq.com/keys
GROQ_API_KEY=gsk_your_key_here

# OpenRouter API Key (Optional - access to free catalog)
# Free Key: https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-your_key_here

# Cerebras Cloud API Key (Optional - ultra low latency)
# Free Key: https://cloud.cerebras.ai
CEREBRAS_API_KEY=csk_your_key_here

# Mistral AI API Key (Optional - reasoning models)
# Free Key: https://console.mistral.ai
MISTRAL_API_KEY=your_key_here

# Provider Failover Order
BLOOMCRAFT_LLM_ORDER=groq,cerebras,mistral,openrouter

# Server Configuration
PORT=5000
FLASK_DEBUG=0
```

> **🛡️ Offline Guarantee**: If zero API keys are provided in `.env`, BloomCraft AI automatically operates using its built-in rule engine and deterministic pedagogical question generator with zero network dependencies!

---

## 🚀 4. Starting the Server

```bash
python backend/app.py
```

Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 🧪 5. Running Automated Verification Tests

Verify backend modules, cognitive calibration, and SQLite privacy isolation:

```bash
# Test 1: Full unit test suite (Bloom calibration, syllabus parsing, blueprints)
python backend/test_generator.py

# Test 2: Multi-faculty privacy isolation and SQLite session storage
python backend/test_auth_history_integration.py
```

