# copy-paste tool for measuring RTT for Google Cloud Platform regions

This is based on the Google's official tool [gcping](https://github.com/GoogleCloudPlatform/gcping).

Usage example:

```
gcloud_ping.py --csv --count 10 --interval 1 us-east1 us-west1 us-central1
```

Use `--help`.

The average is calculated using a [Winsorized Mean](https://en.wikipedia.org/wiki/Winsorizing), which is basically a [Trimmed Mean](https://en.wikipedia.org/wiki/Truncated_mean) but clamps outliers instead of discarding them.
