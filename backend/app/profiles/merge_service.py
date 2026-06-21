"""Merge service for profile import data.

Implements the fill-empty merge strategy:
  - Scalar fields: fill when existing value is None, never overwrite populated fields
  - List fields: append items not already present (dedup by key), preserve existing order
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.profiles.schemas import ImportedProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _dedup_key_institution_degree(item: dict) -> str:
    """Generate a dedup key for an education entry."""
    return f"{item.get('institution', '')}|{item.get('degree', '')}"


def _dedup_key_company_role(item: dict) -> str:
    """Generate a dedup key for a work experience entry."""
    return f"{item.get('company', '')}|{item.get('role', '')}"


def _merge_list(
    existing: list | None,
    incoming: list[dict],
    key_fn: Callable[[dict], str],
) -> list:
    """Merge two lists, appending items from ``incoming`` not already present.

    Deduplication is based on the key returned by ``key_fn`` (e.g., ``"name"``,
    ``"institution|degree"``). Preserves the order of existing items first,
    then appends new incoming items.
    """
    existing_items = existing or []
    existing_keys = {key_fn(item) for item in existing_items}
    merged = list(existing_items)

    for item in incoming:
        k = key_fn(item)
        if k not in existing_keys:
            existing_keys.add(k)
            merged.append(item)

    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class MergeService:
    """Merge imported profile data into an existing profile.

    Uses a fill-empty (additive) strategy:
    - Scalar fields (headline, summary, URLs) are only set when the existing
      value is ``None``. Populated fields are never overwritten.
    - List fields (skills, education, work_experience) append new items and
      skip duplicates by a logical key.
    """

    @staticmethod
    def merge(existing: dict, imported: ImportedProfile) -> dict:
        """Merge ``imported`` profile data into the ``existing`` profile dict.

        Parameters
        ----------
        existing:
            The current profile fields as a flat dict. Expected keys include
            ``headline``, ``summary``, ``linkedin_url``, ``infojobs_url``,
            ``cv_file_url``, ``skills``, ``education``, ``work_experience``.
        imported:
            The ``ImportedProfile`` instance with data from an external source.

        Returns
        -------
        dict
            A dict with ALL import fields set to their merged values.
            Callers can use this to update the ORM model directly.
        """
        # --- Scalar fields: fill-empty ---
        result: dict = {}

        _fill_if_none(result, existing, imported, "headline")
        _fill_if_none(result, existing, imported, "summary")
        _fill_if_none(result, existing, imported, "linkedin_url")
        _fill_if_none(result, existing, imported, "infojobs_url")
        _fill_if_none(result, existing, imported, "cv_file_url")

        # --- List fields: append-new ---
        incoming_skills = [s.model_dump() for s in (imported.skills or [])]
        result["skills"] = _merge_list(
            existing.get("skills"),
            incoming_skills,
            key_fn=lambda x: x.get("name", ""),
        )

        incoming_education = [e.model_dump() for e in (imported.education or [])]
        result["education"] = _merge_list(
            existing.get("education"),
            incoming_education,
            key_fn=_dedup_key_institution_degree,
        )

        incoming_experience = [
            e.model_dump() for e in (imported.work_experience or [])
        ]
        result["work_experience"] = _merge_list(
            existing.get("work_experience"),
            incoming_experience,
            key_fn=_dedup_key_company_role,
        )

        return result


def _fill_if_none(
    result: dict,
    existing: dict,
    imported: ImportedProfile,
    field: str,
) -> None:
    """Set ``result[field]`` to the imported value if existing is ``None``.

    If the existing value is not ``None``, the existing value is preserved.
    If both are ``None``, the result keeps ``None``.
    """
    existing_val = existing.get(field)
    imported_val = getattr(imported, field, None)

    if existing_val is not None:
        result[field] = existing_val
    elif imported_val is not None:
        result[field] = imported_val
    else:
        result[field] = None
