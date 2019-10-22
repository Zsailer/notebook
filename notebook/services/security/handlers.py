from notebook.jupyter_server_shim import jupyter_server_shim

jupyter_server_shim()

from jupyter_server.services.security.handlers import (
    web,
    APIHandler,
    csp_report_uri,
    CSPReportHandler,
    default_handlers
)