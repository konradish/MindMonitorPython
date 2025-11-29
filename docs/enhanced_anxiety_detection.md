# Enhanced Anxiety Detection Implementation Plan

## Problem Statement
Current consciousness monitor missed panic/anxiety state during distressing thoughts, showing "RELAXED" with 72% alpha instead. Need enhanced detection methods for internal distress states that don't manifest as traditional EEG band changes.

## Implementation Goals

### Phase 1: Core Mathematical Features ✅
- [x] Create plan folder and documentation
- [x] Implement spectral entropy calculation (✅ 21/21 tests pass)
- [x] Implement high-gamma (30-100Hz) micro-burst detection (✅ 19/19 tests pass)  
- [x] Implement cross-channel coherence analysis (✅ 23/23 tests pass)

### Phase 2: Integration & Detection Rules
- [ ] **CURRENT**: Integrate new methods into consciousness monitor data pipeline
- [ ] Add spectral centroid shift tracking
- [ ] Create unit tests for signal analysis functions

### Phase 3: Integration & Detection Rules
- [ ] Integrate new features into consciousness monitor data pipeline
- [ ] Create anxiety/distress detection rules using new features
- [ ] Add configuration for sensitivity thresholds
- [ ] Test on known anxiety episodes

### Phase 4: Validation & Refinement
- [ ] Validate against spectrogram patterns
- [ ] Fine-tune detection thresholds
- [ ] Add real-time visualization of new features
- [ ] Document usage and interpretation

## Technical Approach

### 1. Spectral Entropy (Frequency Chaos Measure)
```python
def calculate_spectral_entropy(power_spectrum):
    """
    Calculate entropy of frequency distribution
    Higher entropy = more chaotic/anxious patterns
    """
    # Normalize power spectrum to probability distribution
    # Calculate Shannon entropy: -sum(p * log(p))
```

### 2. High-Gamma Micro-bursts (30-100Hz Activity)
```python
def detect_gamma_bursts(eeg_window, threshold_db=2.0):
    """
    Detect sudden increases in high-gamma activity
    Often associated with anxiety/hypervigilance
    """
    # Extract 30-100Hz band
    # Calculate dB changes over short windows
    # Flag significant spikes
```

### 3. Cross-Channel Coherence
```python
def calculate_coherence(channel1, channel2, freq_bands):
    """
    Measure synchronization between brain regions
    Anxiety often reduces coherence
    """
    # Cross-spectral density analysis
    # Phase-locking value calculation
```

## File Structure
```
consciousness_monitor/
├── analysis/
│   ├── anxiety_detection.py     # New anxiety-specific features
│   ├── spectral_features.py     # Spectral entropy, instability
│   └── coherence_analysis.py    # Cross-channel analysis
├── config/
│   └── anxiety_thresholds.json  # New detection thresholds
└── tests/
    ├── test_anxiety_detection.py
    ├── test_spectral_features.py
    └── test_coherence_analysis.py
```

## Success Criteria
1. **Unit Tests Pass**: All new mathematical functions validated
2. **Detection Improvement**: Catch anxiety states missed by current approach
3. **Low False Positives**: Don't over-detect during genuine relaxation
4. **Real-time Performance**: <100ms processing time per window
5. **Configurable**: Thresholds adjustable without code changes

## Current Status: Phase 1 - Core Mathematical Features
**Next Step**: Implement spectral entropy calculation with unit tests

---
*Updated: 2025-07-30*
*Version: 1.0*