from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.config_manager import (
    recursive_update,
    remove_defaults,
    BaseJSONConfigManager
)


jupyter_server_shim()