class AudioProcessor:
    def __init__(self, audio_data, sample_rate):
        self.audio_data = audio_data
        self.sample_rate = sample_rate

    def get_waveform(self):
        """Return raw waveform data for visualization."""
        pass

    def get_spectrum(self, window_size=2048):
        """Return frequency spectrum (FFT) for visualization."""
        pass
