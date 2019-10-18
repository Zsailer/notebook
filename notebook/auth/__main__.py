import sys
from jupyter_server.auth.__main__ import set_password, main
from notebook.jupyter_server_shim import jupyter_server_shim


jupyter_server_shim(__file__)


if __name__ == "__main__":
	main(sys.argv) 