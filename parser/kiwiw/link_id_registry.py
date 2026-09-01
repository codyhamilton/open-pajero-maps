"""Link ID Registry: joint assignment of Link IDs between the main map layer
(``RoadFrame``/``RoadLink``) and the route-planning layer (Ch.10 RP links).

On the real disc each ``RoadLink`` is identified by its *positional index*
within its parcel's ``RoadFrame`` link list (0-based).  The Ch.10 Link Cost
Record's "Link ID Number" fields (``link_id_origin`` / ``link_id_dest_delta``)
reference these indices.

The ``LinkIdRegistry`` maps an OSM way ID to the ``(parcel_key, positional_index)``
of the ``RoadLink`` derived from that way.  When building the RP layer the
caller looks up each OSM way ID in the registry to retrieve the positional
index and writes it into the ``RpLinkCost.link_id_origin`` field.

Usage (typical pipeline order)
-------------------------------
1.  Build map-layer parcels (``RoadFrame`` lists) -- e.g. from
    ``osm_to_parcel_geometry.extract_parcel_geometry``.
2.  Call ``LinkIdRegistry.from_parcels(parcel_dict)`` to derive the registry
    from all parcel ``RoadLink`` objects that carry a non-None ``osm_way_id``.
3.  Call ``registry.assign_link_ids(parcel_dict)`` to stamp each
    ``RoadLink.link_id`` with its positional index (so the map-layer IR is
    self-consistent even before the RP layer consumes it).
4.  When building ``RpGraph`` objects, call
    ``registry.lookup(osm_way_id)`` for each RP link to get the positional
    index, and store it as ``RpLinkCost.link_id_origin``.

Note: ``osm_way_id`` is the primary join key.  A single OSM way can split
into *multiple* sub-polylines when clipped to parcel boundaries, so the
registry stores only the **first** occurrence encountered (lowest parcel key,
lowest position within that parcel).  In practice, the RP layer uses the same
splitting logic and assigns one cost record per (parcel, sub-polyline) pair,
so callers that need finer granularity should build their own per-(way, chain)
mapping on top of this registry.
"""
from __future__ import annotations

from typing import Optional

# A parcel key is whatever the caller uses to identify a parcel.  In
# osm_to_parcel_geometry.py it is a (level, cell_ix, cell_iy) tuple;
# in tests it can be any hashable value.
ParcelKey = object


class LinkIdRegistry:
    """Map ``osm_way_id → (parcel_key, positional_index_in_parcel)``."""

    def __init__(self) -> None:
        # {osm_way_id: (parcel_key, index)}
        self._table: dict[int, tuple[object, int]] = {}

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def register(self, osm_way_id: int, parcel_key: object, index: int) -> None:
        """Register one entry.  If ``osm_way_id`` is already present, the
        existing entry is kept (first-in-wins policy -- see module docstring).
        """
        if osm_way_id not in self._table:
            self._table[osm_way_id] = (parcel_key, index)

    @classmethod
    def from_parcels(
        cls,
        parcel_dict: "dict[object, list]",
    ) -> "LinkIdRegistry":
        """Build a registry from a dict of ``parcel_key → list[RoadLink]``.

        Only ``RoadLink`` objects whose ``osm_way_id`` is not ``None`` are
        indexed.  The positional index is the 0-based position of each link
        within its parcel's list.

        ``parcel_dict`` can be either:
        - a plain ``dict`` mapping parcel key to a ``list[RoadLink]``, or
        - a ``dict`` mapping parcel key to a sub-dict ``{"roads": list[RoadLink], ...}``
          (the shape produced by ``osm_to_parcel_geometry.extract_parcel_geometry``).
        """
        registry = cls()
        for parcel_key, content in parcel_dict.items():
            if isinstance(content, dict):
                links = content.get("roads", [])
            else:
                links = content
            for idx, link in enumerate(links):
                way_id = getattr(link, "osm_way_id", None)
                if way_id is not None:
                    registry.register(way_id, parcel_key, idx)
        return registry

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def lookup(
        self,
        osm_way_id: int,
        fallback_index: int = 0,
    ) -> tuple[Optional[object], int]:
        """Return ``(parcel_key, positional_index)`` for ``osm_way_id``.

        If ``osm_way_id`` is not in the registry (e.g. the way was filtered
        out of the map layer), returns ``(None, fallback_index)``.
        """
        if osm_way_id in self._table:
            return self._table[osm_way_id]
        return None, fallback_index

    def index_for(self, osm_way_id: int, fallback_index: int = 0) -> int:
        """Convenience: return only the positional index (most common use
        when building ``RpLinkCost.link_id_origin``)."""
        return self.lookup(osm_way_id, fallback_index)[1]

    # ------------------------------------------------------------------
    # Side-effect: stamp RoadLink.link_id fields
    # ------------------------------------------------------------------

    @staticmethod
    def assign_link_ids(parcel_dict: "dict[object, list]") -> None:
        """Stamp each ``RoadLink.link_id`` with its 0-based positional index
        within its parcel's road list.  This mutates the ``RoadLink`` objects
        in place.

        Call this after building the map-layer parcels so the IR is
        self-consistent (``RoadLink.link_id`` always equals the link's position
        in the list, matching the on-disc implicit numbering convention).

        Accepts the same ``parcel_dict`` shapes as ``from_parcels``.
        """
        for content in parcel_dict.values():
            if isinstance(content, dict):
                links = content.get("roads", [])
            else:
                links = content
            for idx, link in enumerate(links):
                link.link_id = idx

    def __len__(self) -> int:
        return len(self._table)

    def __contains__(self, osm_way_id: int) -> bool:
        return osm_way_id in self._table
