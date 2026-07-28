"""
This module sets up the Selenium Chrome driver with optimized options, including rotating proxies.
It is designed to be imported and used in the scraping logic.
It uses the selenium library to create a headless Chrome driver instance with specific configurations.
"""

import atexit
import random
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

import config

PROXIES = config.PROXIES

_SHARED_DRIVER: Optional[webdriver.Chrome] = None


def _is_driver_alive(driver: webdriver.Chrome) -> bool:
    """Return True when the cached Chrome session still accepts commands."""
    try:
        driver.execute_script("return 1")
        return True
    except WebDriverException:
        return False
    except Exception:
        return False


def setup_driver(
    headless: Optional[bool] = None,
    use_proxy: Optional[bool] = None,
    optimized: Optional[bool] = None,
    silent_mode_level: Optional[int] = None,
    windows_size: Optional[str] = None,
    disable_css: Optional[bool] = None,
    disable_image: Optional[bool] = None,
    implicit_wait: Optional[int] = None,
    timeout: Optional[int] = None,
    force_new: bool = False,
) -> webdriver.Chrome:
    """
    Create and cache one Selenium Chrome driver for the application lifetime.

    The driver is reused across requests and only closed at process shutdown to
    avoid repeatedly paying the startup cost of a full Chrome instance.
    """
    global _SHARED_DRIVER

    if force_new:
        shutdown_driver()
    elif _SHARED_DRIVER is not None:
        if _is_driver_alive(_SHARED_DRIVER):
            return _SHARED_DRIVER
        shutdown_driver()

    if headless is None:
        headless = config.SELENIUM_HEADLESS
    if use_proxy is None:
        use_proxy = config.SELENIUM_USE_PROXY
    if optimized is None:
        optimized = config.SELENIUM_OPTIMIZED
    if silent_mode_level is None:
        silent_mode_level = config.SELENIUM_SILENT_MODE_LEVEL
    if windows_size is None:
        windows_size = config.SELENIUM_WINDOW_SIZE
    if disable_css is None:
        disable_css = config.SELENIUM_DISABLE_CSS
    if disable_image is None:
        disable_image = config.SELENIUM_DISABLE_IMAGE
    if implicit_wait is None:
        implicit_wait = config.SELENIUM_IMPLICIT_WAIT
    if timeout is None:
        timeout = config.SELENIUM_TIMEOUT

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    if optimized:
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument('--ignore-certificate-errors-spki-list')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-features=NetworkService")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    if windows_size:
        chrome_options.add_argument(f"--window-size={windows_size}")

    chrome_options.add_argument(f"--log-level={str(silent_mode_level)}")

    prefs = {}
    if disable_image:
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        prefs["profile.managed_default_content_settings.images"] = 2
    if disable_css:
        prefs["profile.default_content_setting_values"] = {
            "cookies": 2, "images": 2, "javascript": 2, "plugins": 2, "popups": 2,
            "geolocation": 2, "notifications": 2, "auto_select_certificate": 2,
            "fullscreen": 2, "mouselock": 2, "mixed_script": 2, "media_stream": 2,
            "media_stream_mic": 2, "media_stream_camera": 2, "protocol_handlers": 2,
            "ppapi_broker": 2, "automatic_downloads": 2, "midi_sysex": 2,
            "push_messaging": 2, "ssl_cert_decisions": 2, "metro_switch_to_desktop": 2,
            "protected_media_identifier": 2, "app_banner": 2, "site_engagement": 2,
            "durable_storage": 2
        }
    if prefs:
        chrome_options.add_experimental_option("prefs", prefs)
    else:
        chrome_options.add_experimental_option(
            "prefs", {"profile.default_content_setting_values.notifications": 2}
        )

    if use_proxy and PROXIES:
        proxy = random.choice(PROXIES)
        chrome_options.add_argument(f'--proxy-server={proxy}')

    try:
        _SHARED_DRIVER = webdriver.Chrome(options=chrome_options)
        _SHARED_DRIVER.set_page_load_timeout(timeout)
        _SHARED_DRIVER.implicitly_wait(implicit_wait)
        return _SHARED_DRIVER
    except Exception:
        raise


def restart_driver() -> webdriver.Chrome:
    """Restart Chrome and return a fresh shared Selenium driver."""
    return setup_driver(force_new=True)


def shutdown_driver() -> None:
    """Close the shared Selenium driver if it exists and clear the cached reference."""
    global _SHARED_DRIVER

    driver = _SHARED_DRIVER
    _SHARED_DRIVER = None
    if driver is None:
        return
    try:
        driver.quit()
    except Exception:
        pass


atexit.register(shutdown_driver)
