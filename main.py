import os
import re
import urllib.parse
from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="HLS Proxy API - Production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Origin": "https://www.pw.live",
    "Referer": "https://www.pw.live/"
}

ALLOWED_DOMAINS = ["pw.live", "penstudios.co.in", "vimeo.com", "cloudfront.net"]

def validate_url(url: str):
    parsed = urllib.parse.urlparse(url)
    if not any(domain in parsed.netloc for domain in ALLOWED_DOMAINS):
        raise HTTPException(status_code=400, detail="Disallowed target URL domain.")

def make_absolute(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = base_url.rsplit('/', 1)[0] + '/'
    return urllib.parse.urljoin(base, path)

@app.get("/pw")
async def get_playlist(url: str, token: str, request: Request):
    validate_url(url)
    headers = DEFAULT_HEADERS.copy()
    headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            content = resp.text
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    base_api_url = str(request.base_url)
    encoded_token = urllib.parse.quote(token, safe='')

    def replace_key_uri(match):
        absolute_key_url = make_absolute(url, match.group(1))
        encoded_key_url = urllib.parse.quote(absolute_key_url, safe='')
        return f'URI="{base_api_url}key_proxy?url={encoded_key_url}&token={encoded_token}"'

    content = re.sub(r'URI="([^"]+)"', replace_key_uri, content)

    def replace_nested_m3u8(match):
        absolute_nested_url = make_absolute(url, match.group(0))
        encoded_nested = urllib.parse.quote(absolute_nested_url, safe='')
        return f"{base_api_url}pw?url={encoded_nested}&token={encoded_token}"

    content = re.sub(r'^(?!#)(\S+\.m3u8\S*)$', replace_nested_m3u8, content, flags=re.MULTILINE)

    def replace_segment(match):
        return make_absolute(url, match.group(0))

    content = re.sub(r'^(?!#)(\S+\.ts\S*)$', replace_segment, content, flags=re.MULTILINE)

    return Response(content=content, media_type="application/vnd.apple.mpegurl")

@app.get("/key_proxy")
async def proxy_key(url: str, token: str):
    validate_url(url)
    headers = DEFAULT_HEADERS.copy()
    headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return Response(content=resp.content, media_type="application/octet-stream")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Key proxy error: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
