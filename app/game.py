
from enum import Enum
from typing import Tuple

from pydantic import BaseModel

MAX_ROUNDS = 3
MOVES_PER_ROUND = 10

offsets = [
    (0, 1),
    (1, 1),
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, -1),
    (-1, 0),
    (-1, 1)
]

class Direction(int, Enum):
    up = 0
    upright = 1
    right = 2
    downright = 3
    down = 4
    downleft = 5
    left = 6
    upleft = 7

class Steer(int, Enum):
    left = 0
    right = 1

class Action(BaseModel):
    fc_timestamp: int
    server_timestamp: int
    player_id: int
    steer: Steer

class Player(BaseModel):
    id: int
    position: Tuple[int, int] = (0, 0)
    direction: Direction = Direction.up
    moves: list[list[Steer]] = [[]]
    wins: int = 0

    def __str__(self) -> str:
        moves = ["".join([str(m.value) for m in moves]) for moves in self.moves]
        return f"Player: id={self.id} position={self.position} direction={self.direction} moves={moves}"
    
    def reset(self) -> None:
        self.position = (0, 0)
        self.direction = Direction.up
        self.moves.append([])
    
    def moves_left(self) -> int:
        return MOVES_PER_ROUND - len(self.moves[-1])
    
    def lives_left(self) -> int:
        return MAX_ROUNDS - len(self.moves) + self.wins + 1

    def move(self, steer: Steer) -> None:
        moves = self.moves[-1]
        moves.append(steer)
        self.direction += 1 if steer == Steer.right else -1
        self.direction = Direction(self.direction % 8)
        self.position = (self.position[0] + offsets[self.direction]
                        [0], self.position[1] + offsets[self.direction][1])


class MoveResult(BaseModel):
    player: Player
    win: bool
    last: bool


class SpaceDegenGame:

    def __init__(self, treasures: list[Tuple[int, int]]) -> None:
        self.state = {}
        self.treasures = treasures
        self.winners = []

    def player(self, player_id: int) -> Player:
        if player_id not in self.state:
            self.state[player_id] = Player(id=player_id)
        return self.state[player_id]
    
    def move(self, action: Action) -> MoveResult:
        player = self.player(action.player_id)
        
        # Move player
        player.move(action.steer)
        
        # Check if player has found a treasure
        if player.position in self.treasures:
            self.treasures.remove(player.position)
            self.winners.append((player, player.position, player.moves[-1][:]))
            player.wins += 1
            player.reset()
            return MoveResult(player=player, win=True, last=True)
        
        # Check if player has completed a round
        if len(player.moves[-1]) % MOVES_PER_ROUND == 0:
            player.reset()
            return MoveResult(player=player, win=False, last=True)

        # Keep playing
        return MoveResult(player=player, win=False, last=False)
            