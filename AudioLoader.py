class AudioLoader:
    def __init__(self):
        self.file_path = None
        self.audio_data = None
        self.sample_rate = None

    def pick_file(self):
        """Open a file dialog and let the user select an audio file."""
        pass

    def load_audio(self, file_path):
        """Decode the audio file and store waveform and sample rate."""
        pass
