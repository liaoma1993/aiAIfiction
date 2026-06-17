from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from app.utils.timezone import now as tz_now


MigrationFn = Callable[[Connection], None]


def _schema_migrations_columns(dialect: str) -> dict[str, str]:
    timestamp_type = "TIMESTAMP" if dialect != "sqlite" else "DATETIME"
    return {
        "version": "VARCHAR(32) PRIMARY KEY",
        "name": "VARCHAR(200) NOT NULL",
        "applied_at": f"{timestamp_type} NOT NULL DEFAULT CURRENT_TIMESTAMP",
    }


def _ensure_migration_table(conn: Connection) -> None:
    dialect = conn.dialect.name
    columns_sql = ", ".join(
        f"{name} {col_type}" for name, col_type in _schema_migrations_columns(dialect).items()
    )
    conn.exec_driver_sql(f"CREATE TABLE IF NOT EXISTS schema_migrations ({columns_sql})")


def _table_exists(conn: Connection, table_name: str) -> bool:
    return inspect(conn).has_table(table_name)


def _column_exists(conn: Connection, table_name: str, column_name: str) -> bool:
    if not _table_exists(conn, table_name):
        return False
    return column_name in {col["name"] for col in inspect(conn).get_columns(table_name)}


def _add_column_if_missing(conn: Connection, table_name: str, column_name: str, column_type: str) -> None:
    if _column_exists(conn, table_name, column_name):
        return
    conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def _normalize_arcs_payload(raw: object) -> list[dict]:
    if raw in (None, "", b""):
        return []
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _build_arc_continuity_index(arcs: list[dict]) -> list[dict]:
    index: list[dict] = []
    for idx, arc in enumerate(arcs):
        index.append(
            {
                "arc_index": idx,
                "name": arc.get("name", ""),
                "arc_type": arc.get("arc_type", ""),
                "closure_level": arc.get("closure_level", ""),
                "must_remain_open": arc.get("must_remain_open") or [],
                "handoff_from_previous": arc.get("handoff_from_previous")
                or arc.get("dependence_on_previous")
                or "",
                "handoff_to_next": arc.get("handoff_to_next") or arc.get("payoff_for_next") or "",
                "opening_state": arc.get("opening_state", ""),
                "ending_state": arc.get("ending_state", ""),
                "arc_step_count": len(arc.get("arc_steps") or [])
                if isinstance(arc.get("arc_steps"), list)
                else 0,
                "character_introduction_plan": arc.get("character_introduction_plan") or [],
                "faction_introduction_plan": arc.get("faction_introduction_plan") or [],
                "bridge_chapter_plan": arc.get("bridge_chapter_plan") or {},
                "protagonist_continuity_state": arc.get("protagonist_continuity_state") or {},
                "character_lifecycle_updates": arc.get("character_lifecycle_updates") or [],
                "faction_lifecycle_updates": arc.get("faction_lifecycle_updates") or [],
                "arc_review_targets": arc.get("arc_review_targets") or [],
                "blueprint_repair_targets": arc.get("blueprint_repair_targets") or [],
            }
        )
    return index


def _build_arc_bridge_checks(arcs: list[dict]) -> list[dict]:
    checks: list[dict] = []
    for idx, arc in enumerate(arcs):
        has_handoff_from_previous = bool(
            arc.get("handoff_from_previous") or arc.get("dependence_on_previous")
        )
        has_handoff_to_next = bool(arc.get("handoff_to_next") or arc.get("payoff_for_next"))
        has_arc_steps = bool(arc.get("arc_steps"))
        checks.append(
            {
                "arc_index": idx,
                "name": arc.get("name", ""),
                "requires_previous_handoff": idx > 0,
                "has_handoff_from_previous": has_handoff_from_previous,
                "has_handoff_to_next": has_handoff_to_next,
                "has_arc_steps": has_arc_steps,
                "needs_repair": (idx > 0 and not has_handoff_from_previous) or not has_arc_steps,
            }
        )
    return checks


def _json_param(conn: Connection, payload: object) -> object:
    if conn.dialect.name == "sqlite":
        return json.dumps(payload, ensure_ascii=False)
    return payload


def _backfill_arc_continuity_metadata(conn: Connection) -> None:
    if not _table_exists(conn, "volumes"):
        return
    required = {"id", "narrative_arcs", "arc_continuity_index", "arc_bridge_checks"}
    existing = {col["name"] for col in inspect(conn).get_columns("volumes")}
    if not required.issubset(existing):
        return

    rows = conn.execute(
        text("SELECT id, narrative_arcs, arc_continuity_index, arc_bridge_checks FROM volumes")
    ).mappings()
    for row in rows:
        arcs = _normalize_arcs_payload(row["narrative_arcs"])
        if not arcs:
            continue
        updates: dict[str, object] = {"id": row["id"]}
        if row["arc_continuity_index"] in (None, "", []):
            updates["arc_continuity_index"] = _json_param(conn, _build_arc_continuity_index(arcs))
        if row["arc_bridge_checks"] in (None, "", []):
            updates["arc_bridge_checks"] = _json_param(conn, _build_arc_bridge_checks(arcs))
        if len(updates) > 1:
            set_sql = ", ".join(f"{key} = :{key}" for key in updates if key != "id")
            conn.execute(text(f"UPDATE volumes SET {set_sql} WHERE id = :id"), updates)


