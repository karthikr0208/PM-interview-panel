"""Story 1.2: resume upload and text extraction.

Two groups of tests, deliberately not all marked `live`. `app.resume`'s
extraction functions are pure — no network — so those tests run in the fast
offline suite, the same split `test_llm_retry.py` uses for the retry wrapper.
Everything that drives an HTTP route is marked `live`: it hits real Supabase
Auth, PostgREST, and Storage through FastAPI's `TestClient`, which runs
`app.main`'s real lifespan exactly as a deployed server would.

THE MOST IMPORTANT TEST IN THIS FILE is
`test_upload_no_text_layer_pdf_fails_with_clear_message_and_writes_nothing`.
A no-text-layer PDF is the single most likely real-world upload failure
(PHASE-1-SPEC.md 1.2), and `pypdf` does not raise on one — `extract_text()`
silently returns "". If that flowed into `resumes.parsed_text`, story 1.3's
Resume Analyst would confidently level a candidate off no evidence at all.

Identities: exactly TWO anonymous identities are minted, once per module,
shared across every test — Supabase rate-limits anonymous sign-ins per IP
(DEV-STATE.md named trap, 2026-07-31). Deliberately NOT sharing fixture code
with `tests/test_rls_policies.py`: that file is today's newly-verified
story 1.1, and duplicating ~15 lines here is cheaper than risking a
regression in an already-verified file for a one-story-only reuse.

Residue: every session, resume row, and storage object this file creates is
deleted in teardown, and a module-scoped autouse fixture asserts the
database and bucket are back to their exact starting counts — not merely
"the tests exited zero." Autouse fixtures are set up before other
module-scoped fixtures and torn down after them (pytest's documented
ordering), so this fixture's "after" measurement runs strictly after
`identities`' own cleanup.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Callable, Iterator

import httpx
import psycopg
import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.config import settings
from app.main import app
from app.resume import MAX_RESUME_BYTES, ResumeValidationError, extract_text

BUCKET = "resumes"


# ═══════════════════════════════════════════════════════════════════════
# Pure extraction tests — no network, part of the fast offline suite.
# ═══════════════════════════════════════════════════════════════════════


def _minimal_pdf_with_text(text: str) -> bytes:
    """A hand-built, minimal single-page PDF with one real, extractable line
    of text. `pypdf.PdfWriter` has no text-drawing API (it manipulates
    existing pages; it does not author new content streams), so a real text
    layer needs either a third-party authoring library or a raw PDF content
    stream — this writes the latter directly rather than adding a dependency
    for one test fixture. Standard PDF structure: one page, one Type1
    Helvetica font (a base-14 font, needs no embedding), a content stream
    with a single `Tj` text-show operator, and a correct xref table so
    `pypdf` (and any real reader) parses it without a repair pass.
    """
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    content_stream = f"BT /F1 18 Tf 20 250 Td ({escaped}) Tj ET".encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 400 400] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content_stream)).encode() + b" >>\nstream\n"
        + content_stream + b"\nendstream",
    ]

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]  # object 0 (the free-list head) is never written as a real object
    for i, obj in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_offset = buf.tell()
    n = len(objects) + 1
    buf.write(f"xref\n0 {n}\n".encode())
    buf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode())
    buf.write(f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode())
    return buf.getvalue()


def _blank_pdf_no_text() -> bytes:
    """A structurally valid PDF with a blank page and no text layer at all —
    the no-text-layer / scanned-document case this whole story exists to
    catch. Built with pypdf's own writer, since a blank page needs no custom
    content stream."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _docx_with_paragraphs(paragraphs: list[str]) -> bytes:
    document = Document()
    for p in paragraphs:
        document.add_paragraph(p)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def test_extract_text_pdf_with_real_content_returns_it() -> None:
    pdf = _minimal_pdf_with_text("Product Manager, Series B fintech")
    kind, text = extract_text(pdf)
    assert kind == "pdf"
    assert "Product Manager" in text


def test_extract_text_docx_with_real_content_returns_it() -> None:
    docx_bytes = _docx_with_paragraphs(["Jordan Alvarez", "Senior PM at a logistics startup"])
    kind, text = extract_text(docx_bytes)
    assert kind == "docx"
    assert "Jordan Alvarez" in text
    assert "logistics startup" in text


