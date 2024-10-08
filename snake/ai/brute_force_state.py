import math

import game_engine


class State:
    def __init__(self, coords: tuple[int, int], parent: tuple[int, int] | None, destination: tuple[int, int]
                 , engine: game_engine.StaticEngine, move_up: bool, max_width: int, max_height: int, depth: int
                 , max_depth: int):
        self.coords = coords
        self.depth = depth

        x, y = coords
        # Moves not tried yet
        self.moves: list[tuple[tuple[int, int], game_engine.Action]] = [
            ((x, y + 1), game_engine.Action.MOVE_DOWN),
            ((x - 1, y), game_engine.Action.MOVE_LEFT),
            ((x + 1, y), game_engine.Action.MOVE_RIGHT)
        ]
        if move_up:
            self.moves.append(((x, y - 1), game_engine.Action.MOVE_UP))

        # Removes the move that lead to this state and moves that are not possible or desired
        self.moves = [move for move in self.moves
                      if move[0] != parent
                      and (game_engine.Interaction.WALL not in engine.get_interactions(move[0][0], move[0][1])
                           or game_engine.Interaction.FOOD in engine.get_interactions(move[0][0], move[0][1]))
                      and in_bounds(move[0], max_width, max_height)
                      and (depth + 1 < max_depth
                           or game_engine.Interaction.WALL in engine.get_interactions(move[0][0], move[0][1] + 1))]

        # Sorts moves based on heuristic
        self.moves.sort(key=lambda start: heuristic(start, destination))


def in_bounds(coords: tuple[int, int], width: int, height: int):
    return 0 < coords[0] < width + 1 and 0 < coords[1] < height + 1


def heuristic(start: tuple[tuple[int, int], game_engine.Action], destination: tuple[int, int]):
    A = start[0]
    B = destination

    # This will get called a lot
    return math.hypot(A[0] - B[0], A[1] - B[1])
