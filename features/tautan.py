import ipaddress
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

MAX_URL_LENGTH = 2000
MAX_HTML_BYTES = 350_000
REQUEST_TIMEOUT = 8
BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.google.com/',
}


class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.metas = {}
        self.json_ld = []
        self._in_title = False
        self._in_ld = False
        self._ld_chunks = []

    def handle_starttag(self, tag, attrs):
        data = {str(key).lower(): value for key, value in attrs}
        if tag == 'title':
            self._in_title = True
        elif tag == 'meta':
            key = (data.get('property') or data.get('name') or data.get('itemprop') or '').strip().lower()
            content = (data.get('content') or '').strip()
            if key and content and key not in self.metas:
                self.metas[key] = content
        elif tag == 'script' and 'ld+json' in (data.get('type') or '').lower():
            self._in_ld = True
            self._ld_chunks = []

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False
        if tag == 'script' and self._in_ld:
            self._in_ld = False
            payload = ''.join(self._ld_chunks).strip()
            if payload:
                self.json_ld.append(payload)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_ld:
            self._ld_chunks.append(data)


def _host_dilarang(hostname):
    host = (hostname or '').strip().lower().rstrip('.')
    if not host or host in {'localhost', 'metadata.google.internal'}:
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    except ValueError:
        return False


def normalisasi_url(value):
    url = (value or '').strip()
    if not url or len(url) > MAX_URL_LENGTH:
        return ''
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc or _host_dilarang(parsed.hostname):
        return ''
    return url


def _nilai_ld(node, key):
    if isinstance(node, dict):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, str):
                return first.strip()
            if isinstance(first, dict):
                return (first.get('url') or first.get('contentUrl') or '').strip()
        if isinstance(value, dict):
            return (value.get('url') or value.get('contentUrl') or '').strip()
        for child in node.values():
            found = _nilai_ld(child, key)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _nilai_ld(item, key)
            if found:
                return found
    return ''


def _dari_json_ld(blobs):
    title = ''
    image = ''
    for blob in blobs:
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        title = title or _nilai_ld(data, 'name')
        image = image or _nilai_ld(data, 'image')
        if title and image:
            break
    return title, image


def ambil_preview_tautan(url):
    url = normalisasi_url(url)
    if not url:
        return None

    parsed = urlparse(url)
    fallback = {
        'url': url,
        'title': parsed.hostname.replace('www.', '') if parsed.hostname else 'Tautan produk',
        'image': '',
        'site': parsed.hostname.replace('www.', '') if parsed.hostname else '',
    }

    try:
        response = requests.get(
            url,
            headers=BROWSER_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            stream=True,
        )
        final_url = normalisasi_url(response.url) or url
        content_type = (response.headers.get('Content-Type') or '').lower()
        if response.status_code >= 400 or 'text/html' not in content_type:
            fallback['url'] = final_url
            return fallback

        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            chunks.append(chunk)
            total += len(chunk)
            if total >= MAX_HTML_BYTES:
                break
        html = b''.join(chunks).decode(response.encoding or 'utf-8', errors='ignore')
    except requests.RequestException:
        return fallback

    parser = _MetaParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        fallback['url'] = final_url
        return fallback

    ld_title, ld_image = _dari_json_ld(parser.json_ld)
    title = (
        parser.metas.get('og:title')
        or parser.metas.get('twitter:title')
        or ld_title
        or parser.title
        or fallback['title']
    )
    image = (
        parser.metas.get('og:image')
        or parser.metas.get('og:image:secure_url')
        or parser.metas.get('twitter:image')
        or parser.metas.get('twitter:image:src')
        or ld_image
    )
    site = parser.metas.get('og:site_name') or fallback['site']
    title = re.sub(r'\s+', ' ', title).strip()[:300]
    image = urljoin(final_url, image.strip()) if image else ''
    if image and not normalisasi_url(image):
        image = ''

    return {
        'url': final_url,
        'title': title[:300],
        'image': image[:2000],
        'site': re.sub(r'\s+', ' ', site).strip()[:100],
    }
