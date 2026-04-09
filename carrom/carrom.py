import pygame
import math
import sys

pygame.init()

# ── Window & Board ────────────────────────────────────────────────────────────
WIN_W, WIN_H = 900, 960
BSIZE = 700
BX, BY = 100, 90
BL, BT = BX, BY
BR, BB = BX + BSIZE, BY + BSIZE
BW = 18                         # border width
PL, PT = BL + BW, BT + BW      # inner play-area corners
PR, PB = BR - BW, BB - BW
CX, CY = (PL + PR) // 2, (PT + PB) // 2

BLY1 = PB - 58   # Player-1 baseline y (bottom)
BLY2 = PT + 58   # Player-2 baseline y (top)
BLX1 = PL + 92   # baseline x left bound
BLX2 = PR - 92   # baseline x right bound

# ── Physics ───────────────────────────────────────────────────────────────────
FPS      = 60
FRICTION = 0.983
VSTOP    = 0.22
MAX_DRAG = 140
MAX_SPD  = 24.0

# ── Sizes ─────────────────────────────────────────────────────────────────────
PCR = 14   # piece radius
STR = 20   # striker radius
PKR = 30   # pocket radius

POCKETS = [(PL, PT), (PR, PT), (PL, PB), (PR, PB)]

# ── Colours ───────────────────────────────────────────────────────────────────
CB    = (20, 12, 5)
CBRD  = (195, 158, 90)
CBDR  = (85, 50, 15)
CLINE = (145, 105, 48)
CPKT  = (8, 5, 3)
CWHT  = (240, 235, 210)
CBLK  = (32, 27, 22)
CRED  = (210, 42, 42)
CP1   = (60, 120, 235)
CP2   = (235, 88, 45)
CTXT  = (228, 205, 150)
CHUD  = (35, 20, 8)
CDRG  = (255, 235, 60)

AIMING, MOVING, GAME_OVER = 0, 1, 2


