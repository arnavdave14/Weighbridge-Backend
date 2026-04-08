from prometheus_client import Counter, Histogram, CollectorRegistry, multiprocess

class NotificationMetrics:
    """
    Prometheus metrics for notification events.
    Thread-safe and process-safe by design (prometheus_client).
    """
    
    # Counter for total notifications sent/failed/queued per channel
    # Labels: channel (email|whatsapp), status (queued|sent|failed)
    NOTIFICATIONS_TOTAL = Counter(
        "notifications_total",
        "Total number of notifications processed",
        ["channel", "status"]
    )
    
    # Counter for retries
    # Labels: channel
    NOTIFICATION_RETRIES_TOTAL = Counter(
        "notification_retries_total",
        "Total number of notification retries",
        ["channel"]
    )
    
    # Counter for DLQ events
    # Labels: channel
    NOTIFICATION_DLQ_TOTAL = Counter(
        "notification_dlq_total",
        "Total number of notifications sent to DLQ",
        ["channel"]
    )
    
    # Histogram for latency
    # Labels: channel
    NOTIFICATION_LATENCY_SECONDS = Histogram(
        "notification_latency_seconds",
        "Latency of notification delivery in seconds",
        ["channel"]
    )

metrics = NotificationMetrics()
