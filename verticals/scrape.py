import requests
from bs4 import BeautifulSoup
from pathlib import Path

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
    
    # 3. Extract Images (<img role="image">)
    image_list = []
    # User specified: ignore spans. Beautiful soup automatically pulls the img tags only.
    for img in soup.find_all("img", role="image"):
        src = img.get("src")
        if src and src not in image_list:
            image_list.append(src)
            
    # FALLBACK for images
    if not image_list:
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src not in image_list:
                image_list.append(src)
            
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
