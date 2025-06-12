import logging
import pathlib

LOG_FILE = pathlib.Path(__file__).resolve().parent.parent / "vacalyser.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s – %(message)s")

def log_event(name: str, details: dict | None = None):
    logging.info("%s – %s", name, details or {})
