# Game Database Schema

The `games` table stores each game. Its model and initial migration are in `app.domain.game`. Django supplies the defaults and automatic timestamps shown below. The table has no database column defaults.

| Column | PostgreSQL type | Nullable | Django default or automatic value | Constraints | Description |
| --- | --- | --- | --- | --- | --- |
| `id` | UUID | No | Generated UUID4 | Primary key | Game identifier. |
| `board` | JSONB | No | Fresh 15×15 empty board | 15 rows of 15 integer cells with values `0`, `1`, or `2`. | Board cells, initially all zero. |
| `current_player` | SMALLINT | No | `1` | Must be `1` or `2`. | Player whose turn it is, or the last mover when the game has ended. |
| `status` | VARCHAR(16) | No | `in_progress` | Must be `in_progress`, `won`, or `draw`. | Game status. |
| `winner` | SMALLINT | Yes | `null` | Must be `1` or `2` for a won game and null otherwise. | Winning player, if any. |
| `created_at` | TIMESTAMP WITH TIME ZONE | No | Set on creation | None | Creation time. |
| `updated_at` | TIMESTAMP WITH TIME ZONE | No | Set on save | None | Last update time. |

| Index | Columns | Type | Purpose |
| --- | --- | --- | --- |
| `games_pkey` (B-tree) | `id` | Primary key | Identifies a game. |

Check constraints enforce the player, status, winner, and status/winner consistency rules. Django's positive small integer fields also produce the PostgreSQL checks `games_current_player_check` and `games_winner_check` for nonnegative values. The table has no foreign keys.

The PostgreSQL board constraint applies to all database writes and rejects decimal cells such as `1.0`, consistent with the game service's integer-cell validation.

## Generated reference evaluation

On 2026-11-20 at `d1edcb7`, a fresh, isolated PostgreSQL 17 database applied only the reviewed [initial game migration](../../../src/app/domain/game/migrations/0001_initial.py). The probe confirmed seven columns, `winner` as the only nullable column, no database defaults, the primary key index, five named game constraints, and the two nonnegative checks. This agrees with the migration and the [game model](../../../src/app/domain/game/model/game.py).

From a fresh worktree, run the initialization and startup commands in the [development setup](../../../README.md#development-setup). Preview `bash scripts/compose.sh exec -T app uv run python manage.py migrate game 0001_initial --plan`, confirm only `game.0001_initial` is listed, and rerun the command without `--plan`. Run the following metadata probe twice and save each stdout to a separate scratch file.

```bash
bash scripts/compose.sh exec -T db psql -X -P pager=off -v ON_ERROR_STOP=1 -U postgres -d gomoku -c '\d+ public.games'
```

`diff -u` exited 0 with no differences between the two probe outputs. In a scratch copy, changing `status` from `character varying(16)` to `character varying(8)` made it exit 1 and identify that row. The probe reads table metadata and leaves data rows untouched.

For a documentation audit, compare one probe with the column and index tables and the constraint descriptions above. Match every column by name and compare its PostgreSQL type, nullability, and database default. Check the index name and definition and the meaning of each constraint. A blank value in the probe's default column means there is no database default. Check Django defaults separately against the model. Report each mismatch in the audit with the field or constraint, its documented definition, and the observed definition. For example, if the probe reports `character varying(8)` for `status`, record that the database shows `VARCHAR(8)` and this reference says `VARCHAR(16)`, even when two consecutive probes match.

Keep the probe as an on-demand verification step. For the single table, a checked-in snapshot would duplicate the physical structure and add a regeneration and review step, while Django defaults, timestamp behavior, and game semantics would still need the maintained reference. Revisit generation if additional tables or frequent schema changes make direct inspection costly.
