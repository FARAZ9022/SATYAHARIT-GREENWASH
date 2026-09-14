import os
import re
import json
import traceback
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except Exception:
    genai = None

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

PRODUCT_KEYWORDS = {
    "bag": "Sustainable Accessory",
    "backpack": "Sustainable Accessory",
    "wallet": "Sustainable Accessory",
    "purse": "Sustainable Accessory",
    "tote": "Sustainable Accessory",
    "sling": "Sustainable Accessory",
    "bottle": "Reusable Drinkware",
    "flask": "Reusable Drinkware",
    "cup": "Reusable Drinkware",
    "mug": "Reusable Drinkware",
    "water": "Reusable Drinkware",
    "shirt": "Eco Apparel",
    "t-shirt": "Eco Apparel",
    "clothing": "Eco Apparel",
    "dress": "Eco Apparel",
    "kurti": "Eco Apparel",
    "pants": "Eco Apparel",
    "top": "Eco Apparel",
    "cream": "Organic Skincare",
    "oil": "Organic Skincare",
    "soap": "Organic Skincare",
    "shampoo": "Organic Skincare",
    "serum": "Organic Skincare",
    "lotion": "Organic Skincare",
    "skincare": "Organic Skincare",
    "face": "Organic Skincare",
    "shoe": "Sustainable Footwear",
    "sneaker": "Sustainable Footwear",
    "sandal": "Sustainable Footwear",
    "boot": "Sustainable Footwear",
    "footwear": "Sustainable Footwear",
}

ECO_CLAIM_PATTERNS = [
    "organic", "recycled", "recyclable", "plastic free", "bpa free", "fair trade",
    "carbon neutral", "vegan", "cruelty free", "compostable", "responsibly sourced",
    "sustainably sourced", "biodegradable", "offset", "zero waste", "eco friendly",
    "natural ingredients", "certified", "made from recycled", "low impact"
]

DEFAULT_IMAGES = {
    "Sustainable Accessory": "https://images.unsplash.com/photo-1544816155-12df9643f363?w=500",
    "Reusable Drinkware": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=500",
    "Eco Apparel": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500",
    "Organic Skincare": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500",
    "Sustainable Footwear": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500",
    "Eco Product": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500",
}


def _normalize_space(text):
    return " ".join((text or "").replace("\xa0", " ").split())


def _get_title_from_url(url):
    try:
        path_segments = [p for p in urlparse(url).path.strip("/").split("/") if p]
        slug = ""
        if "p" in path_segments:
            p_idx = path_segments.index("p")
            if p_idx > 0:
                slug = path_segments[p_idx - 1]
        elif "dp" in path_segments:
            dp_idx = path_segments.index("dp")
            if dp_idx > 0:
                slug = path_segments[dp_idx - 1]
        elif path_segments:
            slug = path_segments[-1]
        if slug and len(slug) > 2:
            extracted = slug.replace("-", " ").replace("_", " ").title()
            if not any(word in extracted.lower() for word in ["access", "maintenance", "error"]):
                return extracted
    except Exception:
        pass
    return "Selected Product"


def _detect_product_type(url, text=""):
    combined = f"{url} {text}".lower()
    for keyword, product_type in PRODUCT_KEYWORDS.items():
        if keyword in combined:
            return product_type
    return "Eco Product"


def _extract_claims(text):
    normalized = (text or "").lower().replace("-", " ").replace("_", " ")
    text_lower = " ".join(normalized.split())
    claims = []

    for phrase in ECO_CLAIM_PATTERNS:
        if phrase in text_lower:
            claims.append(phrase)

    for keyword in [
        "recycled", "bpa free", "bpa", "organic", "eco", "water bottle",
        "reusable", "certified", "fair trade", "compostable", "vegan"
    ]:
        if keyword in text_lower and keyword not in claims:
            claims.append(keyword)

    if not claims:
        title_words = [part for part in re.findall(r"[a-zA-Z]+", text_lower) if len(part) > 3]
        claims = list(dict.fromkeys(title_words[:5]))

    return claims[:10]


