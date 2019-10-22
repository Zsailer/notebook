from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.edit.handlers import (
    web,
    JupyterHandler as IPythonHandler,
    path_regex,
    url_escape,
    # Defined in this module.
    EditorHandler,
    default_handlers
)

jupyter_server_shim()