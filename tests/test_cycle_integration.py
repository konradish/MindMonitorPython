#!/usr/bin/env python3
"""
Test the integrated anxiety-regulation cycle detection system.
"""

import subprocess
import time
import os

def test_cycle_detection_help():
    """Test that cycle detection argument is available"""
    print("🧪 Testing cycle detection help...")
    
    result = subprocess.run([
        "uv", "run", "python", "consciousness_monitor.py", "--help"
    ], capture_output=True, text=True)
    
    if "--cycle-detection" in result.stdout:
        print("✅ Cycle detection argument available")
        return True
    else:
        print("❌ Cycle detection argument not found")
        return False

def test_cycle_detection_startup():
    """Test cycle detection system startup"""
    print("🧪 Testing cycle detection startup...")
    
    # Run with cycle detection for a few seconds
    process = subprocess.Popen([
        "uv", "run", "python", "consciousness_monitor.py", 
        "--konrad-mode", "--cycle-detection", "--sample-rate", "88"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Let it run for 3 seconds
    time.sleep(3)
    process.terminate()
    
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
    
    # Check for successful initialization
    success_indicators = [
        "AnxietyCycleDetector initialized",
        "🔄 Anxiety-regulation cycle detection: ENABLED",
        "Using override sample rate: 88"
    ]
    
    found_indicators = []
    for indicator in success_indicators:
        if indicator in stdout or indicator in stderr:
            found_indicators.append(indicator)
    
    if found_indicators:
        print(f"✅ Cycle detection started successfully")
        print(f"   Found: {found_indicators}")
        return True
    else:
        print("❌ Cycle detection startup failed")
        print(f"STDOUT: {stdout[:500]}...")
        print(f"STDERR: {stderr[:500]}...")
        return False

def test_anxiety_dataset_analysis():
    """Test that we can analyze anxiety datasets"""
    print("🧪 Testing anxiety dataset analysis...")
    
    if os.path.exists("anxiety.csv") and os.path.exists("anxiety2.csv"):
        result = subprocess.run([
            "uv", "run", "python", "analyze_anxiety_datasets.py"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and "Personalized Konrad Thresholds" in result.stdout:
            print("✅ Anxiety dataset analysis working")
            return True
        else:
            print("❌ Anxiety dataset analysis failed")
            print(f"Error: {result.stderr}")
            return False
    else:
        print("⚠️ Anxiety datasets not found - skipping analysis test")
        return True

def test_cycle_detector_standalone():
    """Test the standalone cycle detector"""
    print("🧪 Testing standalone cycle detector...")
    
    result = subprocess.run([
        "uv", "run", "python", "anxiety_cycle_detector.py"
    ], capture_output=True, text=True, timeout=10)
    
    if result.returncode == 0 and "AnxietyCycleDetector initialized" in result.stdout:
        print("✅ Standalone cycle detector working")
        return True
    else:
        print("❌ Standalone cycle detector failed")
        print(f"Error: {result.stderr}")
        return False

def main():
    """Run all tests"""
    print("🔄 ANXIETY-REGULATION CYCLE DETECTION - INTEGRATION TESTS")
    print("=" * 65)
    
    tests = [
        ("Help system", test_cycle_detection_help),
        ("Cycle detector standalone", test_cycle_detector_standalone),
        ("Dataset analysis", test_anxiety_dataset_analysis),
        ("Integrated startup", test_cycle_detection_startup)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n📊 TEST RESULTS:")
    print("=" * 30)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED!")
        print("\nThe anxiety-regulation cycle detection system is ready!")
        print("\nTo use:")
        print("uv run python consciousness_monitor.py --konrad-mode --cycle-detection --sample-rate 88")
        print("\nThis will provide real-time detection of:")
        print("- Cycle initiation (anxiety rising)")
        print("- Peak activation (maximum stress)")  
        print("- Recovery phases (regulation returning)")
        print("- Complete anxiety-regulation cycles")
    else:
        print(f"\n⚠️ {len(results) - passed} tests failed - system may need debugging")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()