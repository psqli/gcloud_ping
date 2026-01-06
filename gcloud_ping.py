#!/usr/bin/env python3

import concurrent.futures
import http.client
import json
import sys

from argparse import ArgumentParser
from time import perf_counter_ns, sleep
from urllib.parse import urlparse

CLOUD_REGIONS_URL = "https://gcping.com/api/endpoints"

WINSORIZED_MEAN_LOWER_LIMIT=0.05
WINSORIZED_MEAN_UPPER_LIMIT=0.10

# Based on https://github.com/scipy/scipy/blob/v1.16.3/scipy/stats/_mstats_basic.py#L2619
def winsorize(l, lower_limit=0, upper_limit=0):
    l_copy = list(l)
    n = len(l_copy)
    if n == 0:
        return l_copy
    # Sort the indexes according to element values
    idx = sorted(range(n), key=l_copy.__getitem__)
    lower_index = int(lower_limit * n)
    if lower_index > 0 and lower_index < n:
        lower_val = l_copy[idx[lower_index]]
        for i in range(0, lower_index):
            l_copy[idx[i]] = lower_val
    upper_index = n - int(upper_limit * n)
    if upper_index > 0 and upper_index < n:
        upper_val = l_copy[idx[upper_index-1]]
        for i in range(upper_index, n):
            l_copy[idx[i]] = upper_val
    return l_copy

class Region:
    def __init__(self, region_id, name, url):
        self.id = region_id
        self.name = name
        self.url = urlparse(url)
        self._conn = http.client.HTTPSConnection(self.url.hostname, timeout=5)
        self._measurements = []
        self._average_rtt_ns = None

    @classmethod
    def from_dict(cls, data):
        return cls(
            region_id=data["Region"],
            name=data["RegionName"],
            url=data["URL"]
        )

    @property
    def average_rtt_ms(self):
        return self._average_rtt_ns // 1000000 if self._average_rtt_ns is not None else -1

    @property
    def last_rtt_ms(self):
        return self._measurements[-1] // 1000000 if self._measurements else -1

    @property
    def ping_count(self):
        return len(self._measurements)

    def ping(self):
        try:
            start_ns = perf_counter_ns()
            self._conn.request("GET", "/api/ping")
            res = self._conn.getresponse()
            _ = res.read()
            if res.status != http.client.OK:
                raise ValueError(f"Unexpected HTTP status code: {res.status}")
            interval_ns = perf_counter_ns() - start_ns
            self._measurements.append(interval_ns)
            # Apply the winsorize function. Instead of discarding outliers, it does set them to the limit values.
            winsorized_values = winsorize(self._measurements,
                                          lower_limit=WINSORIZED_MEAN_LOWER_LIMIT,
                                          upper_limit=WINSORIZED_MEAN_UPPER_LIMIT)
            self._average_rtt_ns = sum(winsorized_values) // len(winsorized_values)
            return self.last_rtt_ms
        except (http.client.HTTPException, ValueError) as e:
            print(f"Error while pinging {self.id}: {type(e).__name__}: {e}", file=sys.stderr)
            return None


def parse_args():
    parser = ArgumentParser(description="Ping Google Cloud Platform regions.")
    parser.add_argument("regions", nargs="*", help="Regions to ping / list (if omitted, defaults to all regions).")
    parser.add_argument("--csv", action="store_true", help="Output in CSV format.")
    parser.add_argument("-c", "--ping-count", type=int, default=64, help="Number of ping cycles.")
    parser.add_argument("-i", "--ping-interval", type=float, default=1, help="Interval (in seconds) between ping cycles.")
    parser.add_argument("-s", "--sort", action="store_true", help="Sort results by average RTT (ascending).")
    parser.add_argument("-l", "--list", action="store_true", help="List regions without pinging.")
    return parser.parse_args()


def main():
    args = parse_args()

    cloud_regions_url_obj = urlparse(CLOUD_REGIONS_URL)

    # Get the JSON with the ping addresses of Google Cloud Platform regions
    try:
        conn = http.client.HTTPSConnection(cloud_regions_url_obj.hostname, timeout=5)
        conn.request("GET", cloud_regions_url_obj.path)
        res = conn.getresponse()
        if res.status != http.client.OK:
            raise ValueError(f"Unexpected HTTP status code: {res.status}")
        res_obj = json.loads(res.read())
    except (http.client.HTTPException, json.JSONDecodeError, ValueError) as e:
        print(f"Error while fetching the list of regions: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    # Select only the regions of interest
    region_data_list = [r for r in res_obj.values() if not args.regions or r["Region"] in args.regions]

    if not region_data_list:
        print("No regions found matching the criteria.", file=sys.stderr)
        sys.exit(1)

    if args.list:
        if args.csv:
            print("region,name,url")
        for region_data in region_data_list:
            if args.csv:
                print(f"{region_data['Region']},{region_data['RegionName']},{region_data['URL']}")
            else:
                print(region_data["Region"])
        sys.exit(0)

    # For each region, create an object with the necessary context for pinging
    regions = [Region.from_dict(region_data) for region_data in region_data_list]

    # Print CSV header if needed
    if args.csv:
        print("region,cur_ms,avg_ms,count")
    else:
        max_region_len = max([len(region.id) for region in regions] + [len("Region")])
        print(f"{'Region':<{max_region_len}}{'Cur. ms':>12}{'Avg. ms':>12} {'Count':>8}")

    # Start a loop to ping continuously
    count = 0
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(regions)) as executor:
            while count < args.ping_count:
                futures = [executor.submit(region.ping) for region in regions]
                concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)
                if args.sort:
                    regions.sort(key=lambda r: r.average_rtt_ms)
                for region in regions:
                    if args.csv:
                        print(f"{region.id},{region.last_rtt_ms},{region.average_rtt_ms},{region.ping_count}")
                    else:
                        print(f"{region.id:.<{max_region_len}}{region.last_rtt_ms:.>12d}{region.average_rtt_ms:.>12d}{region.ping_count:.>8d}")
                count += 1
                if count < args.ping_count:
                    sleep(args.ping_interval)
    except KeyboardInterrupt:
        print("\nUser stopped the program.", file=sys.stderr)


if __name__ == "__main__":
    main()
