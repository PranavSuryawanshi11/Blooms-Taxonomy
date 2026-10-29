# Security Policy

## Supported Versions

Only the latest release on the `main` branch receives active security updates and patches.

| Version | Supported          |
| ------- | ------------------ |
| 4.x / `main` | :white_check_mark: |
| < 4.0   | :x:                |

---

## 🔒 Confidentiality & Credentials Policy

### 1. API Keys & Secrets
- **Never commit `.env` files.** The `.gitignore` is configured to prevent `.env` and `backend/.env` from entering Git history.
- Always use the provided [`.env.example`](.env.example) as the template for configuring local environments.
- API keys (Groq, OpenRouter, Cerebras, Mistral) are strictly consumed on the server backend during runtime and are never sent or exposed to client-side browsers.

### 2. Faculty Data Isolation
- Faculty accounts, hashed credentials, and past examination papers are persisted locally in SQLite database `backend/data/bloomcraft.db`.
- Passwords are encrypted using **PBKDF2-SHA256 with 120,000 hashing rounds** and individual cryptographic salts.
- The `bloomcraft.db` database is strictly excluded from version control to guarantee institutional confidentiality.

---

## 🚨 Reporting a Vulnerability

If you discover any security vulnerability, credential exposure, or exploit within this project:

1. **Do NOT open a public GitHub Issue.**
2. Send a confidential email directly to the project maintainer:
   - **Maintainer**: Pranav Suryawanshi
   - **Email**: `pranavsuryawanshi955@gmail.com`
3. Include detailed steps to reproduce the vulnerability, along with relevant environment details.
4. We commit to acknowledging receipt within 48 hours and providing a resolution timeline.

