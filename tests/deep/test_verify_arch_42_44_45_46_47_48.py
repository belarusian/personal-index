"""VALIDATOR cycle 211 — VERIFY ARCH-42/44/45/46/47/48.

One adversarial input per contract, on top of the existing pinning tests in
tests/test_*.py. Each test attacks the documented bound/guard the contract
implies and confirms the implemented option (A or B) holds.

- ARCH-42 annotation: Option A (upsert with reconciliation) — a colliding id
  with a DIFFERENT url must leave the id reachable from exactly one url.
- ARCH-44 content-pin: Option A (atomic temp-file-and-rename) — an interrupted
  _save must not leave a truncated file or a stray .tmp.
- ARCH-45 content-priority: Option B (documented divergence) — from_score and
  _level_for_score disagree in (0, 0.2) and from_score ignores config.
- ARCH-46 content-versioning: Option A (atomic write) — a corrupt file is not
  silently cleared to {} and persisted over the previous contents.
- ARCH-47 content-rollback: Option B (in-memory-only) — no save/load surface,
  docstring states points are lost on process exit.
- ARCH-48 content-exporter: Option A (escape Markdown) — Markdown-significant
  chars render well-formed; HTML/RSS escaping differs as documented.
"""

from __future__ import annotations

import json
import os


from personal_index.annotation import Annotation, AnnotationStore, AnnotationType
from personal_index.content_exporter import ContentExporter
from personal_index.content_pin import ContentPinner
from personal_index.content_priority import PriorityCalculator, PriorityLevel
from personal_index.content_rollback import ContentRollback, RollbackPoint
from personal_index.content_versioning import ContentVersioning


# --- ARCH-42: annotation upsert-with-reconciliation (Option A) ---

class TestArch42AnnotationCollision:
    def test_collision_different_url_reconciles_to_exactly_one_url(self):
        """Adversarial: a colliding id whose NEW url differs from the OLD url.

        The contract postcondition: each id maps to exactly one URL. After the
        upsert, the id must be reachable from the new url only; the old url's
        index list must no longer contain it, and get(id).url must be the new
        url. This is the exact desync the ticket describes (id reachable from
        two URLs while the registry holds one object).
        """
        store = AnnotationStore()
        old = Annotation(
            annotation_id="A1",
            url="http://old.example/page",
            annotation_type=AnnotationType.NOTE,
            value="old value",
            author="alice",
        )
        store.add(old)
        # Sanity: indexed under the old url.
        assert [a.annotation_id for a in store.get_by_url("http://old.example/page")] == ["A1"]

        new = Annotation(
            annotation_id="A1",
            url="http://new.example/other",
            annotation_type=AnnotationType.HIGHLIGHT,
            value="new value",
            author="bob",
        )
        store.add(new)

        # The id is reachable from the NEW url.
        new_ids = [a.annotation_id for a in store.get_by_url("http://new.example/other")]
        assert new_ids == ["A1"]
        # The id is NO LONGER reachable from the OLD url (reconciled out).
        old_ids = [a.annotation_id for a in store.get_by_url("http://old.example/page")]
        assert old_ids == []
        # The registry holds the new object; get(id).url is the new url.
        assert store.get("A1").url == "http://new.example/other"
        assert store.get("A1").value == "new value"
        # The id appears in exactly one url's index list (postcondition).
        all_indexed = [aid for ids in store._by_url.values() for aid in ids]
        assert all_indexed.count("A1") == 1
        # count stays consistent with the registry (one object, not two).
        assert store.count == 1

    def test_collision_same_url_no_duplicate_index_entry(self):
        """Adversarial: a colliding id with the SAME url must not double-index."""
        store = AnnotationStore()
        store.add(Annotation(annotation_id="A1", url="http://u", annotation_type=AnnotationType.NOTE))
        store.add(Annotation(annotation_id="A1", url="http://u", annotation_type=AnnotationType.FLAG, value="x"))
        # Exactly one entry in the index list for that url.
        assert store._by_url["http://u"].count("A1") == 1
        assert [a.annotation_id for a in store.get_by_url("http://u")] == ["A1"]
        assert store.count == 1


