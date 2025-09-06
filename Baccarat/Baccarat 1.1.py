import pygame, sys, random, time

# --- CONFIG ---
WIDTH, HEIGHT = 1280, 820   # taller to fit UI
CARD_W, CARD_H = 100, 140
FPS = 60
STARTING_CREDITS = 1000
TOTAL_DECKS = 16
CHIP_VALUES = [1, 5, 25, 100, 500]

PAYOUTS = {
    'Player': 1.0,
    'Banker': 0.95,
    'Tie': 8.0,
    'Perfect Pair': 25.0,
    'Any Pair': 5.0,
    'Player Pair': 11.0,
    'Banker Pair': 11.0,
    'Double Perfect Pair': 200.0
}

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Baccarat — Full Functional UI")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("arial", 20, bold=True)
SMALL = pygame.font.SysFont("arial", 16)
BIG = pygame.font.SysFont("arial", 44, bold=True)

SUIT_SYMBOLS = {"C":"♣","D":"♦","H":"♥","S":"♠"}
SUIT_COLORS = {"C": (0,0,0),"S": (0,0,0),"D": (220,20,60),"H": (220,20,60)}
RANKS = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

def make_card(rank,suit):
    surf = pygame.Surface((CARD_W,CARD_H),pygame.SRCALPHA)
    surf.fill((245,245,245))
    pygame.draw.rect(surf,(30,30,30),surf.get_rect(),2,border_radius=8)
    rtxt = FONT.render(rank, True, SUIT_COLORS[suit])
    surf.blit(rtxt,(8,8))
    stxt = FONT.render(SUIT_SYMBOLS[suit], True, SUIT_COLORS[suit])
    surf.blit(stxt,(CARD_W-30,CARD_H-36))
    return surf

def make_back():
    surf = pygame.Surface((CARD_W,CARD_H),pygame.SRCALPHA)
    surf.fill((20,80,30))
    pygame.draw.rect(surf,(0,0,0),surf.get_rect(),2,border_radius=8)
    for y in range(12,CARD_H-8,12):
        pygame.draw.line(surf,(60,150,70),(10,y),(CARD_W-10,y),2)
    return surf

CARDS = {r+s: make_card(r,s) for r in RANKS for s in SUIT_SYMBOLS}
CARD_BACK = make_back()

def rotated_card(card_key):
    """Return a sideways version of the card surface."""
    return pygame.transform.rotate(CARDS[card_key], 90)

def rotated_back():
    """Sideways card back (for animations)."""
    return pygame.transform.rotate(CARD_BACK, 90)

# --- GAME LOGIC ---
def build_deck(): return [r+s for r in RANKS for s in SUIT_SYMBOLS]*TOTAL_DECKS
def card_value(c): r=c[:-1]; return 0 if r in ["10","J","Q","K"] else 1 if r=="A" else int(r)
def hand_total(h): return sum(card_value(c) for c in h)%10
def draw_card(deck): return deck.pop()

def baccarat_round(deck):
    player=[draw_card(deck),draw_card(deck)]
    banker=[draw_card(deck),draw_card(deck)]
    pt,bt=hand_total(player),hand_total(banker)
    if pt>=8 or bt>=8: return player,banker
    player_third=None
    if pt<=5: player_third=draw_card(deck); player.append(player_third); pt=hand_total(player)
    if player_third is None:
        if bt<=5: banker.append(draw_card(deck))
    else:
        pv=card_value(player_third)
        if bt<=2: banker.append(draw_card(deck))
        elif bt==3 and pv!=8: banker.append(draw_card(deck))
        elif bt==4 and pv in [2,3,4,5,6,7]: banker.append(draw_card(deck))
        elif bt==5 and pv in [4,5,6,7]: banker.append(draw_card(deck))
        elif bt==6 and pv in [6,7]: banker.append(draw_card(deck))
    return player,banker

def winner(player,banker):
    pt,bt=hand_total(player),hand_total(banker)
    if pt>bt: return "Player"
    if bt>pt: return "Banker"
    return "Tie"