# ── Piece ─────────────────────────────────────────────────────────────────────
class Piece:
    def __init__(self, x, y, kind, owner=None):
        self.x = float(x)
        self.y = float(y)
        self.vx = self.vy = 0.0
        self.kind  = kind    # 'white' | 'black' | 'red' | 'striker'
        self.owner = owner   # 1 or 2  (striker only)
        self.r     = STR if kind == 'striker' else PCR
        self.alive = True

    def color(self):
        k = self.kind
        if k == 'white':   return CWHT
        if k == 'black':   return CBLK
        if k == 'red':     return CRED
        if k == 'striker': return CP1 if self.owner == 1 else CP2
        return (128, 128, 128)

    def update(self):
        self.x  += self.vx;  self.y  += self.vy
        self.vx *= FRICTION; self.vy *= FRICTION
        if abs(self.vx) < VSTOP: self.vx = 0.0
        if abs(self.vy) < VSTOP: self.vy = 0.0

    @property
    def moving(self):
        return self.vx != 0.0 or self.vy != 0.0

    def bounce(self):
        # Skip wall-bounce if already heading into a pocket zone
        if any(math.hypot(self.x - px, self.y - py) < PKR + self.r
               for px, py in POCKETS):
            return
        if self.x - self.r < PL: self.x = PL + self.r; self.vx =  abs(self.vx) * 0.85
        if self.x + self.r > PR: self.x = PR - self.r; self.vx = -abs(self.vx) * 0.85
        if self.y - self.r < PT: self.y = PT + self.r; self.vy =  abs(self.vy) * 0.85
        if self.y + self.r > PB: self.y = PB - self.r; self.vy = -abs(self.vy) * 0.85

    def in_pocket(self):
        return any(math.hypot(self.x - px, self.y - py) < PKR
                   for px, py in POCKETS)

    def draw(self, surf):
        ix, iy = int(self.x), int(self.y)
        col = self.color()
        pygame.draw.circle(surf, (0, 0, 0), (ix + 2, iy + 2), self.r)
        pygame.draw.circle(surf, col, (ix, iy), self.r)
        hi = tuple(min(255, c + 70) for c in col)
        pygame.draw.circle(surf, hi, (ix - self.r // 3, iy - self.r // 3), self.r // 3)
        pygame.draw.circle(surf, (0, 0, 0), (ix, iy), self.r, 1)
        if self.kind == 'striker':
            pygame.draw.circle(surf, (200, 200, 200), (ix, iy), self.r - 5, 2)
        elif self.kind == 'red':
            pygame.draw.circle(surf, (240, 180, 40), (ix, iy), self.r // 2)


# ── Collision ─────────────────────────────────────────────────────────────────
def collide(a, b):
    dx, dy = b.x - a.x, b.y - a.y
    d  = math.hypot(dx, dy)
    md = a.r + b.r
    if 1e-6 < d < md:
        nx, ny = dx / d, dy / d
        dv = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
        if dv > 0:
            a.vx -= dv * nx; a.vy -= dv * ny
            b.vx += dv * nx; b.vy += dv * ny
        ov = (md - d) / 2
        a.x -= nx * ov; a.y -= ny * ov
        b.x += nx * ov; b.y += ny * ov


# ── Board drawing ─────────────────────────────────────────────────────────────
def draw_board(surf):
    surf.fill(CB)
    pygame.draw.rect(surf, CBDR,  (BL, BT, BSIZE, BSIZE))
    pygame.draw.rect(surf, CBRD,  (PL, PT, PR - PL, PB - PT))

    lc = CLINE
    d = 80
    for cx, cy, sx, sy in [(PL,PT,1,1),(PR,PT,-1,1),(PL,PB,1,-1),(PR,PB,-1,-1)]:
        pygame.draw.line(surf, lc, (cx, cy), (cx + sx*d, cy + sy*d), 2)

    pygame.draw.circle(surf, lc, (CX, CY), 80, 2)
    pygame.draw.circle(surf, lc, (CX, CY), 20, 2)
    pygame.draw.circle(surf, lc, (CX, CY),  4)

    for bly in (BLY1, BLY2):
        pygame.draw.line(surf, lc, (BLX1, bly), (BLX2, bly), 2)
        pygame.draw.circle(surf, lc, (BLX1, bly), 5, 2)
        pygame.draw.circle(surf, lc, (BLX2, bly), 5, 2)

    # Player-side labels on board
    fs = pygame.font.SysFont('Arial', 16)
    surf.blit(fs.render("← P2 baseline →", True, (160, 120, 60)), (CX - 70, BLY2 + 6))
    surf.blit(fs.render("← P1 baseline →", True, (160, 120, 60)), (CX - 70, BLY1 - 22))

    for px, py in POCKETS:
        pygame.draw.circle(surf, CPKT,      (px, py), PKR)
        pygame.draw.circle(surf, (25,18,8), (px, py), PKR, 4)


# ── Initial pieces ────────────────────────────────────────────────────────────
def make_pieces():
    ps = [Piece(CX, CY, 'red')]          # queen at centre
    r1 = PCR * 2.35
    for i in range(6):
        a = math.radians(30 + i * 60)
        ps.append(Piece(CX + r1*math.cos(a), CY + r1*math.sin(a),
                        'white' if i % 2 == 0 else 'black'))
    r2 = PCR * 4.70
    for i in range(12):
        a = math.radians(i * 30)
        ps.append(Piece(CX + r2*math.cos(a), CY + r2*math.sin(a),
                        'white' if i % 2 == 0 else 'black'))
    return ps   # 1 red + 9 white + 9 black = 19


# ── Game ──────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.pieces       = make_pieces()
        self.turn         = 1
        self.striker      = Piece(CX, BLY1, 'striker', 1)
        self.state        = AIMING
        self.score        = {1: 0, 2: 0}
        self.dragging     = False
        self.drag_pt      = None
        self.pocketed_t   = []    # pieces pocketed this shot
        self.striker_fell = False
        self.queen_pend   = False
        self.msg          = ''
        self.msg_t        = 0
        self.winner       = None

    def _bly(self):
        return BLY1 if self.turn == 1 else BLY2

    def set_msg(self, m, t=160):
        self.msg = m; self.msg_t = t

    def _all_stopped(self):
        if self.striker.alive and self.striker.moving:
            return False
        return all(not p.moving for p in self.pieces if p.alive)

    # ── Events ────────────────────────────────────────────────────────────────
    def on_event(self, ev):
        if self.state == GAME_OVER:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                self.reset()
            return

        if self.state != AIMING:
            return

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = ev.pos
            if math.hypot(mx - self.striker.x, my - self.striker.y) < self.striker.r + 14:
                self.dragging = True
                self.drag_pt  = (mx, my)

        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.dragging:
            mx, my = ev.pos
            dx = self.drag_pt[0] - mx
            dy = self.drag_pt[1] - my
            dist = math.hypot(dx, dy)
            if dist > 8:
                spd = min(dist, MAX_DRAG) / MAX_DRAG * MAX_SPD
                self.striker.vx   = dx / dist * spd
                self.striker.vy   = dy / dist * spd
                self.state        = MOVING
                self.pocketed_t   = []
                self.striker_fell = False
            self.dragging = False
            self.drag_pt  = None

    def on_mouse(self, pos):
        if self.state == AIMING and not self.dragging:
            mx, _ = pos
            self.striker.x = float(max(BLX1, min(BLX2, mx)))
            self.striker.y = float(self._bly())

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        if self.msg_t > 0:
            self.msg_t -= 1
        if self.state != MOVING:
            return

        alive = [p for p in self.pieces if p.alive]
        phys  = alive + ([self.striker] if self.striker.alive else [])

        # 1. Move
        for p in phys:
            p.update()

        # 2. Pocket check (before wall bounce so corners work correctly)
        for p in alive:
            if p.in_pocket():
                p.alive = False
                self.pocketed_t.append(p)
                if p.kind == 'red':
                    self.queen_pend = True
                elif p.kind == ('white' if self.turn == 1 else 'black'):
                    self.score[self.turn] += 1

        if self.striker.alive and self.striker.in_pocket():
            self.striker.alive  = False
            self.striker_fell   = True
            self.score[self.turn] = max(0, self.score[self.turn] - 1)
            self.set_msg(f"P{self.turn}: Striker pocketed! −1 point")

        # 3. Wall bounce
        for p in self.pieces:
            if p.alive: p.bounce()
        if self.striker.alive:
            self.striker.bounce()

        # 4. Piece–piece collisions (3 passes for stability)
        alive2 = [p for p in self.pieces if p.alive]
        all_p  = alive2 + ([self.striker] if self.striker.alive else [])
        for _ in range(3):
            for i in range(len(all_p)):
                for j in range(i + 1, len(all_p)):
                    collide(all_p[i], all_p[j])

        if self._all_stopped():
            self._end_turn()

    # ── End of turn ───────────────────────────────────────────────────────────
    def _end_turn(self):
        own = 'white' if self.turn == 1 else 'black'
        own_pocketed = any(p.kind == own for p in self.pocketed_t)

        # Queen rule
        if self.queen_pend:
            if own_pocketed:
                self.score[self.turn] += 3
                self.set_msg(f"P{self.turn}: Queen covered! +3 bonus")
            else:
                q = Piece(CX, CY, 'red')
                self.pieces.append(q)
                self.set_msg("Queen not covered — returned to centre!")
            self.queen_pend = False

        # Win check
        w_left = sum(1 for p in self.pieces if p.kind == 'white' and p.alive)
        b_left = sum(1 for p in self.pieces if p.kind == 'black' and p.alive)
        if w_left == 0:
            self.winner = 1; self.state = GAME_OVER; return
        if b_left == 0:
            self.winner = 2; self.state = GAME_OVER; return

        # Extra turn if own piece pocketed and striker not lost
        extra = own_pocketed and not self.striker_fell
        if not extra:
            self.turn = 2 if self.turn == 1 else 1

        # Reset striker to current-turn baseline
        self.striker.alive = True
        self.striker.vx    = self.striker.vy = 0.0
        self.striker.owner = self.turn
        self.striker.x     = float(CX)
        self.striker.y     = float(self._bly())
        self.state = AIMING

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, surf):
        draw_board(surf)

        for p in self.pieces:
            if p.alive:
                p.draw(surf)
        if self.striker.alive:
            self.striker.draw(surf)

        # Drag / aim indicator
        if self.dragging and self.drag_pt:
            mx, my = pygame.mouse.get_pos()
            sx, sy = int(self.striker.x), int(self.striker.y)
            pygame.draw.line(surf, CDRG, (sx, sy), self.drag_pt, 2)
            pygame.draw.line(surf, CDRG, self.drag_pt, (mx, my), 2)
            dx, dy = self.drag_pt[0] - mx, self.drag_pt[1] - my
            dist = math.hypot(dx, dy)
            if dist > 5:
                frac = min(dist, MAX_DRAG) / MAX_DRAG
                rc = int(frac * 255); gc = int((1 - frac) * 200)
                ac = (rc, gc, 30)
                nx, ny = dx / dist, dy / dist
                pygame.draw.line(surf, ac, (sx, sy),
                                 (int(sx + nx * 110), int(sy + ny * 110)), 3)
                f18 = pygame.font.SysFont('Arial', 18)
                surf.blit(f18.render(f"Power {int(frac*100)}%", True, ac),
                          (mx + 12, my - 10))

        self._draw_hud(surf)

    def _draw_hud(self, surf):
        fb = pygame.font.SysFont('Arial', 24, bold=True)
        fs = pygame.font.SysFont('Arial', 17)

        w_l = sum(1 for p in self.pieces if p.kind == 'white' and p.alive)
        b_l = sum(1 for p in self.pieces if p.kind == 'black' and p.alive)
        q_on = any(p.kind == 'red' and p.alive for p in self.pieces)
        qstr = "  ♛ Queen: on board" if q_on else "  ♛ Queen: pocketed"

        # ── P2 banner (top) ───────────────────────────────────────────────────
        a2 = self.turn == 2 and self.state == AIMING
        pygame.draw.rect(surf, CP2 if a2 else CHUD, (BL, 8, BSIZE, 74), border_radius=8)
        surf.blit(fb.render(
            f"Player 2  ●  (Black)    Score: {self.score[2]}    Left: {b_l}{qstr}",
            True, CTXT), (BL + 14, 16))
        if a2:
            surf.blit(fs.render(
                "▶ YOUR TURN — slide mouse to position striker, click & drag it back, release to shoot",
                True, (255, 255, 140)), (BL + 14, 47))

        # ── P1 banner (bottom) ────────────────────────────────────────────────
        a1 = self.turn == 1 and self.state == AIMING
        pygame.draw.rect(surf, CP1 if a1 else CHUD,
                         (BL, WIN_H - 88, BSIZE, 74), border_radius=8)
        surf.blit(fb.render(
            f"Player 1  ○  (White)    Score: {self.score[1]}    Left: {w_l}{qstr}",
            True, CTXT), (BL + 14, WIN_H - 80))
        if a1:
            surf.blit(fs.render(
                "▶ YOUR TURN — slide mouse to position striker, click & drag it back, release to shoot",
                True, (255, 255, 140)), (BL + 14, WIN_H - 49))

        # ── Floating message ──────────────────────────────────────────────────
        if self.msg and self.msg_t > 0:
            alpha = min(255, self.msg_t * 2)
            ms = fb.render(self.msg, True, (255, 230, 80))
            ms.set_alpha(alpha)
            surf.blit(ms, (WIN_W // 2 - ms.get_width() // 2, WIN_H // 2 - 50))

        # ── Footer ────────────────────────────────────────────────────────────
        surf.blit(fs.render("R: restart  |  ESC: quit", True, (100, 85, 55)),
                  (BL, WIN_H - 14))

        # ── Game-over overlay ─────────────────────────────────────────────────
        if self.state == GAME_OVER:
            ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 165))
            surf.blit(ov, (0, 0))
            ft = pygame.font.SysFont('Arial', 64, bold=True)
            t  = ft.render(f"Player {self.winner} Wins!", True, (255, 230, 80))
            surf.blit(t, (WIN_W // 2 - t.get_width() // 2, WIN_H // 2 - 110))
            t2 = fb.render(
                f"P1: {self.score[1]} points   |   P2: {self.score[2]} points",
                True, CTXT)
            surf.blit(t2, (WIN_W // 2 - t2.get_width() // 2, WIN_H // 2 - 15))
            t3 = fb.render("Press R to play again", True, (180, 180, 180))
            surf.blit(t3, (WIN_W // 2 - t3.get_width() // 2, WIN_H // 2 + 55))


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Carrom — 2 Players")
    clock = pygame.time.Clock()
    game  = Game()

    while True:
        mx, my = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            game.on_event(ev)

        game.on_mouse((mx, my))
        game.update()
        game.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
