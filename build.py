#!/usr/bin/env python3
"""Build a compact Android hosts file from selected StevenBlack sources."""

import argparse
import datetime as dt
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import requests


UPSTREAM = "https://github.com/StevenBlack/hosts.git"
SOURCES = (
    "StevenBlack",
    "adaway.org",
    "add.2o7Net",
    "someonewhocares.org",
    "yoyo.org",
)
# External sources supplement upstream StevenBlack; they are deduplicated below.
FROGEYE_URL = "https://hostfiles.frogeye.fr/firstparty-only-trackers-hosts.txt"
# The Auth-Key is passed through the Actions secret URLHAUS_AUTH_KEY.
URLHAUS_TEMPLATE = "https://urlhaus-api.abuse.ch/v2/files/exports/{key}/hostfile.txt"
MAX_TOTAL_DOMAINS = 55000


def load_external_hosts(url, source, max_source_domains):
    """Read a hosts/plain-domains feed. Never print authenticated URLs."""
    if not url.startswith("https://"):
        raise RuntimeError(source + ": HTTPS is required")
    try:
        response = requests.get(url, timeout=(15, 90), headers={"User-Agent": "segamalaga-hosts/2.0"})
        response.raise_for_status()
        if len(response.content) > 8_000_000:
            raise ValueError("feed is too large")
        body = response.content.decode("utf-8-sig")
    except (requests.RequestException, UnicodeError, ValueError):
        # Requests exceptions normally contain the URL, which may contain the key.
        raise RuntimeError(source + ": download failed; URL and credentials suppressed") from None

    domains = set()
    malformed = 0
    for raw in body.splitlines():
        line = raw.partition("#")[0].strip()
        if not line:
            continue
        fields = line.split()
        if fields[0] in ("0.0.0.0", "127.0.0.1") and len(fields) >= 2:
            candidates = fields[1:]
        elif len(fields) == 1:
            candidates = fields
        else:
            malformed += 1
            continue
        for domain in candidates:
            domain = domain.lower().rstrip(".")
            if domain == "localhost" or not DOMAIN.fullmatch(domain):
                malformed += 1
                continue
            try:
                ipaddress.ip_address(domain)
            except ValueError:
                domains.add(domain)
            else:
                malformed += 1
    if not (10 <= len(domains) <= max_source_domains):
        raise RuntimeError(f"{source}: unexpected domain count ({len(domains)})")
    if malformed > max(50, len(domains) // 20):
        raise RuntimeError(f"{source}: unexpectedly many malformed entries ({malformed})")
    return domains


DOMAIN = re.compile(r"(?i)^(?=.{1,253}$)[a-z0-9_-]+(?:\.[a-z0-9_-]+)+$")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "hosts")
    parser.add_argument("--windows-output", type=Path, default=Path(__file__).parent / "hosts-windows")
    args = parser.parse_args()

    # Prevent upstream update scripts from inheriting our URLhaus credential.
    clean_env = dict(os.environ)
    clean_env.pop("URLHAUS_AUTH_KEY", None)
    with tempfile.TemporaryDirectory(prefix="selected-hosts-") as tmp:
        repo = Path(tmp) / "upstream"
        subprocess.run(["git", "clone", "--depth", "1", "--quiet", UPSTREAM, str(repo)], check=True, env=clean_env)
        commit = subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=repo, text=True, env=clean_env).strip()

        data = repo / "data"
        for source in data.iterdir():
            if source.is_dir() and source.name not in SOURCES:
                shutil.rmtree(source)
        missing = set(SOURCES) - {p.name for p in data.iterdir() if p.is_dir()}
        if missing:
            raise RuntimeError("Selected upstream sources are missing: " + ", ".join(sorted(missing)))

        # Use the source snapshots from this upstream commit. This avoids mixing
        # one source updated today with another that could not be downloaded.
        subprocess.run(
            [sys.executable, "updateHostsFile.py", "--auto", "--noupdate", "--nogendata", "--skipstatichosts"],
            cwd=repo, check=True, stdout=subprocess.DEVNULL, env=clean_env,
        )

        domains = set()
        for line in (repo / "hosts").read_text(encoding="utf-8").splitlines():
            fields = line.partition("#")[0].split()
            if len(fields) < 2 or fields[0] not in ("0.0.0.0", "127.0.0.1"):
                continue
            for domain in fields[1:]:
                domain = domain.lower()
                if not DOMAIN.fullmatch(domain):
                    continue
                try:
                    ipaddress.ip_address(domain)
                except ValueError:
                    domains.add(domain)

        if len(domains) < 10000:
            raise RuntimeError("Unexpectedly few domains; the output was not replaced.")

        original_total = len(domains)
        frogeye = load_external_hosts(FROGEYE_URL, "Frogeye", 30000)
        domains.update(frogeye)
        print(f"Frogeye: {len(frogeye)} source; {len(domains)-original_total} unique added")

        key = os.environ.get("URLHAUS_AUTH_KEY", "").strip()
        if key:
            if not re.fullmatch(r"[A-Za-z0-9_-]{20,128}", key):
                raise RuntimeError("URLhaus: invalid Auth-Key format")
            before_urlhaus = len(domains)
            urlhaus = load_external_hosts(URLHAUS_TEMPLATE.format(key=key), "URLhaus", 30000)
            domains.update(urlhaus)
            print(f"URLhaus: {len(urlhaus)} source; {len(domains)-before_urlhaus} unique added")
        else:
            print("::warning::URLhaus disabled: configure Actions secret URLHAUS_AUTH_KEY")
        print(f"TOTAL {len(domains)} unique domains (original: {original_total})")
        if len(domains) > MAX_TOTAL_DOMAINS:
            raise RuntimeError(f"Exceeded MAX_TOTAL_DOMAINS limit ({len(domains)} > {MAX_TOTAL_DOMAINS}); no files published")

        date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        metadata = [json.loads((data / name / "update.json").read_text(encoding="utf-8")) for name in SOURCES]
        header = [
            "# Personal Android hosts selection; built " + date,
            "# Upstream: " + UPSTREAM + " (commit " + commit + ")",
            "# Unique blocked domains: " + str(len(domains)),
            "# Sources and original URLs (retained for attribution):",
        ]
        for name, info in zip(SOURCES, metadata):
            header.append("# " + name + ": " + info["url"])
        header.append("# Frogeye: https://hostfiles.frogeye.fr/")
        if key:
            header.append("# URLhaus: https://urlhaus.abuse.ch/api/")
        header += [
            "# Dan Pollock: non-commercial use with original URL and attribution.",
            "# Other source licenses: see their URLs above and the upstream README.",
            "# This is a snapshot; rebuilding and copying it to Android are separate steps.",
            "127.0.0.1 localhost",
            "::1 localhost",
            "",
        ]
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.with_name(output.name + ".new")
        with staging.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(header))
            for domain in sorted(domains):
                stream.write("0.0.0.0 " + domain + "\n")
        os.replace(staging, output)
        print(f"{len(domains)} unique domains; {output.stat().st_size} bytes; {output}")

        # Windows' DNS Client handles fewer lines better. Keep nine aliases on
        # each blocking line and preserve attribution; no trailing comments.
        windows_output = args.windows_output.resolve()
        windows_output.parent.mkdir(parents=True, exist_ok=True)
        windows_staging = windows_output.with_name(windows_output.name + ".new")
        windows_header = [
            "# Selected hosts for Windows; " + str(len(domains)) + " blocked domains",
            "# Upstream: " + UPSTREAM + " (commit " + commit + ")",
            "# Source attribution and original URLs:",
        ]
        windows_header += ["# " + name + ": " + info["url"] for name, info in zip(SOURCES, metadata)]
        windows_header.append("# Frogeye: https://hostfiles.frogeye.fr/")
        if key:
            windows_header.append("# URLhaus: https://urlhaus.abuse.ch/api/")
        windows_header += [
            "# Dan Pollock: non-commercial use with original URL and attribution.",
            "127.0.0.1 localhost",
            "::1 localhost",
        ]
        ordered = sorted(domains)
        with windows_staging.open("w", encoding="ascii", newline="\r\n") as stream:
            for line in windows_header:
                stream.write(line + "\n")
            for start in range(0, len(ordered), 9):
                stream.write("0.0.0.0 " + " ".join(ordered[start:start + 9]) + "\n")
        os.replace(windows_staging, windows_output)
        print(f"Windows: {windows_output.stat().st_size} bytes; {windows_output}")


if __name__ == "__main__":
    main()
