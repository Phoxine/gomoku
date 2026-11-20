# Local Two-Player Game

Two players take turns on the same device. Select **New game** to start with an empty 15×15 board. Black plays first, and each player places a stone on an empty intersection. The game ends when a player completes at least five consecutive stones horizontally, vertically, or diagonally, or when the board fills without a winner.

The board shows whose turn it is and the result when the match ends. Games are saved on the server. The same browser can restore its last game, and a player can load an existing game by entering its game ID. Anyone who can reach the server and knows the game ID can view the game and submit moves.

Use **Copy ID** to copy the active game's ID. If the browser blocks clipboard access, copy the ID shown below the board.

Computer opponents, accounts, matchmaking, real-time multiplayer updates, and spectators are outside the current scope.

See the [game domain design](../domains/game/context-designs.md) for the state transition contract and implementation details.
