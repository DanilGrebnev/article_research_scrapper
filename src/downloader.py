import os
from urllib.parse import urlparse

import requests
from selenium.webdriver.remote.webdriver import WebDriver

from config import DOWNLOAD_DIR


def get_selenium_cookies(driver: WebDriver) -> dict[str, str]:
    return {c["name"]: c["value"] for c in driver.get_cookies()}


def download_file(
    url: str,
    save_dir: str | None = None,
    cookies: dict[str, str] | None = None,
    filename: str | None = None,
) -> str:
    save_dir = save_dir or DOWNLOAD_DIR
    os.makedirs(save_dir, exist_ok=True)

    if filename is None:
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path) or "file"

    filepath = os.path.join(save_dir, filename)

    response = requests.get(url, cookies=cookies, stream=True, timeout=60)
    response.raise_for_status()

    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return filepath
