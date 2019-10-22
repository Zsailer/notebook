from ..jupyter_server_shim import jupyter_server_shim

jupyter_server_shim()

from jupyter_server.terminal.api_handlers import (
    TerminalHandler,
    TerminalRootHandler,
)