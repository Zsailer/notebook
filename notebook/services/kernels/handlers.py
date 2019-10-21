from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.services.kernels.handlers import (
    MainKernelHandler,
    KernelHandler,
    KernelActionHandler,
    ZMQChannelsHandler,
    _kernel_id_regex,
    _kernel_action_regex,
    default_handlers
)


jupyter_server_shim()