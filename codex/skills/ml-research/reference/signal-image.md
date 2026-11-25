# Signal & Image Processing: Preprocessing and Feature Extraction

Preprocessing chains, filtering, feature extraction methods, augmentation policies, and how to report each in the Methods section.

## Preprocessing chains: standard patterns

### Image preprocessing (computer vision)

#### Step 1: Load and resize
```python
from PIL import Image
import numpy as np

img = Image.open('image.jpg')
img_resized = img.resize((224, 224), Image.BILINEAR)
img_array = np.array(img_resized)  # shape: (H, W, C)
```

Report: "Images were resized to 224×224 pixels using bilinear interpolation."

#### Step 2: Normalization (ImageNet standard)
```python
# ImageNet statistics (from 1M+ images)
mean = np.array([0.485, 0.456, 0.406])
std = np.array([0.229, 0.224, 0.225])

img_normalized = (img_array / 255.0 - mean) / std
```

Report: "Images were normalized using ImageNet statistics (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]) after scaling to [0, 1]."

#### Step 3: Augmentation (training only)
```python
from torchvision import transforms

train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.08, 1.0)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomVerticalFlip(p=0.1),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

val_test_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])
```

Report: "Training data augmentation: random resized crop (scale ∈ [0.08, 1.0]), random horizontal flip (p=0.5), random vertical flip (p=0.1), color jitter (brightness/contrast/saturation ±0.2). Validation and test sets: center crop only, no augmentation."

### Audio preprocessing (speech, music)

#### Step 1: Load and resample
```python
import librosa

# Load audio at 16 kHz (standard for speech)
y, sr = librosa.load('audio.wav', sr=16000)  # mono, 16 kHz
```

Report: "Audio files were resampled to 16 kHz using librosa's default Kaiser best method."

#### Step 2: Extract STFT spectrogram
```python
# Short-Time Fourier Transform
n_fft = 2048  # ~128 ms window at 16 kHz
hop_length = 512  # 50% overlap
S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
S_mag = np.abs(S)  # magnitude
```

Report: "STFT spectrograms were computed using a 2048-point FFT (≈128 ms window) with 50% overlap (hop length=512), resulting in 1025 frequency bins."

#### Step 3: Log mel-scale
```python
# Convert to mel scale
n_mels = 128
mel_spec = librosa.feature.melspectrogram(S=S_mag, n_mels=n_mels)

# Log scale
mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
```

Report: "Mel-scale spectrograms were computed with 128 mel bands, then converted to dB scale (20 log₁₀) using the maximum magnitude as reference."

#### Step 4: Normalize
```python
# Normalize to [−1, 1] or compute per-frame z-score
mean = np.mean(mel_spec_db, axis=1, keepdims=True)
std = np.std(mel_spec_db, axis=1, keepdims=True) + 1e-8
mel_spec_normalized = (mel_spec_db - mean) / std
```

Report: "Each mel-scale spectrogram was normalized using per-frequency z-score normalization (mean=0, std=1 per frequency bin)."

### Signal preprocessing (time-series, ECG, EEG, seismic)

#### Step 1: Filtering
```python
from scipy import signal

# Bandpass filter (e.g., remove DC and high-frequency noise)
sos = signal.butter(4, [0.5, 100], 'bp', fs=fs, output='sos')  # 4th-order Butterworth
filtered = signal.sosfilt(sos, raw_signal)
```

Report: "A 4th-order Butterworth bandpass filter (cutoff frequencies 0.5–100 Hz) was applied to remove DC offset and high-frequency noise."

#### Step 2: Segmentation and windowing
```python
# Segment into 2-second windows with 50% overlap
segment_length = 2 * fs  # 2 seconds
hop_length = segment_length // 2
segments = []
for i in range(0, len(filtered) - segment_length, hop_length):
    segment = filtered[i:i+segment_length]
    # Apply Hamming window
    segment = segment * np.hamming(len(segment))
    segments.append(segment)
```

Report: "Signal was segmented into 2-second windows with 50% overlap. A Hamming window was applied to each segment to reduce spectral leakage."

#### Step 3: Normalization
```python
# Z-score normalize per segment
segments_normalized = []
for seg in segments:
    seg_norm = (seg - np.mean(seg)) / (np.std(seg) + 1e-8)
    segments_normalized.append(seg_norm)
```

