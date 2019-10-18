from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.files.handlers import (
    FilesHandler,
    default_handlers
)

jupyter_server_shim(__file__)