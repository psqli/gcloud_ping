# copy-paste tool for measuring RTT for Google Cloud Platform regions

This is based on the Google's official tool [gcping](https://github.com/GoogleCloudPlatform/gcping).

Usage:

```sh
gcloud_ping.py [-h] [--csv] [-c PING_COUNT] [-i PING_INTERVAL] [--sort] [--list] [regions ...]
```

Positional arguments:
- `regions` Regions to ping / list (if omitted, defaults to all regions).

Options:
- `-h` `--help` Show the help message and exit.
- `--csv` Output in CSV format.
- `-c` `--ping-count PING_COUNT` Number of ping cycles. Default is `64`.
- `-i` `--ping-interval PING_INTERVAL` Interval (in seconds) between ping cycles. Default is `1`.
- `-s` `--sort` Sort regions by average RTT (ascending) when printing the results.
- `-l` `--list` List regions without pinging.

A ping cycle is the pinging of all regions specified.

The average is calculated using a [Winsorized Mean](https://en.wikipedia.org/wiki/Winsorizing), which is basically a [Trimmed Mean](https://en.wikipedia.org/wiki/Truncated_mean) but clamps outliers instead of discarding them. The lower and upper limits were chosen ~carefully~ arbitrarily.

## Google's current IP addresses

- For clients of Google Cloud Platform, see [Google Cloud Platform IP ranges per region](https://www.gstatic.com/ipranges/cloud.json).
- For other Google services, see [Google user IP ranges](https://www.gstatic.com/ipranges/goog.json).