def _migration_20260609_0001(conn: Connection) -> None:
    json_type = "JSON"
    for column in (
        "blueprint",
        "continuity_checks",
        "arc_step_refs",
        "continuity_from_previous",
        "state_delta",
        "continuity_to_next",
        "relationship_changes",
        "object_states",
        "external_pressures",
        "opening_requirements_for_next",
        "causality_links",
        "foreshadowing_tasks",
        "rhythm_profile",
    ):
        _add_column_if_missing(conn, "chapters", column, json_type)

    for column in ("arc_continuity_index", "arc_bridge_checks"):
        _add_column_if_missing(conn, "volumes", column, json_type)

    _add_column_if_missing(conn, "characters", "current_state", json_type)
    _add_column_if_missing(conn, "characters", "first_appeared_chapter", "INTEGER")
    _add_column_if_missing(conn, "characters", "first_appeared_title", "VARCHAR(200)")
    _add_column_if_missing(conn, "characters", "character_class", "VARCHAR(20)")

    for column in ("hard_rules", "tone_rules", "constraints"):
        _add_column_if_missing(conn, "world_settings", column, json_type)

    _backfill_arc_continuity_metadata(conn)


def _migration_20260609_0002(conn: Connection) -> None:
    _add_column_if_missing(conn, "projects", "project_schema_mode", "VARCHAR(30)")
    _add_column_if_missing(conn, "projects", "arc_generation_version", "VARCHAR(30)")
    _add_column_if_missing(conn, "projects", "chapter_blueprint_version", "VARCHAR(30)")
    _add_column_if_missing(conn, "projects", "continuity_upgrade_notes", "JSON")
    if _table_exists(conn, "projects"):
        conn.execute(
            text(
                "UPDATE projects SET "
                "project_schema_mode = COALESCE(project_schema_mode, 'legacy'), "
                "arc_generation_version = COALESCE(arc_generation_version, 'legacy'), "
                "chapter_blueprint_version = COALESCE(chapter_blueprint_version, 'legacy')"
            )
        )


def _migration_20260610_0003(conn: Connection) -> None:
    timestamp_type = "TIMESTAMP" if conn.dialect.name != "sqlite" else "DATETIME"
    json_type = "JSON"
    if not _table_exists(conn, "llm_call_logs"):
        conn.exec_driver_sql(
            f"""
            CREATE TABLE llm_call_logs (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NULL,
                project_name VARCHAR(200) NOT NULL DEFAULT '',
                task_id VARCHAR(36) NOT NULL DEFAULT '',
                function_name VARCHAR(100) NOT NULL DEFAULT '',
                provider_id VARCHAR(36) NOT NULL DEFAULT '',
                provider_name VARCHAR(100) NOT NULL DEFAULT '',
                provider_type VARCHAR(30) NOT NULL DEFAULT '',
                model_name VARCHAR(120) NOT NULL DEFAULT '',
                request_type VARCHAR(30) NOT NULL DEFAULT 'chat',
                status VARCHAR(20) NOT NULL DEFAULT 'success',
                system_prompt TEXT NOT NULL DEFAULT '',
                prompt TEXT NOT NULL DEFAULT '',
                response_content TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                temperature VARCHAR(20) NOT NULL DEFAULT '',
                max_tokens INTEGER NOT NULL DEFAULT 0,
                request_payload {json_type},
                response_metadata {json_type},
                created_at {timestamp_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at {timestamp_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
            )
            """
        )
    for index_name, column_name in (
        ("ix_llm_call_logs_project_id", "project_id"),
        ("ix_llm_call_logs_project_name", "project_name"),
        ("ix_llm_call_logs_task_id", "task_id"),
        ("ix_llm_call_logs_function_name", "function_name"),
        ("ix_llm_call_logs_model_name", "model_name"),
        ("ix_llm_call_logs_status", "status"),
        ("ix_llm_call_logs_created_at", "created_at"),
    ):
        conn.exec_driver_sql(f"CREATE INDEX IF NOT EXISTS {index_name} ON llm_call_logs ({column_name})")


MIGRATIONS: list[tuple[str, str, MigrationFn]] = [
    (
        "20260609_0001",
        "add narrative continuity columns and safe arc bridge metadata",
        _migration_20260609_0001,
    ),
    (
        "20260609_0002",
        "add project continuity compatibility version fields",
        _migration_20260609_0002,
    ),
    (
        "20260610_0003",
        "create llm call logs table",
        _migration_20260610_0003,
    ),
]


def run_schema_migrations(conn: Connection) -> None:
    """Apply non-destructive schema upgrades without rewriting user-created novels."""
    _ensure_migration_table(conn)
    applied = {
        row[0]
        for row in conn.exec_driver_sql("SELECT version FROM schema_migrations").fetchall()
    }
    for version, name, migration in MIGRATIONS:
        if version in applied:
            continue
        migration(conn)
        conn.execute(
            text(
                "INSERT INTO schema_migrations (version, name, applied_at) "
                "VALUES (:version, :name, :applied_at)"
            ),
            {"version": version, "name": name, "applied_at": tz_now()},
        )
