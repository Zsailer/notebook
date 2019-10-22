from notebook.jupyter_server_shim import jupyter_server_shim

jupyter_server_shim()

from jupyter_server.services.sessions.handlers import (
    json,
    gen,
    web,
    APIHandler,
    date_default,
    maybe_future,
    url_path_join,
    NoSuchKernel,
    SessionRootHandler,
    SessionHandler,
    _session_id_regex,
    default_handlers
)