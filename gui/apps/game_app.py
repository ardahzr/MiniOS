import PySimpleGUI as sg
import random
import time

CELL_SIZE = 20
GRID_SIZE = 20
SPEED = 100
LIVES = 3

class SnakeGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.snake = [(GRID_SIZE // 2, GRID_SIZE // 2)]
        self.direction = (0, -1)
        self.spawn_food()
        self.game_over = False
        self.lives = LIVES

    def spawn_food(self):
        while True:
            self.food = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
            if self.food not in self.snake:
                break

    def step(self):
        if self.game_over:
            return
        head = (self.snake[0][0] + self.direction[0], self.snake[0][1] + self.direction[1])
        # Check wall collision
        if not (0 <= head[0] < GRID_SIZE and 0 <= head[1] < GRID_SIZE) or head in self.snake:
            self.lives -= 1
            if self.lives <= 0:
                self.game_over = True
                return
            else:
                self.snake = [(GRID_SIZE // 2, GRID_SIZE // 2 + i) for i in range(len(self.snake) // 2)]  # Reset snake position
                self.direction = (0, -1)  # Reset direction
                self.spawn_food()
                return
        self.snake.insert(0, head)
        if head == self.food:
            self.spawn_food()
        else:
            self.snake.pop()

    def change_direction(self, new_dir):
        # Prevent reversing
        if (self.direction[0] + new_dir[0], self.direction[1] + new_dir[1]) != (0, 0):
            self.direction = new_dir

    def draw(self, canvas):
        canvas.TKCanvas.delete("all")
        
        # Draw grid lines
        self._draw_grid(canvas)
        
        # Draw snake
        for x, y in self.snake:
            canvas.TKCanvas.create_rectangle(
                x * CELL_SIZE, y * CELL_SIZE,
                (x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE,
                fill="green"
            )
        # Draw food
        fx, fy = self.food
        canvas.TKCanvas.create_rectangle(
            fx * CELL_SIZE, fy * CELL_SIZE,
            (fx + 1) * CELL_SIZE, (fy + 1) * CELL_SIZE,
            fill="red"
        )
    
    def _draw_grid(self, canvas):
        # Draw vertical lines
        for i in range(GRID_SIZE + 1):
            x = i * CELL_SIZE
            canvas.TKCanvas.create_line(
                x, 0, x, GRID_SIZE * CELL_SIZE,
                fill="lightgray", width=1
            )
        
        # Draw horizontal lines
        for i in range(GRID_SIZE + 1):
            y = i * CELL_SIZE
            canvas.TKCanvas.create_line(
                0, y, GRID_SIZE * CELL_SIZE, y,
                fill="lightgray", width=1
            )

class GameApp:
    def __init__(self):
        layout = [
            [sg.Text('Snake Game')],
            [sg.Graph(
                canvas_size=(CELL_SIZE * GRID_SIZE, CELL_SIZE * GRID_SIZE),
                graph_bottom_left=(0, 0),
                graph_top_right=(CELL_SIZE * GRID_SIZE, CELL_SIZE * GRID_SIZE),
                key='-GRAPH-'
            )],
            [sg.Button('Play'), sg.Button('Close')]
        ]
        self.window = sg.Window('Game', layout, finalize=True, return_keyboard_events=True)
        self.game = SnakeGame()
        self.running = False

    def handle_event(self, event, values):
        if event in (sg.WIN_CLOSED, 'Close'):
            return 'close'

        if event == 'Play':
            self.game.reset()
            self.running = True
            self._draw()
        elif event.startswith('Up') or event == 'Up:38':
            self.game.change_direction((0, -1))
        elif event.startswith('Down') or event == 'Down:40':
            self.game.change_direction((0, 1))
        elif event.startswith('Left') or event == 'Left:37':
            self.game.change_direction((-1, 0))
        elif event.startswith('Right') or event == 'Right:39':
            self.game.change_direction((1, 0))

        # Oyun tick'i (her event'te bir adım ilerlet)
        if self.running and not self.game.game_over:
            self.game.step()
            self._draw()
            if self.game.game_over:
                sg.popup("Game Over!")
                self.running = False
        return None

    def _draw(self):
        self.game.draw(self.window['-GRAPH-'])