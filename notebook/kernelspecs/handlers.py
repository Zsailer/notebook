from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.kernelspecs.handlers import (
    web, 
    JupyterHandler as IPythonHandler,
    kernel_name_regex,
    # Defined in this module.
    KernelSpecResourceHandler,
    default_handlers
)


jupyter_server_shim()