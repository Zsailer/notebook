from notebook.jupyter_server_shim import jupyter_server_shim

jupyter_server_shim()

from jupyter_server.services.security.handlers import (
    CSPReportHandler,
    default_handlers
)