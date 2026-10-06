"""Safe email rendering: scripts stripped, a Content-Security-Policy that blocks scripts, and remote
images (which can track you) blocked until the user allows them. Never show raw email HTML elsewhere."""
import html
import re


_PAIRED = re.compile(r"(?is)<(script|iframe|object|embed)\b.*?</\1\s*>")  # tag and its content
_SINGLE = re.compile(r"(?is)</?(script|iframe|object|embed|form|meta|link|base)\b[^>]*>")  # leftover tags
_EVENTS = re.compile(r"""(?i)\s+on\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""")  # onclick= and other event handlers
_JS_URL = re.compile(r"(?i)(href|src)\s*=\s*([\"'])\s*javascript:[^\"']*\2")  # javascript: links
_REMOTE_IMG = re.compile(r"""(?i)<img\b[^>]*\bsrc\s*=\s*["']https?://""")  # Images loaded from the internet


def remote_images(body_html: str | None) -> int:
    return len(_REMOTE_IMG.findall(body_html or ""))


def email_document(body_html: str | None, text: str, show_images: bool) -> str:
    """A self-contained page for the email. Scripts are stripped, and the page's security policy blocks any
    script that slips through; remote images (which can track you) load only when show_images is on."""
    if body_html:
        content = _JS_URL.sub(r'\1="#"', _EVENTS.sub("", _SINGLE.sub("", _PAIRED.sub("", body_html))))
    else:
        linked = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', html.escape(text))
        content = "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in linked.split("\n\n"))
    # Security policy: remote images only when allowed
    images = "img-src data: https: http:;" if show_images else "img-src data:;"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; {images}">
<base target="_blank"><style>
body{{margin:0;padding:18px 20px;font:15px/1.6 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1f2937;background:#fff}}
img{{max-width:100%;height:auto}} a{{color:#4F46E5}} p{{margin:0 0 12px}}
</style></head><body>{content}</body></html>"""
