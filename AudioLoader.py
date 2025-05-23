import librosa
import soundfile as sf
import numpy as np
import os
import subprocess
import tempfile


class AudioLoader:
    def __init__(self):
        self.file_path = None
        self.audio_data = None
        self.sample_rate = None
        self.playback_file = None

    def pick_file(self):
        """Open a file dialog and let the user select an audio file."""
        try:
            # Use osascript to show a native macOS file picker
            script = '''
            tell application "System Events"
                set filePath to choose file with prompt "Select Audio File" of type {"mp3", "wav", "ogg", "flac"}
                return POSIX path of filePath
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script], capture_output=True, text=True)

            if result.returncode == 0:
                file_path = result.stdout.strip()
                return self.load_audio(file_path)
            return False
        except Exception as e:
            print(f"Error selecting file: {e}")
            return False

    def convert_to_wav(self, input_file):
        """Convert audio file to WAV format for playback."""
        try:
            # Create a temporary WAV file
            temp_dir = tempfile.gettempdir()
            temp_wav = os.path.join(temp_dir, 'temp_playback.wav')

            # Use ffmpeg to convert the file
            command = [
                'ffmpeg', '-y',  # -y to overwrite output file
                '-i', input_file,
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-ar', '44100',  # 44.1kHz sample rate
                '-ac', '2',  # stereo
                temp_wav
            ]

            # Run the conversion
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                self.playback_file = temp_wav
                return True
            else:
                print(f"Error converting audio: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error in audio conversion: {e}")
            return False

    def load_audio(self, file_path):
        """Load audio file and convert to mono."""
        try:
            # First try with soundfile
            try:
                self.audio_data, self.sample_rate = sf.read(file_path)
                if len(self.audio_data.shape) > 1:
                    self.audio_data = np.mean(self.audio_data, axis=1)
            except Exception as e:
                print(f"SoundFile failed, trying librosa: {e}")
                # Fallback to librosa
                self.audio_data, self.sample_rate = librosa.load(
                    file_path, sr=None, mono=True)

            # Normalize audio data
            self.audio_data = librosa.util.normalize(self.audio_data)
            self.file_path = file_path

            # Convert to WAV for playback
            if not self.convert_to_wav(file_path):
                print("Warning: Could not convert audio for playback")

            print(f"Successfully loaded audio file: {file_path}")
            print(f"Sample rate: {self.sample_rate}Hz")
            print(
                f"Duration: {len(self.audio_data)/self.sample_rate:.2f} seconds")
            return True
        except Exception as e:
            print(f"Error loading audio file: {e}")
            return False

    def cleanup(self):
        """Clean up temporary files."""
        if self.playback_file and os.path.exists(self.playback_file):
            try:
                os.remove(self.playback_file)
            except Exception as e:
                print(f"Error cleaning up temporary file: {e}")
