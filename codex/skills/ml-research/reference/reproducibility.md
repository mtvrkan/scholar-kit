# Reproducibility for ML Papers

NeurIPS-style reproducibility checklist, environment capture, model cards, and code/data availability.

## NeurIPS-style reproducibility checklist

Use this checklist when writing the Methods section or supplementary materials.

### Experimental design
- [ ] Research question clearly stated (not just empirical)
- [ ] Hypothesis specified before experiments
- [ ] Metric selection justified (why this metric for this task?)
- [ ] Train/val/test split strategy explained (random? stratified? temporal?)
- [ ] Random seed values specified (e.g., seeds = [42, 123, 456, 789, 999])
- [ ] Number of runs reported (≥3 seeds minimum)

### Dataset details
- [ ] Dataset name and source (DOI or URL)
- [ ] Dataset size (total samples, per split: train/val/test)
- [ ] Preprocessing steps (normalization, resizing, feature scaling)
  - What values were used? (e.g., ImageNet mean/std)
  - On which set were preprocessing parameters fitted? (train set only ✓)
- [ ] Data augmentation policy (if used)
  - Type (RandAugment, Mixup, cutout, etc.)
  - Parameters (N=2, M=9 for RandAugment)
  - Applied only to train set ✓
- [ ] Class imbalance (if any): how handled? (class weights, stratification, resampling)
- [ ] Missing data (if any): imputation strategy

### Model architecture
- [ ] Architecture name (ResNet-50, BERT-base, etc.)
- [ ] Architecture description or reference implementation
  - GitHub link with commit hash (not just URL; commit matters)
  - Architecture diagram or pseudocode (supplement)
- [ ] Initialization scheme (Xavier, He, pretrained, etc.)
- [ ] All hyperparameters (see experiment-design.md table example)

### Training procedure
- [ ] Optimizer (Adam, SGD, AdamW, etc.) with settings (β₁, β₂, ε)
- [ ] Learning rate (fixed or schedule? cosine, step, exponential?)
- [ ] Batch size
- [ ] Number of epochs (or training time)
- [ ] Loss function (cross-entropy, MSE, custom, etc.)
- [ ] Regularization (weight decay, dropout rates, batch norm details)
- [ ] Hardware used (GPU model, number of GPUs, RAM, CPU)
- [ ] Wall-clock training time
- [ ] Software versions (PyTorch/TensorFlow version, CUDA, cuDNN)
- [ ] Code availability (GitHub URL, Zenodo DOI, or "upon request")

### Evaluation protocol
- [ ] Metrics used and definitions
- [ ] Statistical test used for significance (paired t-test, Mann-Whitney, etc.)
- [ ] Multiple-comparison correction (if multiple tests: Bonferroni, FDR, etc.)
- [ ] Confidence intervals or error bars (mean ± std over seeds)

### Ablation studies
- [ ] One variable per ablation ✓
- [ ] Same random seeds as main experiment
- [ ] Effect size reported (Δ accuracy, Δ F1, etc.)
- [ ] Statistical significance test per ablation

### Baselines
- [ ] Baseline models named and cited
- [ ] Official implementations used or reimplementation explained
- [ ] Baselines given equal hyperparameter tuning budget
- [ ] Baselines run with same random seeds

## Environment capture

### Requirements file (minimal)

```txt
# requirements.txt
torch==2.0.1
torchvision==0.15.2
numpy==1.24.3
scipy==1.11.0
scikit-learn==1.3.0
pandas==2.0.3
matplotlib==3.7.1
```

**Better: use lock file**

```bash
# Capture exact versions (including transitive deps)
pip freeze > requirements-lock.txt

# Or use poetry
poetry export -f requirements.txt --output requirements.txt --with-credentials
```

### Environment file (conda)

```yaml
# environment.yml
name: ml-project
channels:
  - pytorch
  - conda-forge
dependencies:
  - pytorch::pytorch::2.0.1
  - pytorch::torchvision::0.15.2
  - pytorch::pytorch-cuda=11.8
  - python=3.10
  - numpy=1.24.3
  - scipy=1.11.0
  - scikit-learn=1.3.0
  - pandas=2.0.3
  - pip
  - pip:
    - matplotlib==3.7.1
```

### Hardware specification

Report in Methods or supplementary:
- GPU: "8× NVIDIA V100 GPUs (32 GB each)"
- CPU: "2× Intel Xeon Gold 6248 (20 cores each)"
- RAM: "256 GB"
- Storage: "2 TB NVMe SSD"

Example: "Experiments ran on a single GPU (NVIDIA RTX 4090, 24 GB) for ≈14 hours per seed."

### Software versions

Report in supplementary or code repo:
```python
import torch
import torchvision
import numpy as np

print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"cuDNN version: {torch.backends.cudnn.version()}")
print(f"NumPy: {np.__version__}")
```

**In paper:** "Experiments used PyTorch 2.0.1, CUDA 11.8, cuDNN 8.7, on Ubuntu 22.04 LTS."

### Reproducibility seed setting

```python
import random
import numpy as np
import torch

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

# In training loop
for seed in [42, 123, 456, 789, 999]:
    set_seed(seed)
    model = train()
    results.append(evaluate(model))
```

**Note:** Setting `deterministic=True` may reduce performance; it's a trade-off for reproducibility.

## Model cards

**Model card:** Standard documentation of a trained model's capabilities, limitations, and intended use.

### Minimal model card template

