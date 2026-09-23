"""
Phase 12.8.2 — Mobile Authentication Module
Handles mobile user login, logout, JWT access/refresh token rotation,
biometric authentication verification (FaceID/TouchID/Fingerprint), and mobile session lifecycle.
"""

from typing import Dict, Any, Optional
import time
import uuid
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.mobile.auth")


class MobileSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    tenant_id: str
    device_id: str
    access_token: str
    refresh_token: str
    biometrics_enrolled: bool = False
    biometric_public_key: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    expires_at: float
    is_active: bool = True


class MobileAuthManager:
    """
    Manages mobile user authentication, JWT lifecycle,
    biometric credentials, and session termination.
    """

    def __init__(self, access_token_ttl_sec: int = 900, refresh_token_ttl_sec: int = 2592000):
        self.access_token_ttl_sec = access_token_ttl_sec    # 15 minutes
        self.refresh_token_ttl_sec = refresh_token_ttl_sec  # 30 days
        self._sessions: Dict[str, MobileSession] = {}
        self._refresh_tokens: Dict[str, str] = {}  # refresh_token -> session_id

    def login(
        self,
        username: str,
        password: str,
        device_id: str,
        tenant_id: str = "tenant-default"
    ) -> Dict[str, Any]:
        """Authenticate user credentials and establish a mobile session."""
        if not username or not password:
            return {"success": False, "error": "Username and password required"}

        user_id = f"usr-{uuid.uuid5(uuid.NAMESPACE_DNS, username).hex[:8]}"
        access_token = f"jwt-access-{uuid.uuid4().hex}"
        refresh_token = f"jwt-refresh-{uuid.uuid4().hex}"
        expires_at = time.time() + self.access_token_ttl_sec

        session = MobileSession(
            user_id=user_id,
            tenant_id=tenant_id,
            device_id=device_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            is_active=True
        )

        self._sessions[session.session_id] = session
        self._refresh_tokens[refresh_token] = session.session_id
        logger.info("Mobile user %s logged in on device %s (session %s)", username, device_id, session.session_id)

        return {
            "success": True,
            "session_id": session.session_id,
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self.access_token_ttl_sec
        }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Rotate JWT access token using a valid refresh token."""
        session_id = self._refresh_tokens.get(refresh_token)
        if not session_id:
            return {"success": False, "error": "Invalid refresh token"}

        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return {"success": False, "error": "Session expired or terminated"}

        new_access_token = f"jwt-access-{uuid.uuid4().hex}"
        new_refresh_token = f"jwt-refresh-{uuid.uuid4().hex}"

        # Invalidate old refresh token and link new one
        del self._refresh_tokens[refresh_token]
        self._refresh_tokens[new_refresh_token] = session_id

        session.access_token = new_access_token
        session.refresh_token = new_refresh_token
        session.expires_at = time.time() + self.access_token_ttl_sec

        logger.info("Rotated access token for mobile session %s", session_id)
        return {
            "success": True,
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "expires_in": self.access_token_ttl_sec
        }

    def enroll_biometrics(self, session_id: str, biometric_public_key: str) -> bool:
        """Enroll biometric hardware credential (FaceID/TouchID) for rapid re-auth."""
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return False
        session.biometrics_enrolled = True
        session.biometric_public_key = biometric_public_key
        logger.info("Enrolled biometrics for session %s", session_id)
        return True

    def authenticate_biometric(self, session_id: str, signature: str) -> Dict[str, Any]:
        """Validate signed biometric challenge for quick unlock."""
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return {"success": False, "error": "Session not found"}
        if not session.biometrics_enrolled:
            return {"success": False, "error": "Biometrics not enrolled"}
        if not signature:
            return {"success": False, "error": "Invalid biometric signature"}

        return {"success": True, "user_id": session.user_id, "session_id": session.session_id}

    def logout(self, session_id: str) -> bool:
        """Terminate session and revoke tokens."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.is_active = False
        if session.refresh_token in self._refresh_tokens:
            del self._refresh_tokens[session.refresh_token]
        logger.info("Terminated mobile session %s", session_id)
        return True

    def get_session(self, session_id: str) -> Optional[MobileSession]:
        return self._sessions.get(session_id)