Report: "Each segment was z-score normalized (mean=0, std=1) independently."

## Feature extraction methods

### FFT (Fast Fourier Transform) — frequency domain

```python
import numpy as np
from scipy import signal

# Compute FFT of a segment
freqs = np.fft.rfftfreq(len(segment), d=1/fs)  # frequency axis
fft = np.fft.rfft(segment)  # single-sided FFT
magnitude = np.abs(fft)
phase = np.angle(fft)

# Feature: power spectral density (PSD)
psd = magnitude ** 2 / len(segment)
```

**When to use:** Stationary signals (ECG baseline, steady-state mechanical vibration).

**Pitfalls:**
- FFT assumes periodicity; edge effects if signal not periodic in window.
- Assumes stationarity; use only on segments that don't vary over time.

Report: "Power spectral density was estimated using FFT on 2-second segments; frequency resolution = 0.5 Hz."

### STFT (Short-Time Fourier Transform) — time-frequency

```python
# Already shown in audio preprocessing
S_mag = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
```

**When to use:** Non-stationary signals (speech, music, seismic events) where frequency content changes over time.

**Output:** 2D matrix (frequency × time frames).

Report: "Time-frequency analysis using STFT (2048-point FFT, 512-sample hop) captures dynamics of the non-stationary signal."

### Wavelet transform — multi-scale analysis

```python
import pywt

# Continuous Wavelet Transform (CWT)
scales = np.arange(1, 128)  # scale range
coeffs, freqs = pywt.cwt(signal, scales, 'morl')  # Morlet wavelet

# Or Discrete Wavelet Transform (DWT) for decomposition
cA, cD = pywt.dwt(signal, 'db4')  # Daubechies-4
```

**When to use:** Multi-scale analysis (breakdown into approximation + detail); compression; edge detection.

**Advantage:** Better time-frequency localization than STFT (trade-off depends on scale).

Report: "Continuous wavelet transform using Morlet wavelets (scales 1–127) provides multi-scale time-frequency representation."

### MFCC (Mel-Frequency Cepstral Coefficients) — speech/audio

```python
# Already covered in audio preprocessing
# Extract MFCC features
n_mfcc = 13
mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
# Shape: (n_mfcc, n_frames)

# Often compute delta (first derivative) and delta-delta (second derivative)
mfcc_delta = librosa.feature.delta(mfcc)
mfcc_delta2 = librosa.feature.delta(mfcc, order=2)

# Stack into feature matrix
features = np.vstack([mfcc, mfcc_delta, mfcc_delta2])  # (39, n_frames)
```

**When to use:** Speech recognition, speaker identification, music genre classification.

**Why MFCC?** Mimics human auditory perception (mel scale = perceptual frequency).

Report: "MFCC features (13 coefficients) with delta and delta-delta (39 features total) were extracted from mel-scale spectrograms."

### Handcrafted features (signal domain)

Common handcrafted features for time-series/signal data:

```python
def compute_handcrafted_features(segment):
    features = {}
    features['mean'] = np.mean(segment)
    features['std'] = np.std(segment)
    features['rms'] = np.sqrt(np.mean(segment ** 2))
    features['peak'] = np.max(np.abs(segment))
    features['crest_factor'] = np.max(np.abs(segment)) / features['rms']
    features['skewness'] = scipy.stats.skew(segment)
    features['kurtosis'] = scipy.stats.kurtosis(segment)
    features['zero_crossing_rate'] = np.sum(np.abs(np.diff(np.sign(segment)))) / (2 * len(segment))
    return features
```

**Common handcrafted features:**
- Statistical: mean, std, min, max, range, skewness, kurtosis
- Energy: RMS, peak, crest factor
- Spectral: spectral centroid, spectral bandwidth, spectral entropy
- Temporal: zero-crossing rate, autocorrelation

Report: "Handcrafted features (12-dimensional): mean, std, RMS, peak, crest factor, skewness, kurtosis, zero-crossing rate, spectral centroid, spectral bandwidth, spectral entropy, autocorrelation lag-1."

## Augmentation policies and leakage prevention

### Image augmentation (training only)

