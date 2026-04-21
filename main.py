from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Game configuration
BOARD_WIDTH = 20
BOARD_HEIGHT = 20
INITIAL_SNAKE_LENGTH = 3
INITIAL_SPEED_MS = 300  # Milliseconds per tick, lower is faster
SPEED_INCREMENT_MS = 10  # How much speed increases (interval decreases) per food
MIN_SPEED_MS = 50       # Minimum speed interval

# Global game state (simple for this example, could use a database for multiple games)
game_state = {}

class MoveRequest(BaseModel):
    direction: str

def _place_food():
    """Places food randomly on the board, ensuring it doesn't overlap with the snake."""
    while True:
        food_x = random.randint(0, BOARD_WIDTH - 1)
        food_y = random.randint(0, BOARD_HEIGHT - 1)
        if [food_x, food_y] not in game_state["snake"]:
            game_state["food"] = [food_x, food_y]
            break

def _reset_game():
    """Resets the game state to its initial values."""
    global game_state
    
    # Place snake in the middle, facing right
    start_x = BOARD_WIDTH // 2
    start_y = BOARD_HEIGHT // 2
    snake = []
    for i in range(INITIAL_SNAKE_LENGTH):
        snake.append([start_x - i, start_y]) # Head at start_x, body extending left

    game_state = {
        "board_width": BOARD_WIDTH,
        "board_height": BOARD_HEIGHT,
        "snake": snake,
        "food": [0, 0],  # Placeholder, will be placed immediately
        "direction": "right",
        "score": 0,
        "game_over": False,
        "game_started": True,
        "speed_ms": INITIAL_SPEED_MS  # Milliseconds per game tick
    }
    _place_food() # Place the first food item

def _move_snake():
    """Calculates the next game state based on the current direction."""
    if game_state["game_over"]:
        return

    snake = game_state["snake"]
    direction = game_state["direction"]
    head_x, head_y = snake[0]

    # Calculate new head position
    new_head = list(snake[0]) # Start with current head, then modify
    if direction == "up":
        new_head[1] -= 1
    elif direction == "down":
        new_head[1] += 1
    elif direction == "left":
        new_head[0] -= 1
    elif direction == "right":
        new_head[0] += 1
    else:
        # Should not happen with controlled input, but as a safeguard
        return

    # Check for collisions
    # 1. Wall collision
    if not (0 <= new_head[0] < BOARD_WIDTH and 0 <= new_head[1] < BOARD_HEIGHT):
        game_state["game_over"] = True
        return

    # 2. Self-collision
    # Check if the new head position is part of the current snake body.
    # Exclude the tail if food is not eaten, as the tail will move.
    if new_head in snake:
        game_state["game_over"] = True
        return

    # Check for food
    if new_head == game_state["food"]:
        game_state["score"] += 1
        snake.insert(0, new_head)  # Snake grows
        _place_food()
        # Increase difficulty (decrease speed interval)
        game_state["speed_ms"] = max(MIN_SPEED_MS, game_state["speed_ms"] - SPEED_INCREMENT_MS)
    else:
        # Normal movement: move head, remove tail
        snake.pop()  # Remove tail
        snake.insert(0, new_head)  # Add new head

# Initialize game state when the server starts
_reset_game()

@app.get("/game_state")
async def get_game_state():
    """Returns the current state of the game."""
    return JSONResponse(content=game_state)

@app.post("/start_game")
async def start_game():
    """Resets and starts a new game."""
    _reset_game()
    return JSONResponse(content=game_state)

@app.post("/move")
async def move(request: MoveRequest):
    """
    Updates the snake's direction (if valid) and advances the game by one step.
    Returns the updated game state.
    """
    new_direction = request.direction
    current_direction = game_state["direction"]

    # Prevent reversing direction (e.g., from 'right' to 'left')
    if not game_state["game_over"]:
        if (new_direction == "up" and current_direction == "down") or \
           (new_direction == "down" and current_direction == "up") or \
           (new_direction == "left" and current_direction == "right") or \
           (new_direction == "right" and current_direction == "left"):
            # Ignore invalid move, snake continues in current direction
            pass
        else:
            game_state["direction"] = new_direction
    
    # Execute one step of the game logic
    _move_snake()

    return JSONResponse(content=game_state)

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def home():
    return open("index.html").read()
