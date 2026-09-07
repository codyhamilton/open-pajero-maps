"""Link ID Registry: joint assignment of Link IDs between the main map layer
(``RoadFrame``/``RoadLink``) and the route-planning layer (Ch.10 RP links).

Link identity (docs/design/target-disc.md, "Link identity", settled): "A
road link's identity is ``(osm_way_id, ordinal)``, ordinal assigned at split
time in the map-layer stage, and it is the same key in every layer that
references a link." ``osm_way_id`` alone is *not* a unique key: a single OSM
way is clipped into one sub-polyline ("chain") per parcel it crosses, and
each chain becomes its own ``RoadLink`` with its own ``ordinal`` (0-based,
assigned in chain order along the way's node sequence at the moment
``osm_to_parcel_geometry.split_polyline_by_parcel`` produces it -- see that
function's docstring and ``RoadLink.ordinal`` in ``kiwiw/model.py``).

Ordinals are per *level*: the parcel split (and therefore the set of chains
and their ordinals) is computed independently at each zoom level, so the
same way can legitimately split differently -- and get different ordinals
-- at different levels. This registry is shared across levels, so its key
is the triple ``(level, osm_way_id, ordinal)``, not just ``(osm_way_id,
ordinal)``.

Usage
-----
1.  Build map-layer parcels (``RoadFrame``/``RoadLink`` lists) per level --
    e.g. from ``osm_to_parcel_geometry.extract_parcel_geometry`` -- so every
    synthetic ``RoadLink`` carries its ``osm_way_id`` and ``ordinal``.
2.  Call ``registry.assign(level, osm_way_id, ordinal)`` for each such link
    to get its ``link_id``. Calling it again with the same key is
    idempotent: it returns the same ``link_id``.
3.  When building RP-layer (Ch.10) records that reference a link, call
    ``registry.lookup(level, osm_way_id, ordinal)`` to resolve the same id.

Note on scope: this registry mints stable, arbitrary ``link_id`` values
keyed on the design doc's join key. It does not itself compute positional
indices within an on-disc ``RoadFrame`` link list; a caller that needs a
link's position in its parcel's link list still derives that from the
parcel's own link ordering (unrelated to this registry).
"""
from __future__ import annotations

from typing import Iterator, Optional

# The registry key: (level, osm_way_id, ordinal). See module docstring for
# why level is part of the key (ordinals are per-level, not global).
LinkKey = tuple[int, int, int]


class LinkIdRegistry:
    """Map ``(level, osm_way_id, ordinal) → link_id``.

    ``link_id`` values are minted in first-assign order (0, 1, 2, ...);
    re-assigning an already-known key returns the same id it was first
    given. Different ordinals for the same ``(level, osm_way_id)`` are
    different keys and therefore get different ids.
    """

    def __init__(self) -> None:
        self._table: dict[LinkKey, int] = {}

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def assign(self, level: int, osm_way_id: int, ordinal: int) -> int:
        """Return the ``link_id`` for ``(level, osm_way_id, ordinal)``,
        minting a new one (the next unused integer) on first sight and
        returning the existing one on every subsequent call with the same
        key.
        """
        key: LinkKey = (level, osm_way_id, ordinal)
        link_id = self._table.get(key)
        if link_id is None:
            link_id = len(self._table)
            self._table[key] = link_id
        return link_id

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def lookup(self, level: int, osm_way_id: int, ordinal: int) -> Optional[int]:
        """Return the ``link_id`` already assigned to
        ``(level, osm_way_id, ordinal)``, or ``None`` if it has never been
        assigned (e.g. the way/chain was filtered out of the map layer).
        """
        return self._table.get((level, osm_way_id, ordinal))

    def items(self) -> Iterator[tuple[LinkKey, int]]:
        """Yield ``((level, osm_way_id, ordinal), link_id)`` pairs in
        deterministic order (sorted by key), independent of assignment
        order.
        """
        return iter(sorted(self._table.items()))

    def __len__(self) -> int:
        return len(self._table)

    def __contains__(self, key: LinkKey) -> bool:
        return key in self._table
