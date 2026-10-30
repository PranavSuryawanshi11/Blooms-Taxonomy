# Changelog

All notable changes to **BloomCraft AI** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.0.0] - 2026-10-30

### Initial Production Release

#### Added
- **Revised Bloom's Taxonomy Cognitive Engine**:
  - Full support for Revised Bloom's Taxonomy cognitive tiers: L1 (Remember), L2 (Understand), L3 (Apply), L4 (Analyze), L5 (Evaluate), and L6 (Create).
  - Real-time mark allocation validator and Cognitive Index (CI) calculation.
  - Interactive cognitive slider matrix with automatic percentage normalization to 100%.

- **Automated Syllabus & Curriculum Ingestion**:
  - Direct PDF syllabus upload with automated text extraction via `pdfplumber`.
  - Intelligent module segmentation, topic identification, and Course Outcome (CO) parsing.
  - Pre-loaded university reference curricula (Database Management Systems, Operating Systems, Computer Networks).

- **Multi-Provider Resilient LLM Inference Tier**:
  - Multi-provider dynamic failover client with zero downtime across free-tier inference APIs.
  - First-class support for Groq Cloud (Llama 3.3 70B, Mixtral), OpenRouter free catalog, Cerebras Cloud, and Mistral AI.
  - Dynamic runtime model discovery, auto-benchmarking, and customizable failover order (`BLOOMCRAFT_LLM_ORDER`).

- **AICTE Examination Reform & OBE Compliance**:
  - Strict enforcement of AICTE action verbs mapped to cognitive tiers.
  - Automated question-to-CO mapping and OBE compliance fulfillment matrices.
  - Question regeneration engine preserving Bloom tier specifications and syllabus boundaries.

- **Algorithmic Vector (SVG) Figure Generator**:
  - In-engine procedural vector diagram generation for technical and scientific questions.
  - Schematics for digital logic circuits, neural networks, network topologies, entity-relationship diagrams, and statistical ANOVA tables.

- **Institutional Examination Templates**:
  - Pre-configured university blueprints: RCPIT Shirpur (65-mark and 60-mark End-Sem, 20-mark Unit Test, 25-mark In-Sem) and DJSCE Mumbai (60-mark).
  - Custom institutional layout customizer with customizable watermarks, headers, roll number boxes, and instructions.

- **Multi-Format Examination Document Export**:
  - One-click export to styled Microsoft Word (`.docx`) with formal examination formatting.
  - Print-ready clean CSS preview for direct browser printing.
  - Portable JSON paper archive export and import.

- **Faculty Authentication & Data Isolation**:
  - Secure session-based authentication with `PBKDF2-SHA256` password hashing (120,000 iterations).
  - Isolated SQLite data persistence (`bloomcraft.db`) storing faculty-specific examination histories.

- **Continuous Integration & Quality Automation**:
  - GitHub Actions CI workflow for Python 3.11 with byte-code compilation validation (`compileall`).
  - Pytest test suite with mocked LLM providers for offline, deterministic execution.
  - Non-blocking Ruff code quality analysis.
  - Standalone development dependencies (`requirements-dev.txt`) and `pytest.ini` configuration.

#### Fixed
- **Startup UI Notification**: Suppressed premature default curriculum toast message on unauthenticated initial page load (`frontend/js/syllabus.js`).
- **Faculty Authentication Resilience & Persistence**:
  - Resolved SQLite connection leaks and Windows WAL locking during server reloads by encapsulating database connections in a strict context manager with guaranteed auto-close.
  - Added dual-layer persistent credential synchronization (`seed_users.json`) preventing account loss across server restarts, ephemeral disk wipes (e.g. Render), or clean git checkouts.
  - Implemented flexible identifier matching in `authenticate_user` allowing faculty to log in via username, user ID, or display name with whitespace resilience.
  - Fixed duplicate frontend submit listeners causing concurrent authentication request collisions.
  - Added 1-click instant demo faculty sign-in chips on the authentication portal.

