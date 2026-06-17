from prometheus_client import Counter, Histogram

# Request metrics
REQUEST_COUNT = Counter(
    "request_count_total", 
    "Total number of HTTP requests", 
    ["method", "endpoint"]
)

REQUEST_LATENCY = Histogram(
    "request_latency_seconds", 
    "HTTP request latency in seconds", 
    ["method", "endpoint"]
)

ERROR_COUNT = Counter(
    "error_count_total", 
    "Total number of HTTP errors", 
    ["method", "endpoint", "status_code"]
)

# Cache metrics
CACHE_HITS = Counter(
    "cache_hits_total", 
    "Total number of cache hits"
)

CACHE_MISSES = Counter(
    "cache_misses_total", 
    "Total number of cache misses"
)
