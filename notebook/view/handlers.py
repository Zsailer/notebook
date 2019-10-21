from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.view.handlers import (
    ViewHandler, 
    default_handlers
)


jupyter_server_shim()