# coding: utf-8
"""A tornado based Jupyter notebook server."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import absolute_import, print_function

import notebook
import binascii
import datetime
import errno
import gettext
import hashlib
import hmac
import importlib
import io
import ipaddress
import json
import logging
import mimetypes
import os
import random
import re
import select
import signal
import socket
import sys
import threading
import time
import warnings
import webbrowser

try: #PY3
    from base64 import encodebytes
except ImportError: #PY2
    from base64 import encodestring as encodebytes


from jinja2 import Environment, FileSystemLoader

from jupyter_server.transutils import trans, _

# Install the pyzmq ioloop. This has to be done before anything else from
# tornado is imported.
from zmq.eventloop import ioloop
ioloop.install()

# check for tornado 3.1.0
try:
    import tornado
except ImportError:
    raise ImportError(_("The Jupyter Notebook requires tornado >= 4.0"))
try:
    version_info = tornado.version_info
except AttributeError:
    raise ImportError(_("The Jupyter Notebook requires tornado >= 4.0, but you have < 1.1.0"))
if version_info < (4,0):
    raise ImportError(_("The Jupyter Notebook requires tornado >= 4.0, but you have %s") % tornado.version)

from tornado import httpserver
from tornado import web
from tornado.httputil import url_concat
from tornado.log import LogFormatter, app_log, access_log, gen_log

from notebook import (
    DEFAULT_STATIC_FILES_PATH,
    DEFAULT_TEMPLATE_PATH_LIST,
    __version__,
)

# py23 compatibility
try:
    raw_input = raw_input
except NameError:
    raw_input = input

from jupyter_server.log import log_request

from traitlets.config import Config
from traitlets.config.application import catch_config_error, boolean_flag
from jupyter_core.application import (
    JupyterApp, base_flags, base_aliases,
)
from jupyter_core.paths import jupyter_config_path
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager, NoSuchKernel, NATIVE_KERNEL_NAME
from jupyter_client.session import Session
from nbformat.sign import NotebookNotary
from traitlets import (
    Any, Dict, Unicode, Integer, List, Bool, Bytes, Instance,
    TraitError, Type, Float, observe, default, validate
)
from ipython_genutils import py3compat
from jupyter_core.paths import jupyter_runtime_dir, jupyter_path
from jupyter_server._sysinfo import get_sys_info

from jupyter_server._tz import utcnow, utcfromtimestamp
from jupyter_server.utils import url_path_join, check_pid, url_escape

from jupyter_server.serverapp import (
    random_ports, 
    load_handlers, 
    flags, aliases,
    ServerApp,
    JupyterServerListApp,
    JupyterServerStopApp,
    JupyterPasswordApp
)

#-----------------------------------------------------------------------------
# Module globals
#-----------------------------------------------------------------------------

_examples = """
jupyter notebook                       # start the notebook
jupyter notebook --certfile=mycert.pem # use SSL/TLS certificate
jupyter notebook password              # enter a password to protect the server
"""

#-----------------------------------------------------------------------------
# NotebookApp
#-----------------------------------------------------------------------------

class NotebookApp(JupyterApp):

    name = 'jupyter-notebook'
    version = __version__
    description = _("""The Jupyter HTML Notebook.
    
    This launches a Tornado based HTML Notebook Server that serves up an HTML5/Javascript Notebook client.""")
    examples = _examples

    ignore_minified_js = Bool(False,
            config=True,
            help=_('Deprecated: Use minified JS file or not, mainly use during dev to avoid JS recompilation'), 
            )

    max_body_size = Integer(512 * 1024 * 1024, config=True,
        help="""
        Sets the maximum allowed size of the client request body, specified in 
        the Content-Length request header field. If the size in a request 
        exceeds the configured value, a malformed HTTP message is returned to
        the client.

        Note: max_body_size is applied even in streaming mode.
        """
    )

    max_buffer_size = Integer(512 * 1024 * 1024, config=True,
        help="""
        Gets or sets the maximum amount of memory, in bytes, that is allocated 
        for use by the buffer manager.
        """
    )

    enable_mathjax = Bool(True, config=True,
        help="""Whether to enable MathJax for typesetting math/TeX

        MathJax is the javascript library Jupyter uses to render math/LaTeX. It is
        very large, so you may want to disable it if you have a slow internet
        connection, or for offline use of the notebook.

        When disabled, equations etc. will appear as their untransformed TeX source.
        """
    )

    @observe('enable_mathjax')
    def _update_enable_mathjax(self, change):
        """set mathjax url to empty if mathjax is disabled"""
        if not change['new']:
            self.mathjax_url = u''

    mathjax_url = Unicode("", config=True,
        help="""A custom url for MathJax.js.
        Should be in the form of a case-sensitive url to MathJax,
        for example:  /static/components/MathJax/MathJax.js
        """
    )

    @default('mathjax_url')
    def _default_mathjax_url(self):
        if not self.enable_mathjax:
            return u''
        static_url_prefix = self.tornado_settings.get("static_url_prefix", "static")
        return url_path_join(static_url_prefix, 'components', 'MathJax', 'MathJax.js')
    
    @observe('mathjax_url')
    def _update_mathjax_url(self, change):
        new = change['new']
        if new and not self.enable_mathjax:
            # enable_mathjax=False overrides mathjax_url
            self.mathjax_url = u''
        else:
            self.log.info(_("Using MathJax: %s"), new)

    mathjax_config = Unicode("TeX-AMS-MML_HTMLorMML-full,Safe", config=True,
        help=_("""The MathJax.js configuration file that is to be used.""")
    )

    @observe('mathjax_config')
    def _update_mathjax_config(self, change):
        self.log.info(_("Using MathJax configuration file: %s"), change['new'])


#-----------------------------------------------------------------------------
# Main entry point
#-----------------------------------------------------------------------------

main = launch_new_instance = NotebookApp.launch_instance
