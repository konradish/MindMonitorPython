# Consciousness Monitor - Modular Architecture

## Overview

The consciousness monitor has been transformed from a monolithic 2527-line script into a clean, maintainable modular Python package. This document describes the architecture, design decisions, and development workflows.

## Package Structure

```
consciousness_monitor/
├── __init__.py                      # Package initialization
├── __main__.py                      # CLI entry point (python -m consciousness_monitor)
├── main.py                          # Main orchestrator (540 lines)
├── config/                          # Configuration management
│   ├── __init__.py                  # Config package initialization
│   ├── rules.py                     # Detection rule management
│   ├── thresholds.py               # Artifact threshold management
│   ├── settings.py                 # General settings management
│   ├── detection_rules.json        # Therapeutic pattern rules
│   ├── sub_states.json             # Sub-state definitions
│   ├── artifact_thresholds.json    # Artifact detection thresholds
│   └── konrad_personalized.json    # User-specific settings
├── data/                           # Data processing and parsing
│   ├── __init__.py                 # Data package initialization
│   ├── models.py                   # Data structures (BandPower, AnalysisResult)
│   ├── parsers.py                  # EEG data parsing and format detection
│   └── processors.py              # Signal processing (FFT, filtering, band powers)
├── detection/                      # Pattern detection and analysis
│   ├── __init__.py                 # Detection package initialization
│   ├── engine.py                   # Core detection engine
│   ├── patterns.py                 # Therapeutic pattern analysis
│   ├── artifacts.py                # Artifact filtering
│   └── sub_states.py              # Sub-state detection
├── ui/                            # User interface and display
│   ├── __init__.py                # UI package initialization
│   ├── display.py                 # Console display formatting
│   └── commands.py                # Interactive command handling
└── utils/                         # Utilities and helpers
    ├── __init__.py                # Utils package initialization
    ├── math_helpers.py            # Mathematical utilities
    └── validation.py              # Data validation
```

## Design Principles

