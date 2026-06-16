# Data Directory

This repository includes small synthetic CSV files under `data/samples/` for smoke tests.

Do not commit raw sponsor data or large downloaded datasets.

Recommended local folders:

- `data/raw/` — immutable raw downloads or exports
- `data/interim/` — intermediate transformed files
- `data/processed/` — analytical panels and result inputs
- `data/external/` — third-party reference mappings

These folders are ignored by git except for `.gitkeep` placeholders.
