from notebook.jupyter_server_shim import jupyter_server_shim

jupyter_server_shim()

from jupyter_server.services.kernels.kernelmanager import (
    MappingKernelManager
)