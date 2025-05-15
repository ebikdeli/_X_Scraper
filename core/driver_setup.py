"""
This module sets up the Selenium Chrome driver with optimized options, including rotating proxies.
It is designed to be imported and used in the scraping logic.
It uses the selenium library to create a headless Chrome driver instance with specific configurations.
"""


import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from config import PROXIES

def setup_driver(headless: bool=True, use_proxy: bool=False, optimized: bool=True,
                silent_mode_level: int=5, windows_size: str='1920,1080', disable_css: bool=True,
                disable_image: bool=True, implicit_wait: int=5, timeout: int=30):
    """Initialize and return a headless Selenium Chrome driver with proxy rotation."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    if optimized:
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument('--ignore-certificate-errors-spki-list')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        # options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        # Following 4 options are used to test if performance can get better
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-features=NetworkService")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    if windows_size:
        chrome_options.add_argument(f"--window-size={windows_size}")
    
    # Silent mode
    chrome_options.add_argument(f"--log-level={str (silent_mode_level)}");
    
    # Disable image
    if disable_image:
            # 2 following line both can disable image loading but first one is more common
            chrome_options.add_argument('--blink-settings=imagesEnabled=false')
            chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})

    # Disable css
    if disable_css:
            prefs = {'profile.default_content_setting_values': {'cookies': 2, 'images': 2, 'javascript': 2,
                                'plugins': 2, 'popups': 2, 'geolocation': 2,
                                'notifications': 2, 'auto_select_certificate': 2, 'fullscreen': 2,
                                'mouselock': 2, 'mixed_script': 2, 'media_stream': 2,
                                'media_stream_mic': 2, 'media_stream_camera': 2, 'protocol_handlers': 2,
                                'ppapi_broker': 2, 'automatic_downloads': 2, 'midi_sysex': 2,
                                'push_messaging': 2, 'ssl_cert_decisions': 2, 'metro_switch_to_desktop': 2,
                                'protected_media_identifier': 2, 'app_banner': 2, 'site_engagement': 2,
                                'durable_storage': 2}}
            chrome_options.add_experimental_option(
                "prefs", prefs
            )
    else:
        # Atleast disable notifications
        chrome_options.add_experimental_option(
            "prefs", {"profile.default_content_setting_values.notifications": 2}
        )
    
    # Rotate proxy
    if use_proxy and PROXIES:
        proxy = random.choice(PROXIES)
        chrome_options.add_argument(f'--proxy-server={proxy}')
    # Create the Chrome driver instance
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(timeout)
    driver.implicitly_wait(implicit_wait)
    return driver
