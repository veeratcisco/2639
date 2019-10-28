#!/usr/bin/env python
"""Mission - Cisco AMP

This is your starting point for the Zero-day Workflow.


Copyright (c) 2018-2019 Cisco and/or its affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import json
import sys
from pathlib import Path

import requests
import webexteamssdk
from crayons import blue, green, red
from requests.packages.urllib3.exceptions import InsecureRequestWarning


# Locate the directory containing this file and the repository root.
# Temporarily add these directories to the system path so that we can import
# local files.
here = Path(__file__).parent.absolute()
repository_root = (here / ".." / "..").resolve()

sys.path.insert(0, str(repository_root))

import env_lab  # noqa
import env_user  # noqa


# Disable insecure request warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# Functions
def get_amp_events(
    host=env_lab.AMP.get("host"),
    client_id=env_user.AMP_CLIENT_ID,
    api_key=env_user.AMP_API_KEY,
):
    """Get a list of recent events from Cisco AMP."""
    print(blue("\n==> Getting recent events from AMP"))

    url = f"https://{client_id}:{api_key}@{host}/v1/events"

    response = requests.get(url, verify=False)
    response.raise_for_status()

    events_list = response.json()["data"]

    print(green(f"Retrieved {len(events_list)} events from AMP"))

    return events_list


def get_amp_computer_details( url,
    client_id=env_user.AMP_CLIENT_ID,
    api_key=env_user.AMP_API_KEY,
    ):

    """Get details of infected computer from Cisco AMP."""
    print(blue("\n==> Geting infected computer details from AMP"))
    url = f"https://{client_id}:{api_key}@{url}"
    response = requests.get(url, verify=False)
    response.raise_for_status()
    events_list = response.json()["data"]
    return events_list


def extract_observables(amp_events):
    """Extract hash, IP, and MAC address observables from Malware events."""
    print(blue("\n==> Extracting observables from the AMP events"))

    # Initialize data structures for collecting observables
    observables = []

    # Standard AMP event ID for Malware events
    malware_event_id = 1107296272
    value = ""
    ip = ""
    mac = ""
    sha256= ""
    for event in amp_events:
        if event["event_type_id"] == malware_event_id:
            try:
                hostname = event["computer"]["hostname"]
                """ get the links URL to get details of infected computer"""
                url = event["computer"]["links"]["computer"]
                malU=url.partition("https://")[2]
               
                """ get the links URL to get details of infected computer"""
                events_list = get_amp_computer_details(malU)
                ip = events_list["network_addresses"][0]["ip"]
                mac = events_list["network_addresses"][0]["mac"]
                sha256 = event["file"]["identity"]["sha256"]
                """ Handle missing dict Key errors"""
            except KeyError as ke:
                value = "None"
            observables.append({
                "hostname": hostname,
                "ip_address": ip,
                "mac_address": mac,
                "sha256": sha256,
            })

    if observables:
        print(green(f"Extracted observables from "
                    f"{len(observables)} malware events"))
    else:
        print(red("No malware events found."))
        sys.exit(1)

    return observables


# If this script is the "main" script, run...
if __name__ == "__main__":
    # Get the list of events from AMP
    amp_events = get_amp_events()

    # Extract the Malware event observables
    amp_observables = extract_observables(amp_events)

    # Save the MAC addresses of the endpoints where malware executed to a JSON
    # file.  In the ISE Mission we will read this file and quarantine these
    # endpoints.
    mac_addresses_path = repository_root / "mission-data/mac-addresses.json"
    print(blue(f"\n==> Saving MAC addresses to: {mac_addresses_path}"))

    with open(mac_addresses_path, "w") as file:
        mac_addresses = [o["mac_address"] for o in amp_observables]
        json.dump(mac_addresses, file, indent=2)

    # Save the malware SHA256 hashes to a JSON file. We will use these in the
    # ThreatGrid Mission.
    sha256_list_path = repository_root / "mission-data/sha256-list.json"
    print(blue(f"\n==> Saving SHA256 hashes to: {sha256_list_path}"))

    with open(sha256_list_path, "w") as file:
        sha256_hashes = [o["sha256"] for o in amp_observables]
        json.dump(sha256_hashes, file, indent=2)

    print(green("AMP Workflow Step Completed!!!"))
