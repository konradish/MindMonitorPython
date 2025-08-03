"""Analysis modules for real-time and batch processing."""

# Import available modules
try:
    from .spectral_features import (
        calculate_spectral_entropy,
        calculate_frequency_peak_instability,
        calculate_spectral_centroid,
        calculate_spectral_rolloff
    )
    from .gamma_detection import (
        extract_high_gamma_band,
        calculate_gamma_power_envelope,
        detect_gamma_bursts,
        analyze_gamma_burst_pattern
    )
    from .coherence_analysis import (
        calculate_cross_spectrum,
        calculate_coherence,
        calculate_phase_locking_value,
        analyze_multi_channel_coherence,
        detect_coherence_anomalies
    )
    __all__ = [
        "calculate_spectral_entropy",
        "calculate_frequency_peak_instability", 
        "calculate_spectral_centroid",
        "calculate_spectral_rolloff",
        "extract_high_gamma_band",
        "calculate_gamma_power_envelope",
        "detect_gamma_bursts",
        "analyze_gamma_burst_pattern",
        "calculate_cross_spectrum",
        "calculate_coherence",
        "calculate_phase_locking_value",
        "analyze_multi_channel_coherence",
        "detect_coherence_anomalies"
    ]
except ImportError:
    __all__ = []