import pygame
import random
import math
from collections import deque

# ========= Setup =========
pygame.init()
WIDTH, HEIGHT = 720, 1280
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cascade Slots (5x5)")
clock = pygame.time.Clock()

# ========= Colors & Fonts =========
WHITE = (245, 245, 245)
BLACK = (15, 15, 20)
UI_GOLD = (236, 188, 59)
UI_ACCENT = (159, 115, 255)

FONT = pygame.font.SysFont("arial", 24, bold=True)
BIG = pygame.font.SysFont("arial", 36, bold=True)
FLOAT_FONT = pygame.font.SysFont("arial", 20, bold=True)

# Colors (9 balanced)
SYMBOLS = [
    (255, 0, 0),       # Bright Red
    (0, 255, 0),       # Bright Green
    (0, 0, 255),       # Bright Blue
    (255, 255, 0),     # Yellow
    (255, 165, 0),     # Orange
    (128, 0, 128),     # Purple
    (0, 255, 255),     # Cyan
    (255, 192, 203),   # Pink
    (165, 42, 42),     # Brown
    (128, 128, 128),   # Gray
    (0, 128, 128),     # Teal
    (255, 105, 180),   # Hot Pink
    (0, 100, 0),       # Dark Green
    (210, 180, 140),   # Tan
    (0, 0, 128),       # Navy Blue
#    (240, 230, 140),   # Khaki
    (173, 216, 230),   # Light Blue
    (255, 20, 147),    # Deep Pink
    (75, 0, 130),      # Indigo
    (34, 139, 34),     # Forest Green
]
SYMBOL_WEIGHTS = [20] * len(SYMBOLS)  # balanced

# ========= Grid Config =========
ROWS, COLS = 5, 5
TILE = 110
GRID_W, GRID_H = COLS * TILE, ROWS * TILE
GRID_X = (WIDTH - GRID_W) // 2
GRID_Y = 280

# ========= Economy =========
START_CREDITS = 1000
MIN_BET, MAX_BET = 1, 50
PAYOUT_PER_TILE_FACTOR = 0.05  # per tile

# ========= Anim / Timing =========
DROP_SPEED = 50    # slower
POP_FLASH_TIME = 400 # ms
SPIN_SHAKE_TIME = 420
FILL_STAGGER = 50    # slower cascade
# ========= last win ==============
last_win = 0.0
# ========= Floating Text =========
class FloatingText:
    def __init__(self, text, pos):
        self.text = text
        self.x, self.y = pos
        self.timer = 0
        self.lifetime = 900  # ms
        self.alpha = 255

    def update(self, dt):
        self.timer += dt
        self.y -= 0.04 * dt
        self.alpha = max(0, 255 - int((self.timer / self.lifetime) * 255))

    def draw(self, surf):
        txt_surf = FLOAT_FONT.render(self.text, True, (255, 255, 255))
        txt_surf.set_alpha(self.alpha)
        surf.blit(txt_surf, (self.x, self.y))

    def is_alive(self):
        return self.timer < self.lifetime

# ========= Button helper =========
class Button:
    def __init__(self, rect, label):
        self.rect = pygame.Rect(rect)
        self.label = label

    def draw(self, surf, enabled=True):
        color = UI_GOLD if enabled else (130, 100, 30)
        pygame.draw.rect(surf, color, self.rect, border_radius=16)
        pygame.draw.rect(surf, (255, 255, 255), self.rect, 3, border_radius=16)
        text = BIG.render(self.label, True, BLACK if enabled else (40, 40, 40))
        surf.blit(text, text.get_rect(center=self.rect.center))

    def clicked(self, pos):
        return self.rect.collidepoint(pos)

# ========= Tile object =========
class Tile:
    __slots__ = ("color", "row", "col", "x", "y", "target_y", "popping", "pop_start", "alive")
    def __init__(self, color, row, col, world_x, world_y):
        self.color = color
        self.row = row
        self.col = col
        self.x = world_x
        self.y = world_y - random.randint(0, GRID_H)
        self.target_y = world_y
        self.popping = False
        self.pop_start = 0
        self.alive = True

    def update(self, dt):
        if self.y < self.target_y:
            self.y = min(self.target_y, self.y + DROP_SPEED * (dt / 16.67))

    def draw(self, surf, highlight=False, flash_phase=1.0):
        if not self.alive:
            return
        rect = pygame.Rect(self.x, self.y, TILE - 8, TILE - 8)
        rect.inflate_ip(-8, -8)
        if highlight:
            glow = pygame.Surface((rect.w + 14, rect.h + 14), pygame.SRCALPHA)
            alpha = 80 + int(80 * flash_phase)
            pygame.draw.rect(glow, (255, 255, 255, alpha), glow.get_rect(), border_radius=22)
            surf.blit(glow, (rect.x - 7, rect.y - 7))
        pygame.draw.rect(surf, self.color, rect, border_radius=16)
        sheen = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.ellipse(sheen, (255, 255, 255, 48),
                            (rect.w * 0.1, -rect.h * 0.25, rect.w * 0.8, rect.h * 0.7))
        surf.blit(sheen, rect.topleft)

