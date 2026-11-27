# Game API

The API creates and retrieves games and accepts moves. It has no authentication or participant authorization: anyone with a game UUID can read and update that game. Authentication and authorization must be added before exposing the API where that access is inappropriate.

## Game responses

Responses representing games contain the following fields. Board cells are indexed as `board[y][x]`.

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID string | Game identifier. |
| `board` | array of 15 arrays of 15 integers | `0` is empty; `1` and `2` are players' stones. |
| `current_player` | integer | Player whose turn is next, or the last mover when the game has ended. |
| `status` | string | `in_progress`, `won`, or `draw`. |
| `winner` | integer or null | Winning player (`1` or `2`) for a won game. Otherwise null. |
| `mode` | string | `two_player` or `cpu`. Games saved before CPU mode use `two_player`. |
| `forbidden_move_policy` | string | `off`, `warn`, or `loss`. Saved at creation. Older games use `off`. |
| `result_reason` | string or null | `overline`, `double_four`, or `double_three` for a black forbidden-move loss, or `no_legal_black_move` when white wins under Warn because no legal black move remains. Null for other outcomes and active games. |
| `revision` | integer | Number of occupied cells, from `0` through `225`. Each accepted stone increments it by one. |

A CPU game is waiting for the CPU when `mode` is `cpu`, `status` is `in_progress`, and `current_player` is `2`.

## Shared HTTP behavior

For POST requests, send the CSRF cookie and its `csrftoken` value in the `X-CSRFToken` header, as the game's browser client does. Form POSTs to create a game can supply the token in the `csrfmiddlewaretoken` field with the cookie. JSON move requests use the header. When the CSRF check fails, Django returns `403 Forbidden` with its default error page. See [Django's CSRF guidance](https://docs.djangoproject.com/en/6.1/howto/csrf/).

A malformed UUID does not match the route and returns Django's default `404` response. On a matching route, unsupported methods receive `405 Method Not Allowed` after middleware checks such as CSRF.

After a move conflict or a lost POST response, fetch the saved state before accepting further input. A structured `forbidden_move` response under Warn confirms the rejected move left the saved position unchanged, so the caller can show the reason and let black retry.

## Get CSRF cookie

Obtain the CSRF cookie required for state-changing requests.

`GET /api/v1/csrf/`

Response `200 OK` sets the `csrftoken` cookie:

```json
{"detail": "CSRF cookie set"}
```

## Create a game

Create an empty game with black to move.

`POST /api/v1/games/`

To select the mode or forbidden-move policy, send an `application/json` object containing the optional fields below. An empty body or empty JSON object creates a two-player game with policy Off. Requests with other content types use those same defaults regardless of body contents.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `mode` | string | No | `two_player` | Use `two_player` for two human turns or `cpu` for human black and CPU white. |
| `forbidden_move_policy` | string | No | `off` | Use `off` for five-or-more rules, `warn` to reject a forbidden black move, or `loss` to record a forbidden black move as an immediate white win. Either game mode supports all three values. |

```json
{"mode": "cpu", "forbidden_move_policy": "warn"}
```

Response `201 Created` returns the new game at revision `0`. This example creates a CPU game.

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "board": [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  ],
  "current_player": 1,
  "status": "in_progress",
  "winner": null,
  "mode": "cpu",
  "forbidden_move_policy": "warn",
  "result_reason": null,
  "revision": 0
}
```

Example error response when the requested mode is unsupported.

```json
{"error": "invalid_mode"}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| `400 Bad Request` | `invalid_request` | Malformed JSON, a non-object JSON body, or unknown JSON fields. |
| `400 Bad Request` | `invalid_mode` | The supplied mode is neither `two_player` nor `cpu`. |
| `400 Bad Request` | `invalid_forbidden_move_policy` | The value is outside the set of supported strings. |
| `503 Service Unavailable` | `cpu_creation_unavailable` | CPU game creation is disabled for rollout. Two-player creation remains available. |

## Get a game

Retrieve a saved game by ID without advancing the turn.

`GET /api/v1/games/{id}/`

| Path parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Game identifier. |

Response `200 OK` returns the saved board and current turn or result. This example shows a CPU game at revision `3`, with white to move.

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "board": [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  ],
  "current_player": 2,
  "status": "in_progress",
  "winner": null,
  "mode": "cpu",
  "forbidden_move_policy": "off",
  "result_reason": null,
  "revision": 3
}
```

Example error response when the UUID does not identify a saved game.

```json
{"error": "game_not_found"}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| `404 Not Found` | `game_not_found` | No game exists with the supplied UUID. |

