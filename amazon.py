# amazon.py
import asyncio
import json
from playwright.async_api import async_playwright, TimeoutError

async def scrape_amazon_products(query: str, max_pages: int = 3, output_filename: str = "amazon_data.json"):
    """
    Searches for a product on Amazon, paginates through results, and scrapes all product details
    using a perfected, multi-step parsing logic to ensure all data is captured.
    """
    formatted_query = "+".join(query.split())
    base_url = "https://www.amazon.in"
    search_url = f"{base_url}/s?k={formatted_query}"
    results = []

    print(f"[INFO] Starting scrape for '{query}' on Amazon (headless)...")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
            )
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = await context.new_page()

            await page.goto(search_url, wait_until="load", timeout=90000)

            page_title = await page.title()
            if "robot" in page_title.lower() or "captcha" in page_title.lower():
                print("[ERROR] CAPTCHA detected. Amazon is blocking the request. Cannot proceed.")
                await browser.close()
                return

            current_page_num = 0
            for page_num in range(1, max_pages + 1):
                current_page_num = page_num
                print(f"--- Scraping Page {page_num} ---")

                try:
                    await page.wait_for_selector("div[data-component-type='s-search-result']", timeout=30000)
                except TimeoutError:
                    print("[ERROR] Could not find search results on the page. Stopping.")
                    break

                product_elements = await page.query_selector_all("div[data-component-type='s-search-result']")

                for product in product_elements:
                    asin = await product.get_attribute("data-asin")
                    if not asin or asin.strip() == "":
                        continue

                    title = "N/A"
                    title_el = await product.query_selector('h2 a.a-link-normal span.a-text-normal')
                    if title_el:
                        title = await title_el.text_content()

                    if title == "N/A" or len(title.strip()) < 5:
                        image_el = await product.query_selector('img.s-image')
                        if image_el:
                            alt_text = await image_el.get_attribute('alt')
                            if alt_text and alt_text.strip():
                                title = alt_text

                    if title == "N/A" or len(title.strip()) < 5:
                        simple_title_el = await product.query_selector('h2 a span')
                        if simple_title_el:
                             title = await simple_title_el.text_content()

                    price, rating, image_url = "N/A", "N/A", "N/A"

                    price_el = await product.query_selector('span.a-price-whole')
                    if price_el:
                        price = f"Rs.{await price_el.text_content()}"

                    rating_el = await product.query_selector('span.a-icon-alt')
                    if rating_el:
                        rating = await rating_el.text_content()

                    image_el_for_url = await product.query_selector('img.s-image')
                    if image_el_for_url:
                        image_url = await image_el_for_url.get_attribute('src')
                    
                    product_url = f"{base_url}/dp/{asin}"

                    results.append({
                        "title": title.strip(),
                        "price": price.strip().replace('.',''),
                        "rating": rating.strip(),
                        "image_url": image_url,
                        "product_url": product_url
                    })

                next_button = await page.query_selector("a.s-pagination-next:not(.s-pagination-disabled)")
                if next_button and page_num < max_pages:
                    print("Navigating to the next page...")
                    await next_button.click()
                    await page.wait_for_load_state("load", timeout=60000)
                else:
                    print("No more pages to scrape. Reached the end.")
                    break

            await context.close()
            await browser.close()

        if results:
            print(f"\n[SUCCESS] Scraped details for {len(results)} products across {current_page_num} page(s).")
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            print(f"All data has been saved to '{output_filename}'")
        else:
            print("[WARNING] Scraping complete, but no data was extracted. Please check the selectors and page content.")

    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")

if __name__ == "__main__":
    search_query = input("Enter product to search on Amazon: ").strip() or "nike shoes"
    asyncio.run(scrape_amazon_products(search_query, max_pages=1))