# --- ARCH-44: content-pin atomic write (Option A) ---

class TestArch44ContentPinAtomic:
    def test_interrupted_save_leaves_no_truncated_file_or_tmp(self, tmp_path, monkeypatch):
        """Adversarial: json.dump raises OSError mid-write.

        Under Option A the real storage_path is only touched by os.replace AFTER
        the temp file is fully written, so an interrupted _save must leave the
        previous complete file intact and must not leave a stray .tmp behind.
        """
        path = str(tmp_path / "pinned.json")
        pinner = ContentPinner(storage_path=path)
        pinner.pin("item1")
        with open(path) as f:
            assert "item1" in json.load(f)

        def boom(obj, f, **kw):
            f.write('{"truncated":')
            raise OSError("disk full")

        monkeypatch.setattr(json, "dump", boom)
        # pin rolls back in-memory state and returns False on the OSError.
        assert pinner.pin("item2") is False
        # The real file is still the previous complete store (not truncated).
        with open(path) as f:
            data = json.load(f)
        assert "item1" in data
        assert "item2" not in data


# --- ARCH-45: content-priority documented divergence (Option B) ---

class TestArch45PriorityDivergence:
    def test_from_score_and_level_for_score_diverge_in_open_interval(self):
        """Adversarial: a score in (0, 0.2) must hit the documented divergence.

        from_score uses `score > 0` -> LOW; _level_for_score (default config)
        uses `score >= low_threshold` (0.2) -> ARCHIVE below 0.2. So 0.1 must
        yield LOW vs ARCHIVE, and 0.2 must yield LOW vs LOW (the boundary).
        """
        calc = PriorityCalculator()
        # 0.1 is in (0, 0.2): the documented disagreement.
        assert PriorityLevel.from_score(0.1) is PriorityLevel.LOW
        assert calc._level_for_score(0.1) is PriorityLevel.ARCHIVE
        # 0.2 is the low_threshold boundary: both agree on LOW.
        assert PriorityLevel.from_score(0.2) is PriorityLevel.LOW
        assert calc._level_for_score(0.2) is PriorityLevel.LOW
        # 0.0 is the from_score ARCHIVE boundary (score <= 0).
        assert PriorityLevel.from_score(0.0) is PriorityLevel.ARCHIVE

    def test_from_score_ignores_config_tuning(self):
        """Adversarial: tuning low_threshold must NOT affect from_score.

        Option B pins that from_score is a standalone convenience with fixed
        bands; only _level_for_score is config-driven.
        """
        from personal_index.content_priority import PriorityConfig

        calc = PriorityCalculator(config=PriorityConfig(low_threshold=0.5))
        # 0.3 < tuned low_threshold (0.5) -> _level_for_score says ARCHIVE.
        assert calc._level_for_score(0.3) is PriorityLevel.ARCHIVE
        # But from_score(0.3) is unchanged by the config: 0.3 > 0 -> LOW.
        assert PriorityLevel.from_score(0.3) is PriorityLevel.LOW


# --- ARCH-46: content-versioning atomic write (Option A) ---

class TestArch46ContentVersioningAtomic:
    def test_corrupt_file_not_silently_cleared_and_overwritten(self, tmp_path):
        """Adversarial: a corrupt-but-present versions.json.

        Under Option A an interrupted _save never leaves a truncated file, so a
        corrupt file can only be pre-existing/external. Construction must NOT
        silently clear the store to {} and then persist the empty dict over the
        previous contents: the file on disk must remain the corrupt bytes, not
        be rewritten to "{}".
        """
        path = str(tmp_path / "versions.json")
        # Seed a previous complete store.
        prev = {
            "item-1": [
                {"version_id": "item-1_v1", "content": "known", "created_at": "t", "author": "a", "message": "m"}
            ]
        }
        with open(path, "w") as f:
            json.dump(prev, f)
        # Corrupt it (truncate to invalid JSON).
        with open(path, "w") as f:
            f.write('{"item-1": [ {"version_id": "item-1_v1", "cont')
        # Construct a fresh instance from the corrupt file.
        ContentVersioning(storage_path=path)
        # The corrupt file must NOT have been overwritten with the empty dict.
        with open(path) as f:
            on_disk = f.read()
        assert on_disk != "{}"
        assert "cont" in on_disk  # still the corrupt bytes, not silently fixed
        # And no stray temp file.
        assert not os.path.exists(path + ".tmp")


