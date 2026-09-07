# AI Data Analyst OS — Enterprise Security Guide

## Security Architecture Overview
The platform follows a zero-trust, defense-in-depth model across all layers:

1. **Network & Ingress**:
   - Mandatory TLS 1.3 encryption.
   - HSTS (`Strict-Transport-Security: max-age=31536000; includeSubDomains`).
   - Content Security Policy (CSP), anti-clickjacking (`X-Frame-Options: DENY`), and MIME-sniffing prevention (`X-Content-Type-Options: nosniff`).

2. **Authentication & Authorization**:
   - Short-lived JWT access tokens (30-60 min) signed with HS256/RS256.
   - Cryptographic single-use refresh token rotation with JTI tracking.
   - Immediate revocation blacklisting via Redis.
   - Strict RBAC enforcing principle of least privilege.

3. **Input Sanitization & Injection Defenses**:
   - **SQL Guardrails**: Rejection of all DDL (`DROP`, `ALTER`, `TRUNCATE`), mutation (`DELETE`, `INSERT`, `UPDATE`), and stacked injection attacks.
   - **Prompt Injection Hardening**: Multi-layer regex and heuristic classifiers detecting jailbreaks, system disclosure, and prompt overrides.
   - **File Upload Security**: Rejection of executable extensions (`.exe`, `.sh`, `.bat`), size capping (100MB max), and path traversal protection.

4. **Secrets & Credentials Management**:
   - Zero plaintext secrets in code or repository.
   - Environment variable injection via Docker / Kubernetes Secrets / HashiCorp Vault.
   - Automated secret redaction and masking in logging output.

5. **Auditability & Incident Response**:
   - Complete audit trail logging every administrative, authentication, and data modification action.
   - Real-time intrusion alerting on anomalous query activity or authentication failure spikes.