## Submit a move

Place a stone for the current player in a transaction with a row lock. In CPU mode, the human plays black and the application checks the turn and revision under that lock.

`POST /api/v1/games/{id}/moves/`

| Path parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Game identifier. |

Send an `application/json` object containing exactly `x` and `y` for a two-player game. For a CPU game, include `expected_revision` as well.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `x` | integer | Yes | None | Column, from `0` to `14`. |
| `y` | integer | Yes | None | Row, from `0` to `14`. |
| `expected_revision` | integer | Yes for CPU games | None | Revision of the displayed board, from `0` through `225`. JSON booleans are invalid. |

Example request body for a CPU game.

```json
{"x": 3, "y": 4, "expected_revision": 0}
```

Response `200 OK` returns the saved position after the human move. This example shows revision `1`, with white to move.

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "board": [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  ],
  "current_player": 2,
  "status": "in_progress",
  "winner": null,
  "mode": "cpu",
  "forbidden_move_policy": "off",
  "result_reason": null,
  "revision": 1
}
```

In Loss mode, submitting a forbidden black move returns the same full game response with the submitted black stone, revision incremented by one, `current_player: 1`, `status: "won"`, `winner: 2`, and the specific `result_reason`. If a white move under Warn leaves empty squares but no legal black move, the response shows the final white stone, `current_player: 2`, `status: "won"`, `winner: 2`, and `result_reason: "no_legal_black_move"`. The same outcome can be returned by the CPU endpoint.

Warn rejects a forbidden black move with `409 Conflict`. The server keeps the saved board, turn, revision, and history as they were before the attempt. Example response.

```json
{"error": "forbidden_move", "reason": "double_three"}
```

Example error response when a black turn is submitted from an earlier position.

```json
{"error": "stale_revision"}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| `400 Bad Request` | `invalid_request` | Malformed JSON, a non-object body, or missing or extra fields for the game mode. |
| `400 Bad Request` | `invalid_coordinate` | A coordinate is not an integer. |
| `400 Bad Request` | `out_of_bounds` | A coordinate is outside `0` through `14`. |
| `400 Bad Request` | `invalid_revision` | The supplied revision is not an integer from `0` through `225`. |
| `404 Not Found` | `game_not_found` | No game exists with the supplied UUID. |
| `409 Conflict` | `occupied` | The selected position already contains a stone. |
| `409 Conflict` | `forbidden_move` | Warn rejected a black move. The `reason` is `overline`, `double_four`, or `double_three`. |
| `409 Conflict` | `game_finished` | The game has already ended. |
| `409 Conflict` | `not_human_turn` | An in-progress CPU game is waiting for white. |
| `409 Conflict` | `stale_revision` | An in-progress CPU game is waiting for black at a different revision. |
| `415 Unsupported Media Type` | `unsupported_media_type` | The content type is other than `application/json`. |

## Advance the CPU turn

Apply one white stone to the specified pending position.

`POST /api/v1/games/{id}/cpu-move/`

| Path parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Game identifier. |

Send an `application/json` object with exactly one field.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `expected_revision` | integer | Yes | None | Revision of the pending position, from `0` through `225`. JSON booleans are invalid. |

```json
{"expected_revision": 1}
```

For a CPU game, response `200 OK` returns the game with the same ID and mode. If the game is in progress, white is next, and `expected_revision` matches the saved revision, the CPU places one white stone and the revision increases by one. Otherwise, the response returns the saved state without changing it. A duplicate request for an earlier white turn leaves a later pending white turn intact.

In the example below, the CPU advances revision `1` to `2`.

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "board": [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  ],
  "current_player": 1,
  "status": "in_progress",
  "winner": null,
  "mode": "cpu",
  "forbidden_move_policy": "off",
  "result_reason": null,
  "revision": 2
}
```

Example error response for a request against a two-player game.

```json
{"error": "not_cpu_game"}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| `400 Bad Request` | `invalid_request` | Malformed JSON, a non-object body, or missing or extra fields. |
| `400 Bad Request` | `invalid_revision` | The supplied revision is not an integer from `0` through `225`. |
| `404 Not Found` | `game_not_found` | No game exists with the supplied UUID. |
| `409 Conflict` | `not_cpu_game` | The game uses two-player mode. |
| `415 Unsupported Media Type` | `unsupported_media_type` | The content type is other than `application/json`. |
