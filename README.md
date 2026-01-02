# copy-paste tool for measuring RTT for Google Cloud Platform regions

This is based on the Google's official tool [gcping](https://github.com/GoogleCloudPlatform/gcping).

```
usage: gcloud_ping.py [-h] [--csv] [--count COUNT] [--interval INTERVAL] [--list] [regions ...]

Ping Google Cloud Platform regions

positional arguments:
  regions              Regions to ping / list (if omitted, defaults to all regions)

options:
  -h, --help           show this help message and exit
  --csv                Output in CSV format
  --count COUNT        Number of pings to perform (0 for infinite)
  --interval INTERVAL  Interval between pings in seconds
  --list               List regions without pinging
```

The average is calculated using a [Winsorized Mean](https://en.wikipedia.org/wiki/Winsorizing), which is basically a [Trimmed Mean](https://en.wikipedia.org/wiki/Truncated_mean) but clamps outliers instead of discarding them. The lower and upper limits were chosen ~carefully~ arbitrarily.
