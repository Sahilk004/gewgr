"""Write SYNTHETIC data to backend/data so the app can be demoed before real ingestion.

Usage (from backend/):  python -m scripts.make_sample_data
The UI shows a warning banner whenever the data source is 'synthetic'.
"""
from pathlib import Path

from app.synthetic import write_sample

if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "data"
    write_sample(out)
    print(f"Synthetic sample data written to {out}")
