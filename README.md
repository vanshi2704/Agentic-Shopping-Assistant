# 🛍️ Agentic Shopping Assistant – MVP

This repository contains my **Agentic Shopping Assistant MVP**, an AI-driven multi-agent system that finds, compares, and recommends fashion products across **Amazon**, **Flipkart**, and **Myntra**, with optional **WhatsApp chatbot** integration.

---

## 🧠 Overview
- Multi-agent system built with **Python**  
- Uses **Gemini 2.5 Pro** for text and visual understanding  
- Integrates **Playwright** and **BeautifulSoup** for real-time web scraping  
- Aggregates data from Amazon, Flipkart, and Myntra into structured JSON  
- Optional conversational layer via **Flask + Twilio (WhatsApp)**  
- Performs image-based visual similarity scoring using **Gemini Vision**

---

## 🧩 Key Features
✅ Accepts text or image as search input  
✅ Scrapes product data from Amazon, Flipkart, and Myntra asynchronously  
✅ Merges results into a unified product catalog  
✅ Ranks results using Gemini Vision similarity analysis  
✅ Allows conversational interaction on WhatsApp  
✅ Outputs structured JSON with platform, price, rating, and similarity score  

---

## ⚙️ Run Locally (in VS Code or any IDE)

> 💡 You don’t need to run these for submission — they’re just instructions for anyone reviewing or testing the build.

```bash
# 1️⃣ Clone this repository
git clone https://github.com/<your-username>/Agentic-Shopping-Assistant.git
cd Agentic-Shopping-Assistant

# 2️⃣ Install dependencies
pip install -r requirements.txt

# 3️⃣ Run the core agent
python agent.py

# 4️⃣ (Optional) Launch the WhatsApp bot
python whatsapp_bot.py
