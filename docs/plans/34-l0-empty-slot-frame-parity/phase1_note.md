# Phase 1 frame witnesses

Status: byte-witnessed; no fix or root-cause verdict. Plan 04 Phase 3 remains open.

G pins were fully streamed and verified before bounded census reads. R's historical pin is cited, not remeasured.

All 2,048 cells of L0 blockset 32 / block 0 were replayed through the hardened reader. Lookup failures forbid publication.

Full frame bytes, index reads, sections and zero-padding spans are in the deduplicated byte pools. Source rows are assembly inputs before filtering and trimming.

| Disc | Cells with frames | Frames | G frame / R empty cells |
| --- | ---: | ---: | --- |
| g_successor | 3 | 3 | [[0, 541], [0, 562], [0, 563]] |
| g_historical | 3 | 3 | [[0, 541], [0, 562], [0, 563]] |
| r | 0 | 0 | [] |

Per-cell evidence and spool source offsets:

```json
[
  {
    "cell": [
      0,
      541
    ],
    "discs": {
      "g_successor": {
        "status": "resolved",
        "reason": "indexed_leaf_frames",
        "frames": [
          {
            "leaf_path": [
              928
            ],
            "offset": 197597600,
            "length": 320,
            "sha256": "967b1d86ce25c23859a17c1332e95a6301539b8790cd45960b0f2e893ba72f07",
            "frame_class": "leaf",
            "name_count": 0,
            "background_count": 0,
            "road_count": 0,
            "payload_class": "padded_shell"
          }
        ]
      },
      "g_historical": {
        "status": "resolved",
        "reason": "indexed_leaf_frames",
        "frames": [
          {
            "leaf_path": [
              928
            ],
            "offset": 197597600,
            "length": 320,
            "sha256": "3c927c6b4868664907ab14c8a8c49fbf34d5debb8e5ef4d4a22d28e323251b48",
            "frame_class": "leaf",
            "name_count": 1,
            "background_count": 0,
            "road_count": 0,
            "payload_class": "content"
          }
        ]
      },
      "r": {
        "status": "empty_slot",
        "reason": "absent_BMT_sentinel",
        "frames": []
      }
    },
    "spool_sources": [
      {
        "source_row": 11689,
        "level": 0,
        "cell": [
          0,
          541
        ],
        "cell_offset": 248992624,
        "cell_length": 2616,
        "own": true,
        "backgrounds": []
      }
    ]
  },
  {
    "cell": [
      0,
      562
    ],
    "discs": {
      "g_successor": {
        "status": "resolved",
        "reason": "indexed_leaf_frames",
        "frames": [
          {
            "leaf_path": [
              1600
            ],
            "offset": 197597920,
            "length": 160,
            "sha256": "e22e27dfc439350e6b0ecbaf8821744a99e3d91118e9d5e7127d3ebea9e8b7b9",
            "frame_class": "leaf",
            "name_count": 0,
            "background_count": 0,
            "road_count": 0,
            "payload_class": "padded_shell"
          }
        ]
      },
      "g_historical": {
        "status": "resolved",
        "reason": "indexed_leaf_frames",
        "frames": [
          {
            "leaf_path": [
              1600
            ],
            "offset": 197597920,
            "length": 160,
            "sha256": "e22e27dfc439350e6b0ecbaf8821744a99e3d91118e9d5e7127d3ebea9e8b7b9",
            "frame_class": "leaf",
            "name_count": 0,
            "background_count": 0,
            "road_count": 0,
            "payload_class": "padded_shell"
          }
        ]
      },
      "r": {
        "status": "empty_slot",
        "reason": "absent_BMT_sentinel",
        "frames": []
      }
    },
    "spool_sources": [
      {
        "source_row": 13990,
        "level": 0,
        "cell": [
          0,
          562
        ],
        "cell_offset": 310662272,
        "cell_length": 22872,
        "own": true,
        "backgrounds": []
      }
    ]
  },
  {
    "cell": [
      0,
      563
    ],
    "discs": {
      "g_successor": {
        "status": "resolved",
        "reason": "indexed_leaf_frames",
        "frames": [
          {
            "leaf_path": [
              1632
            ],
            "offset": 197598080,
            "length": 160,
            "sha256": "0126fc2dcd7acff3f718aa72a7d210bbb6aec2a913462e34d88f6b449cd69138",
            "frame_class": "leaf",
            "name_count": 0,
            "background_count": 0,
            "road_count": 0,
            "payload_class": "padded_shell"
          }
        ]
      },
      "g_historical": {
        "status": "resolved",
        "reason": "indexed_leaf_frames",
        "frames": [
          {
            "leaf_path": [
              1632
            ],
            "offset": 197598080,
            "length": 160,
            "sha256": "0126fc2dcd7acff3f718aa72a7d210bbb6aec2a913462e34d88f6b449cd69138",
            "frame_class": "leaf",
            "name_count": 0,
            "background_count": 0,
            "road_count": 0,
            "payload_class": "padded_shell"
          }
        ]
      },
      "r": {
        "status": "empty_slot",
        "reason": "absent_BMT_sentinel",
        "frames": []
      }
    },
    "spool_sources": [
      {
        "source_row": 14169,
        "level": 0,
        "cell": [
          0,
          563
        ],
        "cell_offset": 315499152,
        "cell_length": 1256,
        "own": true,
        "backgrounds": []
      }
    ]
  }
]
```

Extra cells requiring Phase 2 disposition: {"g_historical": [], "g_successor": []}

No O03 reseat, frame suppression, K1 run, protected-disc mutation, or Phase 3 close was performed.
