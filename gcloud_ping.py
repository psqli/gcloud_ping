#!/usr/bin/env python3

import sys
import time
import argparse
import requests

cloud_regions_url = "https://gcping.com/api/endpoints"

def clamp(value, min_value, max_value):
    return max(min(value, max_value), min_value)

# Based on https://github.com/scipy/scipy/blob/v1.16.3/scipy/stats/_mstats_basic.py#L2619
def winsorize(l, lower_limit=None, upper_limit=None):
    l_copy = list(l)
    n = len(l_copy)
    if n == 0:
        return l_copy
    # Sort the indexes according to element values
    idx = sorted(range(n), key=l_copy.__getitem__)
    if lower_limit is not None:
        lower_index = clamp(int(lower_limit * n), 0, n-1)
        lower_val = l_copy[idx[lower_index]]
        for i in range(0, lower_index):
            l_copy[idx[i]] = lower_val
    if upper_limit is not None:
        upper_index = n - clamp(int(upper_limit * n), 0, n-1)
        upper_val = l_copy[idx[upper_index-1]]
        for i in range(upper_index, n):
            l_copy[idx[i]] = upper_val
    return l_copy

class Region:
    def __init__(self, region_id, name, url):
        self.id = region_id
        self.name = name
        self.url = url
        self.rtt_ms_list = []
        self.session = requests.Session()

    @classmethod
    def from_dict(cls, data):
        return cls(
            region_id=data["Region"],
            name=data["RegionName"],
            url=data["URL"]
        )

    @property
    def ping_count(self):
        return len(self.rtt_ms_list)

    @property
    def avg_rtt_ms(self):
        values = [v for v in self.rtt_ms_list if v != -1]
        if not values:
            return -1
        # Apply the winsorize function. Instead of discarding outliers, it does set them to the limit values.
        winsorized_values = winsorize(values, low_limit=0.05, up_limit=0.10)
        return int(sum(winsorized_values) / len(winsorized_values))

    @property
    def cur_rtt_ms(self):
        return self.rtt_ms_list[-1] if self.rtt_ms_list else -1

    def ping(self):
        ping_url = f"{self.url}/api/ping"
        rtt_ms = -1
        try:
            ping_response = self.session.get(ping_url, timeout=5)
            if ping_response.status_code != 200:
                raise Exception(f"Unexpected status code: {ping_response.status_code}")
            rtt_ms = int(ping_response.elapsed.total_seconds() * 1000)
        except Exception as e:
            print(f"Error while pinging {self.id} ({ping_url}): {e}", file=sys.stderr)
        self.rtt_ms_list.append(rtt_ms)
        return rtt_ms


def parse_args():
    parser = argparse.ArgumentParser(description="Ping Google Cloud Platform regions")
    parser.add_argument("--csv", action="store_true", help="Output in CSV format")
    parser.add_argument("--count", type=int, default=0, help="Number of pings to perform (0 for infinite)")
    parser.add_argument("--interval", type=float, default=0.5, help="Interval between pings in seconds")
    parser.add_argument("regions", nargs="+", help="List of region IDs to ping (use 'all' to ping all regions)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Get the JSON with the ping addresses of Google Cloud Platform regions
    try:
        response = requests.get(cloud_regions_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching regions: {e}", file=sys.stderr)
        sys.exit(1)

    # Select only the regions of interest
    region_data_list = [r for r in response.json().values() if args.regions == ["all"] or r["Region"] in args.regions]

    # For each region, create an object with the necessary context for pinging
    regions = [Region.from_dict(region_data) for region_data in region_data_list]

    if not regions:
        print("No regions found matching the criteria.", file=sys.stderr)
        sys.exit(1)

    # Print CSV header if needed
    if args.csv:
        print("region,cur_ms,avg_ms,count")
    else:
        max_region_len = max([len(region.id) for region in regions] + [len("Region")])
        print(f"{'Region':<{max_region_len}}{'Cur. ms':>12}{'Avg. ms':>12} {'Count':>8}")

    # Start a loop to ping continuously
    count = 0
    try:
        while count < args.count or args.count == 0:
            count += 1

            # Print the regions
            for region in regions:
                region.ping()

                if args.csv:
                    print(f"{region.id},{region.cur_rtt_ms},{region.avg_rtt_ms},{region.ping_count}")
                else:
                    print(f"{region.id:.<{max_region_len}}{region.cur_rtt_ms:.>12d}{region.avg_rtt_ms:.>12d}{region.ping_count:.>8d}")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nUser stopped the program.", file=sys.stderr)


if __name__ == "__main__":
    main()
