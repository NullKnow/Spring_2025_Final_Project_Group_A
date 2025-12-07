import pygame
import math
from settings import RED, ENEMY_SIZE, GRAVITY, WIDTH, HEIGHT, YELLOW, GREEN, BLACK

class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy=0, dmg=10):
        super().__init__()
        self.image = pygame.Surface((8, 8))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = vx
        self.vy = vy
        self.damage = dmg

    def update(self, *args):
        self.rect.x += self.vx
        self.rect.y += self.vy
        if self.rect.right < 0 or self.rect.left > WIDTH or self.rect.top > HEIGHT:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, pattern='patrol', bounds=None, speed=2, health=20, melee_damage=10, ranged=False, color=RED):
        super().__init__()
        self.image = pygame.Surface((ENEMY_SIZE, ENEMY_SIZE))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.speed = speed
        self.health = health
        self.max_health = health
        self.pattern = pattern
        self.bounds = bounds
        self.vx = speed
        self.vy = 0
        self.melee_damage = melee_damage
        self.ranged = ranged
        self.fire_cooldown = 0
        self.sine_offset = 0
        self.hitbox = self.rect.copy()
        self.color = color
        self.spawn_x = x
        self.spawn_y = y
        self.current_platform = None
        # Hopping behavior
        self.hop_cooldown = 0
        self.hop_pattern = pattern in ['patrol', 'sine']  # Some enemies hop

    def apply_gravity(self):
        self.vy += GRAVITY
        if self.vy > 10:
            self.vy = 10

    def draw_health_bar(self, surface, camera=None):
        """
        Draw a health bar above the enemy.
        
        Args:
            surface: Pygame surface to draw on
            camera: Optional Camera object to apply offset for scrolling
        """
        bar_width = ENEMY_SIZE
        bar_height = 5
        bar_x = self.rect.x
        bar_y = self.rect.y - 10
        
        # Apply camera offset if provided (for scrolling support)
        if camera is not None:
            bar_x, bar_y = camera.apply_offset_pos(bar_x, bar_y)
        
        # Background (red)
        pygame.draw.rect(surface, RED, (bar_x, bar_y, bar_width, bar_height))
        
        # Health (green)
        health_width = int(bar_width * (self.health / self.max_health))
        if health_width > 0:
            pygame.draw.rect(surface, GREEN, (bar_x, bar_y, health_width, bar_height))

    def update(self, player, platforms, projectiles_group=None):
        # If enemy is completely offscreen horizontally, respawn first
        self._respawn_if_offscreen(margin=100)
        # movement patterns
        if self.pattern == 'patrol':
            self.rect.x += self.vx
            if self.bounds:
                left, right = self.bounds
                # Clamp to bounds instead of just bouncing
                if self.rect.left <= left:
                    self.rect.left = left
                    self.vx = abs(self.vx)
                elif self.rect.right >= right:
                    self.rect.right = right
                    self.vx = -abs(self.vx)
            else:
                # No explicit bounds: clamp to screen width
                if self.rect.left <= 0:
                    self.rect.left = 0
                    self.vx = abs(self.vx)
                elif self.rect.right >= WIDTH:
                    self.rect.right = WIDTH
                    self.vx = -abs(self.vx)
            
            # Hopping behavior for patrol enemies
            if self.hop_pattern and self.hop_cooldown <= 0:
                self.vy = -10  # Jump
                self.hop_cooldown = 60  # Cooldown between hops
        elif self.pattern == 'chase':
            if player.rect.centerx < self.rect.centerx:
                self.rect.x -= self.speed
            else:
                self.rect.x += self.speed
            # Clamp chase enemy to bounds or screen
            if self.bounds:
                left, right = self.bounds
            else:
                left, right = 0, WIDTH
            if self.rect.left < left:
                self.rect.left = left
            if self.rect.right > right:
                self.rect.right = right
        elif self.pattern == 'sine':
            self.sine_offset += 0.05
            self.rect.y += int(math.sin(self.sine_offset) * 2)
            self.rect.x += self.vx
            # Clamp sine enemies to bounds or screen
            if self.bounds:
                left, right = self.bounds
            else:
                left, right = 0, WIDTH
            if self.rect.left < left:
                self.rect.left = left
            if self.rect.right > right:
                self.rect.right = right
            
            # Hopping behavior for sine enemies
            if self.hop_pattern and self.hop_cooldown <= 0:
                self.vy = -8
                self.hop_cooldown = 50

        # Update hop cooldown
        if self.hop_cooldown > 0:
            self.hop_cooldown -= 1

        # simple gravity and platform collision
        self.apply_gravity()
        self.rect.y += self.vy
        on_platform = False
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vy > 0:
                    self.rect.bottom = p.rect.top
                    self.vy = 0
                    on_platform = True
                    self.current_platform = p

        # Prevent enemies from falling off screen
        if self.rect.bottom > HEIGHT:
            self.rect.bottom = HEIGHT
            self.vy = 0
            on_platform = True

        # Update hitbox
        self.hitbox = self.rect.copy()

        # ranged attack
        if self.ranged and projectiles_group is not None:
            if self.fire_cooldown <= 0:
                dx = player.rect.centerx - self.rect.centerx
                dir = 1 if dx > 0 else -1
                proj = Projectile(self.rect.centerx + dir * ENEMY_SIZE // 2, self.rect.centery, vx=dir * 6, dmg=8)
                projectiles_group.add(proj)
                self.fire_cooldown = 60
            else:
                self.fire_cooldown -= 1

    def take_damage(self, amount):
        """Enemy takes damage and is removed when health reaches zero"""
        self.health -= amount
        if self.health <= 0:
            self.kill()

    def _respawn_if_offscreen(self, margin=100):
        """If the enemy has gone off the visible screen horizontally, respawn
        it at its initial spawn position. This prevents enemies from getting
        permanently lost outside the playable area."""
        # Check for offscreen horizontally with margin
        off_left = self.rect.right < -margin
        off_right = self.rect.left > WIDTH + margin
        if off_left or off_right:
            # Respawn to original spawn position
            self.rect.topleft = (self.spawn_x, self.spawn_y)
            # Reset velocities to default patrol/chase defaults
            self.vy = 0
            if self.pattern == 'patrol' or self.pattern == 'sine':
                self.vx = self.speed
            elif self.pattern == 'chase':
                # For chase reset vx to flat speed in direction of player if available
                # Default to positive direction
                self.vx = self.speed
            # Reset platform tracking
            self.current_platform = None
            # Reset hop cooldown so they don't immediately hop on spawn
            self.hop_cooldown = 0


