from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.services.contents.handlers import (
    validate_model,
    ContentsHandler,
    CheckpointsHandler,
    ModifyCheckpointsHandler,
    NotebooksRedirectHandler,
    TrustNotebooksHandler,
    default_handlers
)


jupyter_server_shim()