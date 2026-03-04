from browser import create_browser
from sites.springer.scrape import run as springer_run


def main():
    driver = create_browser()
    try:
        springer_run(driver)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
