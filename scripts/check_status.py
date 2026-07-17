#!/usr/bin/env python3
"""
Domain redirect monitor.

Reads domains.json (brands -> list of domains + the "final" destination domain),
requests each URL, follows redirects, and records the full redirect chain,
final destination, HTTP status code, and response time.

Writes the result to data/status.json, which the static page (index.html) reads.
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "domains.json")
OUTPUT_PATH = os.path.join(ROOT, "data", "status.json")

TIMEOUT = 10          # seconds
USER_AGENT = "Mozilla/5.0 (compatible; DomainStatusBot/1.0; +https://github.com/)"
MAX_REDIRECTS = 10


def normalize_url(domain: str) -> str:
    """Add https:// if the domain has no scheme."""
    domain = domain.strip()
    if domain.startswith("http://") or domain.startswith("https://"):
        return domain
    return f"https://{domain}"


def check_domain(domain: str) -> dict:
    """
    Follow redirects for a single domain and return a result dict.
    Falls back to http:// if https:// fails outright (connection-level error).
    """
    url = normalize_url(domain)
    session = requests.Session()
    session.max_redirects = MAX_REDIRECTS

    result = {
        "domain": domain,
        "requested_url": url,
        "ok": False,
        "status_code": None,
        "final_url": None,
        "redirect_chain": [],
        "error": None,
        "scheme_used": "https",
    }

    for scheme, attempt_url in (("https", url), ("http", url.replace("https://", "http://", 1))):
        try:
            resp = session.get(
                attempt_url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
                allow_redirects=True,
            )

            chain = [{"url": r.url, "status_code": r.status_code} for r in resp.history]
            chain.append({"url": resp.url, "status_code": resp.status_code})

            result.update(
                {
                    "ok": True,
                    "status_code": resp.status_code,
                    "final_url": resp.url,
                    "redirect_chain": chain,
                    "error": None,
                    "scheme_used": scheme,
                }
            )
            return result

        except requests.exceptions.TooManyRedirects:
            result["error"] = f"Too many redirects (>{MAX_REDIRECTS})"
        except requests.exceptions.SSLError as e:
            result["error"] = f"SSL error: {e}"
            continue  # try http:// fallback
        except requests.exceptions.ConnectionError as e:
            result["error"] = f"Connection error: {e}"
            continue  # try http:// fallback
        except requests.exceptions.Timeout:
            result["error"] = f"Timed out after {TIMEOUT}s"
        except requests.exceptions.RequestException as e:
            result["error"] = f"Request failed: {e}"

        # Non-retryable failure on this scheme
        break

    return result


def main():
    if not os.path.exists(CONFIG_PATH):
        print(f"Config not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    output = {
        "last_checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "brands": [],
    }

    for brand in config.get("brands", []):
        brand_name = brand["name"]
        live_domain = brand.get("live", brand.get("final"))

        # "domains" entries can be a plain string, or an object like
        # {"domain": "pgslot.sh", "date": "May 24, 2024"} to record when it
        # was added — the date is only used for display, read directly from
        # domains.json by the page. "reserve" is an object mapping a badge
        # label -> domain, e.g. {"Reserve 1": "pgslot5.sh"} — those domains
        # get checked too, and are displayed after the live domain.
        all_domains = []
        for entry in brand.get("domains", []):
            dom = entry.get("domain") if isinstance(entry, dict) else entry
            if dom and dom not in all_domains:
                all_domains.append(dom)

        reserve = brand.get("reserve", {})
        if isinstance(reserve, dict):
            for dom in reserve.values():
                if dom and dom not in all_domains:
                    all_domains.append(dom)

        if live_domain and live_domain not in all_domains:
            all_domains.append(live_domain)

        print(f"Checking brand: {brand_name} ({len(all_domains)} domains)")
        checked = []
        for domain in all_domains:
            print(f"  -> {domain}")
            res = check_domain(domain)
            res["is_final"] = domain == live_domain
            checked.append(res)

        output["brands"].append({"name": brand_name, "final": live_domain, "live": live_domain, "domains": checked})

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()