import numpy as np
import librosa


class AudioProcessor:
    def __init__(self, audio_data, sample_rate):
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.current_position = 0
        self.chunk_size = 2048  # Reduced chunk size for better responsiveness
        self.hop_length = 512   # Reduced hop length for smoother transitions

    def get_waveform(self):
        """Get the current chunk of waveform data."""
        try:
            if self.current_position >= len(self.audio_data):
                return None

            end_pos = min(self.current_position +
                          self.chunk_size, len(self.audio_data))
            chunk = self.audio_data[self.current_position:end_pos]

            # Update position
            self.current_position += self.hop_length

            # If we've reached the end, loop back to the beginning
            if self.current_position >= len(self.audio_data):
                self.current_position = 0

            return chunk
        except Exception as e:
            print(f"Error getting waveform: {e}")
            return None

    def get_spectrum(self):
        """Get the frequency spectrum of the current chunk."""
        try:
            chunk = self.get_waveform()
            if chunk is None:
                return None

            # Compute the short-time Fourier transform
            D = librosa.stft(chunk, n_fft=self.chunk_size,
                             hop_length=self.hop_length)

            # Convert to magnitude spectrum
            S = np.abs(D)

            # Convert to decibels
            S_db = librosa.amplitude_to_db(S, ref=np.max)

            # Normalize to 0-1 range
            S_norm = (S_db - S_db.min()) / (S_db.max() - S_db.min())

            # Take the mean across time to get a single spectrum
            spectrum = np.mean(S_norm, axis=1)

            # Resize to a fixed length for visualization
            target_length = 128  # Reduced number of frequency bins for better performance
            if len(spectrum) > target_length:
                spectrum = np.interp(
                    np.linspace(0, len(spectrum), target_length),
                    np.arange(len(spectrum)),
                    spectrum
                )

            return spectrum
        except Exception as e:
            print(f"Error getting spectrum: {e}")
            return None
