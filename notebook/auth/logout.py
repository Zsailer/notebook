from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.auth.logout import LogoutHandler, default_handlers


jupyter_server_shim(__file__)