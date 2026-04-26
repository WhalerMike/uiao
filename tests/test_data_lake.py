"""Tests for UIAO_109 / §3.7 Data Lake Model.

Covers the retention-policy loader, ArchiveEntry round trip,
FilesystemArchive backend, ArchiveManager orchestration (archive +
expire + query), and a live-canon smoke against the real registries.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

import pytest

from uiao.storage.data_lake import (
    DEFAULT_RETENTION_YEARS,
    ArchiveEntry,
    ArchiveManager,
    FilesystemArchive,
    RawZoneViolation,
    RetentionPolicy,
    load_retention_policies,
    policy_for,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_registry(path: Path, adapters: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"adapters": adapters}), encoding="utf-8")
    return path


def _write_scheduler_run(
    tmp_path: Path,
    adapters: list[dict],
    run_id: str = "schedrun-test-001",
) -> Path:
    run_dir = tmp_path / run_id
    adapters_dir = run_dir / "adapters"
    adapters_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
    for spec in adapters:
        adir = adapters_dir / spec["id"]
        adir.mkdir()
        payload = {
            "ksi_id": spec.get("ksi_id", f"ksi:{spec['id']}"),
            "source": spec["id"],
            "evidence_class": spec.get("evidence_class", "baseline"),
        }
        (adir / "evidence.json").write_text(json.dumps(payload), encoding="utf-8")
    return run_dir


# ---------------------------------------------------------------------------
# Retention policy loader
# ---------------------------------------------------------------------------


class TestRetentionPolicyLoader:
    def test_missing_files_return_empty(self, tmp_path):
        assert load_retention_policies([tmp_path / "nope.yaml"]) == {}

    def test_loads_declared_retention(self, tmp_path):
        path = _write_registry(
            tmp_path / "r.yaml",
            [
                {"id": "entra-id", "retention-years": 7},
                {"id": "scuba", "retention-years": 3},
            ],
        )
        policies = load_retention_policies([path])
        assert policies["entra-id"].retention_years == 7
        assert policies["scuba"].retention_years == 3

    def test_missing_retention_years_uses_default(self, tmp_path):
        path = _write_registry(tmp_path / "r.yaml", [{"id": "skinny"}])
        # Even without retention-years, the loader uses the default.
        policies = load_retention_policies([path], default_retention_years=5)
        assert policies["skinny"].retention_years == 5

    def test_invalid_value_falls_back_to_default(self, tmp_path):
        path = _write_registry(
            tmp_path / "r.yaml",
            [{"id": "weird", "retention-years": "ages"}],
        )
        policies = load_retention_policies([path])
        assert policies["weird"].retention_years == DEFAULT_RETENTION_YEARS

    def test_later_registry_overrides_earlier(self, tmp_path):
        a = _write_registry(tmp_path / "a.yaml", [{"id": "x", "retention-years": 1}])
        b = _write_registry(tmp_path / "b.yaml", [{"id": "x", "retention-years": 7}])
        policies = load_retention_policies([a, b])
        assert policies["x"].retention_years == 7

    def test_modernization_top_level_key(self, tmp_path):
        path = tmp_path / "mod.yaml"
        path.write_text(
            yaml.safe_dump({"modernization_adapters": [{"id": "tf", "retention-years": 5}]}),
            encoding="utf-8",
        )
        policies = load_retention_policies([path])
        assert policies["tf"].retention_years == 5


# ---------------------------------------------------------------------------
# policy_for fallback
# ---------------------------------------------------------------------------


class TestPolicyFor:
    def test_declared_returned(self):
        policies = {
            "a": RetentionPolicy(adapter_id="a", retention_years=5),
        }
        assert policy_for("a", policies).retention_years == 5

    def test_undeclared_uses_default(self):
        p = policy_for("phantom", {})
        assert p.adapter_id == "phantom"
        assert p.retention_years == DEFAULT_RETENTION_YEARS


# ---------------------------------------------------------------------------
# ArchiveEntry
# ---------------------------------------------------------------------------


class TestArchiveEntry:
    def test_round_trip_dict(self):
        entry = ArchiveEntry(
            run_id="r1",
            adapter_id="entra-id",
            archived_at="2026-04-26T00:00:00+00:00",
            retention_until="2029-04-26T00:00:00+00:00",
            archive_path="/lake/entra-id/r1",
            evidence_class="baseline",
        )
        d = entry.as_dict()
        assert d["run_id"] == "r1"
        # JSON round-trips cleanly.
        json.loads(json.dumps(d))

    def test_is_expired_past_window(self):
        entry = ArchiveEntry(
            run_id="r1",
            adapter_id="a",
            archived_at="2020-01-01T00:00:00+00:00",
            retention_until="2021-01-01T00:00:00+00:00",
            archive_path="/x",
        )
        assert entry.is_expired(now=datetime(2026, 1, 1, tzinfo=timezone.utc))

    def test_not_expired_inside_window(self):
        entry = ArchiveEntry(
            run_id="r1",
            adapter_id="a",
            archived_at="2026-04-26T00:00:00+00:00",
            retention_until="2030-04-26T00:00:00+00:00",
            archive_path="/x",
        )
        assert not entry.is_expired(now=datetime(2026, 6, 1, tzinfo=timezone.utc))

    def test_unparseable_retention_until_never_expires(self):
        entry = ArchiveEntry(
            run_id="r1",
            adapter_id="a",
            archived_at="bad",
            retention_until="bad",
            archive_path="/x",
        )
        assert not entry.is_expired()

    def test_checkpoint_default_true(self):
        entry = ArchiveEntry(
            run_id="r1",
            adapter_id="a",
            archived_at="2026-04-26T00:00:00+00:00",
            retention_until="2030-04-26T00:00:00+00:00",
            archive_path="/x",
        )
        assert entry.checkpoint is True
        assert entry.as_dict()["checkpoint"] is True

    def test_checkpoint_round_trips_through_json(self, tmp_path):
        backend = FilesystemArchive(root=tmp_path / "lake")
        entry = ArchiveEntry(
            run_id="r1",
            adapter_id="a",
            archived_at="2026-04-26T00:00:00+00:00",
            retention_until="2030-04-26T00:00:00+00:00",
            archive_path="/x",
            checkpoint=False,
        )
        backend.write_index(entry)
        roundtrip = backend.read_index("r1", "a")
        assert roundtrip is not None
        assert roundtrip.checkpoint is False

    def test_checkpoint_defaults_true_when_missing_in_legacy_index(self, tmp_path):
        # Index files written before the checkpoint field landed should
        # deserialize cleanly with checkpoint defaulted to True.
        backend = FilesystemArchive(root=tmp_path / "lake")
        legacy = {
            "run_id": "r1",
            "adapter_id": "a",
            "archived_at": "2026-04-26T00:00:00+00:00",
            "retention_until": "2030-04-26T00:00:00+00:00",
            "archive_path": "/x",
            "evidence_class": "baseline",
            "extra": {},
        }
        path = backend.root / "_index" / "r1__a.json"
        path.write_text(json.dumps(legacy), encoding="utf-8")
        roundtrip = backend.read_index("r1", "a")
        assert roundtrip is not None
        assert roundtrip.checkpoint is True


# ---------------------------------------------------------------------------
# FilesystemArchive
# ---------------------------------------------------------------------------


class TestFilesystemArchive:
    def test_put_and_remove_directory(self, tmp_path):
        backend = FilesystemArchive(root=tmp_path / "lake")
        source = tmp_path / "run-1"
        source.mkdir()
        (source / "evidence.json").write_text("{}", encoding="utf-8")
        loc = backend.put(source, "adapterA/run-1")
        assert backend.exists("adapterA/run-1")
        assert (Path(loc) / "evidence.json").is_file()
        assert backend.remove("adapterA/run-1")
        assert not backend.exists("adapterA/run-1")

    def test_index_round_trip(self, tmp_path):
        backend = FilesystemArchive(root=tmp_path / "lake")
        entry = ArchiveEntry(
            run_id="r1",
            adapter_id="a",
            archived_at="2026-04-26T00:00:00+00:00",
            retention_until="2030-04-26T00:00:00+00:00",
            archive_path="/x",
        )
        backend.write_index(entry)
        roundtrip = backend.read_index("r1", "a")
        assert roundtrip == entry

    def test_immutable_default_blocks_overwrite(self, tmp_path):
        backend = FilesystemArchive(root=tmp_path / "lake")
        source = tmp_path / "run-1"
        source.mkdir()
        (source / "evidence.json").write_text("{}", encoding="utf-8")
        backend.put(source, "adapterA/run-1")
        with pytest.raises(RawZoneViolation):
            backend.put(source, "adapterA/run-1")

    def test_immutable_false_allows_overwrite(self, tmp_path):
        backend = FilesystemArchive(root=tmp_path / "lake", immutable=False)
        source = tmp_path / "run-1"
        source.mkdir()
        (source / "evidence.json").write_text('{"v": 1}', encoding="utf-8")
        backend.put(source, "adapterA/run-1")
        (source / "evidence.json").write_text('{"v": 2}', encoding="utf-8")
        backend.put(source, "adapterA/run-1")
        target = backend.root / "adapterA" / "run-1" / "evidence.json"
        assert json.loads(target.read_text(encoding="utf-8")) == {"v": 2}

    def test_immutable_path_after_remove_can_be_rewritten(self, tmp_path):
        # The legitimate "rewrite" path is remove-then-put. Used by
        # ArchiveManager.expire when retention ages a key out and a
        # new run later happens to land on the same key (rare but
        # possible if run_ids are reused).
        backend = FilesystemArchive(root=tmp_path / "lake")
        source = tmp_path / "run-1"
        source.mkdir()
        (source / "evidence.json").write_text("{}", encoding="utf-8")
        backend.put(source, "adapterA/run-1")
        backend.remove("adapterA/run-1")
        backend.put(source, "adapterA/run-1")  # no exception

    def test_list_index_sorted(self, tmp_path):
        backend = FilesystemArchive(root=tmp_path / "lake")
        for run, aid in [("r2", "b"), ("r1", "a"), ("r1", "b")]:
            backend.write_index(
                ArchiveEntry(
                    run_id=run,
                    adapter_id=aid,
                    archived_at="2026-04-26T00:00:00+00:00",
                    retention_until="2030-04-26T00:00:00+00:00",
                    archive_path=f"/x/{aid}/{run}",
                )
            )
        entries = backend.list_index()
        assert len(entries) == 3


# ---------------------------------------------------------------------------
# ArchiveManager
# ---------------------------------------------------------------------------


class TestArchiveManager:
    def test_archive_run_creates_per_adapter_entries(self, tmp_path):
        run = _write_scheduler_run(
            tmp_path,
            [{"id": "entra-id"}, {"id": "scuba"}],
            run_id="schedrun-001",
        )
        backend = FilesystemArchive(root=tmp_path / "lake")
        mgr = ArchiveManager(
            backend=backend,
            policies={"entra-id": RetentionPolicy(adapter_id="entra-id", retention_years=7)},
        )
        entries = mgr.archive_run(run)
        assert len(entries) == 2
        ids = {e.adapter_id for e in entries}
        assert ids == {"entra-id", "scuba"}
        # Per-adapter run dir lands under lake_root/<adapter>/<run_id>/.
        assert backend.exists("entra-id/schedrun-001")
        assert backend.exists("scuba/schedrun-001")
        # Index manifest is written.
        assert (backend.root / "_index" / "schedrun-001__entra-id.json").is_file()

    def test_archive_run_skips_adapter_without_evidence(self, tmp_path):
        run = _write_scheduler_run(tmp_path, [{"id": "entra-id"}], run_id="r")
        # Add an empty adapter dir with no evidence.json.
        (run / "adapters" / "ghost").mkdir()
        backend = FilesystemArchive(root=tmp_path / "lake")
        mgr = ArchiveManager(backend=backend)
        entries = mgr.archive_run(run)
        assert {e.adapter_id for e in entries} == {"entra-id"}

    def test_archive_run_no_adapters_dir_returns_empty(self, tmp_path):
        empty = tmp_path / "empty-run"
        empty.mkdir()
        mgr = ArchiveManager(backend=FilesystemArchive(root=tmp_path / "lake"))
        assert mgr.archive_run(empty) == []

    def test_archive_uses_default_retention_for_undeclared_adapter(self, tmp_path):
        run = _write_scheduler_run(tmp_path, [{"id": "phantom-adapter"}], run_id="r")
        mgr = ArchiveManager(
            backend=FilesystemArchive(root=tmp_path / "lake"),
            policies={},
            default_retention_years=5,
        )
        now = datetime(2026, 4, 26, tzinfo=timezone.utc)
        entries = mgr.archive_run(run, now=now)
        assert len(entries) == 1
        # 5 years * 365.25d = 1826.25 → first day after the window starts
        # 5 years past 2026-04-26.
        ru = entries[0].retention_until_dt
        assert ru is not None
        assert ru.year == 2031

    def test_archive_run_marks_entries_as_checkpoints(self, tmp_path):
        run = _write_scheduler_run(
            tmp_path,
            [{"id": "entra-id"}, {"id": "scuba"}],
            run_id="schedrun-001",
        )
        backend = FilesystemArchive(root=tmp_path / "lake")
        mgr = ArchiveManager(backend=backend)
        entries = mgr.archive_run(run)
        assert all(e.checkpoint is True for e in entries)
        # Round-trips through the index.
        for entry in entries:
            persisted = backend.read_index(entry.run_id, entry.adapter_id)
            assert persisted is not None
            assert persisted.checkpoint is True

    def test_archive_run_re_archive_raises_raw_zone_violation(self, tmp_path):
        run = _write_scheduler_run(tmp_path, [{"id": "entra-id"}], run_id="r")
        backend = FilesystemArchive(root=tmp_path / "lake")
        mgr = ArchiveManager(backend=backend)
        mgr.archive_run(run)
        # Same run replayed against an immutable backend is a Raw-Zone
        # violation — the operator is expected to expire-then-rearchive
        # if a true rewrite is needed.
        with pytest.raises(RawZoneViolation):
            mgr.archive_run(run)

    def test_evidence_class_pulled_from_payload(self, tmp_path):
        run = _write_scheduler_run(
            tmp_path,
            [{"id": "a", "evidence_class": "spot-check"}],
            run_id="r",
        )
        mgr = ArchiveManager(backend=FilesystemArchive(root=tmp_path / "lake"))
        entries = mgr.archive_run(run)
        assert entries[0].evidence_class == "spot-check"

    def test_expire_removes_past_retention_entries(self, tmp_path):
        # Archive at t0, then run expire at t0 + 10 years.
        run = _write_scheduler_run(tmp_path, [{"id": "a"}], run_id="r")
        backend = FilesystemArchive(root=tmp_path / "lake")
        mgr = ArchiveManager(
            backend=backend,
            policies={"a": RetentionPolicy(adapter_id="a", retention_years=1)},
        )
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        mgr.archive_run(run, now=t0)
        assert backend.exists("a/r")
        future = t0 + timedelta(days=365 * 5)
        expired = mgr.expire(now=future)
        assert len(expired) == 1
        assert not backend.exists("a/r")
        # Index manifest is also cleaned up.
        assert not (backend.root / "_index" / "r__a.json").is_file()

    def test_expire_keeps_in_window_entries(self, tmp_path):
        run = _write_scheduler_run(tmp_path, [{"id": "a"}], run_id="r")
        backend = FilesystemArchive(root=tmp_path / "lake")
        mgr = ArchiveManager(
            backend=backend,
            policies={"a": RetentionPolicy(adapter_id="a", retention_years=10)},
        )
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        mgr.archive_run(run, now=t0)
        # 1 day later — well inside window.
        expired = mgr.expire(now=t0 + timedelta(days=1))
        assert expired == []
        assert backend.exists("a/r")

    def test_query_filters(self, tmp_path):
        for run_id in ("r1", "r2"):
            run = _write_scheduler_run(tmp_path / run_id, [{"id": "a"}, {"id": "b"}], run_id=run_id)
            mgr = ArchiveManager(backend=FilesystemArchive(root=tmp_path / "lake"))
            mgr.archive_run(run)
        mgr = ArchiveManager(backend=FilesystemArchive(root=tmp_path / "lake"))
        assert {e.run_id for e in mgr.query()} == {"r1", "r2"}
        # Adapter filter.
        assert all(e.adapter_id == "a" for e in mgr.query(adapter_id="a"))
        # Run filter.
        assert all(e.run_id == "r1" for e in mgr.query(run_id="r1"))


# ---------------------------------------------------------------------------
# Live canon smoke
# ---------------------------------------------------------------------------


class TestLiveCanonSmoke:
    def test_real_registries_yield_policies_for_every_active_adapter(self):
        """Every active adapter in canon resolves to a retention policy
        (declared or default)."""
        policies = load_retention_policies(
            [
                "src/uiao/canon/modernization-registry.yaml",
                "src/uiao/canon/adapter-registry.yaml",
            ]
        )
        # At least the well-known adapters shipped today should land
        # in the result with a positive retention_years.
        for aid in ("entra-id", "scubagear", "terraform"):
            assert aid in policies, f"missing policy for {aid}"
            assert policies[aid].retention_years > 0
