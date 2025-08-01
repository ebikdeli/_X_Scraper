from selenium.common.exceptions import WebDriverException
from application.driver.chrome import setup_driver
import time

def extract_product_data(url):
    driver = setup_driver()
    try:
        driver.get(url)
        time.sleep(3)  # Let JavaScript render
        product = {
            "url": url,
            "title": driver.title or "N/A",
            "price": driver.find_element("css selector", ".price").text if driver.find_elements("css selector", ".price") else "N/A",
            "description": driver.find_element("css selector", ".woocommerce-product-details__short-description").text if driver.find_elements("css selector", ".woocommerce-product-details__short-description") else "N/A",
            "images": [img.get_attribute("src") for img in driver.find_elements("css selector", ".woocommerce-product-gallery__image img")],
            "name": driver.find_element("css selector", ".product_title").text if driver.find_elements("css selector", ".product_title") else "N/A",
            "company_name": "Unknown",
            "category": driver.find_element("css selector", ".posted_in a").text if driver.find_elements("css selector", ".posted_in a") else "Uncategorized"
        }
        return product
    except WebDriverException as e:
        return {"error": str(e), "url": url}
    finally:
        driver.quit()
