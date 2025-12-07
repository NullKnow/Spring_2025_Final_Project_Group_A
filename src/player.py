import pygame
from settings import BLUE, PLAYER_WIDTH, PLAYER_HEIGHT, GRAVITY, WIDTH, HEIGHT

class Attack(pygame.sprite.Sprite):
    """Represents the player's attack hitbox"""
    def __init__(self, x, y, width=70, height=50, direction=1, damage=15):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill((100, 200, 255))
        self.image.set_alpha(100)  # Semi-transparent
        self.rect = self.image.get_rect(topleft=(x, y))
        self.damage = damage
        self.direction = direction
        self.lifetime = 10  # frames

    def update(self, *args):
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(BLUE)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.health = 100
        self.max_health = 100
        self.speed_mod = 1.0
        self.speed_mod_timer = 0
        self.invuln_timer = 0
        self.attack_cooldown = 0
        self.facing_right = True
        self.attacks = pygame.sprite.Group()
        self.falling_through = False
        self.fall_through_timer = 0

    def handle_input(self):
        keys = pygame.key.get_pressed()
        self.vel_x = 0
        base_speed = 5 * self.speed_mod
        if keys[pygame.K_LEFT]:
            self.vel_x = -base_speed
            self.facing_right = False
        if keys[pygame.K_RIGHT]:
            self.vel_x = base_speed
            self.facing_right = True
        if keys[pygame.K_SPACE]:
            # Allow Down + Space to fall through when standing on a platform
            if self.on_ground and keys[pygame.K_DOWN] and not self.falling_through:
                # Fall through this platform
                self.falling_through = True
                self.fall_through_timer = 10
                # Give a little downward kick to start falling
                self.vel_y = 5
            elif self.on_ground:
                # Normal jump
                self.vel_y = -15
        if keys[pygame.K_a]:
            self.attack()

    def attack(self):
        """Create an attack hitbox"""
        if self.attack_cooldown <= 0:
            attack_width = 70  # Increased reach
            attack_height = 50
            if self.facing_right:
                attack_x = self.rect.right
            else:
                attack_x = self.rect.left - attack_width
            
            attack = Attack(attack_x, self.rect.centery - attack_height // 2, 
                          attack_width, attack_height, 
                          direction=1 if self.facing_right else -1, damage=15)
            self.attacks.add(attack)
            self.attack_cooldown = 15  # 15 frame cooldown

    def apply_gravity(self):
        self.vel_y += GRAVITY
        if self.vel_y > 10:
            self.vel_y = 10

    def update(self, platforms):
        # Keep previous on_ground so we can avoid applying gravity when standing
        prev_on_ground = self.on_ground
        self.handle_input()

        # Prevent gravity from being applied while the player is standing on ground
        # (this avoids tiny float velocities and integer rect rounding causing sliding)
        if not prev_on_ground or self.falling_through or self.vel_y != 0:
            self.apply_gravity()
        
        # update temporary modifiers
        if self.speed_mod_timer > 0:
            self.speed_mod_timer -= 1
            if self.speed_mod_timer == 0:
                self.speed_mod = 1.0
        if self.invuln_timer > 0:
            self.invuln_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        # Update fall-through timer
        if self.fall_through_timer > 0:
            self.fall_through_timer -= 1
            if self.fall_through_timer == 0:
                self.falling_through = False

        # Apply horizontal movement
        self.rect.x += self.vel_x
        
        # Apply vertical movement and check collision
        self.rect.y += self.vel_y
        self.on_ground = False
        
        # Optimize collision checks by only considering platforms near the player
        nearby_platforms = [p for p in platforms if abs(p.rect.centerx - self.rect.centerx) < 200 and abs(p.rect.centery - self.rect.centery) < 200]
        for platform in nearby_platforms:
            # Basic overlap collision
            if self.rect.colliderect(platform.rect):
                # Only collide from above when falling or standing normally
                if self.vel_y >= 0:  # Only check when moving down or stationary
                    # Check if we were above the platform before moving
                    old_y = self.rect.y - self.vel_y
                    # Add small epsilon tolerance to avoid float->int rounding issues
                    # when player is very close to the platform top.
                    if old_y + self.height <= platform.rect.top + 1:
                        # We came from above, so land on platform
                        if self.falling_through:
                            # If actively falling through, skip this platform
                            continue
                        self.rect.bottom = platform.rect.top
                        self.vel_y = 0
                        self.on_ground = True
                        self.falling_through = False
                        break  # Stop checking other platforms once landed
                # Also detect 'touching' case: if player bottom equals platform top but not overlapping
            elif abs(self.rect.bottom - platform.rect.top) <= 1 and (self.rect.right > platform.rect.left and self.rect.left < platform.rect.right):
                # Treat as on ground (e.g., initial placement or rounding cases)
                if not self.falling_through:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                    self.falling_through = False
                    break

        # Enforce strict horizontal bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WIDTH:
            self.rect.right = WIDTH

        # Safety: enforce a ground floor
        if self.rect.bottom > HEIGHT:
            self.rect.bottom = HEIGHT
            self.vel_y = 0
            self.on_ground = True
            self.falling_through = False

        # Update attacks
        self.attacks.update()

    def take_damage(self, amount):
        if self.invuln_timer > 0:
            return
        self.health -= amount
        print(f"Player took {amount} damage; health={self.health}")
        self.invuln_timer = 30
        if self.health <= 0:
            print("Player died")
            self.health = 0

    def heal(self, amount):
        """Heal the player"""
        self.health = min(self.health + amount, self.max_health)