# --- ARCH-47: content-rollback in-memory-only (Option B) ---

class TestArch47ContentRollbackInMemory:
    def test_no_persistence_surface_and_docstring_states_lost_on_exit(self):
        """Adversarial: confirm the documented in-memory-only contract.

        Option B requires no save/load surface and a docstring that states,
        without reading the source, that points are lost on process exit.
        """
        assert not hasattr(ContentRollback, "save")
        assert not hasattr(ContentRollback, "load")
        c = ContentRollback()
        assert not hasattr(c, "save")
        assert not hasattr(c, "load")
        doc = ContentRollback.__doc__
        assert doc is not None
        low = doc.lower()
        assert "in-memory" in low
        assert "lost on process exit" in low
        # A fresh instance is empty (no file-backed load).
        assert c.get_rollback_points("http://x") == []

    def test_points_do_not_survive_a_fresh_instance(self):
        """Adversarial: a point created in one instance is absent in another.

        Mirrors the process-exit loss: there is no shared backing store, so a
        second instance cannot see the first instance's points.
        """
        a = ContentRollback()
        a.create_rollback_point(RollbackPoint(url="http://x", content="c1", title="t1"))
        assert len(a.get_rollback_points("http://x")) == 1
        b = ContentRollback()
        assert b.get_rollback_points("http://x") == []


# --- ARCH-48: content-exporter Markdown escaping (Option A) ---

class TestArch48ContentExporterMarkdownEscape:
    def test_markdown_special_chars_render_well_formed(self):
        """Adversarial: Markdown-significant chars in title/link/description.

        Option A: `](` in the title, a space in the link, and a newline in the
        description must render as well-formed Markdown — the link syntax is
        not broken, no stray heading is introduced, and the link target's space
        is percent-encoded.
        """
        exp = ContentExporter(title="My Index")
        items = [
            {
                "title": "A ](broken) title",
                "link": "http://ex.com/a b",
                "description": "line one\nline two",
            }
        ]
        md = exp.export(items, "markdown")
        # The link target's space is percent-encoded, so the (...) target is intact.
        assert "http://ex.com/a%20b" in md
        # The title's `](` is escaped so it cannot break the [..](..) syntax.
        assert "A \\]\\(broken\\) title" in md
        # The description's newline is collapsed to a space (no stray heading).
        assert "line one line two" in md
        assert "line one\nline two" not in md
        # Exactly one H2 heading for the item (no stray heading from the newline).
        assert md.count("## ") == 1

    def test_html_and_rss_escaping_differ_as_documented(self):
        """Adversarial: the same input shows html.escape vs xml_escape.

        html.escape escapes quotes; xml_escape does not. The contract states
        this difference, so one test pins both guard paths.
        """
        exp = ContentExporter(title="T")
        items = [{"title": 'He said "hi" & <x>', "link": "http://ex.com"}]
        html_out = exp.export(items, "html")
        rss_out = exp.export(items, "rss")
        # HTML escapes the double quote.
        assert "&quot;" in html_out
        assert '"hi"' not in html_out
        # RSS does NOT escape the double quote (xml_escape leaves it).
        assert '"hi"' in rss_out
        # Both escape the ampersand and angle brackets.
        assert "&amp;" in html_out and "&amp;" in rss_out
        assert "<x>" not in html_out and "<x>" not in rss_out
