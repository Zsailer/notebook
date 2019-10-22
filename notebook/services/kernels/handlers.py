from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.services.kernels.handlers import (
    json,
    logging,
    dedent,
    gen,
    web,
    Future,
    IOLoop,
    client_protocol_version,
    date_default,
    cast_unicode,
    maybe_future, url_escape, url_path_join,
    APIHandler,
    AuthenticatedZMQStreamHandler,
    deserialize_binary_message,
    MainKernelHandler,
    KernelHandler,
    KernelActionHandler,
    ZMQChannelsHandler,
    _kernel_id_regex,
    _kernel_action_regex,
    default_handlers
)


jupyter_server_shim()