```markdown
# Model Card: ResNet-50 for ImageNet Classification

## Model Details
- **Model type:** Convolutional Neural Network (CNN)
- **Architecture:** ResNet-50
- **Pretraining:** ImageNet-1K (2012)
- **Training data:** ImageNet-1K training set (1,281,167 images, 1000 classes)
- **Training time:** 24 hours (8× V100 GPU)
- **Training procedure:** SGD optimizer, learning rate 0.1, batch size 256, 100 epochs with learning rate decay

## Intended use
- Primary use: Image classification on natural images
- Intended audience: ML researchers, practitioners
- Out-of-scope: Medical imaging, satellite imagery (domain shift not evaluated)

## Model performance
- Test accuracy: 0.762 ± 0.003 (5 seeds)
- Per-class F1: 0.681–0.843 (varies by class, see supplementary)

## Limitations
- Accuracy drops on images with heavy augmentations (blur, rotation >45°)
- Biased toward Western image datasets; performance on non-Western data unknown
- Requires 224×224 input; other resolutions may degrade performance

## Dataset biases
- ImageNet-1K has known class imbalance (some classes have 1000 images, others <100)
- Predominantly photographs from Western regions; rare classes from other regions

## Metrics
- Trained with 5 random seeds; results reported as mean ± std
- Evaluated using standard test set (50,000 held-out images)
- Cross-entropy loss

## Ethical considerations
- Used only for non-commercial research in this work
- Potential for misuse in surveillance; users should consider ethical implications
```

### Full model card (5-10 pages, supplement)

Include: use cases, evaluation findings, caveats and recommendations, training data documentation, computational requirements, environmental impact (CO₂ if applicable).

## Data cards

**Data card:** Standard documentation of a dataset's composition, collection method, and characteristics.

### Minimal data card

```markdown
# Data Card: ImageNet-1K

## Dataset overview
- **Name:** ImageNet-1K (Large Scale Visual Recognition Challenge dataset)
- **Version:** 2012
- **Size:** 1,431,167 images (1,281,167 train, 50,000 validation, 100,000 test by convention)
- **Classes:** 1,000 synsets (animal, vehicle, object, scene categories)
- **Source:** Image-net.org

## Collection methodology
- Collection period: 2009–2011
- Source: Flickr API queries on WordNet synsets
- Human annotation: Amazon Mechanical Turk (multiple raters per image)

## Data characteristics
- **Image resolution:** Variable (typically 256–500 px)
- **File format:** JPEG
- **License:** ImageNet terms of use (research only)

## Known biases & limitations
- Geographic bias: Majority images from Western regions
- Class imbalance: Rare classes (<100 images), common classes (~1000)
- Annotation artifacts: Some images mislabeled or ambiguous

## Exclusion criteria
- Adult content not explicitly removed (small number present)
- Duplicate images may exist within class

## Recommended splits
- Training: 50% of data (stratified by class)
- Validation: 25%
- Test: 25%
- Or standard split: train=1.28M, val=50K, test=100K
```

## Code and data availability statements

### Code available on GitHub

```
"Code is available at https://github.com/username/method-name
(commit: abc123def456). Install dependencies with `pip install -r requirements-lock.txt`,
then run `python train.py --config config/default.yaml --seed 42`.
All results are reproducible within ±0.1% accuracy."
```

### Code available on Zenodo (with DOI)

```
"Code and pretrained models are archived on Zenodo
(https://zenodo.org/record/1234567, DOI: 10.5281/zenodo.1234567).
Instructions for training and evaluation are in README.md."
```

### Data available on Hugging Face

```
"Preprocessed datasets are available on Hugging Face Hub at
https://huggingface.co/datasets/username/dataset-name.
Usage: `from datasets import load_dataset; ds = load_dataset('username/dataset-name')`"
```

### Acknowledgment of closed datasets

```
"The proprietary dataset used in this work cannot be shared due to licensing restrictions.
We provide a synthetic version and evaluation protocol in the supplement that researchers
can use to benchmark their methods."
```

### Code available upon reasonable request

```
"Code and trained models are available upon reasonable request to the corresponding author.
Due to [reason: proprietary data / licensing], we cannot make source code public.
Please contact [email] with your affiliation and intended use."
```

## Checklist for Methods section

When writing Methods, ensure you've covered:

- [ ] Section 1: Dataset
  - [ ] Name, source, size (per split)
  - [ ] Preprocessing (fitted on train only)
  - [ ] Augmentation (if used)
  - [ ] Class imbalance handling
  
- [ ] Section 2: Model
  - [ ] Architecture name, citation or link
  - [ ] All hyperparameters (table in supplementary)
  - [ ] Initialization scheme
  
- [ ] Section 3: Training
  - [ ] Optimizer, learning rate schedule
  - [ ] Loss function
  - [ ] Regularization (dropout, weight decay)
  - [ ] Hardware + training time
  
- [ ] Section 4: Evaluation
  - [ ] Metrics (definitions or citation)
  - [ ] Number of seeds
  - [ ] Statistical tests (paired t-test, etc.)
  - [ ] Train/val/test split strategy
  
- [ ] Supplementary: Reproducibility details
  - [ ] Exact package versions (requirements-lock.txt)
  - [ ] Random seeds used [42, 123, 456, 789, 999]
  - [ ] Code + data availability
  - [ ] Ablation details (one per subsection)
  - [ ] Baseline hyperparameters

