import requests
from bs4 import BeautifulSoup
from pathlib import Path
import urllib.parse
import re

def _normalize_url(url: str) -> str:
    """Strip query parameters and fragments to identify duplicate images.
    Specifically handles Next.js image optimization URLs by extracting the underlying source.
    """
    # 1. Handle Next.js /_next/image wrapper
    if "/_next/image" in url:
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        if "url" in query:
            # Extract the nested URL and resolve it
            url = query["url"][0]

    # 2. Strip standard query params and fragments
    return url.split('?')[0].split('#')[0].strip()

def scrape_url(url: str) -> dict:
    """
    Scrape text and images from a given URL based on specific ARIA roles.
    Returns: {"text": str, "images": list[str]}
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    text_elements = []
    
    # 1. Extract Headings (<h1 role="heading"> and <h2 role="heading">)
    for heading in soup.find_all(['h1', 'h2'], role="heading"):
        text = heading.get_text(strip=True)
        if text:
            text_elements.append(text)
            
    # 2. Extract Text (<p role="paragraph">)
    for para in soup.find_all('p', role="paragraph"):
        text = para.get_text(strip=True)
        if text:
            text_elements.append(text)
            
    # FALLBACK: If the specific roles yielded nothing, use general text extraction
    if not text_elements:
        for heading in soup.find_all(['h1', 'h2']):
            text = heading.get_text(strip=True)
            if text:
                text_elements.append(text)
        for para in soup.find_all('p'):
            text = para.get_text(strip=True)
            if text:
                text_elements.append(text)
            
    combined_text = "\n".join(text_elements)
    
    # 3. Extract Images
    image_list = []
    normalized_seen = set()
    
    # Primary: usually the highest quality cover image is in the meta tag
    meta_image = soup.find("meta", property="og:image")
    if meta_image and meta_image.get("content"):
        img_url = urllib.parse.urljoin(url, meta_image.get("content"))
        norm_url = _normalize_url(img_url)
        image_list.append(img_url)
        normalized_seen.add(norm_url)
        
    # Container-based scoping: search only inside the main content block to avoid sidebars/authors
    main_section = (
        soup.find("main", class_="main__content") or 
        soup.find("div", class_="content__section") or
        soup.find("article") or
        soup
    )

    # 4. Extract img tags with role="image" (high priority)
    for img in main_section.find_all("img", role="image"):
        src = img.get("src")
        if src and not src.startswith("data:"):
            abs_src = urllib.parse.urljoin(url, src)
            norm_src = _normalize_url(abs_src)
            if norm_src not in normalized_seen:
                image_list.append(abs_src)
                normalized_seen.add(norm_src)
            
    # FALLBACK for images: get standard article images, but filter out layout junk and sidebar noise
    # We cap at 10 total candidate images to ensure we have enough after size filtering in server.py
    if len(image_list) < 10:
        for img in main_section.find_all("img"):
            if len(image_list) >= 10:
                break
                
            src = img.get("src")
            # Also check data-src or original-src which news sites sometimes use for lazy loading
            src = src or img.get("data-src") or img.get("data-original")
            
            if not src or src.startswith("data:"):
                continue
                
            abs_src = urllib.parse.urljoin(url, src)
            norm_src = _normalize_url(abs_src)
            
            # Skip if already seen (via normalized URL)
            if norm_src in normalized_seen:
                continue

            # Filtering heuristics
            lower_src = abs_src.lower()
            
            junk_keywords = [
                'logo', 'icon', 'profile', 'avatar', 'svg', 'blank', '.gif', '1x1', 'default',
                'author', 'video', 'related', 'newsletter', 'newsletter-icon', 'sprite',
                'reporter', 'editor', 'staff', 'pwa-data', 'thumb-'
            ]
            if any(bad in lower_src for bad in junk_keywords):
                continue
                
            # Filter by HTML attributes if present (skip small author icons early)
            try:
                w = int(img.get("width", 201))
                h = int(img.get("height", 201))
                if w < 200 or h < 200:
                    continue
            except (ValueError, TypeError):
                pass

            image_list.append(abs_src)
            normalized_seen.add(norm_src)
            
    return {
        "text": combined_text,
        "images": image_list
    }

def download_image(url: str, out_path: str | Path):
    """
    Downloads an image from the specified URL and saves it to out_path.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    resp = requests.get(url, headers=headers, stream=True, timeout=15)
    resp.raise_for_status()
    
    out_path = Path(out_path)
    # Ensure parents exist
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
