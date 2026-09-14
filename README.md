# SATYAHARIT-GREENWASH
# 🌱 SatyaHarit (GreenWash Guard)

> **Exposing Greenwashing with AI & Digital Verification**  
> SatyaHarit is an advanced, high-performance web application designed to detect and expose false environmental claims (greenwashing) made by e-commerce brands. By combining automated web scraping, official certificate registry cross-checking, and a resilient AI fallback mechanism, it delivers a transparent **Green-Trust Score** for any product.

---

## 📋 Project Overview
In today's market, consumers are frequently misled by vague eco-friendly buzzwords like "sustainable," "eco-friendly," or "natural." SatyaHarit bridges this transparency gap. Users simply paste a product link, and the system instantly analyzes page content, scans for official third-party certifications (FSC, USDA Organic, GOTS, etc.), evaluates material disclosures, and provides an objective trust evaluation complete with a custom Hinglish/English review, pros, cons, and verified alternatives.

---

## ✨ Features
* **URL Content Scraping & Ingestion:** Safely extracts titles, images, and descriptive text from modern e-commerce product pages.
* **Certificate & Domain Cross-Checking:** Automatically cross-references detected eco-claims against official governing body domains (`fsc.org`, `usda.gov`, `global-standard.org`, etc.) to flag unverified or suspicious claims.
* **Hyper-Intelligent Dynamic Fallback Engine:** Guarantees 100% uptime. If primary API limits or network outages occur, a built-in heuristic simulation engine takes over seamlessly without crashing the application.
* **High-End Tailwind CSS UI:** A responsive, modern interface featuring real-time scanning animations, category-wise trust scorecards, and visual badge grids.
* **Robust FastAPI Backend:** High-speed asynchronous Python backend supporting CORS, exception handling, and clean JSON payloads.

---

## 🛠️ Technologies Used
* **Frontend:** HTML5, Tailwind CSS, JavaScript (Vanilla ES6+), Inter & Plus Jakarta Sans typography.
* **Backend:** FastAPI (Python), Uvicorn.
* **Scraping & Parsing:** BeautifulSoup4, Requests, Python-Dotenv.
* **AI Integration:** Groq API (Llama-3.3-70b-versatile) via OpenAI client interface.
* **Deployment & Hosting:** Render (Backend Cloud Hosting).

---

## 🤖 AI Tools & Models Used
* **Model:** Llama-3.3-70b-versatile (accessed via Groq API).
* **Purpose:** Analyzes scraped product descriptions and title data to generate:
  * Product category classification (e.g., Sustainable Accessory, Eco Apparel).
  * Context-aware authenticity scoring ($0 - 100$).
  * Granular category ratings with specific reasoning.
  * Targeted pros, cons, and alternatives.

---

## 🚀 Setup & Installation Instructions

### Prerequisites
* Python 3.10+ installed on your system.
* Git for version control.

### 1. Clone the Reposit
```bash
git clone [https://github.com/tumhara-username/satyaharit-backend.git](https://github.com/tumhara-username/satyaharit-backend.git)
cd satyaharit-backend
