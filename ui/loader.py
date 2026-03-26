"""
Data loaders for the AI Software Factory dashboard.
All functions are Streamlit-cache-decorated; import only from here.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

import streamlit as st

from autonomous_delivery.ui.config import DEMO_OUTPUT, STAGE_ORDER


@st.cache_data(ttl=5)
def load_readme() -> dict[str, str]:
    path = DEMO_OUTPUT / "README.md"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    data: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"[-*]\s+([\w_]+):\s+(.+)", line) or re.match(r"\*\*(.+?)\*\*[:\s]+(.+)", line)
        if m:
            data[m.group(1).strip()] = m.group(2).strip()
    return data


@st.cache_data(ttl=5)
def load_artifacts() -> list[dict[str, Any]]:
    """Return list of artifact dicts, each with parsed JSON metadata + md content."""
    arts_dir = DEMO_OUTPUT / "artifacts"
    if not arts_dir.exists():
        return []

    md_by_uuid: dict[str, Any] = {}
    for f in arts_dir.glob("*.md"):
        uuid = f.stem.split("_")[0]
        md_by_uuid[uuid] = f

    artifacts = []
    for json_file in sorted(arts_dir.glob("*.json")):
        uuid = json_file.stem.split("_")[0]
        artifact_type = "_".join(json_file.stem.split("_")[1:])
        try:
            meta = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        md_content = ""
        if uuid in md_by_uuid:
            try:
                md_content = md_by_uuid[uuid].read_text(encoding="utf-8")
            except Exception:
                pass

        artifacts.append({
            "uuid": uuid,
            "type": artifact_type,
            "stage": meta.get("stage", "UNKNOWN"),
            "version": meta.get("version", 1),
            "created_by": meta.get("created_by", ""),
            "status": meta.get("status", ""),
            "meta": meta,
            "md": md_content,
        })

    def _sort_key(item: dict[str, Any]) -> tuple[int, int, str, str]:
        stage = str(item.get("stage", "UNKNOWN"))
        try:
            stage_index = STAGE_ORDER.index(stage)
        except ValueError:
            stage_index = len(STAGE_ORDER)
        version = int(item.get("version", 1) or 1)
        created_at = str(item.get("meta", {}).get("created_at", ""))
        uuid = str(item.get("uuid", ""))
        return stage_index, version, created_at, uuid

    artifacts.sort(key=_sort_key)
    return artifacts


@st.cache_data(ttl=5)
def load_events() -> list[dict[str, Any]]:
    path = DEMO_OUTPUT / "events.jsonl"
    if not path.exists():
        return []
    events = []
    seen_event_ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            event_id = str(event.get("event_id", ""))
            if event_id:
                if event_id in seen_event_ids:
                    continue
                seen_event_ids.add(event_id)
            events.append(event)
        except Exception:
            pass
    events.sort(key=lambda e: (str(e.get("timestamp", "")), str(e.get("event_id", ""))))
    return events


@st.cache_data(ttl=5)
def load_snapshots() -> dict[str, list[dict]]:
    """Return {stage_key: [snapshot, ...]} ordered by step number."""
    snaps_dir = DEMO_OUTPUT / "state_snapshots"
    if not snaps_dir.exists():
        return {}
    by_stage: dict[str, list[dict]] = defaultdict(list)
    for f in sorted(snaps_dir.glob("step_*.json")):
        try:
            snap = json.loads(f.read_text(encoding="utf-8"))
            stage = snap.get("current_stage", "UNKNOWN")
            snap["_filename"] = f.name
            by_stage[stage].append(snap)
        except Exception:
            pass
    return dict(by_stage)
