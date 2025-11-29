#!/usr/bin/env python3
"""
Analyze anxiety training datasets to understand Konrad's anxiety-regulation patterns.

This script analyzes anxiety.csv and anxiety2.csv to extract:
1. Baseline characteristics
2. Anxiety escalation patterns  
3. Peak activation signatures
4. Recovery/regulation patterns
5. Complete cycle structures
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from consciousness_monitor.data.parsers import DataParser
from consciousness_monitor.data.processors import SignalProcessor
import os

def analyze_anxiety_dataset(csv_file, title=""):
    """Analyze a single anxiety dataset for cycle patterns"""
    
    if not os.path.exists(csv_file):
        print(f"❌ File {csv_file} not found")
        return None
    
    print(f"\n{'='*60}")
    print(f"🔍 Analyzing {csv_file} - {title}")
    print(f"{'='*60}")
    
    # Initialize components with corrected sample rate
    parser = DataParser()
    sample_rate = parser.detect_sample_rate(csv_file)
    if sample_rate == 256:  # Fallback wasn't updated, use manual detection
        sample_rate = 88  # Based on our previous analysis
    
    processor = SignalProcessor(sample_rate)
    
    print(f"📊 Using sample rate: {sample_rate}Hz")
    
    # Load data (use large window to get all data)
    latest_data, format_type = parser.get_latest_data(csv_file, 50000)  # Load lots of data
    
    if latest_data is None:
        print("❌ No data could be loaded")
        return None
    
    print(f"📊 Loaded {len(latest_data)} samples")
    print(f"📊 Data format: {format_type}")
    
    # Extract EEG channels
    channels = parser.extract_eeg_channels(latest_data, format_type)
    
    if not channels:
        print("❌ No EEG channels found")
        return None
    
    print(f"📊 Found channels: {list(channels.keys())}")
    
    # Calculate session-wide band power time series
    window_size = int(sample_rate * 0.75)  # 0.75 second windows
    step_size = int(sample_rate * 0.5)     # 0.5 second steps (50% overlap)
    
    time_series = []
    timestamps = []
    
    # Use average across all channels for robustness
    channel_data_list = list(channels.values())
    avg_channel_data = np.mean(channel_data_list, axis=0)
    
    print(f"📊 Processing {len(avg_channel_data)} samples in {window_size}-sample windows...")
    
    for i in range(0, len(avg_channel_data) - window_size, step_size):
        window = avg_channel_data[i:i + window_size]
        
        try:
            band_power = processor.calculate_all_band_powers(window)
            percentages = band_power.as_percentages()
            
            # Store time series data
            time_point = {
                'time': i / sample_rate,  # Time in seconds
                'delta': percentages['delta'],
                'theta': percentages['theta'], 
                'alpha': percentages['alpha'],
                'beta': percentages['beta'],
                'gamma': percentages['gamma'],
                'anxiety_index': percentages['beta'] / max(percentages['alpha'], 5),  # Beta/Alpha ratio
                'regulation_index': percentages['alpha'] / (percentages['beta'] + percentages['gamma'] + 1),
                'arousal_index': percentages['beta'] + percentages['gamma'],
                'calm_index': percentages['alpha'] + percentages['theta']
            }
            
            time_series.append(time_point)
            timestamps.append(time_point['time'])
            
        except Exception as e:
            print(f"⚠️ Error processing window at {i}: {e}")
            continue
    
    if not time_series:
        print("❌ No time series data generated")
        return None
    
    # Convert to arrays for analysis
    data = {key: np.array([tp[key] for tp in time_series]) for key in time_series[0].keys()}
    
    print(f"📊 Generated {len(time_series)} time points over {timestamps[-1]:.1f} seconds")
    
    # Session-wide analysis
    print(f"\n📈 Session Statistics:")
    print(f"Duration: {timestamps[-1]:.1f} seconds ({timestamps[-1]/60:.1f} minutes)")
    
    for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
        values = data[band]
        print(f"{band:>5}: mean={values.mean():>5.1f}% ± {values.std():>4.1f}% | "
              f"range={values.min():>5.1f}-{values.max():>5.1f}%")
    
    # Anxiety metrics
    print(f"\n🧠 Anxiety-Regulation Metrics:")
    print(f"Anxiety Index (β/α):     mean={data['anxiety_index'].mean():.2f} ± {data['anxiety_index'].std():.2f}")
    print(f"Regulation Index:        mean={data['regulation_index'].mean():.2f} ± {data['regulation_index'].std():.2f}")  
    print(f"Arousal Index (β+γ):     mean={data['arousal_index'].mean():.1f}% ± {data['arousal_index'].std():.1f}%")
    print(f"Calm Index (α+θ):        mean={data['calm_index'].mean():.1f}% ± {data['calm_index'].std():.1f}%")
    
    # Detect potential anxiety cycles
    print(f"\n🔄 Cycle Detection Analysis:")
    
    # Use anxiety index (beta/alpha ratio) as primary cycle indicator
    anxiety_signal = data['anxiety_index']
    baseline = np.median(anxiety_signal)  # Use median as robust baseline
    mad = 1.4826 * np.median(np.abs(anxiety_signal - baseline))  # Median Absolute Deviation
    
    print(f"Baseline anxiety index: {baseline:.2f}")
    print(f"MAD (variability): {mad:.2f}")
    
    # Define thresholds
    initiation_threshold = baseline + 2 * mad    # 2 MAD above baseline
    peak_threshold = baseline + 3 * mad          # 3 MAD above baseline  
    recovery_threshold = baseline + 1 * mad      # 1 MAD above baseline
    
    print(f"Initiation threshold: {initiation_threshold:.2f}")
    print(f"Peak threshold: {peak_threshold:.2f}")
    print(f"Recovery threshold: {recovery_threshold:.2f}")
    
    # Simple cycle detection
    above_initiation = anxiety_signal > initiation_threshold
    above_peak = anxiety_signal > peak_threshold
    
    initiation_points = np.where(np.diff(above_initiation.astype(int)) == 1)[0]  # Rising edge
    peak_points = np.where(above_peak)[0]
    recovery_points = np.where(np.diff(above_initiation.astype(int)) == -1)[0]  # Falling edge
    
    print(f"Potential cycle initiations: {len(initiation_points)}")
    print(f"Peak activation periods: {len(peak_points)} time points")
    print(f"Recovery points: {len(recovery_points)}")
    
    # Calculate key percentiles for personalization
    percentiles = {
        'p10': np.percentile(anxiety_signal, 10),
        'p25': np.percentile(anxiety_signal, 25), 
        'p50': np.percentile(anxiety_signal, 50),
        'p75': np.percentile(anxiety_signal, 75),
        'p90': np.percentile(anxiety_signal, 90),
        'p95': np.percentile(anxiety_signal, 95),
        'p99': np.percentile(anxiety_signal, 99)
    }
    
    print(f"\n📊 Anxiety Index Percentiles:")
    for p, val in percentiles.items():
        print(f"{p}: {val:.2f}")
    
    # Return analysis results
    return {
        'file': csv_file,
        'title': title,
        'duration': timestamps[-1],
        'time_series': data,
        'timestamps': np.array(timestamps),
        'baseline': baseline,
        'mad': mad,
        'thresholds': {
            'initiation': initiation_threshold,
            'peak': peak_threshold, 
            'recovery': recovery_threshold
        },
        'percentiles': percentiles,
        'cycles': {
            'initiations': initiation_points,
            'peaks': peak_points,
            'recoveries': recovery_points
        },
        'session_stats': {
            'mean_alpha': data['alpha'].mean(),
            'mean_beta': data['beta'].mean(),
            'mean_anxiety_index': data['anxiety_index'].mean(),
            'max_anxiety_index': data['anxiety_index'].max(),
            'regulation_episodes': len(recovery_points)
        }
    }

def compare_anxiety_sessions(results1, results2):
    """Compare two anxiety sessions to understand pattern differences"""
    
    print(f"\n{'='*60}")
    print(f"🔍 COMPARATIVE ANALYSIS")
    print(f"{'='*60}")
    
    print(f"Session 1: {results1['title']} ({results1['duration']:.1f}s)")
    print(f"Session 2: {results2['title']} ({results2['duration']:.1f}s)")
    
    print(f"\n📊 Baseline Comparison:")
    print(f"{'Metric':<20} {'Session 1':<15} {'Session 2':<15} {'Difference':<15}")
    print(f"{'-'*65}")
    
    metrics = [
        ('Baseline Anxiety', results1['baseline'], results2['baseline']),
        ('Peak Anxiety', results1['session_stats']['max_anxiety_index'], 
         results2['session_stats']['max_anxiety_index']),
        ('Mean Alpha %', results1['session_stats']['mean_alpha'], 
         results2['session_stats']['mean_alpha']),
        ('Mean Beta %', results1['session_stats']['mean_beta'], 
         results2['session_stats']['mean_beta']),
        ('Regulation Episodes', results1['session_stats']['regulation_episodes'], 
         results2['session_stats']['regulation_episodes'])
    ]
    
    for metric_name, val1, val2 in metrics:
        diff = val2 - val1
        print(f"{metric_name:<20} {val1:<15.2f} {val2:<15.2f} {diff:<15.2f}")
    
    # Determine which session was more intense
    intensity_score1 = results1['session_stats']['max_anxiety_index']
    intensity_score2 = results2['session_stats']['max_anxiety_index']
    
    print(f"\n🎯 Session Characterization:")
    if intensity_score1 > intensity_score2:
        print(f"Session 1 ({results1['title']}) was more intense (peak: {intensity_score1:.2f} vs {intensity_score2:.2f})")
        high_intensity = results1
        moderate_intensity = results2
    else:
        print(f"Session 2 ({results2['title']}) was more intense (peak: {intensity_score2:.2f} vs {intensity_score1:.2f})")
        high_intensity = results2
        moderate_intensity = results1
    
    # Generate personalized thresholds
    print(f"\n🎯 Personalized Konrad Thresholds:")
    
    # Use moderate session baseline, high session peak patterns
    personal_baseline = moderate_intensity['baseline']
    personal_peak_range = high_intensity['percentiles']['p95']
    
    personal_thresholds = {
        'baseline': personal_baseline,
        'concern': personal_baseline + moderate_intensity['mad'],
        'escalation': personal_baseline + 2 * moderate_intensity['mad'], 
        'peak': personal_baseline + 3 * moderate_intensity['mad'],
        'crisis': high_intensity['percentiles']['p99']
    }
    
    print(f"Baseline (resting): {personal_thresholds['baseline']:.2f}")
    print(f"Concern (elevated): {personal_thresholds['concern']:.2f}")
    print(f"Escalation (cycle start): {personal_thresholds['escalation']:.2f}")
    print(f"Peak (maximum activation): {personal_thresholds['peak']:.2f}")
    print(f"Crisis (intervention needed): {personal_thresholds['crisis']:.2f}")
    
    return personal_thresholds, high_intensity, moderate_intensity

def main():
    """Main analysis function"""
    
    print("🧠 ANXIETY-REGULATION CYCLE ANALYSIS")
    print("Analyzing Konrad's personal anxiety patterns from training data")
    
    # Analyze both datasets
    anxiety1_results = analyze_anxiety_dataset("anxiety.csv", "Moderate Activation Session")
    anxiety2_results = analyze_anxiety_dataset("anxiety2.csv", "ALPHA Spiral Session")
    
    if anxiety1_results is None or anxiety2_results is None:
        print("❌ Could not analyze one or both datasets")
        return
    
    # Compare sessions and generate personalized thresholds
    personal_thresholds, high_session, moderate_session = compare_anxiety_sessions(
        anxiety1_results, anxiety2_results)
    
    print(f"\n✅ Analysis Complete!")
    print(f"📊 Ready to implement personalized cycle detection")
    
    return {
        'personal_thresholds': personal_thresholds,
        'high_intensity_session': high_session,
        'moderate_session': moderate_session,
        'anxiety1_results': anxiety1_results,
        'anxiety2_results': anxiety2_results
    }

if __name__ == "__main__":
    analysis_results = main()