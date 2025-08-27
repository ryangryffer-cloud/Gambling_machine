import pygame
import random
import os

# Setup
pygame.init()
WIDTH, HEIGHT = 720, 1280  # Smartphone portrait resolution
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Slot Machine")
clock = pygame.time.Clock()

# Game config
ROWS, COLS = 5, 4
TILE_SIZE = 150  # Reduced tile size for mobile
SPIN_TIME = 30
WAGER_MIN, WAGER_MAX = 10, 100
FLASH_TIME = 60

# Fonts and colors
FONT = pygame.font.SysFont("Arial", 24, bold=True)
BIG_FONT = pygame.font.SysFont("Arial", 32, bold=True)
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
YELLOW, BLUE, BG_COLOR = (255, 255, 0), (0, 255, 255), (30, 30, 30)

# Symbols
SYMBOLS = [
    {"color": (255, 0, 0), "name": "Cherry", "multiplier": 1, "is_wild": False},
    {"color": (0, 255, 0), "name": "Gem", "multiplier": 5, "is_wild": False},
    {"color": (0, 0, 255), "name": "Bell", "multiplier": 3, "is_wild": False},
    {"color": (255, 255, 0), "name": "Seven", "multiplier": 10, "is_wild": False},
    {"color": (255, 105, 180), "name": "Star", "multiplier": 4, "is_wild": False},
]
# Add a weights list to bias symbol selection
WEIGHTED_SYMBOLS = (
    [SYMBOLS[0]] * 14 +  # Cherry (common)
    [SYMBOLS[1]] * 7 +   # Gem
    [SYMBOLS[2]] * 5 +   # Bell
    [SYMBOLS[3]] * 2 +   # Seven (rare)
    [SYMBOLS[4]] * 4     # Star
)

WILD_SYMBOL = {"color": (200, 0, 200), "name": "Wild", "multiplier": 1, "is_wild": True}

