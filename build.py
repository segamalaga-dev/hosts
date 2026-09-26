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
import tempfile


UPSTREAM = "https://github.com/StevenBlack/hosts.git"
SOURCES = (
    "StevenBlack",
    "adaway.org",
    "add.2o7Net",
    "someonewhocares.org",
    "URLHaus",
    "yoyo.org",
)
DOMAIN = re.compile(r"(?i)^(?=.{1,253}$)[a-z0-9_-]+(?:\.[a-z0-9_-]+)+$")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "hosts")
    parser.add_argument("--windows-output", type=Path, default=Path(__file__).parent / "hosts-windows")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="selected-hosts-") as tmp:
        repo = Path(tmp) / "upstream"
        subprocess.run(["git", "clone", "--depth", "1", "--quiet", UPSTREAM, str(repo)], check=True)
        commit = subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=repo, text=True).strip()

        data = repo / "data"
        for source in data.iterdir():
            if source.is_dir() and source.name not in SOURCES:
                shutil.rmtree(source)
        if {p.name for p in data.iterdir() if p.is_dir()} != set(SOURCES):
            raise RuntimeError("The upstream source layout has changed; inspect it before building.")

        # Use the source snapshots from this upstream commit. This avoids mixing
        # one source updated today with another that could not be downloaded.
        subprocess.run(
            ["python3", "updateHostsFile.py", "--auto", "--noupdate", "--nogendata", "--skipstatichosts"],
            cwd=repo, check=True, stdout=subprocess.DEVNULL,
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