def _extract_image_url(soup):
    candidates = []

    def add_candidate(value):
        if isinstance(value, list):
            for item in value:
                add_candidate(item)
            return
        if isinstance(value, dict):
            for key in ("url", "contentUrl", "image", "image_url", "product_image"):
                if key in value:
                    add_candidate(value[key])
            return
        if not isinstance(value, str):
            return
        value = value.strip()
        if value.startswith("data:image"):
            return
        if value.startswith("//"):
            value = "https:" + value
        if value.startswith("/"):
            value = "https://" + urlparse(soup.base.get("href", "") if soup.base else "").netloc + value
        if value.startswith("http") and value not in candidates:
            candidates.append(value)

    for script in soup.select("script[type='application/ld+json']"):
        try:
            add_candidate(json.loads(script.string or script.get_text()))
        except (TypeError, json.JSONDecodeError):
            continue

    for script in soup.select("script"):
        script_text = script.string or script.get_text()
        for match in re.findall(r'https?[^"\\ ]+?(?:jpg|jpeg|png|webp)(?:\\?[^"\\ ]*)?', script_text, re.IGNORECASE):
            add_candidate(match.replace("\\/", "/"))

    selectors = [
        "meta[property='og:image']",
        "meta[name='twitter:image']",
        "meta[name='image']",
        "meta[property='twitter:image']",
        "img[src]",
        "img[data-src]",
        "img[data-lazy-src]",
        "source[srcset]"
    ]

    for selector in selectors:
        for tag in soup.select(selector):
            value = tag.get("content") or tag.get("src") or tag.get("data-src") or tag.get("data-lazy-src") or tag.get("srcset")
            if not value:
                continue
            if value.startswith("data:image"):
                continue
            if value.startswith("//"):
                value = "https:" + value
            add_candidate(value)

    if not candidates:
        return ""

    for candidate in candidates:
        if "jpg" in candidate.lower() or "jpeg" in candidate.lower() or "png" in candidate.lower() or "webp" in candidate.lower():
            return candidate
    return candidates[0]


def _make_quick_review(title, product_type, claims, text):
    clean_text = (text or "").lower()
    if not claims and not clean_text:
        return f"{title} ko quick product check ke liye review bana rahe hain; abhi product page par detailed sustainability proof clear nahi dikh rahi."

    if any(word in clean_text for word in ["organic", "recycled", "certified", "fair trade", "bpa free"]):
        return f"{title} me kuch eco-signals mil rahe hain, lekin authenticity verify karne ke liye product page par clear sourcing aur certification proof chahiye."

    return f"{title} ko product preview ke hisaab se dekha gaya; page par eco-claim milte hain, lekin real proof aur transparent material info missing hai."


def extract_product_signals(html_text, url):
    soup = BeautifulSoup(html_text or "", "html.parser")
    title = ""
    for selector in ["meta[property='og:title']", "meta[name='title']", "title"]:
        tag = soup.select_one(selector)
        if tag:
            value = tag.get("content") or tag.get_text(" ", strip=True)
            if value:
                title = value
                break

    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(" ", strip=True)

    meta_desc = ""
    meta_tag = soup.select_one("meta[name='description'], meta[property='og:description']")
    if meta_tag:
        meta_desc = meta_tag.get("content", "")

    body_text = soup.get_text(" ", strip=True)
    clean_text = _normalize_space(body_text)
    short_text = clean_text[:8000]

    claims = _extract_claims(f"{title} {meta_desc} {short_text}")
    if not claims:
        pieces = [title, meta_desc, short_text]
        for piece in pieces:
            if piece and len(piece) > 20:
                claims.append(piece[:80])

    og_image = _extract_image_url(soup)

    return {
        "title": _normalize_space(title) or _get_title_from_url(url),
        "description": _normalize_space(meta_desc),
        "text": short_text,
        "claims": claims,
        "image": og_image,
    }


def _safe_json_loads(raw_value):
    if not raw_value:
        return {}
    cleaned = raw_value.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)
    try:
        return json.loads(cleaned)
    except Exception:
        return {}


def _generate_fallback_report(product_type, title, text, url):
    claim_list = _extract_claims(f"{title} {text}")
    score = 62
    if len(claim_list) >= 4:
        score = 70
    if "recycled" in text.lower() or "organic" in text.lower():
        score += 5
    if "bpa free" in text.lower() or "certified" in text.lower() or "fair trade" in text.lower():
        score += 4
    score = max(35, min(92, score))

    if score >= 78:
        verdict = "Low Greenwashing Risk"
    elif score >= 60:
        verdict = "Moderate Greenwashing Risk"
    else:
        verdict = "High Greenwashing Risk"

    review = _make_quick_review(title, product_type, claim_list, text)

    categories = [
        {"name": "Material Sustainability", "score": 7 if "recycled" in text.lower() or "organic" in text.lower() else 5, "reason": "Page text me material claims dikhi, lekin proof kaafi consistent nahi hai."},
        {"name": "Ethical & Fair Sourcing", "score": 6, "reason": "Sourcing and labor detail page par clear nahi dikh rahi."},
        {"name": "Packaging & Circularity", "score": 6, "reason": "Packaging reuse aur circularity ka mention inconsistent hai."},
        {"name": "Claim Authenticity", "score": 5, "reason": "Eco claims mil rahe hain, par verification details missing hain."},
    ]

    pros = []
    cons = []
    if "recycled" in text.lower() or "organic" in text.lower():
        pros.append("Page me eco-conscious material language dikh rahi hai.")
    else:
        pros.append("Product category ko sustainable positioning ke liye attempt kiya gaya hai.")
    if "certified" in text.lower() or "fair trade" in text.lower():
        pros.append("Claim support ke liye certification mention mil raha hai.")
    else:
        pros.append("Product ko greener positioning ke hisaab se present kiya gaya hai.")

    if "plastic free" in text.lower() or "bpa free" in text.lower():
        cons.append("Specific performance claims ka proof page par weak lag raha hai.")
    else:
        cons.append("Brand ke eco-claims ki authenticity ko verify karne ke liye zyada evidence chahiye, aur website par proof missing hai.")
    cons.append("Packaging, sourcing, and lifecycle transparency detailed nahi mil rahi, isliye kisi bhi website se genuine proof verify karna mushkil hota hai.")

    alternative = (
        "Aisi product choose karein jisme material source, certifications, and lifecycle info clearly mention ho. "
        "Certified recycled, fair-trade, or transparent supply-chain wale brands better option hain."
    )

    return {
        "product_type": product_type,
        "green_trust_score": round(score),
        "ai_authenticity_score": round(score),
        "verdict": verdict,
        "review": review,
        "categories": categories,
        "pros": pros[:2],
        "cons": cons[:2],
        "alternative_suggestion": alternative,
        "claims_detected": [{"phrase": claim} for claim in claim_list[:10]],
        "cert_checks": [],
    }


