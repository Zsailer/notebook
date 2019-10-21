from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.services.contents.checkpoints import (
    Checkpoints,
    GenericCheckpointsMixin
)


jupyter_server_shim()