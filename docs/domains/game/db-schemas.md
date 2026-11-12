# Game Database Schema

The `games` table stores each game. Its model and initial migration are in `app.domain.game`.

| Column | Type | Nullable | Default | Constraints | Description |
| --- | --- | --- | --- | --- | --- |
| `id` | UUID | No | Generated UUID4 | Primary key | Game identifier. |
| `board` | JSON | No | Fresh 15×15 empty board | None | Board cells, initially all zero. |
| `current_player` | positive small integer | No | `1` | Must be `1` or `2`. | Player whose turn it is. |
| `status` | VARCHAR(16) | No | `in_progress` | Must be `in_progress`, `won`, or `draw`. | Game status. |
| `winner` | positive small integer | Yes | `null` | Must be `1` or `2` for a won game and null otherwise. | Winning player, if any. |
| `created_at` | timestamp | No | Set on creation | None | Creation time. |
| `updated_at` | timestamp | No | Set on save | None | Last update time. |

| Index | Columns | Type | Purpose |
| --- | --- | --- | --- |
| Primary key index | `id` | Primary key | Identifies a game. |

Check constraints enforce the player, status, winner, and status/winner consistency rules. The table has no foreign keys.
