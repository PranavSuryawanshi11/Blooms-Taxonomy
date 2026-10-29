# Contributing to BloomCraft AI

Thank you for your interest in contributing to **BloomCraft AI**. We welcome contributions from educators, software engineers, and researchers to make examination generation more rigorous, accessible, and compliant with cognitive taxonomies.

---

## 📜 Intellectual Property & Licensing Notice

Before contributing, please note:
- This project is governed by a **strict non-commercial, source-available license** (see [LICENSE](LICENSE)).
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
# Install development, test & linting tooling:
pip install -r requirements-dev.txt
```

### 4. Configure Local Environment
```bash
cp .env.example .env
# Edit .env and supply your free-tier API keys
```

### 5. Run Verification Tests
Before submitting any changes, ensure all test suites pass:
```bash
# Run automated smoke and unit tests:
pytest tests/ -v

# Check code style with Ruff:
ruff check .

# Run legacy verification suites:
python backend/test_auth_history_integration.py
python backend/test_generator.py
```

---

## 📝 Commit Convention

We adhere to the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat:` A new feature or capability (e.g. `feat(blueprint): add course outcome selector`)
- `fix:` A bug fix (e.g. `fix(ui): suppress default curriculum toast on unauthenticated page load`)
- `docs:` Documentation updates only (e.g. `docs(readme): add live demo link and hosting notes`)
- `ci:` Continuous Integration changes (e.g. `ci: add GitHub Actions workflow for Python 3.11`)
- `test:` Adding or updating automated test suites (e.g. `test: add smoke tests for auth endpoints`)
- `refactor:` Code restructuring without functional behavior changes
- `style:` Formatting, missing semicolons, or whitespace fixes
- `chore:` Maintenance tasks, dependency updates, dev configuration

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

