from jupyter_server.transutils import _

def jupyter_server_shim(src, dst=None):
    """Central warning message for all notebook-->jupyter_server shims"""
    if dst is None:
        dst = src.replace('notebook', 'jupyter_server', 1)

    msg = _("""
    {} has been moved to {}. 
    
    This API will be dropped in the next major
    release of jupyter/notebook. 
    """.format(src, dst))
    raise FutureWarning(msg)