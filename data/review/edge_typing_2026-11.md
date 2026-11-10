# Edge typing by schema definition (2026-11)

Applied mechanically on the owner's instruction; no edge was judged individually.

## Rule

The project defines the two edge types by the kinds of node they join:

- About modal (`visualization/index.html`): connections are "affiliations" (institutional relationships) or "personal" (direct interpersonal connections).
- `data/add_type_column.py --prefill`: person-person = `personal`, otherwise = `affiliation`.
- The editor and the schema add nothing narrower. `personal` does not mean "documented friendship"; `needs_review` only marks personal edges with no shared institution.

So:

- `unknown`, person-person -> `personal` (280 edges)
- `unknown`, person-institution -> `affiliation` (2 edges)
- `affiliation`, person-person -> `personal` (3 edges)

`needs_review` was 0 on all 285 edges before the change and is still 0. They were changed with `database.batch_update_edge_type()`, which does not flag edges.

## Counts

| type | before | after |
|---|---|---|
| affiliation | 5252 | 5251 |
| personal | 141 | 424 |
| unknown | 282 | 0 |

## Affected edges

`affiliation` -> `personal`: 530 (Iris Origo - Bayard Cutting), 1101 (Gabriele d'Annunzio - Arthur Livingston), 5726 (Franco Lalli - Marcello Girosi)

`unknown` -> `affiliation`: 1457 (Oriana Fallaci - Horizon Press Publishers), 1542 (William Burroughs - Olympia Press)

`unknown` -> `personal` (280 edges; names and shared institutions in `data/review/unknown_edges.csv`):
5, 7, 19, 20, 24, 64, 66, 69, 70, 74, 75, 77, 84, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 190, 192, 194, 195, 199, 200, 217, 218, 220, 222, 239, 240, 253, 255, 274, 276, 277, 278, 285, 299, 300, 301, 302, 303, 304, 306, 307, 308, 309, 310, 360, 361, 363, 364, 367, 368, 369, 370, 443, 445, 446, 448, 449, 450, 451, 453, 532, 533, 541, 542, 543, 544, 549, 550, 590, 591, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 614, 617, 620, 621, 622, 623, 624, 625, 639, 640, 641, 642, 643, 647, 649, 650, 651, 652, 654, 655, 656, 659, 671, 674, 675, 679, 680, 682, 685, 694, 705, 716, 750, 751, 752, 756, 758, 771, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 784, 785, 789, 790, 791, 793, 796, 813, 824, 825, 826, 841, 869, 870, 871, 872, 874, 875, 877, 878, 879, 969, 970, 971, 972, 973, 974, 1031, 1032, 1033, 1097, 1098, 1099, 1100, 1102, 1133, 1386, 1387, 1388, 1390, 1391, 1392, 1393, 1394, 1395, 1396, 1397, 1398, 1416, 1429, 1430, 1431, 1446, 1447, 1449, 1459, 1463, 1464, 1465, 1467, 1469, 1482, 1484, 1489, 1490, 1491, 1492, 1493, 1494, 1495, 1496, 1497, 1498, 1499, 1500, 1501, 1503, 1511, 1513, 1519, 1524, 1532, 1533, 1535, 1536, 1537, 1538, 1539, 1540, 1545, 1546, 1552, 1553, 1554, 1555, 1578, 1579, 1580, 1581, 1584, 1592, 1627, 1628, 1629, 1630, 1633, 1634, 1636, 1637, 1651, 1664, 2025, 2027, 2032, 2060, 2066, 2074, 2076, 2077, 2089, 2093, 2096, 2110, 2113, 2128, 2131, 2132, 2133, 2134, 2135, 2139, 2146, 2147, 2149, 2154, 2172, 2180, 2182, 2198

## Reversing

From `data/editor/`:

```python
import database as db
db.backup_db()
db.batch_update_edge_type([5, 7, 19, 20, 24, 64, 66, 69, 70, 74, 75, 77, 84, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 190, 192, 194, 195, 199, 200, 217, 218, 220, 222, 239, 240, 253, 255, 274, 276, 277, 278, 285, 299, 300, 301, 302, 303, 304, 306, 307, 308, 309, 310, 360, 361, 363, 364, 367, 368, 369, 370, 443, 445, 446, 448, 449, 450, 451, 453, 532, 533, 541, 542, 543, 544, 549, 550, 590, 591, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 614, 617, 620, 621, 622, 623, 624, 625, 639, 640, 641, 642, 643, 647, 649, 650, 651, 652, 654, 655, 656, 659, 671, 674, 675, 679, 680, 682, 685, 694, 705, 716, 750, 751, 752, 756, 758, 771, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 784, 785, 789, 790, 791, 793, 796, 813, 824, 825, 826, 841, 869, 870, 871, 872, 874, 875, 877, 878, 879, 969, 970, 971, 972, 973, 974, 1031, 1032, 1033, 1097, 1098, 1099, 1100, 1102, 1133, 1386, 1387, 1388, 1390, 1391, 1392, 1393, 1394, 1395, 1396, 1397, 1398, 1416, 1429, 1430, 1431, 1446, 1447, 1449, 1459, 1463, 1464, 1465, 1467, 1469, 1482, 1484, 1489, 1490, 1491, 1492, 1493, 1494, 1495, 1496, 1497, 1498, 1499, 1500, 1501, 1503, 1511, 1513, 1519, 1524, 1532, 1533, 1535, 1536, 1537, 1538, 1539, 1540, 1545, 1546, 1552, 1553, 1554, 1555, 1578, 1579, 1580, 1581, 1584, 1592, 1627, 1628, 1629, 1630, 1633, 1634, 1636, 1637, 1651, 1664, 2025, 2027, 2032, 2060, 2066, 2074, 2076, 2077, 2089, 2093, 2096, 2110, 2113, 2128, 2131, 2132, 2133, 2134, 2135, 2139, 2146, 2147, 2149, 2154, 2172, 2180, 2182, 2198, 1457, 1542], 'unknown')
db.batch_update_edge_type([530, 1101, 5726], 'affiliation')
```

Then regenerate `visualization/graph.json`. Edge type does not enter `shared_institutions`, so nothing else needs recomputing.
