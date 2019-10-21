from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.kernelspecs.handlers import (
    KernelSpecResourceHandler,
    default_handlers
)


jupyter_server_shim()