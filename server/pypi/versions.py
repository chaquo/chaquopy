#!/usr/bin/env python3

import json
import sys
from urllib.request import urlopen


def versions(package_name):
    url = "https://pypi.org/pypi/%s/json" % (package_name,)

    releases = json.load(urlopen(url))["releases"]

    for release in releases:
        try:
            if int(releases[release][0]['upload_time'].split("-")[0]) >= int(sys.argv[1]):
                if not any(c.isalpha() for c in release):
                    print(release, end=' ')
        except Exception:
            pass
    print()


versions(sys.argv[2])
