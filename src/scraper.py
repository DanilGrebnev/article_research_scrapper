from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import WAIT_TIMEOUT


class Scraper:
    def __init__(self, driver: WebDriver):
        self.driver = driver

    def go_to(self, url: str):
        self.driver.get(url)

    def wait_for(self, css_selector: str, timeout: int | None = None):
        t = timeout if timeout is not None else WAIT_TIMEOUT
        return WebDriverWait(self.driver, t).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )

    def wait_for_clickable(self, css_selector: str, timeout: int | None = None):
        t = timeout if timeout is not None else WAIT_TIMEOUT
        return WebDriverWait(self.driver, t).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
        )

    def get_links(self, css_selector: str = "a") -> list[str]:
        elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
        return [
            href
            for el in elements
            if (href := el.get_attribute("href"))
        ]

    def get_text(self, css_selector: str) -> list[str]:
        elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
        return [el.text for el in elements]

    def get_attribute(self, css_selector: str, attr: str) -> list[str]:
        elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
        return [
            value
            for el in elements
            if (value := el.get_attribute(attr))
        ]

    def click(self, css_selector: str):
        element = self.wait_for_clickable(css_selector)
        element.click()

    def scroll_to_bottom(self):
        self.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

    def get_page_source(self) -> str:
        return self.driver.page_source

    def back(self):
        self.driver.back()

    def current_url(self) -> str:
        return self.driver.current_url
