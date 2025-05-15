from core.extractor import extract_product_data

def test_extract():
    url = "https://example-woocommerce-site.com/product/sample-product"
    product = extract_product_data(url)
    assert "title" in product
    assert isinstance(product.get("images"), list)
