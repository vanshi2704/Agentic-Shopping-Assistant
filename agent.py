import os
import subprocess
import json
import requests
from PIL import Image
from io import BytesIO
import google.generativeai as genai
from typing import List, Dict
import re # Import the regular expressions library

# This function remains the same
def run_scraper_with_input(script_name: str, search_query: str):
    print(f"\n{'='*20}\n[INFO] Running scraper: {script_name} for '{search_query}'\n{'='*20}")
    try:
        process = subprocess.run(
            ['python', script_name], 
            input=search_query, 
            text=True, 
            capture_output=True, 
            check=True, 
            encoding='utf-8',
            timeout=300
        )
        print(f"Output from {script_name}:\n{process.stdout}")
        print(f"[SUCCESS] Finished running {script_name}.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Script {script_name} failed. Stderr:\n{e.stderr}")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred while running {script_name}: {e}")
    return False

# This function remains the same
def load_json_data(filename: str, source_name: str) -> List[Dict]:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data: item['source'] = source_name
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"[WARNING] Could not load or parse '{filename}'.")
        return []

# --- NEW: The fast, batch-based visual analysis function ---
def find_visual_matches_in_batch(all_products: List[Dict], user_image_path: str, api_key: str) -> List[Dict]:
    if not all_products:
        print("[WARNING] No products were scraped, cannot perform visual analysis.")
        return []

    print(f"\n{'='*20}\n[INFO] Preparing images for fast batch analysis...\n{'='*20}")
    
    genai.configure(api_key=api_key)
    vision_model = genai.GenerativeModel('gemini-2.5-pro')
    
    try:
        user_image = Image.open(user_image_path)
    except FileNotFoundError:
        print(f"[ERROR] The user image was not found at the path: {user_image_path}")
        return []
    except Exception as e:
        print(f"[ERROR] The user image file is invalid or corrupted: {e}")
        return []

    # --- Step 1: Prepare the prompt and download all images ---
    # The prompt will contain the user image first, then all product images
    prompt_parts = [
        "You are an AI expert in visual similarity.",
        "The very first image is the user's reference image.",
        "All subsequent images are products from an e-commerce site.",
        "For each product image, compare it to the first user image and generate a similarity score from 0 (completely different) to 10 (nearly identical).",
        "Your final response MUST be a numbered list of scores, one for each product image. For example:",
        "1: 8",
        "2: 3",
        "3: 9",
        "--- USER IMAGE ---",
        user_image,
        "--- PRODUCT IMAGES ---"
    ]
    
    valid_products_for_batch = []
    for i, product in enumerate(all_products):
        product_image_url = product.get('image_url') or product.get('image')
        if not product_image_url or not product_image_url.startswith('http'):
            continue
        
        try:
            print(f"Downloading image {i+1}/{len(all_products)} for batch...")
            response = requests.get(product_image_url, timeout=10)
            response.raise_for_status()
            product_image = Image.open(BytesIO(response.content))
            
            # Add the valid product and its image to our lists
            valid_products_for_batch.append(product)
            prompt_parts.append(product_image)
        except requests.RequestException:
            pass # Silently skip images that fail to download

    if not valid_products_for_batch:
        print("[WARNING] No valid images could be downloaded for comparison.")
        return []

    # --- Step 2: Make ONE single, powerful API call ---
    print(f"\n[INFO] Sending one batch of {len(valid_products_for_batch)} images to Gemini for analysis. This may take a moment...")
    
    try:
        response = vision_model.generate_content(prompt_parts)
        
        # --- Step 3: Parse the single text response to get all scores ---
        print("[INFO] Parsing batch response...")
        scores_text = response.text
        
        # Use regular expressions to find all "number: score" pairs
        matches = re.findall(r'(\d+):\s*(\d+)', scores_text)
        
        for product_index_str, score_str in matches:
            # The model gives us product index (1, 2, 3...), we convert to list index (0, 1, 2...)
            product_index = int(product_index_str) - 1
            score = int(score_str)
            
            if 0 <= product_index < len(valid_products_for_batch):
                valid_products_for_batch[product_index]['visual_score'] = score

    except Exception as e:
        print(f"[ERROR] An error occurred during the batch Gemini API call: {e}")
        return []

    # --- Step 4: Sort and return the top 5 ---
    valid_products_for_batch.sort(key=lambda x: x.get('visual_score', 0), reverse=True)
    return valid_products_for_batch[:5]


