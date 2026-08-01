#!/usr/bin/env python3
"""Install pinned Pandoc and Typst release binaries into the user cache."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path


TOOL_SPECS = {
    "pandoc": {
        "repo": "jgm/pandoc",
        "version": "3.9.0.2",
        "tag": "3.9.0.2",
        "assets": {
            "windows-x86_64": "pandoc-{version}-windows-x86_64.zip",
            "linux-x86_64": "pandoc-{version}-linux-amd64.tar.gz",
            "linux-aarch64": "pandoc-{version}-linux-arm64.tar.gz",
            "macos-x86_64": "pandoc-{version}-x86_64-macOS.zip",
            "macos-aarch64": "pandoc-{version}-arm64-macOS.zip",
        },
    },
    "typst": {
        "repo": "typst/typst",
        "version": "0.14.2",
        "tag": "v0.14.2",
        "assets": {
            "windows-x86_64": "typst-x86_64-pc-windows-msvc.zip",
            "linux-x86_64": "typst-x86_64-unknown-linux-musl.tar.xz",
            "linux-aarch64": "typst-aarch64-unknown-linux-musl.tar.xz",
            "macos-x86_64": "typst-x86_64-apple-darwin.tar.xz",
            "macos-aarch64": "typst-aarch64-apple-darwin.tar.xz",
        },
    },
}


class InstallError(RuntimeError):
    pass


def default_tools_dir():
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "md2pdf" / "tools"
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "md2pdf" / "tools"


def platform_key():
    systems = {"windows": "windows", "linux": "linux", "darwin": "macos"}
    machines = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "aarch64",
        "aarch64": "aarch64",
    }
    system = systems.get(platform.system().lower())
    machine = machines.get(platform.machine().lower())
    if not system or not machine:
        raise InstallError("Unsupported platform: {} {}".format(platform.system(), platform.machine()))
    return "{}-{}".format(system, machine)


def executable_name(tool):
    return tool + (".exe" if os.name == "nt" else "")


def find_cached_tool(tool, root=None):
    root = Path(root or default_tools_dir()) / tool
    if not root.exists():
        return None
    candidates = sorted(root.glob("**/{}".format(executable_name(tool))), reverse=True)
    return candidates[0] if candidates else None


def _request_json(url):
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "documentation-md2pdf"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _download(url, target):
    request = urllib.request.Request(url, headers={"User-Agent": "documentation-md2pdf"})
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def _safe_destination(root, member):
    root = root.resolve()
    destination = (root / member).resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        raise InstallError("Archive contains an unsafe path: {}".format(member))
    return destination


def _extract(archive, target):
    name = archive.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(str(archive)) as bundle:
            for member in bundle.infolist():
                _safe_destination(target, member.filename)
            bundle.extractall(str(target))
        return
    if name.endswith((".tar.gz", ".tar.xz")):
        with tarfile.open(str(archive), "r:*") as bundle:
            for member in bundle.getmembers():
                _safe_destination(target, member.name)
            bundle.extractall(str(target))
        return
    raise InstallError("Unsupported archive: {}".format(archive.name))


def install_tool(tool, root=None, allow_unverified=False):
    spec = TOOL_SPECS[tool]
    root = Path(root or default_tools_dir()).expanduser().resolve()
    destination = root / tool / spec["version"]
    existing = find_cached_tool(tool, root)
    if existing and destination in existing.parents:
        print("{} {} already installed: {}".format(tool, spec["version"], existing))
        return existing

    key = platform_key()
    pattern = spec["assets"].get(key)
    if not pattern:
        raise InstallError("{} {} has no asset for {}".format(tool, spec["version"], key))
    asset_name = pattern.format(version=spec["version"])
    release = _request_json(
        "https://api.github.com/repos/{}/releases/tags/{}".format(spec["repo"], spec["tag"])
    )
    assets = {item["name"]: item for item in release.get("assets", [])}
    asset = assets.get(asset_name)
    if not asset:
        raise InstallError("Release asset not found: {}".format(asset_name))

    expected = asset.get("digest", "")
    if expected.startswith("sha256:"):
        expected = expected.split(":", 1)[1].lower()
    elif not allow_unverified:
        raise InstallError("GitHub did not publish a SHA-256 digest for {}".format(asset_name))

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="md2pdf-install-", dir=str(destination.parent)) as temp_name:
        temp = Path(temp_name)
        archive = temp / asset_name
        print("Downloading {} {}...".format(tool, spec["version"]))
        actual = _download(asset["browser_download_url"], archive)
        if expected and actual != expected:
            raise InstallError("SHA-256 mismatch for {}".format(asset_name))
        extracted = temp / "extracted"
        extracted.mkdir()
        _extract(archive, extracted)
        candidates = list(extracted.glob("**/{}".format(executable_name(tool))))
        if not candidates:
            raise InstallError("{} executable missing from {}".format(tool, asset_name))
        if destination.exists():
            raise InstallError("Destination already exists but is incomplete: {}".format(destination))
        shutil.move(str(extracted), str(destination))

    installed = find_cached_tool(tool, root)
    if not installed:
        raise InstallError("Installed executable could not be found for {}".format(tool))
    installed.chmod(installed.stat().st_mode | stat.S_IXUSR)
    metadata = {
        "tool": tool,
        "version": spec["version"],
        "asset": asset_name,
        "source": asset["browser_download_url"],
        "sha256": actual,
    }
    (destination / "installed.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("Installed {} {}: {}".format(tool, spec["version"], installed))
    return installed


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", choices=("all", "pandoc", "typst"), default="all")
    parser.add_argument("--dest", type=Path, default=default_tools_dir())
    parser.add_argument("--allow-unverified", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    tools = ("pandoc", "typst") if args.tool == "all" else (args.tool,)
    try:
        for tool in tools:
            install_tool(tool, args.dest, args.allow_unverified)
    except (InstallError, OSError, ValueError) as error:
        print("error: {}".format(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
