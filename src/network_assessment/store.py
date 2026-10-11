"""In-memory assessment store: UUID4 ids, hashed owner tokens, TTL sweep, oldest-first eviction, one lock."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field

from network_assessment.report.summary import Assessment


@dataclass(frozen=True)
class Stored:
    id: str
    owner_token: str
    expires_at: float


@dataclass
class _Entry:
    assessment: Assessment
    files: dict[str, bytes]
    token_hash: bytes
    created_at: float
    expires_at: float = field(default=0.0)


@dataclass(frozen=True)
class _BundleTokenEntry:
    assessment_id: str
    expires_at: float


def _is_uuid4(value: str) -> bool:
    try:
        return uuid.UUID(value).version == 4
    except ValueError:
        return False


def _hash(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


class AssessmentStore:
    def __init__(self, ttl_seconds: int, max_items: int, *, clock=time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._max = max_items
        self._clock = clock
        self._items: dict[str, _Entry] = {}
        self._bundle_tokens: dict[bytes, _BundleTokenEntry] = {}
        self._lock = threading.Lock()

    def put(self, assessment: Assessment, files: dict[str, bytes]) -> Stored:
        token = secrets.token_urlsafe(24)
        now = self._clock()
        entry = _Entry(assessment, dict(files), _hash(token), now, now + self._ttl)
        with self._lock:
            self._sweep_locked(now)
            while len(self._items) >= self._max:
                oldest = min(self._items, key=lambda k: self._items[k].created_at)
                del self._items[oldest]
            assessment_id = assessment.id if _is_uuid4(assessment.id) else str(uuid.uuid4())
            self._items[assessment_id] = entry
        return Stored(assessment_id, token, entry.expires_at)

    def _lookup(self, assessment_id: str, token: str | None) -> _Entry | None:
        if not token or not assessment_id:
            return None
        with self._lock:
            entry = self._items.get(assessment_id)
            if entry is None or entry.expires_at <= self._clock():
                return None
            if not hmac.compare_digest(entry.token_hash, _hash(token)):
                return None
            return entry

    def get(self, assessment_id: str, token: str | None) -> tuple[Assessment, dict[str, bytes]] | None:
        entry = self._lookup(assessment_id, token)
        return None if entry is None else (entry.assessment, entry.files)

    def issue_bundle_token(self, assessment_id: str, owner_token: str | None, ttl_seconds: int = 600) -> str | None:
        """Issue a single-use, short-lived token scoped only to GET .../bundle.zip (ADR-0005)."""
        entry = self._lookup(assessment_id, owner_token)
        if entry is None:
            return None
        bundle_token = secrets.token_urlsafe(24)
        now = self._clock()
        expires_at = min(entry.expires_at, now + ttl_seconds)
        with self._lock:
            self._sweep_locked(now)
            self._bundle_tokens[_hash(bundle_token)] = _BundleTokenEntry(assessment_id, expires_at)
        return bundle_token

    def redeem_bundle_token(
        self, assessment_id: str, bundle_token: str | None
    ) -> tuple[Assessment, dict[str, bytes]] | None:
        """Consume a single-use bundle token and return (assessment, files) if valid and unexpired."""
        if not bundle_token or not assessment_id:
            return None
        token_hash = _hash(bundle_token)
        with self._lock:
            now = self._clock()
            bt = self._bundle_tokens.pop(token_hash, None)
            if bt is None or bt.assessment_id != assessment_id or bt.expires_at <= now:
                return None
            entry = self._items.get(assessment_id)
            if entry is None or entry.expires_at <= now:
                return None
            return (entry.assessment, entry.files)

    def expires_at(self, assessment_id: str, token: str | None) -> float | None:
        entry = self._lookup(assessment_id, token)
        return None if entry is None else entry.expires_at

    def delete(self, assessment_id: str, token: str | None) -> bool:
        entry = self._lookup(assessment_id, token)
        if entry is None:
            return False
        with self._lock:
            dead_tokens = [h for h, bt in self._bundle_tokens.items() if bt.assessment_id == assessment_id]
            for h in dead_tokens:
                del self._bundle_tokens[h]
            return self._items.pop(assessment_id, None) is not None

    def sweep(self, now: float | None = None) -> int:
        with self._lock:
            return self._sweep_locked(self._clock() if now is None else now)

    def _sweep_locked(self, now: float) -> int:
        expired = [k for k, v in self._items.items() if v.expires_at <= now]
        for k in expired:
            del self._items[k]
        expired_bt = [
            h for h, bt in self._bundle_tokens.items() if bt.expires_at <= now or bt.assessment_id not in self._items
        ]
        for h in expired_bt:
            del self._bundle_tokens[h]
        return len(expired)

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._bundle_tokens.clear()
