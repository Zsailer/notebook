from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.prometheus.metrics import (
    Histogram,
    Gauge,
    # Defined in this module.
    HTTP_REQUEST_DURATION_SECONDS,
    TERMINAL_CURRENTLY_RUNNING_TOTAL,
    KERNEL_CURRENTLY_RUNNING_TOTAL
)


jupyter_server_shim()