def is_perfect_pair(hand): return len(hand)>=2 and hand[0]==hand[1]
def is_any_pair(p,b): return (len(p)>=2 and p[0][:-1]==p[1][:-1]) or (len(b)>=2 and b[0][:-1]==b[1][:-1])
def is_player_pair(p): return len(p)>=2 and p[0][:-1]==p[1][:-1]
def is_banker_pair(b): return len(b)>=2 and b[0][:-1]==b[1][:-1]

# --- UI ---
class Button:
    def __init__(self, rect,label,cb=None,color=(50,50,50)):
        self.rect=pygame.Rect(rect)
        self.label=label
        self.cb=cb
        self.color=color
    def draw(self,surf):
        pygame.draw.rect(surf,self.color,self.rect,border_radius=8)
        pygame.draw.rect(surf,(0,0,0),self.rect,2,border_radius=8)
        txt=FONT.render(self.label,True,(255,255,255))
        surf.blit(txt,(self.rect.centerx-txt.get_width()//2,self.rect.centery-txt.get_height()//2))
    def handle_event(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self.rect.collidepoint(event.pos):
            if self.cb: self.cb()

class BaccaratGame:
    def __init__(self):
        self.deck=build_deck(); random.shuffle(self.deck)
        self.reshuffle_point=len(self.deck)//2
        self.credits=STARTING_CREDITS
        self.bets={k:0 for k in ['Player','Banker','Tie','Perfect Pair','Any Pair','Player Pair','Banker Pair']}
        self.selected_chip=CHIP_VALUES[1]
        self.chips_rects=[]
        self.bet_zone_rects={}
        self.side_rects={}
        self.player_hand=[]
        self.banker_hand=[]
        self.animating=False
        self.animation_start=0
        self.flip_time=0.45
        self.anim_sequence=[]
        self.tracker=[]
        self.message=''
        self.buttons=[]

    def reshuffle_if_needed(self):
        if len(self.deck)<20 or len(self.deck)<self.reshuffle_point:
            self.deck=build_deck(); random.shuffle(self.deck)
            self.reshuffle_point=len(self.deck)//2
            self.message='Deck reshuffled'

    def select_chip(self,val): self.selected_chip=val; self.message=f"Selected chip {val}"
    def place_bet(self,area):
        if self.animating: self.message='Wait for current round to finish'; return
        if self.credits<self.selected_chip: self.message='Not enough credits'; return
        self.bets[area]+=self.selected_chip; self.credits-=self.selected_chip
        self.message=f"Placed {self.selected_chip} on {area}"
    def clear_bets(self):
        self.credits+=sum(self.bets.values())
        for k in self.bets: self.bets[k]=0
        self.message='Bets cleared'
    def max_bet(self):
        if self.credits<=0: self.message='No credits for Max Bet'; return
        placed=0
        while self.credits>=self.selected_chip:
            self.bets['Player']+=self.selected_chip
            self.credits-=self.selected_chip
            placed+=self.selected_chip
        self.message=f'Max bet placed ({placed}) on Player'

    def start_deal(self):
        if self.animating: return
        if self.bets['Player']+self.bets['Banker']+self.bets['Tie']<=0:
            self.message='Place a main bet first (Player/Banker/Tie)'; return
        self.reshuffle_if_needed()
        self.player_hand,self.banker_hand=baccarat_round(self.deck)
        # Build animation sequence
        left_x=WIDTH//2-380; right_x=WIDTH//2+160; cy=HEIGHT//2-40
        spacing = CARD_W + 16
        seq=[]
        # push the first two player cards (P1,P2)
        for i in range(min(2,len(self.player_hand))):
            seq.append((self.player_hand[i],(left_x+i*spacing,cy)))
        # push the first two banker cards (B1,B2)
        for i in range(min(2,len(self.banker_hand))):
            seq.append((self.banker_hand[i],(right_x+i*spacing,cy)))
        # optional third cards
        if len(self.player_hand)==3:
            seq.append((self.player_hand[2],(left_x+2*spacing,cy)))
        if len(self.banker_hand)==3:
            seq.append((self.banker_hand[2],(right_x+2*spacing,cy)))
        self.anim_sequence=seq
        self.animation_start=time.time(); self.animating=True; self.message='Dealing...'

    def finish_round_and_payouts(self):
        res=winner(self.player_hand,self.banker_hand)
        self.tracker.append(res)
        # Main bets
        for area in ['Player','Banker','Tie']:
            stake=self.bets[area]
            if stake>0:
                if area==res: self.credits+=stake+int(stake*PAYOUTS[area])
        # Side bets - Perfect Pair covers single or double perfect
        if self.bets['Perfect Pair']>0:
            pp_player = is_perfect_pair(self.player_hand)
            pp_banker = is_perfect_pair(self.banker_hand)
            if pp_player and pp_banker:
                self.credits+=self.bets['Perfect Pair']+int(self.bets['Perfect Pair']*PAYOUTS['Double Perfect Pair'])
                self.message = "DOUBLE PERFECT PAIR! Payout applied."
            elif pp_player or pp_banker:
                self.credits+=self.bets['Perfect Pair']+int(self.bets['Perfect Pair']*PAYOUTS['Perfect Pair'])
        if self.bets['Any Pair']>0 and is_any_pair(self.player_hand,self.banker_hand):
            self.credits+=self.bets['Any Pair']+int(self.bets['Any Pair']*PAYOUTS['Any Pair'])
        if self.bets['Player Pair']>0 and is_player_pair(self.player_hand):
            self.credits+=self.bets['Player Pair']+int(self.bets['Player Pair']*PAYOUTS['Player Pair'])
        if self.bets['Banker Pair']>0 and is_banker_pair(self.banker_hand):
            self.credits+=self.bets['Banker Pair']+int(self.bets['Banker Pair']*PAYOUTS['Banker Pair'])
        # Clear bets
        for k in self.bets: self.bets[k]=0
        self.animating=False
        if not self.message.startswith("DOUBLE PERFECT PAIR"):
            self.message=f"{res} Wins!"

    def update_animation(self):
        if not self.animating: return
        elapsed=time.time()-self.animation_start
        index=int(elapsed//self.flip_time)
        if index>=len(self.anim_sequence):
            self.finish_round_and_payouts()

    def draw(self,surf):
        surf.fill((8,80,30))
        # Top: title & credits
        title=BIG.render("Baccarat",True,(255,215,0))
        surf.blit(title,(WIDTH//2-title.get_width()//2,8))
        credits_txt=FONT.render(f"Credits: {self.credits}",True,(255,215,0))
        surf.blit(credits_txt,(WIDTH//2-credits_txt.get_width()//2,64))
        # CARD AREA
        left_x=WIDTH//2-380; right_x=WIDTH//2+160; cy=HEIGHT//2-40
        spacing = CARD_W + 16
        elapsed=time.time()-self.animation_start if self.animating else 999

        # Player cards
        for i in range(3):
            pos=(left_x+i*spacing,cy)
            rect=pygame.Rect(pos[0],pos[1],CARD_W,CARD_H)
            seq_idx=0 if i==0 else 1 if i==1 else 4
            if seq_idx < len(self.anim_sequence):
                start_t = seq_idx * self.flip_time
                # Fully revealed (after flip animation)
                if not self.animating or elapsed >= start_t + self.flip_time:
                    if i < len(self.player_hand):
                        if i == 2:
                            img = rotated_card(self.player_hand[i])
                            r = img.get_rect(center=(rect.centerx, rect.centery+30))  # shift down a little
                            surf.blit(img, r.topleft)
                        else:
                            surf.blit(CARDS[self.player_hand[i]], rect.topleft)
                    else:
                        pygame.draw.rect(surf,(200,200,200),rect,2,border_radius=6)
                # Still waiting to start flip: show back
                elif elapsed < start_t:
                    if i == 2:
                        surf.blit(rotated_back(), rect.topleft)
                    else:
                        surf.blit(CARD_BACK, rect.topleft)
                # In the middle of flip animation
                else:
                    prog = (elapsed - start_t) / self.flip_time
                    # scale width from full to thin to full (flip)
                    scale = int(CARD_W * (1 - 2*prog)) if prog < 0.5 else int(CARD_W * (2*prog))
                    scale = max(2, scale)
                    # pick base image: rotated for third card
                    if i == 2 and i < len(self.player_hand):
                        base_img = rotated_card(self.player_hand[i])
                    elif i < len(self.player_hand):
                        base_img = CARDS[self.player_hand[i]]
                    else:
                        base_img = CARD_BACK
                    img = pygame.transform.smoothscale(base_img, (scale, CARD_H))
                    surf.blit(img, img.get_rect(center=rect.center).topleft)
            else:
                # no animation for this slot (cards already shown / empty)
                if i < len(self.player_hand):
                    if i == 2:
                        img = rotated_card(self.player_hand[i])
                        r = img.get_rect(center=(rect.centerx, rect.centery+30))
                        surf.blit(img, r.topleft)
                    else:
                        surf.blit(CARDS[self.player_hand[i]], rect.topleft)
                else:
                    pygame.draw.rect(surf,(200,200,200),rect,2,border_radius=6)

        # Banker cards
        for i in range(3):
            pos=(right_x+i*spacing,cy)
            rect=pygame.Rect(pos[0],pos[1],CARD_W,CARD_H)
            seq_idx=2+i if i<2 else 5
            if seq_idx < len(self.anim_sequence):
                start_t = seq_idx * self.flip_time
                if not self.animating or elapsed >= start_t + self.flip_time:
                    if i < len(self.banker_hand):
                        if i == 2:
                            img = rotated_card(self.banker_hand[i])
                            r = img.get_rect(center=(rect.centerx, rect.centery+30))
                            surf.blit(img, r.topleft)
                        else:
                            surf.blit(CARDS[self.banker_hand[i]], rect.topleft)
                    else:
                        pygame.draw.rect(surf,(200,200,200),rect,2,border_radius=6)
                elif elapsed < start_t:
                    if i == 2:
                        surf.blit(rotated_back(), rect.topleft)
                    else:
                        surf.blit(CARD_BACK, rect.topleft)
                else:
                    prog = (elapsed - start_t) / self.flip_time
                    scale = int(CARD_W * (1 - 2*prog)) if prog < 0.5 else int(CARD_W * (2*prog))
                    scale = max(2, scale)
                    if i == 2 and i < len(self.banker_hand):
                        base_img = rotated_card(self.banker_hand[i])
                    elif i < len(self.banker_hand):
                        base_img = CARDS[self.banker_hand[i]]
                    else:
                        base_img = CARD_BACK
                    img = pygame.transform.smoothscale(base_img, (scale, CARD_H))
                    surf.blit(img, img.get_rect(center=rect.center).topleft)
            else:
                if i < len(self.banker_hand):
                    if i == 2:
                        img = rotated_card(self.banker_hand[i])
                        r = img.get_rect(center=(rect.centerx, rect.centery+30))
                        surf.blit(img, r.topleft)
                    else:
                        surf.blit(CARDS[self.banker_hand[i]], rect.topleft)
                else:
                    pygame.draw.rect(surf,(200,200,200),rect,2,border_radius=6)

        # Scores
        surf.blit(FONT.render(f"Player: {hand_total(self.player_hand) if self.player_hand else '-'}",True,(255,255,255)),(left_x,cy-36))
        surf.blit(FONT.render(f"Banker: {hand_total(self.banker_hand) if self.banker_hand else '-'}",True,(255,255,255)),(right_x,cy-36))

        # Main bets
        bet_y=HEIGHT-280; zone_w,zone_h=220,90
        zones={'Player':pygame.Rect(WIDTH//2-zone_w-240,bet_y,zone_w,zone_h),
               'Tie':pygame.Rect(WIDTH//2-zone_w//2,bet_y,zone_w,zone_h),
               'Banker':pygame.Rect(WIDTH//2+240,bet_y,zone_w,zone_h)}
        colors={'Player':(30,130,200),'Tie':(200,180,40),'Banker':(180,30,40)}
        for name,rect in zones.items():
            pygame.draw.rect(surf,colors[name],rect,border_radius=10)
            pygame.draw.rect(surf,(255,255,255),rect,2,border_radius=10)
            surf.blit(BIG.render(name.upper(),True,(255,255,255)),(rect.centerx-50,rect.top+8))
            surf.blit(FONT.render(f"Bet: {self.bets[name]}",True,(255,255,255)),(rect.left+8,rect.bottom-32))
            self.bet_zone_rects[name]=rect

        # Side bets
        side_names=['Perfect Pair','Any Pair','Player Pair','Banker Pair']
        side_start_x=WIDTH//2-(len(side_names)*180)//2; side_y=bet_y+zone_h+12
        for i,name in enumerate(side_names):
            r=pygame.Rect(side_start_x+i*180,side_y,170,44)
            pygame.draw.rect(surf,(45,70,45),r,border_radius=8)
            pygame.draw.rect(surf,(255,255,255),r,2,border_radius=8)
            surf.blit(FONT.render(name,True,(255,255,255)),(r.left+8,r.top+8))
            surf.blit(FONT.render(str(self.bets[name]),True,(255,215,0)),(r.right-60,r.top+8))
            self.side_rects[name]=r

        # Chip tray
        tray_y=HEIGHT-100; tray_x=WIDTH//2-(len(CHIP_VALUES)*100)//2
        self.chips_rects=[]
        for i,val in enumerate(CHIP_VALUES):
            r=pygame.Rect(tray_x+i*100,tray_y,72,72)
            pygame.draw.circle(surf,(210,170,60),r.center,34)
            pygame.draw.circle(surf,(0,0,0),r.center,36,2)
            txt=FONT.render(str(val),True,(0,0,0))
            surf.blit(txt,(r.centerx-txt.get_width()//2,r.centery-txt.get_height()//2))
            if val==self.selected_chip: pygame.draw.circle(surf,(255,255,255),r.center,38,3)
            self.chips_rects.append((r,val))

        # Tracker top right
        cols,rows=12,4
        cell=20
        margin=24
        tx=WIDTH - (cols*(cell+4)) - margin
        ty=120  # just below credits
        surf.blit(FONT.render('Tracker:',True,(255,255,255)),(tx,ty-28))
        for i,res in enumerate(self.tracker[-cols*rows:]):
            x=i%cols; y=i//cols
            rect=pygame.Rect(tx+x*(cell+4),ty+y*(cell+6),cell,cell)
            color=(200,200,200)
            if res=='Player': color=(30,144,255)
            elif res=='Banker': color=(220,20,60)
            elif res=='Tie': color=(200,180,40)
            pygame.draw.rect(surf,color,rect)

        # Buttons (Clear / Max) - drawn at right
        for b in self.buttons:
            b.draw(surf)

        # Message
        surf.blit(FONT.render(self.message,True,(255,215,0)),(24,24))

    def handle_click(self,pos):
        # Main bets
        for name,rect in self.bet_zone_rects.items():
            if rect.collidepoint(pos): self.place_bet(name)
        for name,rect in self.side_rects.items():
            if rect.collidepoint(pos): self.place_bet(name)
        for r,val in self.chips_rects:
            if r.collidepoint(pos): self.select_chip(val)
        for b in self.buttons: b.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,{'pos':pos,'button':1}))

# --- INIT GAME ---
game=BaccaratGame()
# Buttons
btn_clear=Button((WIDTH-180,HEIGHT-100,160,44),"Clear Bets",game.clear_bets)
btn_max=Button((WIDTH-180,HEIGHT-50,160,44),"Max Bet",game.max_bet)
game.buttons=[btn_clear,btn_max]

# --- MAIN LOOP ---
running=True
while running:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type==pygame.QUIT: running=False
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1: game.handle_click(event.pos)
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE: running=False
            elif event.key==pygame.K_SPACE: game.start_deal()
            elif event.key==pygame.K_c: game.clear_bets()
            elif event.key==pygame.K_m: game.max_bet()
            elif event.key in [pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4,pygame.K_5]:
                idx=event.key-pygame.K_1; game.select_chip(CHIP_VALUES[idx])
    game.update_animation()
    game.draw(screen)
    pygame.display.flip()
pygame.quit()
sys.exit()
