from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.edit.handlers import (
    EditorHandler,
    default_handlers
)

jupyter_server_shim(__file__)