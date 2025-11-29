#!/usr/bin/env python3
"""
Band Power Math Validation using meditation.csv

This script tests the band power calculations against the meditation data
to ensure alpha dominance is correctly detected during meditation.
"""

import numpy as np
import pandas as pd
from consciousness_monitor.data.parsers import DataParser
from consciousness_monitor.data.processors import SignalProcessor
import os

def test_band_power_accuracy(csv_file="meditation.csv", num_samples=1000):
    """Test band power calculations on meditation.csv data"""
    
    if not os.path.exists(csv_file):
        print(f"❌ File {csv_file} not found")
        return
    
    print(f"🧠 Testing band power accuracy on {csv_file}")
    print("=" * 60)
    
    # Initialize components
    parser = DataParser()
    
    try:
        # Get sample rate from the data
        sample_rate = parser.detect_sample_rate(csv_file)
        print(f"📊 Detected sample rate: {sample_rate:.1f} Hz")
        
        # Initialize processor with detected rate
        processor = SignalProcessor(sample_rate)
        
        # Get latest data (limiting samples for testing)
        latest_data, format_type = parser.get_latest_data(csv_file, num_samples)
        
        if latest_data is None:
            print("❌ No data could be loaded")
            return
            
        print(f"📊 Loaded {len(latest_data)} samples")
        print(f"📊 Data format: {format_type}")
        
        # Extract EEG channels
        channels = parser.extract_eeg_channels(latest_data, format_type)
        
        if not channels:
            print("❌ No EEG channels found")
            return
            
        print(f"📊 Found channels: {list(channels.keys())}")
        
        # Test each channel
        channel_results = {}
        
        for channel_name, channel_data in channels.items():
            print(f"\n🧠 Analyzing {channel_name}:")
            print("-" * 30)
            
            if len(channel_data) < 100:
                print(f"⚠️ Not enough data ({len(channel_data)} samples)")
                continue
                
            # Raw data stats
            print(f"Raw data: {len(channel_data)} samples")
            print(f"  Range: {np.min(channel_data):.1f} to {np.max(channel_data):.1f} µV")
            print(f"  Mean: {np.mean(channel_data):.1f} µV")
            print(f"  Std: {np.std(channel_data):.1f} µV")
            
            try:
                # Test preprocessing
                processed = processor.preprocess_signal(channel_data)
                print(f"Processed: mean={np.mean(processed):.3f}, std={np.std(processed):.1f}")
                
                # Calculate band powers
                band_power = processor.calculate_all_band_powers(channel_data)
                
                # Get percentages
                percentages = band_power.as_percentages()
                
                print("Band Powers (absolute):")
                for band, power in band_power.as_dict().items():
                    print(f"  {band:>5}: {power:>8.6f}")
                    
                print("Band Powers (percentages):")
                total_pct = 0
                for band, pct in percentages.items():
                    print(f"  {band:>5}: {pct:>5.1f}%")
                    total_pct += pct
                
                print(f"  Total: {total_pct:>5.1f}%")
                
                # Store results
                channel_results[channel_name] = {
                    'percentages': percentages,
                    'raw_stats': {
                        'mean': np.mean(channel_data),
                        'std': np.std(channel_data),
                        'range': (np.min(channel_data), np.max(channel_data))
                    }
                }
                
                # Analyze for meditation characteristics
                alpha_pct = percentages.get('alpha', 0)
                beta_pct = percentages.get('beta', 0)
                delta_pct = percentages.get('delta', 0)
                theta_pct = percentages.get('theta', 0)
                
                print(f"\n🧘 Meditation Analysis:")
                if alpha_pct > 40:
                    print(f"  ✅ High alpha ({alpha_pct:.1f}%) - Good for meditation")
                else:
                    print(f"  ⚠️ Low alpha ({alpha_pct:.1f}%) - May not be meditative")
                    
                if beta_pct < 25:
                    print(f"  ✅ Low beta ({beta_pct:.1f}%) - Low stress/tension")
                else:
                    print(f"  ⚠️ High beta ({beta_pct:.1f}%) - May indicate stress")
                    
                # Check for artifacts
                if delta_pct > 60:
                    print(f"  ⚠️ Very high delta ({delta_pct:.1f}%) - Possible artifact")
                if any(pct > 90 for pct in percentages.values()):
                    print(f"  ⚠️ Single band dominance - Possible processing error")
                    
            except Exception as e:
                print(f"  ❌ Error processing {channel_name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Multi-channel analysis
        print(f"\n🔍 Multi-Channel Summary:")
        print("=" * 40)
        
        if len(channel_results) > 1:
            # Average across channels
            all_alphas = [r['percentages'].get('alpha', 0) for r in channel_results.values()]
            all_betas = [r['percentages'].get('beta', 0) for r in channel_results.values()]
            
            avg_alpha = np.mean(all_alphas)
            avg_beta = np.mean(all_betas)
            
            print(f"Average Alpha: {avg_alpha:.1f}% (range: {min(all_alphas):.1f}-{max(all_alphas):.1f}%)")
            print(f"Average Beta:  {avg_beta:.1f}% (range: {min(all_betas):.1f}-{max(all_betas):.1f}%)")
            
            # Overall meditation assessment
            print(f"\n🧘 Overall Meditation Assessment:")
            if avg_alpha > 40 and avg_beta < 25:
                print("  ✅ Excellent meditation state - High alpha, low beta")
            elif avg_alpha > 35:
                print("  ✅ Good meditation state - Moderate alpha")
            elif avg_alpha > 25:
                print("  ⚠️ Light meditation state - Some alpha activity")
            else:
                print("  ❌ Not in meditative state - Low alpha activity")
                
        # Test specific consciousness detection
        print(f"\n🤖 Consciousness Detection Test:")
        print("-" * 40)
        
        if channel_results:
            # Use first channel for detection test
            first_channel = list(channel_results.keys())[0]
            percentages = channel_results[first_channel]['percentages']
            
            # Test against Konrad's relaxed threshold (40% alpha)
            if percentages.get('alpha', 0) >= 40:
                print("  ✅ Would detect as RELAXED (Konrad's threshold)")
            else:
                print("  ❌ Would NOT detect as RELAXED")
                
            # Test therapeutic patterns
            alpha = percentages.get('alpha', 0)
            beta = percentages.get('beta', 0)
            delta = percentages.get('delta', 0)
            theta = percentages.get('theta', 0)
            
            if alpha >= 80 and beta < 15:
                print("  ✅ Would detect as JHANA/TRANSCENDENT")
            elif alpha >= 75 and beta < 15 and delta < 20:
                print("  ✅ Would detect as HOPEFUL PART ACTIVE")
            elif theta >= 30 and alpha < 20:
                print("  ✅ Would detect as MEDITATIVE")
            else:
                print("  ℹ️ Would detect as general state based on band ratios")
        
        return channel_results
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = test_band_power_accuracy()