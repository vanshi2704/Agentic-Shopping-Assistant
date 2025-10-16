from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import threading
import os
import requests
import importlib.util
import sys
import json

# ------------------------------------------------------------------
# Dynamically import your existing agent.py (no rename required)
# ------------------------------------------------------------------
module_name = "agent"
module_path = os.path.join(os.path.dirname(__file__), "agent.py")
spec = importlib.util.spec_from_file_location(module_name, module_path)
agent = importlib.util.module_from_spec(spec)
sys.modules[module_name] = agent
spec.loader.exec_module(agent)

run_scraper_with_input = agent.run_scraper_with_input
load_json_data = agent.load_json_data
find_visual_matches_in_batch = agent.find_visual_matches_in_batch
get_expert_recommendation = agent.get_expert_recommendation

# ------------------------------------------------------------------
# Twilio configuration
# ------------------------------------------------------------------
ACCOUNT_SID = os.getenv("ACCOUNT_SID", "YOUR_TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "YOUR_TWILIO_AUTH_TOKEN")
WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Twilio Sandbox
GEMINI_API_KEY = "AIzaSyA6GoBeROA-qIGZ7By0E0DVp4uA2S0FNIc"  # Your existing key

app = Flask(__name__)
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ------------------------------------------------------------------
# Download media from WhatsApp
# ------------------------------------------------------------------
def download_media(media_url: str, filename: str) -> str:
    try:
        os.makedirs("downloads", exist_ok=True)
        path = os.path.join("downloads", filename)
        response = requests.get(media_url, stream=True, auth=(ACCOUNT_SID, AUTH_TOKEN))
        response.raise_for_status()
        with open(path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"[INFO] ✅ Image downloaded → {path}")
        return path
    except Exception as e:
        print(f"[ERROR] Failed to download media: {e}")
        return None

# ------------------------------------------------------------------
# Real URL shortener using TinyURL API
# ------------------------------------------------------------------
def shorten_url_real(url: str) -> str:
    try:
        api_url = f"http://tinyurl.com/api-create.php?url={url}"
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[WARN] URL shortening failed for {url}: {e}")
        return url  # fallback to original

# ------------------------------------------------------------------
# Background thread — run scrapers & send a single WhatsApp message
# ------------------------------------------------------------------
def process_visual_search(to_number, query, image_path):
    try:
        print(f"[THREAD] Starting visual search for '{query}'")

        # 1️⃣ Run all scrapers
        run_scraper_with_input("flipkart_scraper.py", query)
        run_scraper_with_input("amazon.py", query)
        run_scraper_with_input("scrape_myntra.py", query)

        # 2️⃣ Load all scraped data
        all_products = (
            load_json_data("flipkart_data.json", "Flipkart")
            + load_json_data("amazon_data.json", "Amazon")
            + load_json_data("myntra_data.json", "Myntra")
        )
        if not all_products:
            client.messages.create(
                from_=WHATSAPP_NUMBER, to=to_number,
                body="❌ No products found on Amazon, Flipkart, or Myntra."
            )
            return

        # 3️⃣ Find top 5 visual matches (if image provided)
        if image_path:
            top_5 = find_visual_matches_in_batch(all_products, image_path, api_key=GEMINI_API_KEY)
            if not top_5:
                client.messages.create(
                    from_=WHATSAPP_NUMBER, to=to_number,
                    body="⚠️ Could not find visually similar products."
                )
                return
        else:
            top_5 = all_products[:5]  # just take top 5 if no image

        # 4️⃣ Prepare single message with all products
        message_lines = [f"✅ Top 5 Matches for: {query}\n"]
        first_img = None

        for i, p in enumerate(top_5, 1):
            name = p.get("name") or p.get("title", "Product")
            price = p.get("price", "N/A")
            rating = p.get("rating", "N/A")
            visual = p.get("visual_score", "N/A")
            url = p.get("product_url", "")
            img = p.get("image_url")

            # Shorten Flipkart URLs to reduce message length
            if "flipkart.com" in url:
                url = shorten_url_real(url)

            message_lines.append(
                f"{i}. {name}\n💰 {price}\n⭐ {rating} | 🎯 Match: {visual}/10\n🔗 {url}\n"
            )

            # Only use the first image
            if not first_img and img:
                first_img = img

        # Combine text into a single message
        final_message = "\n".join(message_lines)
        if len(final_message) > 1500:
            final_message = final_message[:1500] + "\n⚠️ Results truncated."

        # Send the single WhatsApp message
        if first_img:
            client.messages.create(
                from_=WHATSAPP_NUMBER,
                to=to_number,
                body=final_message,
                media_url=[first_img]
            )
        else:
            client.messages.create(
                from_=WHATSAPP_NUMBER,
                to=to_number,
                body=final_message
            )

        print(f"[THREAD] ✅ Results sent to {to_number}")

    except Exception as e:
        print(f"[ERROR] process_visual_search failed: {e}")
        try:
            client.messages.create(
                from_=WHATSAPP_NUMBER, to=to_number,
                body=f"⚠️ Something went wrong while processing your request: {e}"
            )
        except:
            pass

# ------------------------------------------------------------------
# WhatsApp webhook
# ------------------------------------------------------------------
@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    from_number = request.values.get("From", "").strip()
    incoming_msg = request.values.get("Body", "").strip()
    num_media = int(request.values.get("NumMedia", 0))

    print(f"📩 Incoming message from {from_number}: '{incoming_msg}' | Media: {num_media}")

    resp = MessagingResponse()
    msg = resp.message()

    if not incoming_msg and num_media == 0:
        msg.body("Please send a product name and optionally an image 🛍️")
        return str(resp)

    image_path = None
    if num_media > 0:
        media_url = request.values.get("MediaUrl0")
        image_path = download_media(media_url, f"user_{from_number[-4:]}.jpg")
        msg.body(f"📸 Received your image for '{incoming_msg}'. Searching visually... ⏳")
    else:
        msg.body(f"🔍 Searching '{incoming_msg}' across Amazon, Flipkart & Myntra...")

    threading.Thread(target=process_visual_search,
                     args=(from_number, incoming_msg, image_path)).start()
    return str(resp)

# ------------------------------------------------------------------
# Run the Flask server
# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(port=5000, debug=False, use_reloader=False)
