# Session: EEG Admin Panel

**Date:** 2025-12-06
**Duration:** ~30 minutes

## Summary

Built a complete Streamlit-based admin panel for viewing brain states, managing labels, and monitoring EEG data.

## What Was Built

### Admin Panel (`admin/`)

```
admin/
├── app.py                      # Main entry point with modern CSS
├── pages/
│   ├── 1_📊_Dashboard.py       # Real-time brain state visualization
│   ├── 2_📁_Sessions.py        # Session browser with export
│   ├── 3_🏷️_Annotations.py     # Label management (add/view/delete)
│   ├── 4_⚙️_State_Definitions.py  # Custom state pattern editor
│   └── 5_📐_Baselines.py       # Baseline comparison tool
└── utils/
    └── db.py                   # Database utilities (all queries)
```

### Features Implemented

| Page | Capabilities |
|------|--------------|
| Dashboard | Real-time state display, band power bars, area charts, state timeline, auto-refresh |
| Sessions | List all sessions, view stats, band power charts per session, CSV export |
| Annotations | Add labels with notes, filter by session/time/label, delete, bulk CSV import |
| State Definitions | Create/edit/delete custom states, band thresholds, test against current state |
| Baselines | Save current averages, visual comparison bars, diff metrics vs current |

### Design Decisions

- **Streamlit** chosen over Gradio for better dashboard flexibility
- **Modern UI** with gradients, rounded corners (2025 design trends)
- **State emoji mapping** for visual recognition
- **Color-coded band power bars** for quick scanning
- **Auto-refresh** on dashboard (2-second interval)

## Files Changed

- `admin/` - New directory with entire admin panel
- `docker/compose.yml` - Added `admin` service
- `docker/Dockerfile.admin` - New Dockerfile for admin container
- `pyproject.toml` - Added `streamlit>=1.40.0` dependency
- `CLAUDE.md` - Added admin panel documentation

## How to Run

```bash
# Ensure database is running
docker compose -f docker/compose.yml up -d db

# Launch admin panel
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
  uv run streamlit run admin/app.py --server.headless=true

# Open http://localhost:8501
```

## Verified Working

- Database connection tested with 137,875 EEG windows
- All imports working
- Current state query returns "K_DOWNSHIFT"
- 6 custom state definitions visible
- 6 baselines visible
- Health check endpoint responding

## Future Enhancements

- Time range selector on dashboard charts
- Annotation editing (currently add/delete only)
- Real-time WebSocket updates instead of polling
- Dark/light theme toggle
- Mobile-responsive layout
