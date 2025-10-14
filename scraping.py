import requests
from bs4 import BeautifulSoup
import json
import time

BASE_URL = "https://www.bigle.gr"

# --- Get all category links from homepage ---
def get_category_links():
    url = BASE_URL
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    category_links = soup.find_all('a', class_='category-anchor')
    return [BASE_URL + link['href'] for link in category_links if link.get('href')]

# --- Get all product links from all pages of a category ---
def get_all_product_links(category_url):
    product_links = []
    visited_pages = set()
    current_url = category_url

    while current_url and current_url not in visited_pages:
        print(f"🔎 Scraping category page: {current_url}")
        visited_pages.add(current_url)

        response = requests.get(current_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- Extract product links ---
        products_container = soup.find(
            'div',
            class_='mt-1 row row-cols-1 row-cols-sm-1 row-cols-md-2 row-cols-lg-3 row-cols-xl-4 row-cols-xxl-5 gx-1 gy-1'
        )
        if products_container:
            links = products_container.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.startswith("/products"):
                    full_url = BASE_URL + href
                    product_links.append(full_url)

        # --- Look for next page button ("»") ---
        next_btn = soup.find('a', class_='page-link', string=lambda s: s and "»" in s.strip())
        if next_btn and next_btn.get('href'):
            next_url = BASE_URL + next_btn['href']
            if next_url in visited_pages:
                break
            current_url = next_url
        else:
            current_url = None

        time.sleep(0.1)

    return list(set(product_links))

# --- Scrape product details ---
def scrape_product(product_url):
    response = requests.get(product_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Product name
    product_name_element = soup.find('h1', class_='d-flex justify-content-center text-center mt-4 fs-lg fw-bold')
    product_name = product_name_element.get_text(strip=True) if product_name_element else 'Not found'

    # Product image
    product_image_element = soup.find('img', class_='results-product-image')
    if product_image_element and 'src' in product_image_element.attrs:
        product_image_url = product_image_element['src']
        if product_image_url.startswith("/"):
            product_image_url = BASE_URL + product_image_url
    else:
        product_image_url = 'Not found'

    # Store data
    products = []
    info_containers = soup.find_all('div', class_='bottom-border white-container row mx-auto d-md-flex d-block mt-4 pb-2')
    for info_container in info_containers:
        store_img = info_container.find('img', class_='d-flex justify-content-center store-logo')
        store_name = store_img.get('alt') if store_img else 'Not found'

        link_tag = info_container.find('a')
        product_link = BASE_URL + link_tag['href'] if link_tag and 'href' in link_tag.attrs else 'Not found'

        price_tag = info_container.find('span', class_='d-flex justify-content-center fs-xx-lg fw-bold')
        price = price_tag.get_text(strip=True) if price_tag else 'Not found'

        unit_price_tag = info_container.find('span', class_='d-flex justify-content-center fs-md')
        unit_price = unit_price_tag.get_text(strip=True) if unit_price_tag else 'Not found'

        products.append({
            "product_name": product_name,
            "product_image": product_image_url,
            "store_name": store_name,
            "product_link": product_link,
            "price": price,
            "unit_price": unit_price
        })

    return products

# --- Main crawler ---
def main():
    categories = get_category_links()
    print(f"📂 Found {len(categories)} categories")

    all_data = []
    product_to_batch = {}  # ✅ map (name + image) to batch_id
    next_batch_id = 1

    for category_url in categories:
        category_name = category_url.replace(BASE_URL, "").strip("/").split("/")[-1]
        product_links = get_all_product_links(category_url)
        total = len(product_links)
        print(f"🛒 {total} products found in {category_url}")

        for i, product_url in enumerate(product_links, start=1):
            try:
                products = scrape_product(product_url)
                for p in products:
                    # --- unique key for this product across stores
                    product_key = (p["product_name"].strip(), p["product_image"].strip())

                    # --- reuse same batch_id if product already exists
                    if product_key not in product_to_batch:
                        product_to_batch[product_key] = next_batch_id
                        next_batch_id += 1

                    batch_id = product_to_batch[product_key]

                    all_data.append({
                        "batch_id": batch_id,
                        "category": category_name,
                        **p
                    })

                # ✅ Save progress incrementally
                with open("products.json", "w", encoding="utf-8") as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"\n⚠️ Error scraping {product_url}: {e}")

            percent = (i / total) * 100
            print(f"\rProgress: {i}/{total} ({percent:.1f}%)", end='')
            time.sleep(0.1)

        print("\n✅ Finished category.")

    print("✅ All data saved to products.json")

if __name__ == "__main__":
    main()