def test_extract_text_blank_pdf_raises_clear_error_not_empty_string() -> None:
    """THE assertion this story exists for. pypdf does not raise on a
    no-text-layer PDF — extract_text() must, with a message a candidate can
    act on, not a silent empty string."""
    with pytest.raises(ResumeValidationError) as exc_info:
        extract_text(_blank_pdf_no_text())
    message = str(exc_info.value)
    assert "scanned" in message.lower() or "text-based" in message.lower()


def test_extract_text_empty_docx_raises_clear_error() -> None:
    with pytest.raises(ResumeValidationError) as exc_info:
        extract_text(_docx_with_paragraphs([]))
    assert "no extractable text" in str(exc_info.value).lower()


def test_extract_text_rejects_content_that_matches_neither_magic_bytes() -> None:
    with pytest.raises(ResumeValidationError) as exc_info:
        extract_text(b"just some plain text, not a real document at all")
    assert "pdf or docx" in str(exc_info.value).lower()


def test_extract_text_rejects_a_zip_that_is_not_actually_a_docx() -> None:
    """A ZIP signature alone (`PK\\x03\\x04`) is not proof of a DOCX — any
    ZIP-based format (.xlsx, a plain .zip) shares it. `detect_file_kind`
    cannot tell them apart from the magic bytes alone; `python-docx` itself
    is what must reject the package structure downstream."""
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("not_a_docx.txt", "this is a zip, but not a word document")
    with pytest.raises(ResumeValidationError) as exc_info:
        extract_text(buf.getvalue())
    assert "not a valid docx" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════
# Live tests — real HTTP routes, real Supabase Auth / PostgREST / Storage.
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Identity:
    user_id: str
    access_token: str


def _sign_up_anonymous() -> Identity:
    resp = httpx.post(
        f"{settings.supabase_url}/auth/v1/signup",
        headers={"apikey": settings.supabase_anon_key, "Content-Type": "application/json"},
        json={},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    return Identity(user_id=body["user"]["id"], access_token=body["access_token"])


def _delete_user(user_id: str) -> None:
    resp = httpx.delete(
        f"{settings.supabase_url}/auth/v1/admin/users/{user_id}",
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        },
        timeout=30,
    )
    assert resp.status_code in (200, 404), f"failed to delete auth user {user_id}: {resp.text}"


def _auth_header(identity: Identity) -> dict[str, str]:
    return {"Authorization": f"Bearer {identity.access_token}"}


def _service_headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }


