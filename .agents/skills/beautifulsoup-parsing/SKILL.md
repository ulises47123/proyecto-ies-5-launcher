---
name: beautifulsoup-parsing
description: >-
  Expert guide for BeautifulSoup HTML parsing, CSS selectors, regex searching,
  robust DOM navigation, attribute extraction, and web scraping fallback strategies.
---

# BeautifulSoup Parsing & Web Scraping Skill Guide

This skill provides production-grade techniques for HTML parsing, DOM navigation, and resilient scraping using `BeautifulSoup4` in Python.

---

## 1. Robust Element & Attribute Extraction

```python
import re
from bs4 import BeautifulSoup

def extract_profile_image(html_content: str, base_url: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Search by class, id, or src patterns with regex case-insensitive matching
    img_tag = (
        soup.find('img', class_=re.compile(r'perfil|foto|avatar|user', re.I)) or
        soup.find('img', src=re.compile(r'foto|ver_foto|archivos|imagen|perfil', re.I)) or
        soup.find('img')
    )
    
    if img_tag and img_tag.get('src'):
        src = img_tag.get('src', '').strip()
        if src and not any(ignored in src.lower() for ignored in ['spacer', 'pixel', 'blank', 'bullet', 'icon']):
            return src if src.startswith('http') else f"{base_url.rstrip('/')}/{src.lstrip('/')}"
            
    return ""
```

---

## 2. Table & Grid Parsing Strategies

- Use CSS selectors (`soup.select('table.listado tr')`) or `find_all('tr')`.
- Always check column length before indexing `tds[1]`.
- Clean text whitespace with `.strip()` or custom `limpiar_html()` utility.
