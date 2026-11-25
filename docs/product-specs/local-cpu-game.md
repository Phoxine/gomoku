# Local Game Against the CPU

**Status** — Proposed

A player can play Gomoku against a computer opponent from the game page. The player controls one color, and the CPU places stones for the other color automatically.

## Start a game

The new-game flow lets the player choose **Two players** or **Play against CPU**. In a CPU game, the player plays black and takes the first turn. The CPU plays white at a single difficulty. A new game starts with an empty 15×15 board. If a game is already open, it stays available by its game ID after the player starts another one.

## Play a turn

The page identifies the game mode, the player's color, and whose turn it is. On their turn, the player selects an empty intersection. After a valid player move, if the game is still in progress, the CPU makes one legal move on an empty intersection. The page shows that the CPU is taking its turn and prevents the player from placing another stone until the CPU move is resolved.

The [local two-player rules](local-two-player-game.md) also apply. At least five consecutive stones of the same color win horizontally, vertically, or diagonally. A full board without a winner is a draw. The page announces a player win, a CPU win, or a draw as soon as it occurs. A winning final move takes precedence over a draw. The board accepts no more moves after the result, and a player move that ends the game triggers no CPU move.

## Resume a game

The same browser can restore its last game, and the player can load a saved game by ID. The page shows the active game's ID and offers **Copy ID**, with the displayed ID available for manual copying. The game retains its mode, board, turn, and any final result. If a saved game is waiting for the CPU's move, loading it continues that turn automatically. Refreshing or reopening a completed game shows its final board and result.

If the CPU turn fails, the page explains the interruption and lets the player retry the CPU turn. The player can continue from the committed board state without having to submit their previous move again. Reloading, retrying, or opening the same game in a second tab must never place an extra CPU stone.

## First release

The first release offers one CPU difficulty and a fixed player color. Difficulty selection, choosing a color, undo, and offline play are deferred. The two-player mode remains available from the same page.

## Acceptance criteria

| Scenario | Expected result |
| --- | --- |
| Start a CPU game | An empty board opens with the player assigned black, the CPU assigned white, and black to move. |
| Make a legal move that leaves the game in progress | The player's stone appears. The page indicates the CPU's turn, then shows exactly one new white stone on a previously empty intersection. If the game continues, control returns to the player. |
| Choose an occupied intersection on the player's turn | The board and turn stay the same, and the CPU makes no move. |
| Select another intersection while the CPU is taking its turn | The selection places no stone. |
| Complete five or more in a row as the player | The page shows a player win and the CPU makes no further move. |
| Complete five or more in a row as the CPU | The page shows a CPU win and the board stops accepting moves. |
| Fill the last empty intersection | The game ends immediately. The final move wins if it completes a line of five or more. Otherwise, the page shows a draw. |
| Refresh or load a saved CPU game by ID | The game opens in CPU mode with its saved board and result or next turn. A pending CPU turn completes once, even if the game is opened twice or the turn is retried. |
| Interrupt a CPU turn after the player's move is saved | The page offers a retry. When the game continues, the player's stone remains and exactly one CPU response is recorded. |
| Copy a CPU game's ID, start another game, and reopen the first game by ID | The first game returns with its saved board and mode. The displayed ID can be copied manually if clipboard access is blocked. |
| Start a two-player game or load one saved before CPU mode was introduced | Both turns remain under human control. |
