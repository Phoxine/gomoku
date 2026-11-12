# Game Database Schema

The `games` table stores each game. Its model and initial migration are in `app.domain.game`.

| Column | Type | Constraints and meaning |
| --- | --- | --- |
| `id` | UUID | Primary key; generated with UUID4. |
| `board` | JSON | Required; defaults to a fresh 15×15 zero-filled board. |
| `current_player` | positive small integer | Required; defaults to 1; must be 1 or 2. |
| `status` | varchar(16) | Required; defaults to `in_progress`; permitted values are `in_progress`, `won`, and `draw`. |
| `winner` | positive small integer | Nullable; must be 1 or 2 for a won game and null otherwise. |
| `created_at` | timestamp | Required; set on creation. |
| `updated_at` | timestamp | Required; updated on save. |

The primary key is indexed. Check constraints enforce player, status, winner, and status/winner consistency. There are no foreign keys.
