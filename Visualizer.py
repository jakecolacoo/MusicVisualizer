import pygame
import numpy as np
from colorsys import hsv_to_rgb
import math
import random
from scipy.interpolate import interp1d


def to_rgba(color, alpha=255):
    # Ensure color is a tuple of 3 or 4 ints in 0-255, and append/replace alpha
    if not isinstance(color, (tuple, list)):
        color = (255, 255, 255)
    if len(color) == 4:
        color = color[:3]
    color = tuple(int(min(255, max(0, c))) for c in color)
    return color + (int(min(255, max(0, alpha))),)


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
        self.beat_scale = 1.0  # Add beat scale for yellow circle
        self.clap_flatten_frames = 0  # Counter for flattening waveform
        self.clap_flatten_total = 0   # Total duration for smooth transition

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
        # Ensure color values are properly clamped and converted to integers
        r, g, b = hsv_to_rgb(h, s, v)
        return (int(min(255, max(0, r * 255))),
                int(min(255, max(0, g * 255))),
                int(min(255, max(0, b * 255))))

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

    def add_particles(self, n, color, type='normal'):
        # Ensure color is a valid RGB tuple
        if not isinstance(color, tuple) or len(color) != 3:
            color = (255, 255, 255)  # Default to white if invalid
        color = tuple(min(255, max(0, int(c))) for c in color)

        for _ in range(n):
            angle = random.uniform(0, 2 * math.pi)
            if type == 'orbit':
                # Orbiting particles
                radius = random.uniform(
                    self.screen_height*0.18, self.screen_height*0.38)
                speed = random.uniform(0.6, 1.8)
                particle = {
                    'type': 'orbit',
                    'angle': angle,
                    'radius': radius,
                    'speed': speed,
                    'color': color,
                    'size': random.randint(8, 18),
                    'life': random.uniform(2.5, 4.5),
                    'trail': []
                }
            elif type == 'comet':
                # Comet trail particles
                speed = random.uniform(7, 13)
                particle = {
                    'type': 'comet',
                    'x': self.center_x,
                    'y': self.center_y,
                    'dx': math.cos(angle) * speed,
                    'dy': math.sin(angle) * speed,
                    'color': color,
                    'size': random.randint(10, 22),
                    'life': random.uniform(0.7, 1.3),
                    'trail': []
                }
            else:
                # Normal/starburst as before
                speed = random.uniform(
                    2, 7) if type == 'normal' else random.uniform(8, 16)
                particle = {
                    'x': self.center_x,
                    'y': self.center_y,
                    'dx': math.cos(angle) * speed,
                    'dy': math.sin(angle) * speed,
                    'life': random.uniform(0.7, 1.2) if type == 'normal' else random.uniform(0.3, 0.6),
                    'color': color,
                    'size': random.randint(6, 16) if type == 'normal' else random.randint(10, 24),
                    'type': type,
                    'angle': angle
                }
            self.particles.append(particle)

    def update_particles(self, dt):
        for p in self.particles[:]:
            if p.get('type') == 'orbit':
                # Orbiting logic
                p['angle'] += p['speed'] * dt * (0.7 + 1.2*random.random())
                mod_radius = p['radius'] * \
                    (1 + 0.08 * math.sin(self.time*1.2 + p['angle']*2))
                x = self.center_x + math.cos(p['angle']) * mod_radius
                y = self.center_y + math.sin(p['angle']) * mod_radius
                p['trail'].append((x, y))
                if len(p['trail']) > 18:
                    p['trail'].pop(0)
                p['life'] -= dt
                alpha = int(120 * min(1, p['life']))
                for i, (tx, ty) in enumerate(p['trail']):
                    t_alpha = int(alpha * (i/len(p['trail'])))
                    surf = pygame.Surface(
                        (p['size'], p['size']), pygame.SRCALPHA)
                    pygame.draw.circle(surf, to_rgba(
                        p['color'], t_alpha), (p['size']//2, p['size']//2), p['size']//2)
                    self.screen.blit(
                        surf, (tx-p['size']//2, ty-p['size']//2), special_flags=pygame.BLEND_RGBA_ADD)
                surf = pygame.Surface(
                    (p['size']*2, p['size']*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, to_rgba(
                    p['color'], alpha), (p['size'], p['size']), p['size'])
                self.screen.blit(
                    surf, (x-p['size'], y-p['size']), special_flags=pygame.BLEND_RGBA_ADD)
                if p['life'] <= 0:
                    self.particles.remove(p)
            elif p.get('type') == 'comet':
                p['x'] += p['dx'] * dt * 60
                p['y'] += p['dy'] * dt * 60
                p['trail'].append((p['x'], p['y']))
                if len(p['trail']) > 22:
                    p['trail'].pop(0)
                p['life'] -= dt
                alpha = int(160 * min(1, p['life']))
                for i, (tx, ty) in enumerate(p['trail']):
                    t_alpha = int(alpha * (i/len(p['trail'])))
                    surf = pygame.Surface(
                        (p['size'], p['size']), pygame.SRCALPHA)
                    pygame.draw.circle(surf, to_rgba(
                        p['color'], t_alpha), (p['size']//2, p['size']//2), p['size']//2)
                    self.screen.blit(
                        surf, (tx-p['size']//2, ty-p['size']//2), special_flags=pygame.BLEND_RGBA_ADD)
                surf = pygame.Surface(
                    (p['size']*2, p['size']*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, to_rgba(
                    p['color'], alpha), (p['size'], p['size']), p['size'])
                self.screen.blit(
                    surf, (p['x']-p['size'], p['y']-p['size']), special_flags=pygame.BLEND_RGBA_ADD)
                if p['life'] <= 0:
                    self.particles.remove(p)
            else:
                p['x'] += p['dx'] * dt * 60
                p['y'] += p['dy'] * dt * 60
                p['life'] -= dt
                alpha = int(180 * p['life'])
                surf = pygame.Surface(
                    (p['size']*2, p['size']*2), pygame.SRCALPHA)
                if p.get('type', 'normal') == 'starburst':
                    points = []
                    spikes = 7
                    for i in range(spikes * 2):
                        r = p['size'] if i % 2 == 0 else p['size']//2
                        a = p['angle'] + i * math.pi / spikes
                        x = p['size'] + math.cos(a) * r
                        y = p['size'] + math.sin(a) * r
                        points.append((x, y))
                    pygame.draw.polygon(surf, to_rgba(
                        p['color'], alpha), points)
                    pygame.draw.polygon(surf, to_rgba(
                        (255, 255, 255), int(alpha*0.5)), points, 2)
                else:
                    pygame.draw.circle(surf, to_rgba(
                        p['color'], alpha), (p['size'], p['size']), p['size'])
                    pygame.draw.circle(surf, to_rgba((255, 255, 255), int(
                        alpha*0.5)), (p['size'], p['size']), p['size']//2)
                self.screen.blit(
                    surf, (p['x']-p['size'], p['y']-p['size']), special_flags=pygame.BLEND_RGBA_ADD)
                if p['life'] <= 0:
                    self.particles.remove(p)

    def draw_background(self, amp=0.5, spectrum=None):
        # Smooth vertical gradient: blend between two palette colors, slow color cycling
        slow_factor = 0.025  # much slower than before
        top_t = (self.time * slow_factor) % len(self.palette)
        bot_t = (self.time * slow_factor + 2) % len(self.palette)
        top_color = self.get_palette_color(top_t, amp, spectrum)
        bot_color = self.get_palette_color(bot_t, amp, spectrum)
        # Make the gradient much darker by blending with a dark base
        darken = 0.55  # Increased from 0.32
        dark_base = (12, 12, 24)  # deep blue-black
        for y in range(self.screen_height):
            frac = y / self.screen_height
            color = tuple(
                int((top_color[i] * (1 - frac) + bot_color[i] *
                    frac) * (1 - darken) + dark_base[i] * darken)
                for i in range(3)
            )
            pygame.draw.line(self.screen, to_rgba(color, 255),
                             (0, y), (self.screen_width, y))
        # --- True animated ripple effect ---
        ripple_surf = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA)
        cx, cy = self.center_x, self.center_y
        ripple_strength = 32 + amp * 48  # amplitude of ripple
        ripple_freq = 0.022 + amp * 0.018  # frequency of ripple
        ripple_speed = 2.0 + amp * 2.0
        for r in range(0, int(0.7 * min(self.screen_width, self.screen_height)), 4):
            # Calculate phase for this radius
            phase = (self.time * ripple_speed - r * ripple_freq)
            offset = int(math.sin(phase) * ripple_strength)
            alpha = int(38 + 60 * amp * (0.7 - r /
                        (0.7 * min(self.screen_width, self.screen_height))))
            color = self.get_palette_color(
                self.time * 0.18 + r * 0.002, amp, spectrum)
            if alpha > 0:
                pygame.draw.circle(ripple_surf, to_rgba(
                    color, alpha), (cx, cy), r + offset, 2)
        self.screen.blit(ripple_surf, (0, 0),
                         special_flags=pygame.BLEND_RGBA_ADD)
        # --- Draw yellow circle with beat scaling ---
        yellow = (255, 240, 80)
        base_radius = int(min(self.screen_width, self.screen_height) * 0.32)
        radius = int(base_radius * self.beat_scale)
        pygame.draw.circle(self.screen, yellow,
                           (self.center_x, self.center_y), radius)
        # --- Beat-responsive ripples ---
        ripple_surf2 = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA)
        ripple_count = 5 + int(amp * 4)
        base_radius = min(self.screen_width, self.screen_height) // 6
        ripple_speed2 = 1.2 + amp * 2.5
        for i in range(ripple_count):
            phase = (self.time * ripple_speed2 + i * 0.7) % 1.0
            radius = int(base_radius + (self.time * 180 *
                         ripple_speed2 + i * 60) % (self.center_x * 0.9))
            alpha = int(60 * (1 - phase) * (0.5 + amp))
            color = self.get_palette_color(
                self.time * 0.2 + i * 0.5, amp, spectrum)
            if alpha > 0:
                pygame.draw.circle(ripple_surf2, to_rgba(color, alpha),
                                   (self.center_x, self.center_y), radius, 6)
        self.screen.blit(ripple_surf2, (0, 0),
                         special_flags=pygame.BLEND_RGBA_ADD)
        # Animated radial pastel overlay (still subtle, slow color cycling)
        overlay = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA)
        for r in range(int(min(self.screen_width, self.screen_height)//2), 0, -12):
            t = (self.time * slow_factor + r/120) % len(self.palette)
            color = self.get_palette_color(t, amp, spectrum)
            alpha = int(
                30 * (1 - r/(min(self.screen_width, self.screen_height)//2)))
            if alpha > 0:
                pygame.draw.circle(overlay, to_rgba(color, alpha),
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
                pygame.draw.circle(surf, to_rgba(s['color'], int(s['alpha'])),
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
        num_points = 120  # Increased for smoother outline
        bass_end = max(1, int(len(spectrum) * 0.10))
        bass_energy = np.mean(spectrum[:bass_end]) if spectrum is not None and len(
            spectrum) > 0 else 0
        # More responsive to bass and drop
        base_radius = (80 + bass_energy * 180) * drop_scale
        # Smooth the spectrum for less jagged morphing
        if spectrum is not None and len(spectrum) > 6:
            window_size = 6
            smooth_spectrum = np.convolve(spectrum, np.ones(
                window_size)/window_size, mode='same')
        else:
            smooth_spectrum = spectrum if spectrum is not None else []
        points = []
        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi
            freq_idx = int(len(smooth_spectrum) * i /
                           num_points) if smooth_spectrum is not None and len(smooth_spectrum) > 0 else 0
            freq_val = smooth_spectrum[freq_idx] if smooth_spectrum is not None and freq_idx < len(
                smooth_spectrum) else 0
            # More dynamic morphing
            morph = 1 + 0.38 * \
                math.sin(angle * 6 + self.time * 2.2) * freq_val + 0.12 * amp
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
            pygame.draw.polygon(glow_surf, to_rgba(color, alpha), points, 0)
        self.screen.blit(glow_surf, (0, 0),
                         special_flags=pygame.BLEND_RGBA_ADD)
        # Main blob
        color = self.get_palette_color(self.time*0.7, amp, spectrum)
        pygame.draw.polygon(self.screen, to_rgba(color, 255), points, 0)
        # Outline
        outline_color = self.get_palette_color(
            self.time*0.7 + 2, amp, spectrum)
        pygame.draw.polygon(self.screen, to_rgba(
            outline_color, 255), points, 3)

    def draw_waveform(self, waveform, amp=0.5, spectrum=None):
        if waveform is None or len(waveform) == 0:
            return
        # Smoothing: moving average
        window_size = 12  # Previous value for energetic curve
        if len(waveform) > window_size:
            smooth_waveform = np.convolve(waveform, np.ones(
                window_size)/window_size, mode='same')
        else:
            smooth_waveform = waveform
        # Interpolate for smoothness
        interp_points = 12  # Previous value for dense curve
        x_vals = np.linspace(0, self.screen_width, len(smooth_waveform))
        f = interp1d(x_vals, smooth_waveform, kind='cubic') if len(
            smooth_waveform) > 3 else interp1d(x_vals, smooth_waveform, kind='linear')
        x_dense = np.linspace(0, self.screen_width, len(
            smooth_waveform) * interp_points)
        y_dense = f(x_dense)
        base_amplitude = 0.45  # Previous value for dramatic amplitude
        # Smooth flatten transition
        amplitude = base_amplitude
        if hasattr(self, 'clap_flatten_frames') and self.clap_flatten_frames > 0 and hasattr(self, 'clap_flatten_total') and self.clap_flatten_total > 0:
            t = 1 - (self.clap_flatten_frames / self.clap_flatten_total)
            # Fade out and back in (ease in/out)
            if t < 0.5:
                amplitude = base_amplitude * (1 - 2*t)  # Fade out
            else:
                amplitude = base_amplitude * (2*t - 1)  # Fade in
            amplitude = max(amplitude, 0.0)
        points = [(int(x), int(self.center_y + y * self.screen_height * amplitude))
                  for x, y in zip(x_dense, y_dense)]
        if len(points) > 1:
            # Thinner lines
            glow_color = self.get_palette_color(
                self.time*1.2 + 3, amp, spectrum)
            pygame.draw.lines(self.screen, to_rgba(
                glow_color, 180), False, points, 10)
            color = self.get_palette_color(self.time*1.2, amp, spectrum)
            pygame.draw.lines(self.screen, to_rgba(
                color, 255), False, points, 3)

    def draw_spectrum(self, spectrum, amp=0.5):
        if spectrum is None or len(spectrum) == 0:
            return
        num_bars = 128  # Doubled the number of bars
        total_width = self.screen_width
        # Calculate bar width to fill the entire screen width
        bar_width = max(1, (total_width - (num_bars - 1)) //
                        num_bars)  # Account for gaps
        gap = 1  # Reduced gap for denser packing
        max_bar_height = int(self.screen_height * 0.13)  # Shorter bars

        for i in range(num_bars):
            freq_idx = int(len(spectrum) * i / num_bars)
            val = spectrum[freq_idx] if freq_idx < len(spectrum) else 0
            h = int(val * max_bar_height)
            # Position each bar with gap from left edge
            x = i * (bar_width + gap)
            color = self.get_palette_color(
                self.time*0.5 + i*0.1, amp, spectrum)  # Adjusted color cycling
            # Glow
            glow_surf = pygame.Surface((bar_width, h+20), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, to_rgba(
                color, 80), (0, 0, bar_width, h+20))
            self.screen.blit(glow_surf, (x, self.center_y-h//2-10),
                             special_flags=pygame.BLEND_RGBA_ADD)
            # Main bar
            pygame.draw.rect(self.screen, to_rgba(color, 255),
                             (x, self.center_y-h//2, bar_width, h))

    def detect_treble_burst(self, spectrum):
        # Treble is the last 20% of spectrum
        if spectrum is None or len(spectrum) == 0:
            return False
        treble_start = int(len(spectrum) * 0.8)
        treble_energy = np.mean(spectrum[treble_start:])
        if not hasattr(self, 'prev_treble_energy'):
            self.prev_treble_energy = 0
        burst = False
        if treble_energy - self.prev_treble_energy > 0.22:
            burst = True
        self.prev_treble_energy = treble_energy
        return burst

    def detect_clap(self, waveform, spectrum):
        # Simple clap detection: high amplitude and high-frequency energy
        if waveform is None or spectrum is None:
            return False
        amp = np.abs(waveform).mean()
        n = len(spectrum)
        high_freq_energy = np.mean(spectrum[int(n*0.7):])
        # Lowered thresholds for more sensitivity
        return amp > 0.10 and high_freq_energy > 0.35

    def update(self, screen):
        self.screen = screen
        dt = 1/60  # Assume 60 FPS for animation timing
        self.time += dt
        waveform = self.audio_processor.get_waveform()
        spectrum = self.audio_processor.get_spectrum()
        amp = np.abs(waveform).mean() if waveform is not None else 0
        # Clap detection
        if self.detect_clap(waveform, spectrum):
            self.clap_flatten_frames = 12  # Lasts longer
            self.clap_flatten_total = 12
        else:
            if self.clap_flatten_frames > 0:
                self.clap_flatten_frames -= 1
        # Beat detection and scale update
        beat = self.detect_beat(amp, dt, spectrum)
        if beat:
            self.beat_scale = 1.18  # Pulse up on beat
        else:
            self.beat_scale += (1.0 - self.beat_scale) * \
                0.15  # Smoothly decay to 1.0
        # Draw background
        self.draw_background(amp, spectrum)
        # Bass drop detection and shockwave
        drop, bass_energy = self.detect_bass_drop(spectrum)
        drop_scale = 1.0
        if drop:
            self.trigger_shockwave(bass_energy, amp, spectrum)
            # Blend two palette colors for drop particles
            color1 = self.get_palette_color(self.time*2.2, amp, spectrum)
            color2 = self.get_palette_color(self.time*2.2+1.5, amp, spectrum)
            blended = tuple(int((c1+c2)/2) for c1, c2 in zip(color1, color2))
            # Slightly more frequent
            self.add_particles(random.randint(40, 64), blended)
            # NEW: Comet trails on drop
            comet_color1 = self.get_palette_color(self.time*3.7, amp, spectrum)
            comet_color2 = self.get_palette_color(
                self.time*3.7+1.8, amp, spectrum)
            comet_blended = tuple(int((c1+c2)/2)
                                  for c1, c2 in zip(comet_color1, comet_color2))
            # Slightly more frequent
            self.add_particles(random.randint(
                6, 10), comet_blended, type='comet')
            drop_scale = 1.25 + min(0.5, bass_energy)
        self.update_shockwaves(dt)
        # Beat detection and particles (now uses bass)
        if self.detect_beat(amp, dt, spectrum):
            color1 = self.get_palette_color(self.time*1.5, amp, spectrum)
            color2 = self.get_palette_color(self.time*1.5+1.2, amp, spectrum)
            blended = tuple(int((c1+c2)/2) for c1, c2 in zip(color1, color2))
            # Slightly more frequent
            self.add_particles(random.randint(24, 40), blended)
            # NEW: Orbiting particles on beat
            orbit_color1 = self.get_palette_color(self.time*2.8, amp, spectrum)
            orbit_color2 = self.get_palette_color(
                self.time*2.8+1.1, amp, spectrum)
            orbit_blended = tuple(int((c1+c2)/2)
                                  for c1, c2 in zip(orbit_color1, orbit_color2))
            # Slightly more frequent
            self.add_particles(random.randint(
                3, 6), orbit_blended, type='orbit')
        # Treble burst: starburst particles
        if self.detect_treble_burst(spectrum):
            color1 = self.get_palette_color(self.time*3.1, amp, spectrum)
            color2 = self.get_palette_color(self.time*3.1+2.2, amp, spectrum)
            blended = tuple(int((c1+c2)/2) for c1, c2 in zip(color1, color2))
            self.add_particles(random.randint(16, 28), blended,
                               type='starburst')  # Slightly more frequent
        self.update_particles(dt)
        # Draw morphing blob (with drop scale)
        if spectrum is not None:
            self.draw_morphing_blob(amp, spectrum, drop_scale)
        # Draw waveform
        self.draw_waveform(waveform, amp, spectrum)
