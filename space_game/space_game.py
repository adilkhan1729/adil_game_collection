import pygame
import random
import math
import sys
import numpy as np

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# ── Sound synthesis ────────────────────────────────────────────────────────────

SAMPLE_RATE = 44100

def _make_sound(samples):
    """Convert a float32 numpy array (-1..1) into a pygame Sound (stereo)."""
    mono = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    stereo = np.column_stack((mono, mono))
    return pygame.sndarray.make_sound(stereo)

def _sine(freq, duration, volume=0.5, fade_out=True):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    s = np.sin(2 * np.pi * freq * t) * volume
    if fade_out:
        s *= np.linspace(1, 0, len(s))
    return s

def _noise(duration, volume=0.3):
    return (np.random.uniform(-1, 1, int(SAMPLE_RATE * duration)) * volume).astype(np.float32)

def make_laser_sound():
    t = np.linspace(0, 0.15, int(SAMPLE_RATE * 0.15), endpoint=False)
    freq = np.linspace(900, 300, len(t))
    s = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE) * 0.5
    s *= np.linspace(1, 0, len(s))
    return _make_sound(s)

def make_explosion_sound():
    n = _noise(0.45, volume=0.8)
    t = np.linspace(0, 0.45, len(n))
    env = np.exp(-8 * t)
    return _make_sound(n * env)

def make_enemy_laser_sound():
    t = np.linspace(0, 0.18, int(SAMPLE_RATE * 0.18), endpoint=False)
    freq = np.linspace(400, 150, len(t))
    s = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE) * 0.35
    s *= np.linspace(1, 0, len(s))
    return _make_sound(s)

def make_player_hit_sound():
    n = _noise(0.25, volume=0.6)
    t = np.linspace(0, 0.25, len(n))
    tone = _sine(120, 0.25, volume=0.4)
    s = n * np.exp(-5 * t) + tone * np.exp(-4 * t)
    return _make_sound(s)

def make_wave_clear_sound():
    notes = [523, 659, 784, 1047]
    chunks = [_sine(f, 0.12, volume=0.4) for f in notes]
    return _make_sound(np.concatenate(chunks))

def make_boss_hit_sound():
    t = np.linspace(0, 0.1, int(SAMPLE_RATE * 0.1), endpoint=False)
    s = np.sin(2 * np.pi * 200 * t) * 0.5 * np.linspace(1, 0, len(t))
    n = _noise(0.1, volume=0.2)
    return _make_sound(s + n)

def make_game_over_sound():
    notes = [392, 349, 330, 262]
    chunks = [_sine(f, 0.22, volume=0.45) for f in notes]
    return _make_sound(np.concatenate(chunks))

# Pre-build all sounds
SFX = {
    "laser":      make_laser_sound(),
    "explosion":  make_explosion_sound(),
    "enemy_laser":make_enemy_laser_sound(),
    "player_hit": make_player_hit_sound(),
    "wave_clear": make_wave_clear_sound(),
    "boss_hit":   make_boss_hit_sound(),
    "game_over":  make_game_over_sound(),
}

def play(name, volume=1.0):
    sfx = SFX.get(name)
    if sfx:
        sfx.set_volume(volume)
        sfx.play()

# --- Constants ---
WIDTH, HEIGHT = 900, 700
FPS = 60

BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
YELLOW  = (255, 255, 0)
CYAN    = (0, 255, 255)
RED     = (220, 40, 40)
GREEN   = (0, 220, 80)
ORANGE  = (255, 140, 0)
PURPLE  = (160, 32, 240)
BLUE    = (30, 100, 255)
GREY    = (160, 160, 160)
DARK    = (10, 10, 30)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Defender")
clock = pygame.time.Clock()

# --- Fonts ---
font_large  = pygame.font.SysFont("arial", 64, bold=True)
font_medium = pygame.font.SysFont("arial", 36, bold=True)
font_small  = pygame.font.SysFont("arial", 24)

