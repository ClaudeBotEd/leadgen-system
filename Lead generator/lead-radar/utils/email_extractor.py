"""Email extractie + validatie helpers.

- Vindt emails in HTML/tekst
- Filtert obfuscated emails (info[at]domain[dot]com)
- Filtert valid email syntax (RFC 5322 light)
- Optioneel: MX-record check via dnspython
"""

import re
from typing import Iterable

EMAIL_RE = re.compile(
    r"(?:[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*)"
    r"@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?"
)

# Strict obfuscated email pattern — requires:
#  - whitespace OR explicit brackets around "at"/"dot"
#  - dat zorgt dat 'gstatic.com' of 'cookieblocksrc' niet als email matcht
OBFUSCATED_RE = re.compile(
    r"([a-zA-Z0-9._%+-]+)"
    r"(?:"
        r"\s+(?:at|AT)\s+"                  # info at example
        r"|\s*\[\s*(?:at|AT|@)\s*\]\s*"     # info [at] example
        r"|\s*\(\s*(?:at|AT|@)\s*\)\s*"     # info (at) example
        r"|\s*\{\s*(?:at|AT|@)\s*\}\s*"     # info {at} example
    r")"
    r"([a-zA-Z0-9.-]+)"
    r"(?:"
        r"\s+(?:dot|DOT)\s+"
        r"|\s*\[\s*(?:dot|DOT|\.)\s*\]\s*"
        r"|\s*\(\s*(?:dot|DOT|\.)\s*\)\s*"
        r"|\s*\{\s*(?:dot|DOT|\.)\s*\}\s*"
    r")"
    r"([a-zA-Z]{2,})"
)

BLACKLIST_LOCAL_PARTS = {
    "no-reply", "noreply", "donotreply", "do-not-reply",
    "postmaster", "mailer-daemon", "abuse",
    "example", "test", "demo", "user",
}

# Local-part prefixen die wijzen op asset / URL fragment, geen echte email
ASSET_PREFIXES = (
    "www.", "api.", "cdn.", "static.", "assets.", "img.", "image.",
    "fonts.", "iframe.", "element.", "script.", "style.", "stylesheet.",
    "media.", "video.", "audio.", "font.", "icon.",
    "track.", "tracker.", "tag.", "tags.", "pixel.",
    "analytics.", "metrics.", "ads.", "ad.",
    "youtu.", "youtube.", "twitter.", "facebook.", "instagram.",
    "google.", "googleads.", "googletagmanager.",
)

BLACKLIST_DOMAINS = {
    "example.com", "example.org", "example.net",
    "domain.com", "yourdomain.com", "company.com",
    "test.com", "sentry.io", "wixpress.com",
    "godaddy.com", "wix.com", "squarespace.com",
    "wordpress.com", "shopify.com",
    "sentry-next.wixpress.com",
    # CDN's en third-party assets die emails-achtig kunnen lijken
    "gstatic.com", "googleapis.com", "googletagmanager.com",
    "google-analytics.com", "googleadservices.com", "doubleclick.net",
    "cloudflare.com", "cloudfront.net", "akamaihd.net", "akamai.net",
    "fbcdn.net", "twimg.com", "ytimg.com",
    "jquery.com", "bootstrapcdn.com", "jsdelivr.net", "unpkg.com",
    "cookielaw.org", "onetrust.com", "cookiebot.com",
    "facebook.com", "instagram.com", "twitter.com", "linkedin.com",
    "youtube.com", "tiktok.com", "pinterest.com",
    "whatsapp.com", "wa.me",
    "schema.org", "w3.org",
}

# Whitelist van bekende geldige TLD's — vooral NL/BE focus + grote internationale
KNOWN_TLDS = {
    # NL/BE/EU
    "nl", "be", "eu", "lu", "de", "fr", "uk", "ie", "es", "it", "pt", "at",
    "ch", "se", "no", "dk", "fi", "pl", "cz", "hu", "ro", "gr",
    # Internationaal
    "com", "net", "org", "info", "biz", "co", "io", "ai", "app",
    "tech", "shop", "store", "online", "site", "website", "world",
    "agency", "company", "services", "expert", "pro",
    "email", "mail", "name",
    # Branche
    "energy", "solar", "construction", "design", "build", "build",
    "estate", "rental", "house", "home", "tools",
    # Anders
    "us", "ca", "au", "nz", "jp", "cn", "in", "br", "mx", "ru",
}

