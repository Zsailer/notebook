from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.services.api.handlers import (
    APISpecHandler,
    APIStatusHandler,
    default_handlers
)


jupyter_server_shim()
