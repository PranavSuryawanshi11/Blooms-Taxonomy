# Contributing to BloomCraft AI

Thank you for your interest in contributing to **BloomCraft AI**. We welcome contributions from educators, software engineers, and researchers to make examination generation more rigorous, accessible, and compliant with cognitive taxonomies.

---

## 📜 Intellectual Property & Licensing Notice

Before contributing, please note:
- This project is governed by the **BloomCraft AI Non-Commercial Source-Available License** (see [LICENSE](LICENSE)).
- **Commercial sale, distribution, or monetization of this software is prohibited without prior written consent from Pranav Suryawanshi.**
- By submitting a Pull Request, you agree that your contributions will be licensed under the project's existing license terms.

---

## 🛠️ Development Workflow

### 1. Fork & Clone
```bash
git clone https://github.com/PranavSuryawanshi11/Blooms-Taxonomy.git
cd Blooms-Taxonomy
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv

# Windows:
.\venv\Scripts\activate

# macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Local Environment
```bash
cp .env.example .env
# Edit .env and supply your free-tier API keys
```

### 5. Run Verification Tests
Before submitting any changes, ensure all test suites pass:
```bash
python backend/test_auth_history_integration.py
python backend/test_generator.py
```

---

## 📝 Commit Convention

We adhere to the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat:` A new feature or capability
- `fix:` A bug fix
- `docs:` Documentation updates only
- `style:` Formatting, missing semicolons, whitespace fixes
- `refactor:` Code restructuring without functional behavior changes
- `test:` Adding or updating automated test suites
- `chore:` Maintenance tasks, dependency updates, configuration

Example:
```text
feat(diagram_ai): add algorithmic SVG generation for binary search trees
```

---

## 📬 Pull Request Process

1. Create a descriptive feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Verify that **NO `.env` or sensitive credential files** are tracked (`git status`).
3. Push to your fork and submit a Pull Request against the `main` branch.
4. Fill in the Pull Request template completely.

