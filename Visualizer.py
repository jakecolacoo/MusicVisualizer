import pygame
import numpy as np
from colorsys import hsv_to_rgb
import math
import random


class Visualizer:
    def __init__(self, audio_processor, screen_width, screen_height):
        self.audio_processor = audio_processor
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
        self.time = 0
        self.hue = 0
        self.particles = []
        self.last_beat_time = 0
        self.prev_amp = 0
        self.beat_threshold = 0.18
        self.beat_cooldown = 0.18  # seconds
        self.palette = [
            (0.85, 1, 1),   # neon pink
            (0.55, 1, 1),   # neon blue
            (0.33, 1, 1),   # neon green
            (0.13, 1, 1),   # neon yellow
            (0.75, 0.6, 1),  # pastel purple
            (0.55, 0.4, 1),  # pastel blue
            (0.33, 0.4, 1),  # pastel green
            (0.13, 0.4, 1),  # pastel yellow
        ]
        self.shockwaves = []
        self.prev_bass_energy = 0
        self.drop_threshold = 0.32  # Higher than beat threshold
        self.last_drop_time = 0
        self.drop_cooldown = 0.7  # seconds

    def get_connotation_color(self, amp, spectrum):
        # Amplitude: 0 (quiet) to 1 (loud)
        amp = min(1.0, max(0.0, amp))
        # Frequency bands
        if spectrum is not None and len(spectrum) > 0:
            n = len(spectrum)
            bass = np.mean(spectrum[:int(n*0.15)])
            mid = np.mean(spectrum[int(n*0.15):int(n*0.5)])
            treble = np.mean(spectrum[int(n*0.5):])
            total = bass + mid + treble + 1e-6
            bass_frac = bass / total
            mid_frac = mid / total
            treble_frac = treble / total
            # Complexity: how "spread out" is the spectrum?
            complexity = np.std(spectrum) / (np.mean(spectrum)+1e-6)
        else:
            bass_frac = mid_frac = treble_frac = 1/3
            complexity = 0
        # Start with amplitude mapping
        if amp > 0.7:
            # High energy: red/orange/pink
            base_hue = 0.0 + 0.08 * (1-amp)  # 0.0=red, 0.08=orange
            base_sat = 1.0
            base_val = 1.0
        elif amp < 0.25:
            # Calm: blue/purple
            base_hue = 0.6 + 0.2 * (0.25-amp)/0.25  # 0.6=blue, 0.8=purple
            base_sat = 0.7
            base_val = 0.7
        else:
            # Mid: green
            base_hue = 0.33
            base_sat = 0.8
            base_val = 0.9
        # Blend in frequency connotations
        # Bass: red/orange, Mid: green, Treble: yellow, Complexity: purple
        hue = (base_hue * 0.5 + 0.0 * bass_frac + 0.33 * mid_frac +
               0.13 * treble_frac + 0.75 * complexity * 0.7)
        sat = min(1.0, base_sat + 0.3 * (bass_frac + treble_frac))
        val = min(1.0, base_val + 0.2 * (treble_frac + complexity))
        return (hue % 1.0, sat, val)

    def get_palette_color(self, t, amp=0.5, spectrum=None):
        # Use connotation color as base, then rotate for palette cycling
        base_h, base_s, base_v = self.get_connotation_color(amp, spectrum)
        # Palette cycling: rotate hue
        h = (base_h + 0.12 * (t % len(self.palette))) % 1.0
        s = base_s
        v = base_v
        return tuple(int(x * 255) for x in hsv_to_rgb(h, s, v))

    def detect_beat(self, amp, dt, spectrum=None):
        # Use bass energy for beat detection
        beat = False
        bass_energy = 0
        if spectrum is not None and len(spectrum) > 0:
            bass_end = max(1, int(len(spectrum) * 0.10))
            bass_energy = np.mean(spectrum[:bass_end])
        if bass_energy - self.prev_amp > self.beat_threshold and (self.time - self.last_beat_time) > self.beat_cooldown:
            beat = True
            self.last_beat_time = self.time
        self.prev_amp = bass_energy
        return beat

    def add_particles(self, n, color):
        for _ in range(n):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 7)
            self.particles.append({
                'x': self.center_x,
                'y': self.center_y,
                'dx': math.cos(angle) * speed,
                'dy': math.sin(angle) * speed,
                'life': random.uniform(0.7, 1.2),
                'color': color,
                'size': random.randint(6, 16)
            })

    def update_particles(self, dt):
        for p in self.particles[:]:
            p['x'] += p['dx'] * dt * 60
            p['y'] += p['dy'] * dt * 60
            p['life'] -= dt
            if p['life'] <= 0:
                self.particles.remove(p)
            else:
                alpha = int(180 * p['life'])
                surf = pygame.Surface(
                    (p['size']*2, p['size']*2), pygame.SRCALPHA)
                pygame.draw.circle(
                    surf, p['color'] + (alpha,), (p['size'], p['size']), p['size'])
                pygame.draw.circle(surf, (255, 255, 255, int(
                    alpha*0.5)), (p['size'], p['size']), p['size']//2)
                self.screen.blit(
                    surf, (p['x']-p['size'], p['y']-p['size']), special_flags=pygame.BLEND_RGBA_ADD)

    def draw_background(self, amp=0.5, spectrum=None):
        # Smooth vertical gradient: blend between two palette colors, slow color cycling
        slow_factor = 0.025  # much slower than before
        top_t = (self.time * slow_factor) % len(self.palette)
        bot_t = (self.time * slow_factor + 2) % len(self.palette)
        top_color = self.get_palette_color(top_t, amp, spectrum)
        bot_color = self.get_palette_color(bot_t, amp, spectrum)
        for y in range(self.screen_height):
            frac = y / self.screen_height
            color = tuple(
                int(top_color[i] * (1 - frac) + bot_color[i] * frac)
                for i in range(3)
            )
            pygame.draw.line(self.screen, color, (0, y),
                             (self.screen_width, y))
        # Animated radial pastel overlay (still subtle, slow color cycling)
        overlay = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA)
        for r in range(int(min(self.screen_width, self.screen_height)//2), 0, -12):
            t = (self.time * slow_factor + r/120) % len(self.palette)
            color = self.get_palette_color(t, amp, spectrum)
            alpha = int(
                30 * (1 - r/(min(self.screen_width, self.screen_height)//2)))
            if alpha > 0:
                pygame.draw.circle(overlay, color + (alpha,),
                                   (self.center_x, self.center_y), r)
        self.screen.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def trigger_shockwave(self, bass_energy, amp=0.5, spectrum=None):
        self.shockwaves.append({
            'radius': 80,
            'max_radius': int(min(self.screen_width, self.screen_height) * 0.7),
            'alpha': 180,
            'width': 16 + int(bass_energy * 24),
            'color': self.get_palette_color(self.time*1.5, amp, spectrum)
        })

    def update_shockwaves(self, dt):
        for s in self.shockwaves[:]:
            s['radius'] += 18 * dt * 60
            s['alpha'] *= 0.93
            s['width'] = max(2, int(s['width'] * 0.97))
            if s['radius'] > s['max_radius'] or s['alpha'] < 8:
                self.shockwaves.remove(s)
            else:
                surf = pygame.Surface(
                    (self.screen_width, self.screen_height), pygame.SRCALPHA)
                pygame.draw.circle(surf, s['color'] + (int(s['alpha']),),
                                   (self.center_x, self.center_y), int(s['radius']), s['width'])
                self.screen.blit(
                    surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def detect_bass_drop(self, spectrum):
        # Bass is the first 10% of spectrum
        bass_end = max(1, int(len(spectrum) * 0.10))
        bass_energy = np.mean(spectrum[:bass_end]) if spectrum is not None and len(
            spectrum) > 0 else 0
        drop = False
        if (bass_energy - self.prev_bass_energy > self.drop_threshold and
                (self.time - self.last_drop_time) > self.drop_cooldown):
            drop = True
            self.last_drop_time = self.time
        self.prev_bass_energy = bass_energy
        return drop, bass_energy

    def draw_morphing_blob(self, amp, spectrum, drop_scale=1.0):
        # Central morphing, glowing blob, now reacts to bass
        num_points = 40
        bass_end = max(1, int(len(spectrum) * 0.10))
        bass_energy = np.mean(spectrum[:bass_end]) if spectrum is not None and len(
            spectrum) > 0 else 0
        # More responsive to bass and drop
        base_radius = (80 + bass_energy * 180) * drop_scale
        points = []
        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi
            freq_idx = int(len(spectrum) * i / num_points)
            freq_val = spectrum[freq_idx] if freq_idx < len(spectrum) else 0
            morph = 1 + 0.25 * math.sin(angle * 6 + self.time * 2) * freq_val
            r = base_radius * morph
            x = self.center_x + math.cos(angle) * r
            y = self.center_y + math.sin(angle) * r
            points.append((x, y))
        # Glow
        glow_surf = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA)
        for g in range(18, 0, -4):
            color = self.get_palette_color(
                self.time*0.7 + g*0.2, amp, spectrum)
            alpha = int(60 * (g/18))
            pygame.draw.polygon(glow_surf, color + (alpha,), points, 0)
        self.screen.blit(glow_surf, (0, 0),
                         special_flags=pygame.BLEND_RGBA_ADD)
        # Main blob
        color = self.get_palette_color(self.time*0.7, amp, spectrum)
        pygame.draw.polygon(self.screen, color, points, 0)
        # Outline
        outline_color = self.get_palette_color(
            self.time*0.7 + 2, amp, spectrum)
        pygame.draw.polygon(self.screen, outline_color, points, 3)

    def draw_waveform(self, waveform, amp=0.5, spectrum=None):
        if waveform is None or len(waveform) == 0:
            return
        points = []
        for i, value in enumerate(waveform):
            x = int(i * self.screen_width / len(waveform))
            y = int(self.center_y + value * self.screen_height * 0.25)
            points.append((x, y))
        if len(points) > 1:
            # Glow
            glow_color = self.get_palette_color(
                self.time*1.2 + 3, amp, spectrum)
            pygame.draw.lines(self.screen, glow_color, False, points, 10)
            # Main line
            color = self.get_palette_color(self.time*1.2, amp, spectrum)
            pygame.draw.lines(self.screen, color, False, points, 3)

    def draw_spectrum(self, spectrum, amp=0.5):
        if spectrum is None or len(spectrum) == 0:
            return
        num_bars = 64  # More bars for finer look
        bar_width = max(2, self.screen_width // (num_bars * 2))  # Thinner bars
        gap = bar_width  # Gap between bars
        max_bar_height = int(self.screen_height * 0.13)  # Shorter bars
        for i in range(num_bars):
            freq_idx = int(len(spectrum) * i / num_bars)
            val = spectrum[freq_idx] if freq_idx < len(spectrum) else 0
            h = int(val * max_bar_height)
            x = i * (bar_width + gap)
            color = self.get_palette_color(
                self.time*0.5 + i*0.2, amp, spectrum)
            # Glow
            glow_surf = pygame.Surface((bar_width, h+20), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, color + (80,), (0, 0, bar_width, h+20))
            self.screen.blit(glow_surf, (x, self.center_y-h//2-10),
                             special_flags=pygame.BLEND_RGBA_ADD)
            # Main bar
            pygame.draw.rect(self.screen, color,
                             (x, self.center_y-h//2, bar_width, h))

    def update(self, screen):
        self.screen = screen
        dt = 1/60  # Assume 60 FPS for animation timing
        self.time += dt
        waveform = self.audio_processor.get_waveform()
        spectrum = self.audio_processor.get_spectrum()
        amp = np.abs(waveform).mean() if waveform is not None else 0
        # Draw background
        self.draw_background(amp, spectrum)
        # Bass drop detection and shockwave
        drop, bass_energy = self.detect_bass_drop(spectrum)
        drop_scale = 1.0
        if drop:
            self.trigger_shockwave(bass_energy, amp, spectrum)
            self.add_particles(random.randint(32, 48),
                               self.get_palette_color(self.time*2.2, amp, spectrum))
            drop_scale = 1.25 + min(0.5, bass_energy)
        self.update_shockwaves(dt)
        # Beat detection and particles (now uses bass)
        if self.detect_beat(amp, dt, spectrum):
            color = self.get_palette_color(self.time*1.5, amp, spectrum)
            self.add_particles(random.randint(18, 32), color)
        self.update_particles(dt)
        # Draw morphing blob (with drop scale)
        if spectrum is not None:
            self.draw_morphing_blob(amp, spectrum, drop_scale)
        # Draw waveform
        self.draw_waveform(waveform, amp, spectrum)
        # Draw spectrum
        self.draw_spectrum(spectrum, amp)
