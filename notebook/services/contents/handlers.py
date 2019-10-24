from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.services.contents.handlers import (
    json,
    gen,
    web,
    maybe_future,
    url_escape,
    url_path_join,
    date_default,
    JupyterHandler as IPythonHandler,
    APIHandler,
    path_regex,
    # Defined in this module.
    validate_model,
    ContentsHandler,
    CheckpointsHandler,
    ModifyCheckpointsHandler,
    NotebooksRedirectHandler,
    TrustNotebooksHandler,
    default_handlers
)


jupyter_server_shim()