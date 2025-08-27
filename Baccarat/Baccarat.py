import pygame, sys, random

# --- CONFIG ---
WIDTH, HEIGHT = 1200, 750
CARD_WIDTH, CARD_HEIGHT = 80, 120
FPS = 30
STARTING_CREDITS = 1000
BET_AMOUNT = 50
TOTAL_DECKS = 16

# --- INIT ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Baccarat Simulator")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 22, bold=True)
big_font = pygame.font.SysFont("arial", 48, bold=True)

# --- SUITS, SYMBOLS, COLORS ---
suit_symbols = {"C":"♣","D":"♦","H":"♥","S":"♠"}
suit_colors = {"C":(0,0,0),"S":(0,0,0),"D":(220,20,60),"H":(220,20,60)}
ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

def make_card(rank,suit):
    surf = pygame.Surface((CARD_WIDTH,CARD_HEIGHT))
    surf.fill((255,255,255))
    pygame.draw.rect(surf,(0,0,0),surf.get_rect(),2)
    text = font.render(rank,True,suit_colors[suit])
    surf.blit(text,(5,5))
    stext = font.render(suit_symbols[suit],True,suit_colors[suit])
    surf.blit(stext,(CARD_WIDTH-30,CARD_HEIGHT-35))
    return surf

cards_img = {r+s: make_card(r,s) for r in ranks for s in suit_symbols}

# --- GAME LOGIC ---
def card_value(card):
    rank = card[:-1]
    if rank in ["10","J","Q","K"]: return 0
    elif rank=="A": return 1
    else: return int(rank)

def hand_total(hand): return sum(card_value(c) for c in hand)%10
def draw_card(deck): return deck.pop()

def baccarat_round(deck):
    player=[draw_card(deck),draw_card(deck)]
    banker=[draw_card(deck),draw_card(deck)]
    pt,bt=hand_total(player),hand_total(banker)
    if pt>=8 or bt>=8: return player, banker
    player_third=None
    if pt<=5:
        player_third=draw_card(deck); player.append(player_third); pt=hand_total(player)
    if player_third is None:
        if bt<=5: banker.append(draw_card(deck))
    else:
        pv=card_value(player_third)
        if bt<=2: banker.append(draw_card(deck))
        elif bt==3 and pv!=8: banker.append(draw_card(deck))
        elif bt==4 and pv in [2,3,4,5,6,7]: banker.append(draw_card(deck))
        elif bt==5 and pv in [4,5,6,7]: banker.append(draw_card(deck))
        elif bt==6 and pv in [6,7]: banker.append(draw_card(deck))
    return player, banker

def winner(player, banker):
    pt,bt=hand_total(player),hand_total(banker)
    if pt>bt: return "Player"
    elif bt>pt: return "Banker"
    else: return "Tie"

def build_deck(): return [r+s for r in ranks for s in suit_symbols]*TOTAL_DECKS

# Side bet checkers
def is_perfect_pair(hand): return len(hand)>=2 and hand[0]==hand[1]
def is_any_pair(p,b):
    return (len(p)>=2 and p[0][:-1]==p[1][:-1]) or (len(b)>=2 and b[0][:-1]==b[1][:-1])
def is_player_pair(p): return len(p)>=2 and p[0][:-1]==p[1][:-1]
def is_banker_pair(b): return len(b)>=2 and b[0][:-1]==b[1][:-1]