# ========= Utility =========
def world_pos(r, c):
    return GRID_X + c * TILE, GRID_Y + r * TILE

def random_symbol_with_bias(grid, r, c):
    if random.random() < 0.35:
        neighbors = []
        if r > 0 and grid[r-1][c] is not None:
            neighbors.append(grid[r-1][c].color)
        if c > 0 and grid[r][c-1] is not None:
            neighbors.append(grid[r][c-1].color)
        if neighbors:
            return random.choice(neighbors)
    return random.choices(SYMBOLS, weights=SYMBOL_WEIGHTS, k=1)[0]

def make_initial_grid():
    grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            color = random_symbol_with_bias(grid, r, c)
            x, y = world_pos(r, c)
            grid[r][c] = Tile(color, r, c, x, y)
    return grid

def scan_clusters(grid):
    seen = [[False]*COLS for _ in range(ROWS)]
    clusters = []
    for r in range(ROWS):
        for c in range(COLS):
            tile = grid[r][c]
            if tile is None or seen[r][c]:
                continue
            color = tile.color
            q = deque([(r, c)])
            blob = []
            seen[r][c] = True
            while q:
                rr, cc = q.popleft()
                blob.append((rr, cc))
                for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr, nc = rr+dr, cc+dc
                    if 0 <= nr < ROWS and 0 <= nc < COLS and not seen[nr][nc]:
                        t2 = grid[nr][nc]
                        if t2 and t2.color == color:
                            seen[nr][nc] = True
                            q.append((nr, nc))
            if len(blob) >= 3:
                clusters.append(blob)
    return clusters

def mark_popping(grid, clusters, now_ms):
    for blob in clusters:
        for r, c in blob:
            t = grid[r][c]
            if t and not t.popping:
                t.popping = True
                t.pop_start = now_ms

