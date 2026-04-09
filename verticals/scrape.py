import requests
from bs4 import BeautifulSoup
from pathlib import Path
import urllib.parse

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
    
    # Primary: usually the highest quality cover image is in the meta tag
    meta_image = soup.find("meta", property="og:image")
    if meta_image and meta_image.get("content"):
        image_list.append(urllib.parse.urljoin(url, meta_image.get("content")))
        
    # User specified: extract img tags with role="image"
    for img in soup.find_all("img", role="image"):
        src = img.get("src")
        if src and not src.startswith("data:"):
            abs_src = urllib.parse.urljoin(url, src)
            if abs_src not in image_list:
                image_list.append(abs_src)
            
    # FALLBACK for images: get standard article images, but filter out layout junk and sidebar noise
    # We cap at 5 total images to ensure we only get the most relevant ones at the top
    if len(image_list) < 5:
        for img in soup.find_all("img"):
            if len(image_list) >= 5:
                break
                
            src = img.get("src")
            if not src or src.startswith("data:"):
                continue
                
            abs_src = urllib.parse.urljoin(url, src)
            lower_src = abs_src.lower()
            
            # Expanded heuristic to weed out author profiles, related videos, icons, etc.
            # India Today often uses 'medium_crop' or 'author' for irrelevant sidebar images
            junk_keywords = [
                'logo', 'icon', 'profile', 'avatar', 'svg', 'blank', '.gif', '1x1', 'default',
                'author', 'video', 'related', 'newsletter', 'newsletter-icon', 'sprite'
            ]
            if any(bad in lower_src for bad in junk_keywords):
                continue
                
            if abs_src not in image_list:
                image_list.append(abs_src)
            
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
