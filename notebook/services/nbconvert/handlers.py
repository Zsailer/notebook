from notebook.jupyter_server_shim import jupyter_server_shim

jupyter_server_shim()

from jupyter_server.services.nbconvert.handlers import (
    json,
    web,
    APIHandler,
    NbconvertRootHandler,
    default_handlers
)