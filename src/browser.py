import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config import CHROME_URL, HEADLESS, WAIT_TIMEOUT


def create_browser(retries=5, delay=3):
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    for attempt in range(1, retries + 1):
        try:
            driver = webdriver.Remote(
                command_executor=CHROME_URL,
                options=options,
            )
            driver.implicitly_wait(WAIT_TIMEOUT)
            return driver
        except Exception:
            if attempt == retries:
                raise
            time.sleep(delay)