# UI Rects
spin_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 300, 200, 60)
auto_spin_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 230, 200, 60)
wager_up_button = pygame.Rect(WIDTH // 2 + 80, HEIGHT - 160, 40, 40)
wager_down_button = pygame.Rect(WIDTH // 2 - 120, HEIGHT - 160, 40, 40)
max_bet_button = pygame.Rect(WIDTH // 2 + 40, HEIGHT - 100, 100, 40)
min_bet_button = pygame.Rect(WIDTH // 2 - 140, HEIGHT - 100, 100, 40)
shop_button = pygame.Rect(WIDTH - 200, 20, 80, 40)
info_button = pygame.Rect(WIDTH - 120, HEIGHT - 60, 100, 40)
shop_back_button = pygame.Rect(WIDTH - 200, 20, 80, 40)
shop_credit_buttons = [
    {"rect": pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 - 100, 400, 60), "credits": 10, "price": 1},
    {"rect": pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2, 400, 60), "credits": 100, "price": 10},
    {"rect": pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 + 100, 400, 60), "credits": 1000, "price": 100},
]


# State
display_credits = 0  # starts equal to credits
credits = 0
wager = 10
grid = [[random.choice(WEIGHTED_SYMBOLS) for _ in range(COLS)] for _ in range(ROWS)]
spinning = False
spin_frames = 0
payout = 0
show_info = False
show_shop = False
winning_lines = []
wild_columns = []
wild_doubler_triggered = False
flash_index = 0
flash_timer = 0
total_credits_spent = 0
total_credits_won = 0
auto_spin = False
auto_spin_pause = 0  # frames to wait before next spin
PAUSE_DURATION = 30  # 30 frames ≈ 1 second at 30 FPS


def read_log():
    global total_credits_spent, total_credits_won
    if not os.path.exists("slot_log.txt"):
        return
    with open("slot_log.txt", "r") as f:
        for line in f:
            if "Total Credits Spent" in line:
                total_credits_spent = int(line.strip().split(":")[1].strip())
            elif "Total Credits Won" in line:
                total_credits_won = int(line.strip().split(":")[1].strip())

def write_log():
    with open("slot_log.txt", "w") as f:
        f.write(f"Total Credits Spent: {total_credits_spent}\n")
        f.write(f"Total Credits Won: {total_credits_won}\n")

read_log()

def draw_grid():
    x_offset = (WIDTH - (COLS * TILE_SIZE)) // 2
    y_offset = 100  # Keep grid toward top of screen
    for row in range(ROWS):
        for col in range(COLS):
            symbol = grid[row][col]
            rect = pygame.Rect(x_offset + col * TILE_SIZE, y_offset + row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, symbol["color"], rect)
            pygame.draw.rect(screen, BLACK, rect, 3)
            label = FONT.render(symbol["name"], True, BLACK)
            screen.blit(label, (rect.x + 5, rect.y + 5))

def draw_info_screen():
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(220)
    overlay.fill((20, 20, 20))
    screen.blit(overlay, (0, 0))
    screen.blit(BIG_FONT.render("Symbol Info", True, WHITE), (WIDTH // 2 - 100, 30))

    for i, symbol in enumerate(SYMBOLS + [WILD_SYMBOL]):
        x = 100
        y = 100 + i * 80
        pygame.draw.rect(screen, symbol["color"], (x, y, 60, 60))
        pygame.draw.rect(screen, BLACK, (x, y, 60, 60), 2)

        if symbol["is_wild"]:
            desc = f"{symbol['name']} - substitutes any symbol"
            bonus = "50% chance to double total win!"
            screen.blit(FONT.render(desc, True, WHITE), (x + 80, y + 5))
            screen.blit(FONT.render(bonus, True, YELLOW), (x + 80, y + 30))
        else:
            label = f"x{symbol['multiplier']} payout"
            desc = f"{symbol['name']} - {label}"
            screen.blit(FONT.render(desc, True, WHITE), (x + 80, y + 15))

    screen.blit(FONT.render("Click INFO again to close", True, YELLOW), (WIDTH // 2 - 140, HEIGHT - 50))

def draw_shop_screen():
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(230)
    overlay.fill((40, 40, 40))
    screen.blit(overlay, (0, 0))
    screen.blit(BIG_FONT.render("Shop", True, WHITE), (WIDTH // 2 - 50, 40))

    for item in shop_credit_buttons:
        pygame.draw.rect(screen, (100, 200, 100), item["rect"])
        pygame.draw.rect(screen, BLACK, item["rect"], 3)
        label = f"+{item['credits']} Credits - ${item['price']}"
        text = BIG_FONT.render(label, True, BLACK)
        screen.blit(text, (item["rect"].x + 30, item["rect"].y + 10))

    pygame.draw.rect(screen, (200, 50, 50), shop_back_button)
    pygame.draw.rect(screen, BLACK, shop_back_button, 3)
    screen.blit(FONT.render("BACK", True, WHITE), (shop_back_button.x + 10, shop_back_button.y + 10))

def draw_ui():
    # SPIN
    pygame.draw.rect(screen, (200, 200, 200), spin_button)
    pygame.draw.rect(screen, BLACK, spin_button, 3)
    screen.blit(FONT.render("SPIN", True, BLACK), (spin_button.x + 60, spin_button.y + 15))

    # AUTO SPIN
    color = (100, 255, 100) if auto_spin else (180, 180, 180)
    pygame.draw.rect(screen, color, auto_spin_button)
    pygame.draw.rect(screen, BLACK, auto_spin_button, 3)
    label = "AUTO ON" if auto_spin else "AUTO OFF"
    screen.blit(FONT.render(label, True, BLACK), (auto_spin_button.x + 50, auto_spin_button.y + 15))

    # WAGER DISPLAY
    wager_text = BIG_FONT.render(f"Wager: {wager}", True, WHITE)
    screen.blit(wager_text, (WIDTH // 2 - wager_text.get_width() // 2, HEIGHT - 160))

    # WAGER UP/DOWN
    pygame.draw.rect(screen, WHITE, wager_up_button)
    pygame.draw.rect(screen, BLACK, wager_up_button, 2)
    screen.blit(FONT.render("+", True, BLACK), (wager_up_button.x + 10, wager_up_button.y + 5))
    pygame.draw.rect(screen, WHITE, wager_down_button)
    pygame.draw.rect(screen, BLACK, wager_down_button, 2)
    screen.blit(FONT.render("-", True, BLACK), (wager_down_button.x + 10, wager_down_button.y + 5))

    # MAX/MIN
    pygame.draw.rect(screen, WHITE, max_bet_button)
    pygame.draw.rect(screen, BLACK, max_bet_button, 2)
    screen.blit(FONT.render("MAX", True, BLACK), (max_bet_button.x + 15, max_bet_button.y + 5))

    pygame.draw.rect(screen, WHITE, min_bet_button)
    pygame.draw.rect(screen, BLACK, min_bet_button, 2)
    screen.blit(FONT.render("MIN", True, BLACK), (min_bet_button.x + 15, min_bet_button.y + 5))

    # SHOP & INFO
    pygame.draw.rect(screen, (255, 165, 0), shop_button)
    pygame.draw.rect(screen, BLACK, shop_button, 2)
    screen.blit(FONT.render("SHOP", True, WHITE), (shop_button.x + 10, shop_button.y + 10))

    pygame.draw.rect(screen, (100, 100, 255), info_button)
    pygame.draw.rect(screen, BLACK, info_button, 2)
    screen.blit(FONT.render("INFO", True, WHITE), (info_button.x + 10, info_button.y + 10))

    # Credits display
    screen.blit(FONT.render(f"Credits: {int(display_credits)}", True, WHITE), (300, 880))

    if payout > 0:
        win_text = f"You won {payout}!"
        if wild_doubler_triggered:
            win_text += " (Doubled by Wild!)"
        screen.blit(FONT.render(win_text, True, YELLOW), (20, 60))

def animate_spin():
    global spin_frames, spinning
    if spin_frames < SPIN_TIME:
        if spin_frames % 2 == 0:
            for row in range(ROWS):
                for col in range(COLS):
                    grid[row][col] = random.choice(WEIGHTED_SYMBOLS)

        spin_frames += 1
    else:
        spinning = False
        spin()

def spin():
    global grid, wild_columns, wild_doubler_triggered
    wild_columns.clear()
    wild_doubler_triggered = False
    grid = []

    for row in range(ROWS):
        new_row = []
        for col in range(COLS):
            if col in [1, 3] and random.random() < 0.01:
                new_row.append(WILD_SYMBOL)
                if col not in wild_columns:
                    wild_columns.append(col)
            else:
                new_row.append(random.choice(WEIGHTED_SYMBOLS))
        grid.append(new_row)

    for col in wild_columns:
        for row in range(ROWS):
            grid[row][col] = WILD_SYMBOL

    if wild_columns and random.random() < 0.5:
        wild_doubler_triggered = True

def symbol_match(sym_list):
    names = [s["name"] for s in sym_list]
    base = names[0]
    matches = sum(1 for s in sym_list if s["name"] == base or s["is_wild"])
    return matches >= len(sym_list)  # Require full match

def calculate_payout():
    global payout, credits, winning_lines, flash_index, flash_timer, total_credits_won
    payout = 0
    winning_lines.clear()

    for row_idx, row in enumerate(grid):
        if symbol_match(row):
            winning_lines.append(("row", row_idx))
            payout += row[0]["multiplier"] * wager

    for col in range(COLS):
        col_syms = [grid[r][col] for r in range(ROWS)]
        if symbol_match(col_syms):
            winning_lines.append(("col", col))
            payout += col_syms[0]["multiplier"] * wager

    diag1 = [grid[i][i] for i in range(min(ROWS, COLS))]
    if symbol_match(diag1):
        winning_lines.append(("diag", "tlbr"))
        payout += diag1[0]["multiplier"] * wager

    diag2 = [grid[i][COLS - 1 - i] for i in range(min(ROWS, COLS))]
    if symbol_match(diag2):
        winning_lines.append(("diag", "trbl"))
        payout += diag2[0]["multiplier"] * wager

    if wild_doubler_triggered:
        payout *= 2

    total_credits_won += payout
    credits += payout
    flash_index = 0
    flash_timer = 0

    write_log()

def draw_paylines():
    if not winning_lines:
        return
    global flash_index, flash_timer
    if flash_timer == 0:
        line = winning_lines[flash_index % len(winning_lines)]
        x_offset = (WIDTH - (COLS * TILE_SIZE)) // 2
        y_offset = 80

        if line[0] == "row":
            y = y_offset + line[1] * TILE_SIZE + TILE_SIZE // 2
            pygame.draw.line(screen, BLUE, (x_offset, y), (x_offset + COLS * TILE_SIZE, y), 5)
        elif line[0] == "col":
            x = x_offset + line[1] * TILE_SIZE + TILE_SIZE // 2
            pygame.draw.line(screen, BLUE, (x, y_offset), (x, y_offset + ROWS * TILE_SIZE), 5)
        elif line[1] == "tlbr":
            pygame.draw.line(screen, BLUE, (x_offset, y_offset),
                             (x_offset + COLS * TILE_SIZE, y_offset + ROWS * TILE_SIZE), 5)
        elif line[1] == "trbl":
            pygame.draw.line(screen, BLUE, (x_offset + COLS * TILE_SIZE, y_offset),
                             (x_offset, y_offset + ROWS * TILE_SIZE), 5)

    flash_timer += 1
    if flash_timer > FLASH_TIME:
        flash_timer = 0
        flash_index += 1

# Game loop
running = True
while running:
    screen.fill(BG_COLOR)

    if show_info:
        draw_info_screen()
    elif show_shop:
        draw_shop_screen()
    else:
        draw_grid()
        draw_paylines()
        draw_ui()

    pygame.draw.rect(screen, (100, 100, 255), info_button)
    pygame.draw.rect(screen, BLACK, info_button, 3)
    screen.blit(FONT.render("INFO", True, WHITE), (info_button.x + 5, info_button.y + 5))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if show_shop:
                if shop_back_button.collidepoint(event.pos):
                    show_shop = False
                for item in shop_credit_buttons:
                    if item["rect"].collidepoint(event.pos):
                        credits += item["credits"]
                        show_shop = False
            elif show_info:
                if info_button.collidepoint(event.pos):
                    show_info = False
            elif auto_spin_button.collidepoint(event.pos):
                 auto_spin = not auto_spin

            else:
                if info_button.collidepoint(event.pos):
                    show_info = True
                elif shop_button.collidepoint(event.pos):
                    show_shop = True
                elif spin_button.collidepoint(event.pos) and not spinning and credits >= wager:
                    credits -= wager
                    total_credits_spent += wager
                    spinning = True
                    spin_frames = 0
                    payout = 0
                    winning_lines.clear()
                elif not spinning:
                    if wager_up_button.collidepoint(event.pos):
                        wager = min(wager + 1, WAGER_MAX)
                    elif wager_down_button.collidepoint(event.pos):
                        wager = max(wager - 1, WAGER_MIN)
                    elif max_bet_button.collidepoint(event.pos):
                        wager = min(WAGER_MAX, credits)
                    elif min_bet_button.collidepoint(event.pos):
                        wager = WAGER_MIN
    
    if spinning and not show_info and not show_shop:
        animate_spin()
        if not spinning:
            calculate_payout()
            if auto_spin and credits >= wager:
                auto_spin_pause = PAUSE_DURATION

    if auto_spin_pause > 0:
        auto_spin_pause -= 1
        if auto_spin_pause == 0 and not spinning and credits >= wager:
            credits -= wager
            total_credits_spent += wager
            spinning = True
            spin_frames = 0
            payout = 0
            winning_lines.clear()

    # Animate credits increase smoothly
    if display_credits < credits:
        display_credits += max(1, (credits - display_credits) * 0.1)
        if display_credits > credits:
            display_credits = credits
    elif display_credits > credits:
        display_credits -= max(1, (display_credits - credits) * 0.1)
        if display_credits < credits:
            display_credits = credits

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
