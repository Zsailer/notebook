from notebook.jupyter_server_shim import jupyter_server_shim

jupyter_server_shim()

from jupyter_server.services.shutdown import (
    web,
    ioloop,
    JupyterHandler as IPythonHandler,
    ShutdownHandler,
    default_handlers
)