# ── Sprite drawing helpers ─────────────────────────────────────────────────────

def draw_player_ship(surface, color=CYAN):
    """Draw a sleek player ship onto a surface (centered)."""
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    # Main body
    body = [(cx, cy - h // 2 + 4),
            (cx + w // 3, cy + h // 4),
            (cx, cy + h // 6),
            (cx - w // 3, cy + h // 4)]
    pygame.draw.polygon(surface, color, body)
    # Engine glow
    pygame.draw.polygon(surface, ORANGE,
                        [(cx - 8, cy + h // 6),
                         (cx + 8, cy + h // 6),
                         (cx, cy + h // 2 - 2)])
    # Cockpit
    pygame.draw.ellipse(surface, WHITE, (cx - 6, cy - 14, 12, 14))
    # Wing lines
    pygame.draw.line(surface, WHITE, (cx, cy - 10), (cx - w // 3 + 4, cy + h // 4 - 4), 1)
    pygame.draw.line(surface, WHITE, (cx, cy - 10), (cx + w // 3 - 4, cy + h // 4 - 4), 1)


def draw_alien_ship(surface, color=RED, style=0):
    """Draw an alien ship onto a surface (centered). style 0-2 for variety."""
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    if style == 0:
        # Classic saucer
        pygame.draw.ellipse(surface, color, (4, cy - 6, w - 8, 20))
        pygame.draw.ellipse(surface, PURPLE, (cx - 14, cy - 16, 28, 18))
        pygame.draw.ellipse(surface, WHITE,  (cx - 6,  cy - 12, 12, 8))
        # Lights
        for i, lx in enumerate(range(8, w - 8, 10)):
            c = YELLOW if i % 2 == 0 else RED
            pygame.draw.circle(surface, c, (lx, cy + 4), 3)
    elif style == 1:
        # Crab-like
        pygame.draw.ellipse(surface, color, (cx - 20, cy - 12, 40, 28))
        pygame.draw.rect(surface, color, (cx - 6, cy - 20, 12, 12))
        # Claws
        for dx in (-1, 1):
            pygame.draw.line(surface, color,
                             (cx + dx * 20, cy),
                             (cx + dx * (w // 2 - 4), cy - 10), 4)
            pygame.draw.line(surface, color,
                             (cx + dx * (w // 2 - 4), cy - 10),
                             (cx + dx * (w // 2 - 4), cy + 6), 4)
        pygame.draw.circle(surface, WHITE, (cx, cy - 4), 7)
        pygame.draw.circle(surface, RED,   (cx, cy - 4), 4)
    else:
        # Angular fighter
        pts = [(cx, cy - h // 2 + 4),
               (cx + w // 2 - 4, cy + h // 2 - 4),
               (cx + 10, cy),
               (cx, cy + 10),
               (cx - 10, cy),
               (cx - w // 2 + 4, cy + h // 2 - 4)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.circle(surface, YELLOW, (cx, cy), 8)
        pygame.draw.circle(surface, RED,    (cx, cy), 4)


def make_surface(w, h, draw_fn, **kw):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    draw_fn(surf, **kw)
    return surf


# ── Particle system ────────────────────────────────────────────────────────────

class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, color):
        super().__init__()
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.radius = random.randint(2, 5)
        self.life = random.randint(20, 40)
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect(center=(x, y))
        self.x, self.y = float(x), float(y)

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()
            return
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1  # gravity
        alpha = int(255 * self.life / 40)
        self.image.fill((0, 0, 0, 0))
        r = max(1, self.radius * self.life // 40)
        pygame.draw.circle(self.image, (*self.color[:3], alpha), (self.radius, self.radius), r)
        self.rect.center = (int(self.x), int(self.y))


def explode(groups, x, y, colors, count=30):
    for _ in range(count):
        p = Particle(x, y, random.choice(colors))
        for g in groups:
            g.add(p)


# ── Star background ────────────────────────────────────────────────────────────

class Star:
    def __init__(self):
        self.reset(random.randint(0, HEIGHT))

    def reset(self, y=0):
        self.x = random.randint(0, WIDTH)
        self.y = y
        self.speed = random.uniform(0.5, 2.5)
        self.size  = random.randint(1, 3)
        self.brightness = random.randint(100, 255)

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.reset()

    def draw(self, surf):
        c = (self.brightness,) * 3
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.size)


# ── Bullet ─────────────────────────────────────────────────────────────────────

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dy=-14, color=CYAN, enemy=False):
        super().__init__()
        self.image = pygame.Surface((6, 18), pygame.SRCALPHA)
        # Glowing laser look
        pygame.draw.rect(self.image, color, (2, 0, 2, 18), border_radius=2)
        pygame.draw.rect(self.image, WHITE, (2, 2, 2, 6), border_radius=1)
        self.rect = self.image.get_rect(center=(x, y))
        self.dy = dy
        self.enemy = enemy

    def update(self):
        self.rect.y += self.dy
        if self.rect.bottom < 0 or self.rect.top > HEIGHT:
            self.kill()


# ── Player ─────────────────────────────────────────────────────────────────────

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.base_image = make_surface(60, 70, draw_player_ship, color=CYAN)
        self.image = self.base_image.copy()
        self.rect  = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 70))
        self.speed = 6
        self.shoot_cooldown = 0
        self.shoot_delay    = 15   # frames between shots
        self.lives  = 3
        self.shield = 0            # invincibility frames after hit
        self.score  = 0

    def update(self, keys):
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.rect.x += self.speed
        if keys[pygame.K_UP]    or keys[pygame.K_w]: self.rect.y -= self.speed
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: self.rect.y += self.speed
        self.rect.clamp_ip(screen.get_rect())

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.shield > 0:
            self.shield -= 1
            # Flicker effect
            self.image = self.base_image.copy() if (self.shield // 4) % 2 == 0 else \
                         make_surface(60, 70, draw_player_ship, color=GREY)
        else:
            self.image = self.base_image.copy()

    def shoot(self):
        if self.shoot_cooldown == 0:
            self.shoot_cooldown = self.shoot_delay
            return Bullet(self.rect.centerx, self.rect.top + 10, dy=-16, color=CYAN)
        return None

    def hit(self):
        if self.shield == 0:
            self.lives -= 1
            self.shield = 90
            return True
        return False


# ── Enemy ──────────────────────────────────────────────────────────────────────

class Enemy(pygame.sprite.Sprite):
    STYLES = [
        {"color": RED,    "style": 0, "hp": 1, "pts": 10, "speed": 1.5},
        {"color": ORANGE, "style": 1, "hp": 2, "pts": 20, "speed": 1.2},
        {"color": PURPLE, "style": 2, "hp": 3, "pts": 30, "speed": 1.0},
    ]

    def __init__(self, x, y, kind=0):
        super().__init__()
        cfg = self.STYLES[kind]
        self.color  = cfg["color"]
        self.style  = cfg["style"]
        self.hp     = cfg["hp"]
        self.pts    = cfg["pts"]
        self.base_speed = cfg["speed"]
        self.image  = make_surface(60, 50, draw_alien_ship,
                                   color=self.color, style=self.style)
        self.rect   = self.image.get_rect(topleft=(x, y))
        # Formation movement
        self.origin_x = float(x)
        self.t        = random.uniform(0, math.pi * 2)
        self.dive     = False
        self.dive_dx  = 0.0
        self.dive_dy  = 0.0
        self.shoot_timer = random.randint(180, 400)

    def update(self):
        if not self.dive:
            self.t += 0.025
            self.rect.x = int(self.origin_x + math.sin(self.t) * 30)
            self.rect.y += 0.3
        else:
            self.rect.x += int(self.dive_dx)
            self.rect.y += int(self.dive_dy)
        if self.rect.top > HEIGHT + 20:
            self.kill()

    def maybe_shoot(self):
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = random.randint(180, 380)
            return Bullet(self.rect.centerx, self.rect.bottom,
                          dy=random.randint(3, 5), color=RED, enemy=True)
        return None

    def start_dive(self, target_x):
        self.dive = True
        dx = target_x - self.rect.centerx
        dy = HEIGHT - self.rect.y
        dist = math.hypot(dx, dy) or 1
        spd  = self.base_speed * 4
        self.dive_dx = dx / dist * spd
        self.dive_dy = dy / dist * spd

    def take_hit(self):
        self.hp -= 1
        return self.hp <= 0


# ── Boss ───────────────────────────────────────────────────────────────────────

class Boss(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.max_hp = 30
        self.hp     = self.max_hp
        self.image  = pygame.Surface((140, 100), pygame.SRCALPHA)
        self._draw()
        self.rect   = self.image.get_rect(center=(WIDTH // 2, -60))
        self.entering = True
        self.target_y = 100
        self.vx = 2
        self.shoot_timer = 120

    def _draw(self):
        s = self.image
        s.fill((0, 0, 0, 0))
        cx, cy = 70, 50
        # Hull
        pygame.draw.ellipse(s, (180, 0, 0), (10, 30, 120, 50))
        pygame.draw.ellipse(s, PURPLE, (30, 10, 80, 50))
        pygame.draw.ellipse(s, WHITE,  (54, 14, 32, 24))
        # Cannons
        for dx in (-40, 0, 40):
            pygame.draw.rect(s, GREY, (cx + dx - 4, cy + 30, 8, 20), border_radius=3)
        # Lights
        for i, lx in enumerate(range(14, 126, 12)):
            pygame.draw.circle(s, YELLOW if i % 2 == 0 else RED, (lx, 56), 4)
        # HP bar frame (drawn separately in draw_hud)

    def update(self):
        if self.entering:
            self.rect.y += 2
            if self.rect.centery >= self.target_y:
                self.entering = False
        else:
            self.rect.x += self.vx
            if self.rect.right > WIDTH - 20 or self.rect.left < 20:
                self.vx *= -1

    def maybe_shoot(self):
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = 70
            bullets = []
            for dx in (-40, 0, 40):
                b = Bullet(self.rect.centerx + dx,
                           self.rect.bottom,
                           dy=random.randint(4, 6),
                           color=ORANGE, enemy=True)
                bullets.append(b)
            return bullets
        return []

    def take_hit(self):
        self.hp -= 1
        return self.hp <= 0


# ── Wave manager ───────────────────────────────────────────────────────────────

def spawn_wave(wave, all_sprites, enemies):
    enemies.empty()
    rows = min(2 + wave, 5)
    cols = min(5 + wave, 11)
    for row in range(rows):
        for col in range(cols):
            x = 60 + col * 75
            y = 60 + row * 70
            kind = min(row, 2)
            e = Enemy(x, y, kind=kind)
            e.base_speed = 1.0 + wave * 0.15
            all_sprites.add(e)
            enemies.add(e)


# ── HUD ────────────────────────────────────────────────────────────────────────

def draw_hud(surf, player, wave, boss=None):
    # Score
    score_surf = font_small.render(f"SCORE  {player.score:06d}", True, WHITE)
    surf.blit(score_surf, (14, 10))

    # Lives
    heart = make_surface(26, 26, draw_player_ship, color=CYAN)
    heart = pygame.transform.scale(heart, (26, 26))
    for i in range(player.lives):
        surf.blit(heart, (WIDTH - 40 - i * 32, 8))

    # Wave
    wave_surf = font_small.render(f"WAVE  {wave}", True, YELLOW)
    surf.blit(wave_surf, (WIDTH // 2 - wave_surf.get_width() // 2, 10))

    # Boss HP bar
    if boss:
        bar_w = 400
        bar_x = WIDTH // 2 - bar_w // 2
        bar_y = HEIGHT - 30
        ratio = boss.hp / boss.max_hp
        pygame.draw.rect(surf, GREY,  (bar_x, bar_y, bar_w, 16), border_radius=8)
        pygame.draw.rect(surf, RED,   (bar_x, bar_y, int(bar_w * ratio), 16), border_radius=8)
        pygame.draw.rect(surf, WHITE, (bar_x, bar_y, bar_w, 16), 2, border_radius=8)
        lbl = font_small.render("BOSS", True, RED)
        surf.blit(lbl, (bar_x - 46, bar_y - 1))


# ── Screens ────────────────────────────────────────────────────────────────────

def draw_title(surf, stars):
    surf.fill(DARK)
    for s in stars: s.draw(surf)
    title = font_large.render("SPACE DEFENDER", True, CYAN)
    surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 180))
    sub = font_medium.render("Press ENTER to Start", True, WHITE)
    surf.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 280))
    controls = [
        "Arrow Keys / WASD  — Move",
        "SPACE              — Shoot",
        "Destroy all aliens to advance waves!",
    ]
    for i, line in enumerate(controls):
        t = font_small.render(line, True, GREY)
        surf.blit(t, (WIDTH // 2 - t.get_width() // 2, 360 + i * 32))


def draw_game_over(surf, score, stars):
    surf.fill(DARK)
    for s in stars: s.draw(surf)
    msg  = font_large.render("GAME OVER", True, RED)
    scr  = font_medium.render(f"Final Score: {score:06d}", True, YELLOW)
    cont = font_small.render("Press ENTER to Play Again   |   ESC to Quit", True, WHITE)
    surf.blit(msg,  (WIDTH // 2 - msg.get_width()  // 2, 220))
    surf.blit(scr,  (WIDTH // 2 - scr.get_width()  // 2, 310))
    surf.blit(cont, (WIDTH // 2 - cont.get_width() // 2, 380))


def draw_wave_clear(surf, wave, stars):
    surf.fill(DARK)
    for s in stars: s.draw(surf)
    msg  = font_large.render(f"WAVE {wave} CLEAR!", True, GREEN)
    cont = font_small.render("Press ENTER for next wave", True, WHITE)
    surf.blit(msg,  (WIDTH // 2 - msg.get_width()  // 2, 270))
    surf.blit(cont, (WIDTH // 2 - cont.get_width() // 2, 360))


# ── Main game loop ─────────────────────────────────────────────────────────────

def main():
    stars = [Star() for _ in range(180)]

    # ---- state machine ----
    STATE_TITLE      = "title"
    STATE_PLAYING    = "playing"
    STATE_WAVE_CLEAR = "wave_clear"
    STATE_BOSS       = "boss"
    STATE_GAME_OVER  = "game_over"
    state = STATE_TITLE

    def init_game():
        nonlocal player, all_sprites, enemies, bullets, enemy_bullets, particles
        nonlocal boss, wave, dive_timer

        all_sprites   = pygame.sprite.Group()
        enemies       = pygame.sprite.Group()
        bullets       = pygame.sprite.Group()
        enemy_bullets = pygame.sprite.Group()
        particles     = pygame.sprite.Group()

        player = Player()
        all_sprites.add(player)
        wave  = 1
        boss  = None
        dive_timer = 0
        spawn_wave(wave, all_sprites, enemies)

    player = None
    all_sprites = enemies = bullets = enemy_bullets = particles = None
    boss  = None
    wave  = 1
    dive_timer = 0

    init_game()

    running = True
    while running:
        clock.tick(FPS)

        # ── events ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if state == STATE_TITLE and event.key == pygame.K_RETURN:
                    init_game()
                    state = STATE_PLAYING
                elif state == STATE_WAVE_CLEAR and event.key == pygame.K_RETURN:
                    wave += 1
                    boss = None
                    if wave % 5 == 0:
                        # Boss wave
                        enemies.empty()
                        boss = Boss()
                        all_sprites.add(boss)
                        state = STATE_BOSS
                    else:
                        spawn_wave(wave, all_sprites, enemies)
                        state = STATE_PLAYING
                elif state == STATE_GAME_OVER and event.key == pygame.K_RETURN:
                    init_game()
                    state = STATE_PLAYING

        # ── update stars ──
        for s in stars:
            s.update()

        # ── TITLE ──
        if state == STATE_TITLE:
            draw_title(screen, stars)
            pygame.display.flip()
            continue

        # ── GAME OVER ──
        if state == STATE_GAME_OVER:
            draw_game_over(screen, player.score, stars)
            pygame.display.flip()
            continue

        # ── WAVE CLEAR ──
        if state == STATE_WAVE_CLEAR:
            draw_wave_clear(screen, wave, stars)
            pygame.display.flip()
            continue

        # ── PLAYING ──
        keys = pygame.key.get_pressed()
        player.update(keys)

        # Player shoot
        if keys[pygame.K_SPACE]:
            b = player.shoot()
            if b:
                all_sprites.add(b)
                bullets.add(b)
                play("laser", 0.6)

        # Enemy dive occasionally
        if state == STATE_PLAYING:
            dive_timer -= 1
            if dive_timer <= 0 and len(enemies) > 0:
                dive_timer = random.randint(220, 400)
                diver = random.choice(list(enemies))
                diver.start_dive(player.rect.centerx)

            for e in list(enemies):
                e.update()
                eb = e.maybe_shoot()
                if eb:
                    all_sprites.add(eb)
                    enemy_bullets.add(eb)
                    play("enemy_laser", 0.4)

        # Boss logic
        if state == STATE_BOSS and boss:
            boss.update()
            for eb in boss.maybe_shoot():
                all_sprites.add(eb)
                enemy_bullets.add(eb)
                play("enemy_laser", 0.5)

        bullets.update()
        enemy_bullets.update()
        particles.update()

        # ── collisions: player bullets vs enemies ──
        hits = pygame.sprite.groupcollide(enemies, bullets, False, True)
        for enemy, _ in hits.items():
            if enemy.take_hit():
                explode([all_sprites, particles], enemy.rect.centerx, enemy.rect.centery,
                        [enemy.color, ORANGE, YELLOW])
                play("explosion", 0.7)
                player.score += enemy.pts
                enemy.kill()

        # ── collisions: player bullets vs boss ──
        if state == STATE_BOSS and boss:
            if pygame.sprite.spritecollide(boss, bullets, True):
                if boss.take_hit():
                    explode([all_sprites, particles], boss.rect.centerx, boss.rect.centery,
                            [RED, ORANGE, YELLOW, WHITE], count=60)
                    play("explosion", 1.0)
                    player.score += 500
                    boss.kill()
                    boss = None
                else:
                    play("boss_hit", 0.6)

        # ── enemy bullets vs player ──
        if pygame.sprite.spritecollide(player, enemy_bullets, True):
            if player.hit():
                explode([all_sprites, particles], player.rect.centerx, player.rect.centery,
                        [CYAN, WHITE, BLUE], count=20)
                play("player_hit", 0.8)

        # ── enemies reach bottom / collide player ──
        if pygame.sprite.spritecollide(player, enemies, False):
            if player.hit():
                explode([all_sprites, particles], player.rect.centerx, player.rect.centery,
                        [CYAN, WHITE, BLUE], count=20)
                play("player_hit", 0.8)

        # ── check death ──
        if player.lives <= 0:
            play("game_over")
            state = STATE_GAME_OVER

        # ── check wave clear ──
        if state == STATE_PLAYING and len(enemies) == 0:
            play("wave_clear")
            state = STATE_WAVE_CLEAR
        if state == STATE_BOSS and boss is None:
            play("wave_clear")
            state = STATE_WAVE_CLEAR

        # ── draw ──
        screen.fill(DARK)
        for s in stars:
            s.draw(screen)

        all_sprites.draw(screen)
        draw_hud(screen, player, wave, boss if state == STATE_BOSS else None)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
