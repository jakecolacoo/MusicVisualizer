import pygame
import sys
import os
from AudioLoader import AudioLoader
from AudioProcessor import AudioProcessor
from Visualizer import Visualizer


def main():
    # Initialize Pygame
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

    # Set up the display
    screen_width = 1280
    screen_height = 720
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Music Visualizer")
    fullscreen = False

    # Initialize components
    audio_loader = AudioLoader()
    audio_processor = None
    visualizer = None

    # Main loop
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.DROPFILE:
                try:
                    # Stop any currently playing music
                    pygame.mixer.music.stop()

                    # Load and play the new file
                    print(f"Loading audio file: {event.file}")
                    if audio_loader.load_audio(event.file):
                        audio_data = audio_loader.audio_data
                        sample_rate = audio_loader.sample_rate
                        audio_processor = AudioProcessor(
                            audio_data, sample_rate)
                        visualizer = Visualizer(
                            audio_processor, screen_width, screen_height)
                        if audio_loader.playback_file and os.path.exists(audio_loader.playback_file):
                            pygame.mixer.music.load(audio_loader.playback_file)
                            pygame.mixer.music.play()
                            print(
                                f"Playing audio file: {os.path.basename(event.file)}")
                        else:
                            print(
                                "Warning: No playback file available for Pygame mixer.")
                    else:
                        print(f"Failed to load audio file: {event.file}")
                except Exception as e:
                    print(f"Error loading audio file: {e}")
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode(
                            (0, 0), pygame.FULLSCREEN)
                        screen_width, screen_height = screen.get_size()
                    else:
                        screen = pygame.display.set_mode((1280, 720))
                        screen_width, screen_height = 1280, 720
                    # Update visualizer dimensions if it exists
                    if visualizer is not None:
                        visualizer.screen_width = screen_width
                        visualizer.screen_height = screen_height
                        visualizer.center_x = screen_width // 2
                        visualizer.center_y = screen_height // 2

        # Clear the screen
        screen.fill((0, 0, 0))

        # Update and draw visualization if available
        if visualizer is not None:
            try:
                visualizer.update(screen)
            except Exception as e:
                print(f"Error drawing visualization: {e}")
        else:
            # Show drag-and-drop prompt
            font = pygame.font.Font(None, 48)
            text = font.render(
                "Drag and drop an audio file here", True, (255, 255, 255))
            text_rect = text.get_rect(center=(screen_width/2, screen_height/2))
            screen.blit(text, text_rect)

        # Update the display
        pygame.display.flip()

        # Cap the frame rate
        clock.tick(60)

    # Cleanup
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error in main: {e}")
        pygame.quit()
        sys.exit(1)
