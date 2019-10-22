from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.files.handlers import (
    mimetypes,
    json,
    decodebytes,
    gen,
    web,
    JupyterHandler as IPythonHandler,
    maybe_future,
    #Defined in this module.
    FilesHandler,
    default_handlers
)

jupyter_server_shim()