def _select_as(token: str, table: str, column: str, value: str) -> list[dict]:
    resp = httpx.get(
        f"{settings.supabase_url}/rest/v1/{table}",
        headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"},
        params={column: f"eq.{value}", "select": "*"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _select_as_service(table: str, column: str, value: str) -> list[dict]:
    resp = httpx.get(
        f"{settings.supabase_url}/rest/v1/{table}",
        headers=_service_headers(),
        params={column: f"eq.{value}", "select": "*"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _delete_session_service(session_id: str) -> None:
    """Cascade-deletes a session and its resumes row (on delete cascade,
    0001_initial_schema.sql) via the service-role DB connection."""
    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            cur.execute("delete from sessions where id = %s", (session_id,))
        conn.commit()
    finally:
        conn.close()


def _list_bucket_prefix(prefix: str) -> list[dict]:
    resp = httpx.post(
        f"{settings.supabase_url}/storage/v1/object/list/{BUCKET}",
        headers=_service_headers(),
        json={"prefix": prefix, "limit": 1000, "sortBy": {"column": "name", "order": "asc"}},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _count_bucket_objects(prefix: str = "") -> int:
    """Recursively counts real objects (not folder placeholders) under
    `prefix`. Supabase Storage's list endpoint is one level deep per call —
    an entry with `id is None` is a folder, not a file, and needs a further
    call to see what is inside it."""
    total = 0
    for entry in _list_bucket_prefix(prefix):
        if entry.get("id") is None:
            total += _count_bucket_objects(f"{prefix}{entry['name']}/")
        else:
            total += 1
    return total


def _delete_storage_prefix(prefix: str) -> None:
    """Deletes every object directly under `prefix` (one level — this
    project only ever writes `{session_id}/resume.<ext>`, never nested
    further)."""
    entries = _list_bucket_prefix(prefix)
    paths = [f"{prefix}{e['name']}" for e in entries if e.get("id") is not None]
    if not paths:
        return
    resp = httpx.request(
        "DELETE",
        f"{settings.supabase_url}/storage/v1/object/{BUCKET}",
        headers=_service_headers(),
        json={"prefixes": paths},
        timeout=30,
    )
    resp.raise_for_status()


def _table_count(table: str) -> int:
    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            cur.execute(f"select count(*) from {table}")
            return cur.fetchone()[0]
    finally:
        conn.close()


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """One TestClient for the whole module — it runs `app.main`'s real
    lifespan (opens an AsyncPostgresSaver) on entry/exit, and there is no
    reason to pay that cost once per test when every test in this file
    shares it safely."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def identities() -> Iterator[tuple[Identity, Identity]]:
    a = _sign_up_anonymous()
    b = _sign_up_anonymous()
    assert a.user_id != b.user_id, "two signups minted the same identity"
    try:
        yield a, b
    finally:
        _delete_user(a.user_id)
        _delete_user(b.user_id)


@pytest.fixture
def new_session(
    client: TestClient, identities: tuple[Identity, Identity]
) -> Iterator[Callable[[Identity], str]]:
    """Creates a fresh session through the real `POST /session` route, as
    whichever identity the test passes in. Tears down by cascade-deleting
    the session (takes any resumes row with it) and clearing anything
    written to that session's storage prefix — storage is not tied to the
    app tables by a foreign key, so nothing else would clean it up.
    """
    created: list[str] = []

    def make(identity: Identity) -> str:
        resp = client.post("/session", headers=_auth_header(identity))
        assert resp.status_code == 200, resp.text
        session_id = resp.json()["session_id"]
        created.append(session_id)
        return session_id

    yield make

    for session_id in created:
        _delete_storage_prefix(f"{session_id}/")
        _delete_session_service(session_id)


@pytest.mark.live
class TestResumeRoutesLive:
    """Every test here drives a real HTTP route against real Supabase Auth,
    PostgREST, and Storage. Grouped in a class specifically so `_residue_report`
    below can be a CLASS-scoped autouse fixture: autouse fixtures only apply
    within the scope they are defined in, so putting it here (rather than at
    module level) is what keeps the pure extraction tests above network-free
    under `-m "not live"` — they are not part of this class and never see it.

    Class-level `pytestmark = pytest.mark.live` (applied via the decorator
    above the class) marks every method here in one place, rather than
    repeating `@pytest.mark.live` per test.
    """

    @pytest.fixture(scope="module", autouse=True)
    def _residue_report(self) -> Iterator[None]:
        """Brackets the WHOLE class, once — `scope="module"` matters here as
        much as `autouse`: `identities` and `client` are module-scoped too,
        and pytest sets up higher- (or equal-, when autouse) scoped fixtures
        before lower-scoped ones regardless of autouse position. A
        function-scoped version of this fixture would run once per test
        while `identities` stayed alive underneath it the whole time, and
        would never observe the true 0-before-any-identity 0-after-cleanup
        baseline this docstring claims — caught by actually reading the `-s`
        output rather than trusting "18 passed" on its first pass here.

        With `scope="module"`, being autouse at the SAME scope as
        `identities`/`client` is what gives it priority: instantiated before
        them, torn down after them. So the "after" measurement below runs
        strictly after `identities` has deleted its two auth.users rows and
        every test's own session/storage cleanup has run — counts must land
        exactly where they started, not merely close.
        """
        before = {
            "sessions": _table_count("sessions"),
            "resumes": _table_count("resumes"),
            "auth.users": _table_count("auth.users"),
            "bucket_objects": _count_bucket_objects(),
        }
        print(f"\n[residue] before: {before}")
        yield
        after = {
            "sessions": _table_count("sessions"),
            "resumes": _table_count("resumes"),
            "auth.users": _table_count("auth.users"),
            "bucket_objects": _count_bucket_objects(),
        }
        print(f"[residue] after:  {after}")
        assert after == before, f"test residue left behind: before={before} after={after}"

    def test_create_session_populates_user_id_from_jwt(
        self,
        client: TestClient,
        identities: tuple[Identity, Identity],
        new_session: Callable[[Identity], str],
    ) -> None:
        a, _ = identities
        session_id = new_session(a)
        rows = _select_as_service("sessions", "id", session_id)
        assert len(rows) == 1
        assert rows[0]["user_id"] == a.user_id
        assert rows[0]["status"] == "created"

    def test_session_readable_by_own_identity_and_by_nobody_else(
        self, identities: tuple[Identity, Identity], new_session: Callable[[Identity], str]
    ) -> None:
        """The join between story 1.1 and 1.2: a session created through
        `POST /session` must be visible to the identity that created it,
        through the real PostgREST path, and invisible to a second real
        identity."""
        a, b = identities
        session_id = new_session(a)

        owner_sees_it = _select_as(a.access_token, "sessions", "id", session_id)
        assert len(owner_sees_it) == 1, "the owning identity cannot read its own session"

        stranger_sees_it = _select_as(b.access_token, "sessions", "id", session_id)
        assert stranger_sees_it == [], f"a different identity can read this session: {stranger_sees_it}"

    def test_create_session_without_authorization_header_is_rejected(self, client: TestClient) -> None:
        """No `Authorization` header at all never reaches route code —
        FastAPI's `Header(...)` dependency rejects it at request validation,
        422, not 401. Asserting 401 here would be wrong and would mask the
        header actually being optional if the route signature ever
        changed."""
        resp = client.post("/session")
        assert resp.status_code == 422, resp.text

    def test_create_session_with_garbage_token_is_rejected(self, client: TestClient) -> None:
        resp = client.post("/session", headers={"Authorization": "Bearer not-a-real-token"})
        assert resp.status_code == 401, resp.text

    def test_upload_pdf_resume_extracts_and_persists_text(
        self,
        client: TestClient,
        identities: tuple[Identity, Identity],
        new_session: Callable[[Identity], str],
    ) -> None:
        a, _ = identities
        session_id = new_session(a)
        pdf = _minimal_pdf_with_text("Grew activation 18.2 pts leading a four person squad")

        resp = client.post(
            f"/session/{session_id}/resume",
            headers=_auth_header(a),
            files={"file": ("resume.pdf", pdf, "application/pdf")},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["storage_path"] == f"{session_id}/resume.pdf"

        rows = _select_as_service("resumes", "session_id", session_id)
        assert len(rows) == 1
        assert rows[0]["storage_path"] == body["storage_path"]
        assert "activation 18.2 pts" in rows[0]["parsed_text"]

        assert _count_bucket_objects(f"{session_id}/") == 1

    def test_upload_docx_resume_extracts_and_persists_text(
        self,
        client: TestClient,
        identities: tuple[Identity, Identity],
        new_session: Callable[[Identity], str],
    ) -> None:
        a, _ = identities
        session_id = new_session(a)
        docx_bytes = _docx_with_paragraphs(["Priya Natarajan", "Led pricing experiments at a B2B SaaS"])

        resp = client.post(
            f"/session/{session_id}/resume",
            headers=_auth_header(a),
            files={
                "file": (
                    "resume.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert resp.status_code == 200, resp.text
        rows = _select_as_service("resumes", "session_id", session_id)
        assert len(rows) == 1
        assert "Priya Natarajan" in rows[0]["parsed_text"]
        assert _count_bucket_objects(f"{session_id}/") == 1

    def test_upload_no_text_layer_pdf_fails_with_clear_message_and_writes_nothing(
        self,
        client: TestClient,
        identities: tuple[Identity, Identity],
        new_session: Callable[[Identity], str],
    ) -> None:
        """THE test this story exists for. A scanned / image-only PDF must
        be rejected with an actionable message — not accepted with an empty
        `parsed_text`, and not left as a storage object with nothing
        pointing at it either."""
        a, _ = identities
        session_id = new_session(a)

        resp = client.post(
            f"/session/{session_id}/resume",
            headers=_auth_header(a),
            files={"file": ("scan.pdf", _blank_pdf_no_text(), "application/pdf")},
        )
        assert resp.status_code == 400, resp.text
        detail = resp.json()["detail"].lower()
        assert "scanned" in detail or "text-based" in detail

        assert _select_as_service("resumes", "session_id", session_id) == [], (
            "a resumes row was written despite the extraction failing"
        )
        assert _count_bucket_objects(f"{session_id}/") == 0, (
            "a storage object was left behind despite the extraction failing — "
            "validation must happen before the upload, not after"
        )

    def test_upload_rejects_file_by_content_not_extension(
        self,
        client: TestClient,
        identities: tuple[Identity, Identity],
        new_session: Callable[[Identity], str],
    ) -> None:
        """A `.pdf` filename proves nothing — the bytes are plain text, not
        a PDF, and must be rejected by content inspection."""
        a, _ = identities
        session_id = new_session(a)

        resp = client.post(
            f"/session/{session_id}/resume",
            headers=_auth_header(a),
            files={"file": ("resume.pdf", b"just plain text pretending to be a pdf", "application/pdf")},
        )
        assert resp.status_code == 400, resp.text
        assert "pdf or docx" in resp.json()["detail"].lower()
        assert _count_bucket_objects(f"{session_id}/") == 0

    def test_upload_rejects_oversized_file_before_full_read(
        self,
        client: TestClient,
        identities: tuple[Identity, Identity],
        new_session: Callable[[Identity], str],
    ) -> None:
        a, _ = identities
        session_id = new_session(a)
        oversized = b"%PDF-1.4\n" + b"0" * (MAX_RESUME_BYTES + 1024)

        resp = client.post(
            f"/session/{session_id}/resume",
            headers=_auth_header(a),
            files={"file": ("huge.pdf", oversized, "application/pdf")},
        )
        assert resp.status_code == 400, resp.text
        assert "limit" in resp.json()["detail"].lower()
        assert _count_bucket_objects(f"{session_id}/") == 0

    def test_upload_rejects_when_session_belongs_to_another_identity(
        self,
        client: TestClient,
        identities: tuple[Identity, Identity],
        new_session: Callable[[Identity], str],
    ) -> None:
        a, b = identities
        b_session = new_session(b)

        resp = client.post(
            f"/session/{b_session}/resume",
            headers=_auth_header(a),
            files={"file": ("resume.pdf", _minimal_pdf_with_text("hello"), "application/pdf")},
        )
        assert resp.status_code == 403, resp.text
        assert _count_bucket_objects(f"{b_session}/") == 0

    def test_upload_rejects_unknown_session_id(
        self, client: TestClient, identities: tuple[Identity, Identity]
    ) -> None:
        a, _ = identities
        resp = client.post(
            "/session/00000000-0000-0000-0000-000000000000/resume",
            headers=_auth_header(a),
            files={"file": ("resume.pdf", _minimal_pdf_with_text("hello"), "application/pdf")},
        )
        assert resp.status_code == 404, resp.text

    def test_resumes_bucket_object_has_no_public_url(
        self,
        client: TestClient,
        identities: tuple[Identity, Identity],
        new_session: Callable[[Identity], str],
    ) -> None:
        """Complements
        `tests/test_schema.py::test_resumes_bucket_exists_and_is_private`
        end to end: a real object uploaded through this story's own route
        must still be unreachable at the bucket's public-URL shape, with no
        auth."""
        a, _ = identities
        session_id = new_session(a)
        resp = client.post(
            f"/session/{session_id}/resume",
            headers=_auth_header(a),
            files={"file": ("resume.pdf", _minimal_pdf_with_text("hello"), "application/pdf")},
        )
        assert resp.status_code == 200, resp.text
        storage_path = resp.json()["storage_path"]

        public_resp = httpx.get(
            f"{settings.supabase_url}/storage/v1/object/public/{BUCKET}/{storage_path}", timeout=15
        )
        assert public_resp.status_code != 200, (
            "a private bucket object was served from the public-URL path with no auth at all"
        )