# --- This function is now used for the FINAL recommendation step only ---
def get_expert_recommendation(top_5_products: List[Dict], user_query: str, api_key: str) -> str:
    if not top_5_products:
        return "Could not determine the best product as no visual matches were found."

    print(f"\n{'='*20}\n[INFO] Sending top 5 visual matches to Gemini Pro for final recommendation...\n{'='*20}")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    product_json_string = json.dumps(top_5_products, indent=2)

    prompt = f"""
    You are a professional e-commerce shopping assistant.
    The user is searching for "{user_query}".
    After a visual search, we have found these 5 products that look the most similar to what the user wants.

    Here is the list of the top 5 visually similar products:
    ```json
    {product_json_string}
    ```

    Your task is to analyze this curated list and provide a final recommendation. Follow these instructions:
    1.  Decide which single product is the "Best Value" or "Top Recommendation". Consider a balance of price, rating, and visual score.
    2.  Begin your response with a "Top Recommendation" section, clearly stating which product you chose and why in 2-3 sentences.
    3.  After that, provide an "Other Good Options" section, briefly listing the other 4 products and a one-sentence reason to choose them.
    4.  Format your response clearly with markdown. Do not return JSON.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[ERROR] An error occurred during the final recommendation API call: {e}")
        return "There was an error generating the final recommendation."

def main():
    search_query = input("Enter the product name to search for (e.g., 'blue polo t-shirt'): ").strip()
    image_path = input("Enter the full path to your reference image: ").strip().strip('"')

    if not search_query or not image_path:
        print("Both a product name and an image path are required. Please run again.")
        return
        
    GEMINI_API_KEY = "AIzaSyA6GoBeROA-qIGZ7By0E0DVp4uA2S0FNIc" # PASTE YOUR KEY HERE
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("[ERROR] API Key is missing in agent.py.")
        return

    # Scraping
    run_scraper_with_input('flipkart_scraper.py', search_query)
    run_scraper_with_input('amazon.py', search_query)
    run_scraper_with_input('scrape_myntra.py', search_query)
    
    # Consolidation
    print(f"\n{'='*20}\n[INFO] Consolidating all scraped data...\n{'='*20}")
    all_scraped_products = (
        load_json_data('flipkart_data.json', 'Flipkart') +
        load_json_data('amazon_data.json', 'Amazon') +
        load_json_data('myntra_data.json', 'Myntra')
    )
    if not all_scraped_products:
        print("\n[ERROR] No data was scraped from any platform. Exiting.")
        return
    print(f"[SUCCESS] Found a total of {len(all_scraped_products)} products to analyze.")

    # Step 1: Find the Top 5 Visual Matches using the fast batch method
    top_5_visual_matches = find_visual_matches_in_batch(all_scraped_products, image_path, GEMINI_API_KEY)

    # Step 2: Get the Final Expert Recommendation on that Top 5 list
    final_recommendation = get_expert_recommendation(top_5_visual_matches, search_query, GEMINI_API_KEY)

    # Display the final, reasoned output
    print(f"\n{'='*30}\n[AGENT'S RECOMMENDATION]\n{'='*30}")
    print(final_recommendation)

    # Optionally, print the raw details of the top 5 for reference
    if top_5_visual_matches:
        print(f"\n\n--- (Details of the Top 5 Visually-Matched Products) ---")
        for i, product in enumerate(top_5_visual_matches, 1):
            name = product.get('name') or product.get('title', 'N/A')
            price = product.get('price', 'N/A')
            rating = product.get('rating', 'N/A')
            source = product.get('source', 'N/A')
            url = product.get('product_url', 'N/A')
            visual_score = product.get('visual_score', 'N/A')
            print(f"\n{i}. {name} (Visual Score: {visual_score}/10)")
            print(f"   - Source: {source}, Price: {price}, Rating: {rating}")
            print(f"   - URL: {url}")

if __name__ == "__main__":
    main()