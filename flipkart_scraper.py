# flipkart_scraper.py
import asyncio
import json
from playwright.async_api import async_playwright, TimeoutError

async def scrape_flipkart_products(query: str, output_filename: str = "flipkart_data.json"):
    formatted_query = "+".join(query.split())
    base_url = "https://www.flipkart.com"
    search_url = f"{base_url}/search?q={formatted_query}"
    results = []

    print(f"[INFO] Starting Flipkart scrape for '{query}'")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.goto(search_url, wait_until="load", timeout=90000)

            try:
                await page.wait_for_selector("div[data-id]", timeout=20000)
                print("[INFO] Product grid found. Extracting products...")
            except TimeoutError:
                print("[WARNING] No visible grid. Page might be empty or changed.")
                await browser.close()
                json.dump([], open(output_filename, "w", encoding="utf-8"))
                return

            product_cards = await page.query_selector_all("div[data-id]")
            if not product_cards:
                print("[WARNING] No product cards found!")
                await browser.close()
                json.dump([], open(output_filename, "w", encoding="utf-8"))
                return

            for card in product_cards:
                # Title (multiple layout fallbacks)
                name = None
                for selector in [
                    "div.KzDlHZ",   # phones
                    "div._4rR01T",  # general
                    "a.IRpwTa",     # fashion
                    "a.s1Q9rs",     # generic
                    "a.WKTcLC"      # watches / accessories
                ]:
                    el = await card.query_selector(selector)
                    if el:
                        name = (await el.inner_text()).strip()
                        break

                # Price (multiple versions)
                price = None
                for selector in ["div.Nx9bqj", "div._30jeq3", "div._25b18c"]:
                    el = await card.query_selector(selector)
                    if el:
                        price = (await el.inner_text()).strip()
                        break

                # Rating (optional)
                rating = "N/A"
                for selector in ["div._3LWZlK", "span.wjcEIp"]:
                    el = await card.query_selector(selector)
                    if el:
                        rating = (await el.inner_text()).strip()
                        break

                # Image (lazy-load fallback)
                img_el = await card.query_selector("img")
                image_url = None
                if img_el:
                    image_url = await img_el.get_attribute("src") or await img_el.get_attribute("data-src")

                # Product link
                link_el = await card.query_selector("a[href*='/p/']")
                product_href = await link_el.get_attribute("href") if link_el else None
                product_url = f"{base_url}{product_href}" if product_href and product_href.startswith("/") else product_href

                if name and price:
                    results.append({
                        "name": name,
                        "price": price,
                        "rating": rating,
                        "image_url": image_url or "",
                        "product_url": product_url or ""
                    })

            await browser.close()

        if results:
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            print(f"[SUCCESS] {len(results)} products scraped and saved to '{output_filename}'")
        else:
            print("[WARNING] No products extracted, saving empty file.")
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump([], f)

    except Exception as e:
        print(f"[ERROR] Flipkart scraper crashed: {e}")

if __name__ == "__main__":
    query = input("Enter product to search on Flipkart: ").strip() or "iphone 17"
    asyncio.run(scrape_flipkart_products(query))
