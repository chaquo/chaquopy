#!/usr/bin/env python3

import argparse
import json
import sys
import ssl
from urllib.request import urlopen

import certifi


def get_versions(python_version, package_name, year):
    url = f"https://pypi.org/pypi/{package_name}/json"

    # ensure we're using a root certificate that works with PyPI
    context = ssl.create_default_context(cafile=certifi.where())
    releases = json.load(urlopen(url, context=context))['releases']

    versions = set()

    for version, release in releases.items():
        for package in release:
            if (
                package['packagetype'] == 'bdist_wheel'
                and "-macosx_" in package['filename']
                and int(package['upload_time'].split('-')[0]) >= year
                and not any(c.isalpha() for c in version)
                and package['python_version'] == f"cp{python_version.replace('.', '')}"
            ):
                versions.add(version)

    return sorted(versions)


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--help", action="help", help=argparse.SUPPRESS)
    ap.add_argument("--year", required=True, help="Consider package built after this year only")
    ap.add_argument("--package_name", required=True, help="Package to check versions for")
    ap.add_argument("--python", required=True, help="Python version to consider")

    args = ap.parse_args()
    kwargs = vars(args)

    year = int(kwargs.pop("year"))
    package_name = kwargs.pop("package_name")
    python_version = kwargs.pop("python")
    print(" ".join(get_versions(python_version, package_name, year)))


if __name__ == "__main__":
    try:
        main()
    except CommandError as e:
        log("Error: " + str(e))
        sys.exit(1)
