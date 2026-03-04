import os

CHROME_URL = os.getenv("CHROME_URL", "http://localhost:4444/wd/hub")

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads")

WAIT_TIMEOUT = 15

HEADLESS = True
