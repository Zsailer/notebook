from notebook.jupyter_server_shim import jupyter_server_shim

jupyter_server_shim()

from jupyter_server.services.sessions.handlers import (
    SessionRootHandler,
    SessionHandler,
    _session_id_regex,
    default_handlers
)