FILE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".css", ".js", ".html", ".htm", ".json", ".xml",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
}


def extract_emails(text: str) -> list[str]:
    """Vind alle emails in een tekst (HTML of plain). Returns deduplicated lowercase list."""
    if not text:
        return []

    found: set[str] = set()

    for match in EMAIL_RE.findall(text):
        found.add(match.lower())

    for local, domain, tld in OBFUSCATED_RE.findall(text):
        candidate = f"{local}@{domain}.{tld}".lower()
        if EMAIL_RE.fullmatch(candidate):
            found.add(candidate)

    return [e for e in sorted(found) if is_usable_email(e)]


def is_usable_email(email: str) -> bool:
    """True als email syntactisch valide en niet op blacklist staat."""
    email = email.lower().strip()
    if not EMAIL_RE.fullmatch(email):
        return False

    local, _, domain = email.partition("@")
    if not local or not domain:
        return False

    # Hard blacklist
    if local in BLACKLIST_LOCAL_PARTS:
        return False
    for blocked in BLACKLIST_LOCAL_PARTS:
        if local.startswith(blocked):
            return False

    # Asset / URL fragments — local part begint met www. / api. / fonts. / etc.
    for prefix in ASSET_PREFIXES:
        if local.startswith(prefix):
            return False

    # Domain blacklist (CDN's, social platforms, etc.)
    if domain in BLACKLIST_DOMAINS:
        return False
    for blocked_domain in BLACKLIST_DOMAINS:
        if domain.endswith("." + blocked_domain):
            return False

    # File extension false positives
    for ext in FILE_EXTENSIONS:
        if email.endswith(ext):
            return False

    # Substrings die wijzen op asset/script
    suspicious_substrings = (
        "sentry", "wixpress", "googleusercontent",
        "rocketlazyload", "lazyload", "cookieblock",
        "wp-content", "wpcontent", "asset.", "assets.",
        "polyfill", "addthis", "googletag", "tagmanager",
    )
    if any(s in domain for s in suspicious_substrings):
        return False
    if any(s in local for s in suspicious_substrings):
        return False

    # TLD validatie — moet bekende TLD zijn (anti-junk: cookieblocksrc, rocketlazyloaded)
    tld = domain.rsplit(".", 1)[-1]
    if not (2 <= len(tld) <= 24):
        return False
    if tld not in KNOWN_TLDS:
        return False

    # Te veel dots in local part = waarschijnlijk URL fragment
    if local.count(".") > 2:
        return False

    return True


def rank_emails(emails: Iterable[str]) -> list[str]:
    """Sorteer emails op kwaliteit (named > info@ > sales@ > rest)."""
    high_quality_locals = ("contact", "info", "office", "hello", "hallo", "welkom")
    medium_quality_locals = ("sales", "support", "klantenservice", "service")

    def score(email: str) -> int:
        local = email.split("@")[0].lower()
        if "." in local and not any(local.startswith(p) for p in high_quality_locals + medium_quality_locals):
            return 0
        if 3 <= len(local) <= 12 and local.isalpha():
            return 1
        if any(local.startswith(p) for p in high_quality_locals):
            return 2
        if any(local.startswith(p) for p in medium_quality_locals):
            return 3
        return 4

    return sorted(set(emails), key=score)


def has_mx_record(domain: str, timeout: float = 3.0) -> bool:
    """Check of domein MX records heeft. Gebruikt dnspython als beschikbaar."""
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        answers = resolver.resolve(domain, "MX")
        return len(answers) > 0
    except Exception:
        return False


if __name__ == "__main__":
    sample = """
    Mail naar info@voorbeeld-installatie.nl of bel 020-1234567.
    Voor offertes: jan.devries [at] voorbeeld-installatie [dot] nl
    Algemeen: contact (at) installatiebedrijf-amsterdam (dot) nl
    Niet versturen naar: noreply@spam.com of info@example.com
    """
    print("Found emails:", extract_emails(sample))
    print("Ranked:", rank_emails(extract_emails(sample)))
