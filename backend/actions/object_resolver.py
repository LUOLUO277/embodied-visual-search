from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolvedObject:
    object_id: str
    object_type: str
    indexed_name: str
    metadata: dict[str, Any]


@dataclass
class ResolveResult:
    success: bool
    resolved: ResolvedObject | None = None
    message: str = ""
    candidates: list[str] = field(default_factory=list)


class ObjectResolver:
    def __init__(self, metadata: dict[str, Any]) -> None:
        self.metadata = metadata or {}
        self.objects = list(self.metadata.get("objects") or [])
        self.agent_position = ((self.metadata.get("agent") or {}).get("position") or {})
        self.by_object_id: dict[str, dict[str, Any]] = {}
        self.by_object_type: dict[str, list[dict[str, Any]]] = {}
        self.by_indexed_name: dict[str, dict[str, Any]] = {}
        self._build_indexes()

    def _build_indexes(self) -> None:
        deduped_by_type: dict[str, list[dict[str, Any]]] = {}
        seen_keys: set[tuple[str, float, float]] = set()
        for obj in self.objects:
            object_id = str(obj.get("objectId") or obj.get("name") or obj.get("objectType") or "")
            object_type = str(obj.get("objectType") or obj.get("name") or "Unknown")
            if not object_id:
                continue
            self.by_object_id[object_id] = obj
            self.by_object_type.setdefault(object_type.lower(), []).append(obj)
            position = obj.get("position") or {}
            dedup_key = (
                object_type.lower(),
                round(float(position.get("x", 0.0)), 2),
                round(float(position.get("z", 0.0)), 2),
            )
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            deduped_by_type.setdefault(object_type, []).append(obj)

        for object_type, objects in deduped_by_type.items():
            ordered = sorted(objects, key=self._sort_key)
            for index, obj in enumerate(ordered, start=1):
                self.by_indexed_name[f"{object_type}_{index}".lower()] = obj

    def resolve(self, argument: str | None) -> ResolveResult:
        if not argument or not argument.strip():
            return ResolveResult(success=False, message="Action requires an object argument.")
        text = argument.strip()
        lowered = text.lower()
        if lowered.startswith("objectid:"):
            return self._resolve_object_id(text.split(":", 1)[1].strip())
        if lowered.startswith("objecttype:"):
            return self._resolve_object_type(text.split(":", 1)[1].strip())
        if lowered.startswith("indexed:"):
            return self._resolve_indexed(text.split(":", 1)[1].strip())
        if text in self.by_object_id:
            return self._wrap(self.by_object_id[text])
        if lowered in self.by_indexed_name:
            return self._wrap(self.by_indexed_name[lowered])
        exact_type_matches = self.by_object_type.get(lowered)
        if exact_type_matches:
            return self._resolve_from_candidates(exact_type_matches, text)
        return ResolveResult(success=False, message=f"Unable to resolve object '{text}'.")

    def resolve_visible_ref(self, ref: str | None, visible_ref_map: dict[str, str] | None) -> ResolveResult:
        if not ref or not ref.strip():
            return ResolveResult(success=False, message="Action requires a visible object ref.")
        if not visible_ref_map:
            return ResolveResult(success=False, message="No visible objects are available for interaction.")
        object_id = visible_ref_map.get(ref.strip())
        if not object_id:
            return ResolveResult(success=False, message=f"Object '{ref}' is not visible in the current observation.")
        return self._resolve_object_id(object_id)

    def _resolve_object_id(self, object_id: str) -> ResolveResult:
        obj = self.by_object_id.get(object_id)
        if obj is None:
            return ResolveResult(success=False, message=f"ObjectId '{object_id}' not found.")
        return self._wrap(obj)

    def _resolve_object_type(self, object_type: str) -> ResolveResult:
        candidates = self.by_object_type.get(object_type.lower()) or []
        if not candidates:
            return ResolveResult(success=False, message=f"Object type '{object_type}' not found.")
        return self._resolve_from_candidates(candidates, object_type)

    def _resolve_indexed(self, indexed_name: str) -> ResolveResult:
        obj = self.by_indexed_name.get(indexed_name.lower())
        if obj is None:
            return ResolveResult(success=False, message=f"Indexed object '{indexed_name}' not found.")
        return self._wrap(obj)

    def _resolve_from_candidates(self, candidates: list[dict[str, Any]], label: str) -> ResolveResult:
        visible = [obj for obj in candidates if obj.get("visible")]
        if len(visible) == 1:
            return self._wrap(visible[0])
        if len(visible) > 1:
            ranked_visible = sorted(visible, key=self._sort_key)
            candidate_names = [self.indexed_name_for(obj) for obj in ranked_visible[:5]]
            return ResolveResult(
                success=False,
                message=f"Ambiguous object '{label}'. Use an indexed name such as {', '.join(candidate_names)}.",
                candidates=candidate_names,
            )
        if len(candidates) == 1:
            return self._wrap(candidates[0])
        ranked = sorted(candidates, key=self._distance_to_agent)
        if not ranked:
            return ResolveResult(success=False, message=f"Object '{label}' not found.")
        top_distance = self._distance_to_agent(ranked[0])
        tied = [obj for obj in ranked if abs(self._distance_to_agent(obj) - top_distance) < 1e-4]
        if len(tied) > 1:
            candidate_names = [self.indexed_name_for(obj) for obj in tied[:5]]
            return ResolveResult(
                success=False,
                message=f"Ambiguous object '{label}'. Nearby candidates: {', '.join(candidate_names)}.",
                candidates=candidate_names,
            )
        return self._wrap(ranked[0])

    def indexed_name_for(self, obj: dict[str, Any]) -> str:
        object_id = str(obj.get("objectId") or "")
        for name, candidate in self.by_indexed_name.items():
            if str(candidate.get("objectId") or "") == object_id:
                parts = name.split("_")
                return f"{parts[0]}_{parts[1]}"
        return str(obj.get("objectType") or object_id)

    def legal_navigations(self) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        for obj in self.objects:
            object_type = str(obj.get("objectType") or "")
            indexed_name = self.indexed_name_for(obj)
            include = bool(obj.get("visible") or obj.get("receptacle") or obj.get("openable") or object_type in {"Sofa", "Desk", "CounterTop", "Cabinet", "Drawer", "Fridge", "Sink"})
            if not include:
                continue
            for candidate in [indexed_name, object_type]:
                if candidate and candidate not in seen:
                    seen.add(candidate)
                    names.append(candidate)
        return names[:80]

    def legal_interactions(self) -> list[dict[str, Any]]:
        interactions: list[dict[str, Any]] = []
        for obj in self.objects:
            if not obj.get("visible"):
                continue
            indexed_name = self.indexed_name_for(obj)
            base = {
                "object": indexed_name,
                "objectType": str(obj.get("objectType") or ""),
                "objectId": str(obj.get("objectId") or ""),
            }
            if obj.get("openable"):
                interactions.append({**base, "action": "close" if obj.get("isOpen") else "open"})
            if obj.get("pickupable"):
                interactions.append({**base, "action": "pickup"})
            if obj.get("toggleable"):
                interactions.append({**base, "action": "toggle"})
            if obj.get("receptacle"):
                interactions.append({**base, "action": "put in"})
        return interactions[:120]

    def metadata_summary(self) -> dict[str, Any]:
        visible = [self.indexed_name_for(obj) for obj in self.objects if obj.get("visible")]
        return {
            "visible_count": len(visible),
            "visible_objects": visible[:20],
            "inventory_count": len(self.metadata.get("inventoryObjects") or []),
        }

    def _wrap(self, obj: dict[str, Any]) -> ResolveResult:
        return ResolveResult(
            success=True,
            resolved=ResolvedObject(
                object_id=str(obj.get("objectId") or ""),
                object_type=str(obj.get("objectType") or "Unknown"),
                indexed_name=self.indexed_name_for(obj),
                metadata=obj,
            ),
        )

    def _sort_key(self, obj: dict[str, Any]) -> tuple[int, float, float, str]:
        position = obj.get("position") or {}
        return (
            0 if obj.get("visible") else 1,
            round(float(position.get("x", 0.0)), 2),
            round(float(position.get("z", 0.0)), 2),
            str(obj.get("objectId") or ""),
        )

    def _distance_to_agent(self, obj: dict[str, Any]) -> float:
        position = obj.get("position") or {}
        return math.dist(
            (
                float(self.agent_position.get("x", 0.0)),
                float(self.agent_position.get("y", 0.0)),
                float(self.agent_position.get("z", 0.0)),
            ),
            (
                float(position.get("x", 0.0)),
                float(position.get("y", 0.0)),
                float(position.get("z", 0.0)),
            ),
        )
