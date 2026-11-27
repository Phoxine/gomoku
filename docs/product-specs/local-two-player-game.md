# Local Two-Player Game

Two players take turns on the same device. Select **New game** to start with an empty 15×15 board. Black plays first, and each player places a stone on an empty intersection. Under the default rules, the game ends when a player completes at least five consecutive stones horizontally, vertically, or diagonally, or when the board fills without a winner.

Hover over an empty intersection where you can play to preview a translucent stone in the current player's color. The preview switches between black and white as turns change. Occupied intersections and a completed board show no preview.

## Optional black forbidden moves

Before starting a two-player or CPU game, select **Enable black forbidden moves** to choose **Warn and retry** or **Immediate loss**. The initial consequence is **Warn and retry**. Leaving the checkbox clear uses the default five-or-more rule. [CPU game](local-cpu-game.md)

With the rule enabled, black wins by completing exactly five in any direction. If black completes five and a forbidden pattern in the same move, black wins. In other cases, six or more in a row, a double-four, or a double-three is forbidden. White still wins with five or more in a row.

| Setting or scenario | Expected result |
| --- | --- |
| Black submits a forbidden move under Warn and retry | A dialog explains the reason and the square stays empty. Select **Choose another move** or press Escape to return focus to the board and try another move as black. |
| Black submits a forbidden move under Immediate loss | A dialog explains why white won. The board keeps the final black stone and placement ends. Select **Back to board** or press Escape to close the dialog, then use **View result details** to reopen it. |
| White leaves empty squares, but every black move would be forbidden under Warn and retry | The game ends with a white win and explains that black has no legal move. The only new stone is white's last move. |
| Load a game or refresh | The board shows the saved setting and state. A saved forbidden-move loss automatically reopens the result dialog. If white won because black had no legal move, the result status explains the reason. |

The board shows whose turn it is and the result when the match ends. Games are saved on the server. The same browser can restore its last game, and a player can load an existing game by entering its game ID. Anyone who can reach the server and knows the game ID can view the game and submit moves.

Use **Copy ID** to copy the active game's ID. If the browser blocks clipboard access, copy the ID shown below the board.

Computer opponents, accounts, matchmaking, real-time multiplayer updates, and spectators are outside the current scope.

See the [game domain design](../domains/game/context-designs.md) for the state transition contract and implementation details.