def _call_gemini_report(product_type, title, url, content_text):
    if genai is None or not GOOGLE_API_KEY:
        return None

    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = f"""
You are an expert sustainability auditor. Analyze the actual product page content only.

Product Title: {title}
URL: {url}
Product Category: {product_type}

Actual page text extracted from the URL:
{content_text[:7000]}

Give a realistic greenwashing assessment in Hinglish and return ONLY valid JSON. Use this exact structure:
{{
  "product_type": "...",
  "green_trust_score": 68,
  "verdict": "Moderate Greenwashing Risk",
  "review": "Detailed Hinglish review here",
  "categories": [
        {{"name": "Material Sustainability", "score": 7, "reason": "..."}},
        {{"name": "Ethical & Fair Sourcing", "score": 6, "reason": "..."}},
        {{"name": "Packaging & Circularity", "score": 6, "reason": "..."}},
        {{"name": "Claim Authenticity", "score": 5, "reason": "..."}}
  ],
  "pros": ["...", "..."],
  "cons": ["...", "..."],
  "alternative_suggestion": "..."
}}
        """
        response = model.generate_content(prompt)
        raw_text = getattr(response, "text", "") or ""
        parsed = _safe_json_loads(raw_text)
        if parsed:
            return parsed
    except Exception as e:
        print(f"Gemini analysis failed: {e}")
    return None


def fetch_product_page(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.text
    except Exception:
        return ""


def _analyze(data: dict):
    if not isinstance(data, dict):
        return {"error": "Invalid payload."}

    url = str(data.get("url", "")).strip()
    if not url:
        return {"error": "Please provide a valid product URL."}

    html_text = fetch_product_page(url)
    signals = extract_product_signals(html_text, url)
    title = signals["title"] or _get_title_from_url(url)
    product_type = _detect_product_type(url, f"{title} {signals['description']} {signals['text']}")
    product_image = signals["image"] or DEFAULT_IMAGES.get(product_type, DEFAULT_IMAGES["Eco Product"])

    report = _call_gemini_report(product_type, title, url, signals["text"])
    if not report:
        report = _generate_fallback_report(product_type, title, signals["text"], url)

    if "green_trust_score" not in report and "ai_authenticity_score" in report:
        report["green_trust_score"] = report["ai_authenticity_score"]
    if "product_type" not in report:
        report["product_type"] = product_type
    if "product_title" not in report:
        report["product_title"] = title
    if "product_image" not in report:
        report["product_image"] = product_image
    if "verdict" not in report:
        report["verdict"] = "Moderate Greenwashing Risk"
    if "claims_detected" not in report:
        report["claims_detected"] = [{"phrase": claim} for claim in signals["claims"]]
    if "cert_checks" not in report:
        report["cert_checks"] = []
    if "review" not in report:
        report["review"] = f"Product {title} ke liye review available nahi tha."

    return {
        "product_type": report.get("product_type", product_type),
        "product_title": report.get("product_title", title),
        "product_image": report.get("product_image", product_image),
        "green_trust_score": report.get("green_trust_score", report.get("ai_authenticity_score", 62)),
        "ai_authenticity_score": report.get("ai_authenticity_score", report.get("green_trust_score", 62)),
        "verdict": report.get("verdict", "Moderate Greenwashing Risk"),
        "review": report.get("review", "No review available."),
        "categories": report.get("categories", []),
        "claims_detected": report.get("claims_detected", [{"phrase": claim} for claim in signals["claims"]]),
        "cert_checks": report.get("cert_checks", []),
        "pros": report.get("pros", []),
        "cons": report.get("cons", []),
        "alternative_suggestion": report.get("alternative_suggestion", "Choose a more transparent option with clear certifications."),
    }


@app.post("/analyze")
def analyze(data: dict):
    try:
        return _analyze(data)
    except Exception as e:
        print("=== /analyze CRASHED ===")
        traceback.print_exc()
        return {"error": f"Backend execution error: {str(e)}"}


@app.get("/")
def health_check():
    return {"status": "ok"}