```python
# Example: aggressive augmentation (RandAugment)
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.08, 1.0)),
    transforms.RandAugment(num_ops=2, magnitude=9),  # Apply 2 random ops from a pool
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])
```

Report: "RandAugment (num_ops=2, magnitude=9) was applied during training to improve robustness."

### Audio augmentation (training only)

```python
# Example: augmentation for audio
train_transform = [
    # Time stretch (pitch-preserving speed change)
    lambda y: librosa.effects.time_stretch(y, rate=np.random.uniform(0.9, 1.1)),
    # Pitch shift
    lambda y: librosa.effects.pitch_shift(y, sr=16000, n_steps=np.random.randint(-2, 3)),
    # SpecAugment (mask time and frequency regions in spectrogram)
    # Add Gaussian noise
    lambda y: y + np.random.normal(0, 0.01 * np.std(y), len(y))
]
```

Report: "Augmentation during training: time stretch (rate ∈ [0.9, 1.1]), pitch shift (±2 semitones), SpecAugment (10% time/frequency masking), Gaussian noise (σ = 0.01 × signal std)."

### Leakage prevention in augmentation

**⚠️ DO NOT:** Fit augmentation parameters on the entire dataset before splitting into train/val/test.

Example of leakage:
```python
# WRONG: compute rotation angle needed for augmentation on all data
max_rotation = compute_image_rotation_correction(all_data)  # Leak!
# Then split
train, val, test = split(all_data)
```

**Correct way:**
```python
# Correct: augmentation parameters fixed, not learned from data
train, val, test = split(all_data)
train_augmented = apply_augmentation(train, augmentation_policy)
# Validation and test: no augmentation (or minimal center crop only)
```

Report: "Data augmentation was applied only to the training set. Augmentation parameters were fixed and not adapted based on any data."

### Mixup and Cutmix (advanced image augmentation)

```python
# Mixup: blend two images and their labels
def mixup(x1, x2, y1, y2, alpha=1.0):
    lam = np.random.beta(alpha, alpha)
    mixed_x = lam * x1 + (1 - lam) * x2
    mixed_y = lam * y1 + (1 - lam) * y2
    return mixed_x, mixed_y

# Cutmix: blend crops of two images
def cutmix(x1, x2, y1, y2, alpha=1.0):
    lam = np.random.beta(alpha, alpha)
    # Random box position and size
    cut_ratio = np.sqrt(1.0 - lam)
    # Copy region from x2 into x1
    mixed_x = x1.copy()
    mixed_x[box] = x2[box]
    mixed_y = lam * y1 + (1 - lam) * y2
    return mixed_x, mixed_y
```

Report: "Mixup (α=1.0) and Cutmix (α=1.0) were applied during training to improve generalization."

## Reporting preprocessing in Methods

### Minimal Methods section (1 paragraph)

"All images were resized to 224×224 pixels and normalized using ImageNet statistics (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]). Training data augmentation included random resized crop, horizontal flip, and color jitter. Validation and test sets used center crop only, without augmentation."

### Detailed Methods section (subsection)

#### Data Preprocessing
"Raw images were resized to 224×224 pixels using bilinear interpolation. All pixel values were scaled to [0, 1] and normalized using ImageNet statistics (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]).

#### Augmentation Strategy
Training images underwent the following augmentations:
- Random resized crop (scale ∈ [0.08, 1.0], aspect ratio ∈ [0.75, 1.33])
- Random horizontal flip (p=0.5)
- Random vertical flip (p=0.1)
- Color jitter (brightness/contrast/saturation ±0.2)

Validation and test images were not augmented; only center crop (224×224 from 256×256) was applied.

#### Statistical Properties
Preprocessing statistics were computed on the training set only. No global statistics across all splits were used, preventing leakage."

### Supplementary: detailed algorithm

If space permits, include a flowchart or pseudocode:
```
Input: raw image
├─ Resize to 224×224 (bilinear interpolation)
├─ Scale to [0, 1]
├─ Augment (train only):
│  ├─ Random resized crop
│  ├─ Random horizontal flip (p=0.5)
│  ├─ Color jitter (brightness/contrast/saturation ±0.2)
│  └─ Normalize with ImageNet statistics
├─ Center crop (val/test only)
└─ Normalize with ImageNet statistics (fitted on train)
Output: (224, 224, 3) tensor, normalized
```

