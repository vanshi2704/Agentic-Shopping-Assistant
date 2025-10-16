# scrape_myntra.py
import asyncio
import json
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup

async def scrape_myntra_products(query: str, output_filename: str = "myntra_data.json"):
    """
    Searches for a product on Myntra, scrolls to the bottom to load all results,
    scrapes all product details, and saves them to a JSON file.
    This version uses a more reliable page loading strategy.
    """
    url = f"https://www.myntra.com/{query.replace(' ', '-')}"
    results = []

    print(f"[INFO] Starting scrape for '{query}' on Myntra...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=50)
            page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            
            print(f"Navigating to: {url}")
            
            await page.goto(url, wait_until="load", timeout=90000)

            try:
                print("Page loaded. Waiting for the product grid to become visible...")
                await page.wait_for_selector("ul.results-base", timeout=30000)
                print("[SUCCESS] Product grid found. Starting to scroll...")
            except TimeoutError:
                print("[ERROR] Could not find product grid after page load.")
                print("   This can happen if there are no search results or the page layout has changed.")
                await browser.close()
                return

            last_height = await page.evaluate("document.body.scrollHeight")
            while True:
                await page.mouse.wheel(0, 1000)
                await page.wait_for_timeout(2000)
                
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    print("Reached the bottom of the page.")
                    break
                last_height = new_height

            print("Getting final page content...")
            html = await page.content()
            await browser.close()

        print("Parsing HTML with BeautifulSoup...")
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("li.product-base")

        if not items:
            print("[WARNING] No product items found after parsing. The selector 'li.product-base' might be outdated.")
            return

        for item in items:
            title_el = item.select_one("h3.product-brand")
            name_el = item.select_one("h4.product-product")
            price_el = item.select_one("span.product-discountedPrice") or item.select_one("div.product-price > span")
            link_el = item.select_one("a")
            image_el = item.select_one("img.img-responsive")

            if title_el and name_el and price_el and link_el and image_el:
                full_title = f"{title_el.get_text(strip=True)} {name_el.get_text(strip=True)}"
                price = price_el.get_text(strip=True)
                href = link_el['href']
                product_url = "https://www.myntra.com/" + href.lstrip('/')
                image_url = image_el.get('src', 'N/A')

                results.append({
                    "title": full_title,
                    "price": price,
                    "image_url": image_url,
                    "product_url": product_url
                })

        if results:
            print(f"\n[SUCCESS] Scraped details for {len(results)} products.")
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            print(f"All data has been saved to '{output_filename}'")
        else:
            print("[WARNING] Scraping complete, but no data was extracted. Please check the selectors.")

    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")

if __name__ == "__main__":
    search_query = input("Enter product to search on Myntra: ").strip() or "nike shoes"
    asyncio.run(scrape_myntra_products(search_query))