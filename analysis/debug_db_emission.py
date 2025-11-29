#!/usr/bin/env python3
"""
Debug script to test database emission with consciousness monitor.
"""

import os
import uuid
from consciousness_monitor_db_v2 import DatabaseConsciousnessWrapper

# Test with debugging
debug_session_id = str(uuid.uuid4())
wrapper = DatabaseConsciousnessWrapper(
    session_id=debug_session_id,
    mode='db-only',
    csv_path='demo_consciousness_data.csv',
    konrad_mode=True,
    sample_rate=256,
    debug=True  # Enable debug mode
)

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

print("Testing database emission with debug session")
print(f"Session ID: {wrapper.session_id}")
print(f"Database sink: {wrapper.db_sink}")
print(f"Monitor emit_windows: {wrapper.monitor.emit_windows}")

# Run for a short time to see what happens
try:
    # Manually test the emission logic
    if wrapper.monitor.emit_windows:
        print("✅ Window emission is enabled")
        
        # Test database sink directly
        from datetime import datetime, timezone
        import json
        
        test_data = [{
            'session_id': str(wrapper.session_id),
            'ts_start': datetime.now(timezone.utc),
            'ts_end': datetime.now(timezone.utc),
            'alpha_rel': 25.0,
            'beta_rel': 20.0,
            'theta_rel': 15.0,
            'delta_rel': 35.0,
            'gamma_rel': 5.0,
            'entropy': 2.1,
            'artifact_flags': {},
            'features': {'test': True}
        }]
        
        print("Testing direct database write...")
        wrapper.db_sink.on_windows(test_data)
        print("✅ Direct database write successful!")
        
    else:
        print("❌ Window emission is NOT enabled")
        
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()