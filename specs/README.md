# Boundary Specifications

This folder contains architectural boundary documentation for the MindMonitorPython codebase.

## Specs-First Workflow

**Always modify specs before implementing changes:**

1. Add/edit row in `boundary_specs.csv` with `[PROVISIONAL]` in Notes
2. Implement the change in code
3. Add tests
4. Remove `[PROVISIONAL]` when complete

See `CLAUDE.md` → Development Workflow for details.

## Files

- `boundary_specs.csv` - Complete component inventory with boundaries, side effects, and tests

## CSV Columns

| Column | Description |
|--------|-------------|
| Component | Name of the component (class/module/script) |
| File Path | Relative path from project root |
| Type | class, module, script, dataclass, json, yaml, sql, test, shell |
| Layer | orchestrator, data, detection, config, ui, sink, utils, analysis, network, mcp, infra, tools, tests |
| Responsibility | What the component does |
| Dependencies | Key imports and dependencies |
| Side Effects | DB, Network, File, UI, Audio, Threading, Clipboard, Process, None |
| Boundary Type | Internal API, External API, Data Contract, Configuration API, Output API, Input API, External Network API, Infrastructure |
| Related Tests | Test files that cover this component |
| Notes | Additional context |

## Key Boundaries

### External APIs (require careful change management)
- **eeg_mcp_server.py** - Claude Desktop integration (MCP tools)
- **osc_receiver.py** - Mind Monitor UDP input (OSC protocol)
- **TimescaleSink** - Database writes (schema changes need migration)

### Data Contracts (breaking changes affect multiple components)
- **EEGReading, BandPower, AnalysisResult** - Core data models
- **detection_rules.json, sub_states.json** - Rule definitions
- **init.sql** - Database schema

### Side Effect Summary

| Side Effect | Components |
|-------------|------------|
| Database Write | TimescaleSink, osc_receiver.py, tools/* |
| Database Read | DetectionEngine, eeg_mcp_server.py |
| Network UDP | osc_receiver*.py, udp_forward_to_wsl.py |
| Network MCP | eeg_mcp_server.py |
| File Read | DataParser, RuleManager, ArtifactThresholds |
| File Write | osc_receiver.py, ReportGenerator |
| UI Output | DisplayManager |
| Threading | CommandInterface |

## Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│                  External Network                    │
│   (Mind Monitor OSC → osc_receiver.py → UDP:5000)   │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│                   Orchestrator                       │
│          (EnhancedConsciousnessMonitor)             │
└───────────────────────┬─────────────────────────────┘
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│    Data     │  │  Detection  │  │     UI      │
│  DataParser │  │  Engine     │  │  Display    │
│  Signal     │  │  Artifacts  │  │  Commands   │
│  Processor  │  │  Patterns   │  │  Reports    │
└──────┬──────┘  └──────┬──────┘  └─────────────┘
       │                │
       ▼                ▼
┌─────────────┐  ┌─────────────┐
│   Config    │  │    Sink     │
│  Rules      │  │  Timescale  │
│  Thresholds │  │    DB       │
└─────────────┘  └──────┬──────┘
                        ▼
              ┌─────────────────┐
              │  External MCP   │
              │ (Claude Desktop)│
              └─────────────────┘
```

## Test Coverage

21 test files covering:
- Detection patterns (therapeutic, flow, excitement, meditation)
- Signal processing (FFT, band power, sample rate)
- Integration (enhanced monitor, refactored architecture)
- Output formatting (display, interval logic)