def perform_pop(grid, bet, floating_texts):
    popped_positions = []
    per_tile_value = bet * PAYOUT_PER_TILE_FACTOR
    for r in range(ROWS):
        for c in range(COLS):
            t = grid[r][c]
            if t and t.popping and t.alive:
                t.alive = False
                grid[r][c] = None
                popped_positions.append((r, c))
                fx, fy = world_pos(r, c)
                floating_texts.append(
                    FloatingText(f"+{per_tile_value:.2f}", (fx + TILE//3, fy + TILE//3))
                )
    return popped_positions

def collapse_columns(grid):
    for c in range(COLS):
        stack = [grid[r][c] for r in range(ROWS) if grid[r][c] is not None]
        for r in range(ROWS-1, -1, -1):
            t = stack.pop() if stack else None
            grid[r][c] = t
            if t:
                t.row, t.col = r, c
                t.x, t.target_y = world_pos(r, c)

def fill_new_tiles(grid):
    for r in range(ROWS-1, -1, -1):
        for c in range(COLS):
            if grid[r][c] is None:
                color = random_symbol_with_bias(grid, r, c)
                x, y = world_pos(r, c)
                grid[r][c] = Tile(color, r, c, x, y)

# ========= Game State =========
STATE_IDLE = "idle"
STATE_SPIN_SHAKE = "spin_shake"
STATE_RESOLVE = "resolve"

spin_btn = Button((WIDTH//2 - 120, HEIGHT - 210, 240, 90), "SPIN")
minus_btn = Button((60, HEIGHT - 210, 90, 90), "–")
plus_btn  = Button((WIDTH - 150, HEIGHT - 210, 90, 90), "+")
max_btn   = Button((WIDTH//2 - 120, HEIGHT - 110, 240, 70), "MAX BET")

grid = make_initial_grid()
credits = float(START_CREDITS)
bet = 5.0

state = STATE_IDLE
state_timer = 0
last_time = pygame.time.get_ticks()
pending_clusters = []
total_popped_this_spin = 0
last_fill_time = 0
floating_texts = []

def start_spin():
    global state, state_timer, total_popped_this_spin, pending_clusters
    state = STATE_SPIN_SHAKE
    state_timer = 0
    total_popped_this_spin = 0
    for r in range(ROWS):
        for c in range(COLS):
            color = random_symbol_with_bias(grid, r, c)
            x, y = world_pos(r, c)
            grid[r][c] = Tile(color, r, c, x, y)

def settle_and_score():
    global credits, state, last_win
    payout = total_popped_this_spin * bet * PAYOUT_PER_TILE_FACTOR
    credits += payout
    last_win = payout  # Store the win here
    state = STATE_IDLE

# ========= Main Loop =========
running = True
while running:
    now = pygame.time.get_ticks()
    dt = now - last_time
    last_time = now

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if state == STATE_IDLE:
                if minus_btn.clicked((mx, my)):
                    bet = max(MIN_BET, bet - 1)
                elif plus_btn.clicked((mx, my)):
                    bet = min(MAX_BET, bet + 1)
                elif max_btn.clicked((mx, my)):
                    bet = MAX_BET
                elif spin_btn.clicked((mx, my)) and credits >= bet:
                    credits -= bet
                    start_spin()

    for r in range(ROWS):
        for c in range(COLS):
            t = grid[r][c]
            if t:
                t.update(dt)

    for ft in floating_texts:
        ft.update(dt)
    floating_texts = [ft for ft in floating_texts if ft.is_alive()]

    if state == STATE_SPIN_SHAKE:
        state_timer += dt
        if state_timer >= SPIN_SHAKE_TIME:
            state = STATE_RESOLVE
            state_timer = 0
            pending_clusters = scan_clusters(grid)
            if pending_clusters:
                mark_popping(grid, pending_clusters, now)
            else:
                settle_and_score()

    elif state == STATE_RESOLVE:
        if pending_clusters:
            earliest = min(grid[r][c].pop_start for blob in pending_clusters for r, c in blob)
            if now - earliest >= POP_FLASH_TIME:
                popped = perform_pop(grid, bet, floating_texts)
                total_popped_this_spin += len(popped)
                pending_clusters = []
                collapse_columns(grid)
                last_fill_time = now
        else:
            if now - last_fill_time >= FILL_STAGGER:
                fill_new_tiles(grid)
                pending_clusters = scan_clusters(grid)
                if pending_clusters:
                    mark_popping(grid, pending_clusters, now)
                else:
                    settle_and_score()

    # ======= Draw =======
    screen.fill(BLACK)

    pygame.draw.rect(screen, (28, 28, 40), (0, 0, WIDTH, 160))
    title = BIG.render("ULTRAEDGE CASCADE SLOTS", True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH//2, 60)))

    pygame.draw.rect(screen, (24, 24, 32), (40, 170, WIDTH-80, 90), border_radius=18)
    credits_text = FONT.render(f"Credits: {credits:.2f}", True, UI_GOLD)
    bet_text = FONT.render(f"Bet: {bet:.2f}", True, UI_ACCENT)
    screen.blit(credits_text, (60, 200))
    screen.blit(bet_text, (WIDTH//2 + 50, 200))

    for r in range(ROWS):
        for c in range(COLS):
            cell = pygame.Rect(GRID_X + c*TILE, GRID_Y + r*TILE, TILE, TILE)
            pygame.draw.rect(screen, (16, 16, 26), cell, border_radius=18)
            pygame.draw.rect(screen, (45, 45, 70), cell, 2, border_radius=18)

    flash_phase = (math.sin(now / 80.0) + 1) * 0.5
    highlight_positions = set()
    if state == STATE_RESOLVE and pending_clusters:
        for blob in pending_clusters:
            for r, c in blob:
                highlight_positions.add((r, c))

    for r in range(ROWS):
        for c in range(COLS):
            t = grid[r][c]
            if t:
                highlight = (r, c) in highlight_positions
                t.draw(screen, highlight=highlight, flash_phase=flash_phase)

    for ft in floating_texts:
        ft.draw(screen)

    minus_btn.draw(screen, enabled=(state == STATE_IDLE and bet > MIN_BET))
    plus_btn.draw(screen, enabled=(state == STATE_IDLE and bet < MAX_BET))
    spin_btn.draw(screen, enabled=(state == STATE_IDLE and credits >= bet))
    max_btn.draw(screen, enabled=(state == STATE_IDLE and bet < MAX_BET))

    # Small status text
    win_text = FONT.render(f"Win: {last_win:.2f}", True, (255, 255, 255))
    win_rect = win_text.get_rect(center=(WIDTH // 2, spin_btn.rect.top - 30))
    screen.blit(win_text, win_rect)
    if state == STATE_IDLE:
        status = "Press SPIN to drop colors. Matches of 3+ pop. No diagonals."
    elif state == STATE_SPIN_SHAKE:
        status = "Spinning..."
    else:
        status = "Resolving cascades..."
    st = FONT.render(status, True, WHITE)
    screen.blit(st, (GRID_X, GRID_Y + GRID_H + 20))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
