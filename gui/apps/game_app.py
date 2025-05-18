import PySimpleGUI as sg
import random
import time

CELL_SIZE = 20
GRID_SIZE = 20
SPEED = 100  # milliseconds

class SnakeGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.snake = [(GRID_SIZE // 2, GRID_SIZE // 2)]
        self.direction = (0, -1)
        self.spawn_food()
        self.game_over = False

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
            self.game_over = True
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
        self.window = sg.Window('Game', layout, modal=True, return_keyboard_events=True, finalize=True)
        self.game = SnakeGame()
        self.running = False

    def run(self):
        graph = self.window['-GRAPH-']
        while True:
            event, values = self.window.read(timeout=SPEED if self.running else None)
            if event in (sg.WIN_CLOSED, 'Close'):
                break
            elif event == 'Play':
                self.game.reset()
                self.running = True
            elif event in ('Up:38', 'w', 'W'):
                self.game.change_direction((0, -1))
            elif event in ('Down:40', 's', 'S'):
                self.game.change_direction((0, 1))
            elif event in ('Left:37', 'a', 'A'):
                self.game.change_direction((-1, 0))
            elif event in ('Right:39', 'd', 'D'):
                self.game.change_direction((1, 0))

            if self.running:
                self.game.step()
                self.game.draw(graph)
                if self.game.game_over:
                    sg.popup('Game Over! Score: %d' % (len(self.game.snake) - 1))
                    self.running = False
        self.window.close()