# --- MAIN LOOP ---
def main():
    deck=build_deck(); random.shuffle(deck)
    reshuffle_point=len(deck)//2
    credits=STARTING_CREDITS
    main_bet=None; side_bets=[]
    player_hand,banker_hand=[],[]
    result=""; tracker=[]

    while True:
        for e in pygame.event.get():
            if e.type==pygame.QUIT: sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_1: main_bet="Player"
                if e.key==pygame.K_2: main_bet="Banker"
                if e.key==pygame.K_3: main_bet="Tie"
                if e.key==pygame.K_q: side_bets.append("Perfect Pair")
                if e.key==pygame.K_w: side_bets.append("Any Pair")
                if e.key==pygame.K_e: side_bets.append("Player Pair")
                if e.key==pygame.K_r: side_bets.append("Banker Pair")
                if e.key==pygame.K_SPACE and main_bet:
                    if len(deck)<20 or len(deck)<reshuffle_point:
                        deck=build_deck(); random.shuffle(deck)
                        reshuffle_point=len(deck)//2
                        print(">>> Deck reshuffled <<<")
                    player_hand,banker_hand=baccarat_round(deck)
                    result=winner(player_hand,banker_hand)
                    tracker.append(result)
                    # main bet payout
                    if result==main_bet:
                        if result=="Player": credits+=BET_AMOUNT
                        elif result=="Banker": credits+=int(BET_AMOUNT*0.95)
                        else: credits+=BET_AMOUNT*8
                    else:
                        credits-=BET_AMOUNT
                    # side bet payouts
                    for sb in side_bets:
                        if sb=="Perfect Pair" and (is_perfect_pair(player_hand) or is_perfect_pair(banker_hand)):
                            credits+=BET_AMOUNT*25
                        elif sb=="Any Pair" and is_any_pair(player_hand,banker_hand):
                            credits+=BET_AMOUNT*5
                        elif sb=="Player Pair" and is_player_pair(player_hand):
                            credits+=BET_AMOUNT*11
                        elif sb=="Banker Pair" and is_banker_pair(banker_hand):
                            credits+=BET_AMOUNT*11
                        else:
                            credits-=BET_AMOUNT
                    side_bets=[]; main_bet=None

        # Draw
        screen.fill((0,100,0))
        for i,c in enumerate(player_hand): screen.blit(cards_img[c],(100+i*100,200))
        screen.blit(font.render(f"Player: {hand_total(player_hand)}",True,(255,255,255)),(100,150))
        for i,c in enumerate(banker_hand): screen.blit(cards_img[c],(100+i*100,400))
        screen.blit(font.render(f"Banker: {hand_total(banker_hand)}",True,(255,255,255)),(100,350))
        screen.blit(font.render(f"Credits: {credits}",True,(255,215,0)),(WIDTH-250,30))

        if not main_bet:
            screen.blit(font.render("Press 1=Player, 2=Banker, 3=Tie",True,(255,255,255)),(WIDTH//2-200,HEIGHT-90))
            screen.blit(font.render("Q=Perfect Pair, W=Any Pair, E=Player Pair, R=Banker Pair",True,(255,255,255)),(WIDTH//2-300,HEIGHT-60))
            screen.blit(font.render("Press SPACE to deal",True,(255,255,255)),(WIDTH//2-150,HEIGHT-30))
        else:
            screen.blit(font.render(f"Main bet: {main_bet}",True,(255,255,255)),(WIDTH//2-150,HEIGHT-70))
            if side_bets:
                screen.blit(font.render(f"Sides: {', '.join(side_bets)}",True,(255,255,255)),(WIDTH//2-200,HEIGHT-40))

        if result:
            rtext=big_font.render(f"{result} Wins!",True,(255,255,0))
            screen.blit(rtext,(WIDTH//2-rtext.get_width()//2,50))

        # Tracker
        cols,rows=20,6; cell=25
        ox,oy=WIDTH-(cols*cell+40),120
        for i,res in enumerate(tracker[-cols*rows:]):
            x=i%cols; y=i//cols
            rect=pygame.Rect(ox+x*cell,oy+y*cell,cell-2,cell-2)
            color=(255,255,255)
            if res=="Player": color=(30,144,255)
            elif res=="Banker": color=(220,20,60)
            elif res=="Tie": color=(255,215,0)
            pygame.draw.rect(screen,color,rect)
        pygame.draw.rect(screen,(255,255,255),(ox-5,oy-5,cols*cell+10,rows*cell+10),2)

        # Info legend
        lx,ly=WIDTH-320,HEIGHT-180
        legend=[
            "Legend / Odds:",
            "Player Win: 1:1",
            "Banker Win: 0.95:1",
            "Tie: 8:1",
            "Perfect Pair: 25:1 (Q)",
            "Any Pair: 5:1 (W)",
            "Player Pair: 11:1 (E)",
            "Banker Pair: 11:1 (R)"
        ]
        for i,line in enumerate(legend):
            screen.blit(font.render(line,True,(255,255,255)),(lx,ly+i*22))

        pygame.display.flip(); clock.tick(FPS)

if __name__=="__main__": main()
