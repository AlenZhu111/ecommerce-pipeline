from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CORRUPTED_DIR = DATA_DIR / "corrupted"
CURATED_DIR = DATA_DIR / "curated"
ANALYTICS_DIR = DATA_DIR / "analytics"
REPORTS_DIR = PROJECT_ROOT / "reports"

RAW_SAMPLE_FILE = RAW_DIR / "ecommerce_events_sample.csv"
CORRUPTED_FILE = CORRUPTED_DIR / "ecommerce_events_with_bad_records.csv"
QUALITY_REPORT_FILE = REPORTS_DIR / "data_quality_report.json"
OUTPUT_VERIFICATION_REPORT_FILE = REPORTS_DIR / "output_verification_report.json"
KAGGLE_DEFAULT_FILE = RAW_DIR / "2019-Oct.csv"

VALID_EVENT_TYPES = ["view", "cart", "remove_from_cart", "purchase"]
