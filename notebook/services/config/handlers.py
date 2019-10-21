from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.services.config.handlers import (
    ConfigHandler,
    default_handlers
)


jupyter_server_shim()