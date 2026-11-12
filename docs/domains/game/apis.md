# Game API

The API creates and retrieves games and accepts moves. It has no authentication or participant authorization: anyone with a game UUID can read and update that game. Authentication and authorization must be added before exposing the API where that access is inappropriate.

Responses representing games contain the following fields. Board cells are indexed as `board[y][x]`.

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID string | Game identifier. |
| `board` | array of 15 arrays of 15 integers | `0` is empty; `1` and `2` are players' stones. |
| `current_player` | integer | Player whose turn is next, or the last mover when the game has ended. |
| `status` | string | `in_progress`, `won`, or `draw`. |
| `winner` | integer or null | Winning player (`1` or `2`) for a won game; otherwise null. |

Browser clients must obtain a CSRF cookie and send its `csrftoken` value in the `X-CSRFToken` header for POST requests. Django's CSRF middleware rejects missing or invalid tokens with `403 Forbidden`; this response uses Django's default error page.

## Get CSRF cookie

`GET /api/v1/csrf/`

Example request: `GET /api/v1/csrf/`

Response `200 OK` sets the `csrftoken` cookie:

```json
{"detail": "CSRF cookie set"}
```

## Create a game

Create an empty game with player 1 to move. No request body is required.

`POST /api/v1/games/`

Example request: `POST /api/v1/games/`

Response `201 Created`:

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
  "winner": null
}
```

## Get a game

`GET /api/v1/games/{id}/`

| Path parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Game identifier. |

Example request: `GET /api/v1/games/123e4567-e89b-12d3-a456-426614174000/`

Response `200 OK` has the same fields and format as the game in the create response above. For a newly created game, it contains the same board and state.

Response `404 Not Found` for a well-formed UUID that does not identify a game:

```json
{"error": "game_not_found"}
```

A malformed UUID does not match the route and returns Django's default `404` response.

## Submit a move

Apply the move for the current player. A successful update is performed in a transaction with a row lock.

`POST /api/v1/games/{id}/moves/`

| Path parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Game identifier. |

The request content type must be `application/json`. The JSON body must be an object containing exactly these two fields:

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `x` | integer | Yes | None | Column, from `0` to `14`. |
| `y` | integer | Yes | None | Row, from `0` to `14`. |

Example request: `POST /api/v1/games/123e4567-e89b-12d3-a456-426614174000/moves/`

```json
{"x": 3, "y": 4}
```

Response `200 OK`:

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
  "winner": null
}
```

Errors use the following JSON format, for example:

```json
{"error": "occupied"}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| `400 Bad Request` | `invalid_request` | Malformed JSON or an object with missing or extra fields. |
| `400 Bad Request` | `invalid_coordinate` | A coordinate is not an integer. |
| `400 Bad Request` | `out_of_bounds` | A coordinate is outside `0` through `14`. |
| `404 Not Found` | `game_not_found` | No game exists with the supplied UUID. |
| `409 Conflict` | `occupied` | The selected position already contains a stone. |
| `409 Conflict` | `game_finished` | The game has already ended. |
| `415 Unsupported Media Type` | `unsupported_media_type` | The request content type is not `application/json`. |

A malformed UUID does not match the route and returns Django's default `404` response. Unsupported HTTP methods receive `405 Method Not Allowed`.
