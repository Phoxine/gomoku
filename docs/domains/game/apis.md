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
| `mode` | string | Proposed. `two_player` or `cpu`. Existing games use `two_player`. |
| `revision` | integer | Proposed. Number of occupied cells, from `0` through `225`. Each accepted stone increments it by one. |

A CPU game is waiting for the CPU when `mode` is `cpu`, `status` is `in_progress`, and `current_player` is `2`.

## Shared HTTP behavior

For POST requests, send the CSRF cookie and its `csrftoken` value in the `X-CSRFToken` header, as the game's browser client does. Form POSTs to create a game can supply the token in the `csrfmiddlewaretoken` field with the cookie. JSON move requests use the header. When the CSRF check fails, Django returns `403 Forbidden` with its default error page. See [Django's CSRF guidance](https://docs.djangoproject.com/en/6.1/howto/csrf/).

A malformed UUID does not match the route and returns Django's default `404` response. On a matching route, unsupported methods receive `405 Method Not Allowed` after middleware checks such as CSRF.

## Get CSRF cookie

Obtain the CSRF cookie required for state-changing requests.

`GET /api/v1/csrf/`

Response `200 OK` sets the `csrftoken` cookie:

```json
{"detail": "CSRF cookie set"}
```

## Create a game

Create an empty game with player 1 to move. The current endpoint ignores the body and creates a two-player game.

`POST /api/v1/games/`

Under the proposal, send an `application/json` object with the following field. An empty body or an empty JSON object creates a two-player game. Requests with other content types keep the legacy behavior and create a two-player game regardless of body contents. Form submissions keep their existing CSRF handling.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `mode` | string | No | `two_player` | Use `two_player` for two human turns or `cpu` for human black and CPU white. |

```json
{"mode": "cpu"}
```

Response `201 Created` returns the new game. This example shows the proposed response when creating a CPU game at revision `0`.

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
  "revision": 0
}
```

Example error response under the proposal when the requested mode is unsupported.

```json
{"error": "invalid_mode"}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| `400 Bad Request` | `invalid_request` | Malformed JSON, a non-object JSON body, or unknown JSON fields. |
| `400 Bad Request` | `invalid_mode` | The requested mode is outside the supported values. |

## Get a game

Retrieve a saved game by ID without advancing the turn.

`GET /api/v1/games/{id}/`

| Path parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Game identifier. |

Response `200 OK` returns the saved board and current turn or result. This example shows the proposed response for a CPU game at revision `3`, with white to move.

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

Place a stone for the current player in a transaction with a row lock. Under the CPU proposal, the human always plays black and the application checks the turn and revision under that lock.

`POST /api/v1/games/{id}/moves/`

| Path parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Game identifier. |

Send an `application/json` object containing exactly `x` and `y` for a two-player game. The proposal adds the required `expected_revision` field for CPU games.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `x` | integer | Yes | None | Column, from `0` to `14`. |
| `y` | integer | Yes | None | Row, from `0` to `14`. |
| `expected_revision` | integer | Yes for CPU games | None | Revision of the displayed board, from `0` through `225`. JSON booleans are invalid. |

Example request body for a proposed CPU game.

```json
{"x": 3, "y": 4, "expected_revision": 0}
```

Response `200 OK` returns the saved position after the human move. This example shows the proposed response at revision `1`, with white to move.

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
  "revision": 1
}
```

Example error response under the proposal when the submitted position differs from the saved position.

```json
{"error": "stale_revision"}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| `400 Bad Request` | `invalid_request` | Malformed JSON, a non-object body, or missing or extra fields for the game mode. |
| `400 Bad Request` | `invalid_coordinate` | A coordinate is not an integer. |
| `400 Bad Request` | `out_of_bounds` | A coordinate is outside `0` through `14`. |
| `400 Bad Request` | `invalid_revision` | CPU proposal. The supplied revision is not an integer from `0` through `225`. |
| `404 Not Found` | `game_not_found` | No game exists with the supplied UUID. |
| `409 Conflict` | `occupied` | The selected position already contains a stone. |
| `409 Conflict` | `game_finished` | The game has already ended. |
| `409 Conflict` | `not_human_turn` | CPU proposal. An in-progress CPU game is waiting for white. |
| `409 Conflict` | `stale_revision` | CPU proposal. The submitted position differs from the saved position. |
| `415 Unsupported Media Type` | `unsupported_media_type` | The content type is other than `application/json`. |

After a conflict or an uncertain POST result, fetch the saved state before accepting further input.

## Advance the CPU turn

Apply one white stone to the specified pending position. This endpoint is part of the CPU proposal.

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
