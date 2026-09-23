"""Enterprise Security Hardening for Phase 8.

Protection against:
- SQL Injection
- Prompt Injection
- Cross-Site Scripting (XSS)
- Rate Limiting
- Sandboxed Python Execution

Outputs:
{
  "security_status": "PASS"
}
"""

from __future__ import annotations

import ast
import html
import logging
import re
import time
from collections import defaultdict
from typing import Any

logger = logging.getLogger("security")

# SQL Injection signature patterns
SQLI_PATTERNS = [
    re.compile(r"(\bOR\b|\bAND\b)\s+['\"]?1['\"]?\s*=\s*['\"]?1['\"]?", re.IGNORECASE),
    re.compile(r";\s*--", re.IGNORECASE),
    re.compile(r"\bUNION(\s+ALL)?\s+SELECT\b", re.IGNORECASE),
    re.compile(r"\b(DROP|TRUNCATE|ALTER)\s+(TABLE|DATABASE)\b", re.IGNORECASE),
    re.compile(r"\bEXEC(UTE)?\s*\(", re.IGNORECASE),
    re.compile(r"\bxp_\w+", re.IGNORECASE),
    re.compile(r"\bWAITFOR\s+DELAY\b", re.IGNORECASE),
    re.compile(r"\bBENCHMARK\s*\(", re.IGNORECASE),
    re.compile(r"\bSLEEP\s*\(", re.IGNORECASE),
    re.compile(r"';\s*(DELETE|UPDATE|INSERT)\b", re.IGNORECASE),
]

# Prompt Injection signatures
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|directives|prompts)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(rules|constraints|instructions)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(developer\s+mode|unrestricted|DAN)", re.IGNORECASE),
    re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+)?(system\s+prompt|hidden\s+instructions|api\s*key)", re.IGNORECASE),
    re.compile(r"forget\s+everything\s+you\s+were\s+told", re.IGNORECASE),
    re.compile(r"act\s+as\s+an\s+evil|jailbreak", re.IGNORECASE),
]

# XSS attack patterns
XSS_PATTERNS = [
    re.compile(r"<\s*script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"onerror\s*=", re.IGNORECASE),
    re.compile(r"onload\s*=", re.IGNORECASE),
    re.compile(r"<\s*iframe[^>]*>", re.IGNORECASE),
    re.compile(r"<\s*img[^>]+src\s*=\s*['\"]?javascript:", re.IGNORECASE),
]

# Python sandbox forbidden AST nodes and calls
FORBIDDEN_PYTHON_BUILTINS = {
    "eval", "exec", "compile", "__import__", "open", "input", "breakpoint",
}
FORBIDDEN_PYTHON_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "requests", "urllib", "pty", "commands",
}


class SecurityHardening:
    """Enterprise security inspector, rate limiter, and code sandbox guard."""

    def __init__(self) -> None:
        self._rate_limits: dict[str, list[float]] = defaultdict(list)

    def check_sql_injection(self, sql_query: str) -> dict[str, Any]:
        """Verify that a SQL query contains no injection patterns."""
        clean_query = sql_query.strip()
        for pattern in SQLI_PATTERNS:
            if pattern.search(clean_query):
                logger.warning("SQL injection blocked: pattern=%s", pattern.pattern)
                return {
                    "security_status": "BLOCKED",
                    "threat_type": "sql_injection",
                    "reason": f"Malicious SQL pattern detected: {pattern.pattern}",
                }
        return {"security_status": "PASS"}

    def check_prompt_injection(self, prompt: str) -> dict[str, Any]:
        """Detect prompt injection and jailbreak attempts."""
        clean_prompt = prompt.strip()
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(clean_prompt):
                logger.warning("Prompt injection blocked: pattern=%s", pattern.pattern)
                return {
                    "security_status": "BLOCKED",
                    "threat_type": "prompt_injection",
                    "reason": f"Prompt injection detected: {pattern.pattern}",
                }
        return {"security_status": "PASS"}

    def check_xss(self, user_input: str) -> dict[str, Any]:
        """Detect Cross-Site Scripting (XSS) vectors."""
        for pattern in XSS_PATTERNS:
            if pattern.search(user_input):
                logger.warning("XSS blocked: pattern=%s", pattern.pattern)
                return {
                    "security_status": "BLOCKED",
                    "threat_type": "xss",
                    "reason": f"Malicious XSS script pattern detected: {pattern.pattern}",
                    "sanitized": html.escape(user_input),
                }
        return {"security_status": "PASS"}

    def check_rate_limit(
        self,
        client_id: str,
        limit: int = 100,
        window_seconds: int = 60,
    ) -> dict[str, Any]:
        """Sliding-window rate limiter."""
        now = time.time()
        timestamps = self._rate_limits[client_id]

        # Purge timestamps outside sliding window
        window_start = now - window_seconds
        valid_timestamps = [t for t in timestamps if t > window_start]
        self._rate_limits[client_id] = valid_timestamps

        if len(valid_timestamps) >= limit:
            logger.warning("Rate limit exceeded for client_id=%s", client_id)
            return {
                "security_status": "BLOCKED",
                "threat_type": "rate_limit",
                "reason": f"Rate limit of {limit} requests per {window_seconds}s exceeded",
                "retry_after_seconds": int(window_seconds - (now - valid_timestamps[0])),
            }

        valid_timestamps.append(now)
        return {"security_status": "PASS"}

    def validate_python_sandbox(self, python_code: str) -> dict[str, Any]:
        """Inspect Python code AST to ensure it does not use unsafe modules or calls."""
        try:
            tree = ast.parse(python_code)
        except SyntaxError as e:
            return {
                "security_status": "BLOCKED",
                "threat_type": "syntax_error",
                "reason": f"Invalid syntax: {e}",
            }

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg in FORBIDDEN_PYTHON_MODULES:
                        return {
                            "security_status": "BLOCKED",
                            "threat_type": "sandboxed_code_violation",
                            "reason": f"Import of dangerous module '{root_pkg}' is forbidden in sandbox",
                        }
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_pkg = node.module.split(".")[0]
                    if root_pkg in FORBIDDEN_PYTHON_MODULES:
                        return {
                            "security_status": "BLOCKED",
                            "threat_type": "sandboxed_code_violation",
                            "reason": f"Import from dangerous module '{root_pkg}' is forbidden in sandbox",
                        }
            # Check forbidden calls (eval, exec, __import__, open)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in FORBIDDEN_PYTHON_BUILTINS:
                        return {
                            "security_status": "BLOCKED",
                            "threat_type": "sandboxed_code_violation",
                            "reason": f"Call to dangerous builtin '{node.func.id}()' is forbidden in sandbox",
                        }

        return {"security_status": "PASS"}

    def inspect_input(
        self,
        text: str,
        client_id: str | None = None,
        check_sql: bool = True,
        check_prompt: bool = True,
        check_xss: bool = True,
    ) -> dict[str, Any]:
        """Unified security gate validating inputs across all attack vectors."""
        if client_id:
            rl = self.check_rate_limit(client_id)
            if rl["security_status"] != "PASS":
                return rl

        if check_prompt:
            p_res = self.check_prompt_injection(text)
            if p_res["security_status"] != "PASS":
                return p_res

        if check_sql:
            s_res = self.check_sql_injection(text)
            if s_res["security_status"] != "PASS":
                return s_res

        if check_xss:
            x_res = self.check_xss(text)
            if x_res["security_status"] != "PASS":
                return x_res

        return {"security_status": "PASS"}


# Global security hardening singleton
security_hardening = SecurityHardening()