### 1. Single Responsibility Principle
Each module has a focused, single responsibility:
- **config/**: Manages all configuration aspects (rules, thresholds, settings)
- **data/**: Handles data structures, parsing, and signal processing
- **detection/**: Focuses on pattern detection and state analysis
- **ui/**: Manages all user interface and display concerns
- **utils/**: Provides reusable utilities and helpers

### 2. Separation of Concerns
Clear boundaries between different aspects of the system:
- Data processing is isolated from pattern detection
- Configuration is separate from business logic
- User interface is decoupled from core functionality
- Mathematical operations are centralized in utilities

### 3. Dependency Inversion
High-level modules don't depend on low-level modules. Both depend on abstractions:
- Main orchestrator depends on abstract interfaces
- Detection engine is configurable through dependency injection
- Data parsers are pluggable based on format detection

### 4. Open/Closed Principle
The system is open for extension but closed for modification:
- New detection patterns can be added without changing core logic
- New data formats can be supported by adding parsers
- New therapeutic rules can be loaded externally

## Module Responsibilities

### main.py - Core Orchestrator
- **Primary Role**: Coordinates all system components
- **Key Functions**: 
  - Real-time EEG analysis workflow
  - File-based analysis for recordings
  - Command-line interface handling
  - Component initialization and dependency injection
- **Size**: 540 lines (down from 2527 in monolithic version)

### config/ - Configuration Management
- **rules.py**: Manages detection rule loading, validation, and tuning
- **thresholds.py**: Handles artifact detection threshold configuration
- **settings.py**: General application settings and data column mapping
- **JSON files**: External configuration that can be modified without code changes

### data/ - Data Processing Pipeline
- **models.py**: Core data structures (BandPower, AnalysisResult, SessionEvent)
- **parsers.py**: EEG data format detection and parsing (Mind Monitor, Muse Player, generic)
- **processors.py**: Signal processing (FFT, band power calculation, multichannel averaging)

### detection/ - Pattern Recognition Engine
- **engine.py**: Core detection logic, rule evaluation, and state determination
- **patterns.py**: Therapeutic pattern analysis (IFS parts work, meditation states)
- **artifacts.py**: Artifact detection and filtering (multiband spikes, impossible combinations)
- **sub_states.py**: Hierarchical state detection (flow sub-types, jhana stages)

### ui/ - User Interface Layer
- **display.py**: Console output formatting, real-time display updates
- **commands.py**: Interactive command handling, hotkey processing

### utils/ - Shared Utilities
- **math_helpers.py**: Mathematical operations (dB conversion, band normalization, FFT helpers)
- **validation.py**: Data validation and error checking

## Data Flow Architecture

```
1. Raw EEG Data Input
   ├── CSV File (Mind Monitor format)
   ├── Live OSC Stream 
   └── Muse Player format

2. Data Parsing (data/parsers.py)
   ├── Format Detection
   ├── Channel Extraction
   └── Timestamp Processing

3. Signal Processing (data/processors.py)
   ├── DC Removal
   ├── FFT Analysis
   ├── Band Power Calculation
   └── Multi-channel Averaging

4. Pattern Detection (detection/engine.py)
   ├── Artifact Filtering
   ├── Rule Evaluation
   ├── State Detection
   └── Sub-state Analysis

5. Therapeutic Analysis (detection/patterns.py)
   ├── Parts Work Detection
   ├── Meditation Pattern Analysis
   ├── Nervous System Assessment
   └── Unusual Pattern Recognition

6. Output Formatting (ui/display.py)
   ├── Real-time Display
   ├── State Visualization
   ├── Insight Generation
   └── Interactive Commands
```

## Configuration Architecture

### External Configuration Files
- **detection_rules.json**: Therapeutic pattern detection rules
- **sub_states.json**: Hierarchical sub-state definitions
- **artifact_thresholds.json**: Artifact detection parameters
- **konrad_personalized.json**: User-specific customizations

### Configuration Management
- Centralized in `config/` package
- JSON-based for easy modification
- Runtime rule tuning via CLI
- Version control for rule changes
- Backwards compatibility support

### Rule System Architecture
```python
# Example rule structure
{
    "jhana": {
        "priority": 2,
        "conditions": {
            "alpha_min": 80,
            "beta_max": 15
        },
        "emoji": "🧘",
        "insights": ["Deep meditative absorption state"]
    }
}
```

## Extension Points

### Adding New Detection Patterns
1. Add rule definition to `detection_rules.json`
2. Implement specialized conditions in `detection/engine.py` if needed
3. Add therapeutic insights in `detection/patterns.py`

### Supporting New Data Formats
1. Add format detection logic to `data/parsers.py`
2. Implement parser for new format
3. Update data models if needed

### Adding New User Interface Elements
1. Extend display formatting in `ui/display.py`
2. Add command handlers in `ui/commands.py`
3. Update main orchestrator for new UI features

## Testing Strategy

### Unit Testing
Each module can be tested independently:
- **Data processing**: Test signal processing algorithms with known inputs
- **Detection engine**: Test rule evaluation with synthetic band powers
- **Pattern analysis**: Test therapeutic pattern detection with mock data
- **Configuration**: Test rule loading and validation

### Integration Testing
- Test data flow between modules
- Verify configuration changes affect behavior correctly
- Test CLI interfaces and command handling

### End-to-End Testing
- Process real EEG recordings
- Verify therapeutic pattern detection accuracy
- Test real-time processing performance

## Performance Considerations

### Memory Efficiency
- Modular design reduces memory footprint
- Clear separation allows garbage collection of unused components
- Data structures designed for streaming processing

### Processing Speed
- Signal processing optimized with NumPy
- Rule evaluation uses efficient data structures
- Display updates are throttled to prevent UI lag

### Scalability
- Modular architecture supports horizontal scaling
- Configuration-driven rules enable rapid deployment
- Clean interfaces support distributed processing

## Migration and Compatibility

### Backward Compatibility
- Original CLI interface preserved
- All existing functionality maintained
- Legacy configuration formats supported

### Migration Path
```bash
# Old monolithic approach (still works)
uv run python consciousness_monitor.py --konrad-mode

# New modular approach (recommended)
uv run python -m consciousness_monitor --konrad-mode
```

### Future-Proofing
- Clear module boundaries support major changes
- Configuration externalization enables rapid adaptation
- Plugin architecture ready for community extensions

## Development Workflow

### Adding New Features
1. Identify appropriate module based on responsibility
2. Implement feature with unit tests
3. Update configuration if needed
4. Add integration tests
5. Update documentation

### Debugging and Maintenance
1. Use debug mode for rule evaluation tracing
2. Module isolation simplifies bug hunting  
3. Configuration changes don't require code deployment
4. Clear logging and error handling

### Code Organization Guidelines
- Keep modules under 300 lines
- Maintain clear interfaces between modules
- Use type hints for better maintainability
- Follow consistent naming conventions
- Document public APIs thoroughly

## Benefits Achieved

### Maintainability
- 78% reduction in main file size (2527 → 540 lines)
- Clear separation of concerns
- Focused, testable modules
- Consistent code organization

### Extensibility
- Easy to add new detection patterns
- Support for new data formats
- Pluggable user interface components
- Configuration-driven behavior

### Reliability
- Better error isolation
- Independent module testing
- Clear data flow paths
- Robust error handling

### Performance
- Optimized memory usage
- Efficient signal processing
- Minimal interdependencies
- Lazy loading of components

This modular architecture provides a solid foundation for future development while maintaining all existing functionality and improving system reliability.