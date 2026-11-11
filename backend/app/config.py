import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR", str(ROOT / "data")))
DATA.mkdir(parents=True, exist_ok=True)
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
KEY = os.getenv("GEMINI_API_KEY", "")
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
COLLECTION = "mitchell_v1"
SOURCE_URL = "https://www.cs.cmu.edu/~tom/files/MachineLearningTomMitchell.pdf"
MAX_QUESTIONS = 4
