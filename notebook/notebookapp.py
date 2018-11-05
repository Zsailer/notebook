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

from notebook.transutils import trans, _

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

from .base.handlers import Template404, RedirectWithParams
from .log import log_request
from .services.kernels.kernelmanager import MappingKernelManager
from .services.config import ConfigManager
from .services.contents.manager import ContentsManager
from .services.contents.filemanager import FileContentsManager
from .services.contents.largefilemanager import LargeFileManager
from .services.sessions.sessionmanager import SessionManager

from .auth.login import LoginHandler
from .auth.logout import LogoutHandler
from .base.handlers import FileFindHandler

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
from notebook._sysinfo import get_sys_info

from ._tz import utcnow, utcfromtimestamp
from .utils import url_path_join, check_pid, url_escape

#-----------------------------------------------------------------------------
# Module globals
#-----------------------------------------------------------------------------

_examples = """
jupyter notebook                       # start the notebook
jupyter notebook --certfile=mycert.pem # use SSL/TLS certificate
jupyter notebook password              # enter a password to protect the server
"""

#-----------------------------------------------------------------------------
# Helper functions
#-----------------------------------------------------------------------------

def random_ports(port, n):
    """Generate a list of n random ports near the given port.

    The first 5 ports will be sequential, and the remaining n-5 will be
    randomly selected in the range [port-2*n, port+2*n].
    """
    for i in range(min(5, n)):
        yield port + i
    for i in range(n-5):
        yield max(1, port + random.randint(-2*n, 2*n))

def load_handlers(name):
    """Load the (URL pattern, handler) tuples for each component."""
    mod = __import__(name, fromlist=['default_handlers'])
    return mod.default_handlers

#-----------------------------------------------------------------------------
# The Tornado web application
#-----------------------------------------------------------------------------

class NotebookWebApplication(web.Application):

    def __init__(self, jupyter_app, kernel_manager, contents_manager,
                 session_manager, kernel_spec_manager,
                 config_manager, extra_services, log,
                 base_url, default_url, settings_overrides, jinja_env_options):


        settings = self.init_settings(
            jupyter_app, kernel_manager, contents_manager,
            session_manager, kernel_spec_manager, config_manager,
            extra_services, log, base_url,
            default_url, settings_overrides, jinja_env_options)
        handlers = self.init_handlers(settings)

        super(NotebookWebApplication, self).__init__(handlers, **settings)

    def init_settings(self, jupyter_app, kernel_manager, contents_manager,
                      session_manager, kernel_spec_manager,
                      config_manager, extra_services,
                      log, base_url, default_url, settings_overrides,
                      jinja_env_options=None):

        _template_path = settings_overrides.get(
            "template_path",
            jupyter_app.template_file_path,
        )
        if isinstance(_template_path, py3compat.string_types):
            _template_path = (_template_path,)
        template_path = [os.path.expanduser(path) for path in _template_path]

        jenv_opt = {"autoescape": True}
        jenv_opt.update(jinja_env_options if jinja_env_options else {})

        env = Environment(loader=FileSystemLoader(template_path), extensions=['jinja2.ext.i18n'], **jenv_opt)
        sys_info = get_sys_info()

        # If the user is running the notebook in a git directory, make the assumption
        # that this is a dev install and suggest to the developer `npm run build:watch`.
        base_dir = os.path.realpath(os.path.join(__file__, '..', '..'))
        dev_mode = os.path.exists(os.path.join(base_dir, '.git'))

        nbui = gettext.translation('nbui', localedir=os.path.join(base_dir, 'notebook/i18n'), fallback=True)
        env.install_gettext_translations(nbui, newstyle=False)

        if dev_mode:
            DEV_NOTE_NPM = """It looks like you're running the notebook from source.
    If you're working on the Javascript of the notebook, try running

    %s

    in another terminal window to have the system incrementally
    watch and build the notebook's JavaScript for you, as you make changes.""" % 'npm run build:watch'
            log.info(DEV_NOTE_NPM)

        if sys_info['commit_source'] == 'repository':
            # don't cache (rely on 304) when working from master
            version_hash = ''
        else:
            # reset the cache on server restart
            version_hash = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        if jupyter_app.ignore_minified_js:
            log.warning(_("""The `ignore_minified_js` flag is deprecated and no longer works."""))
            log.warning(_("""Alternatively use `%s` when working on the notebook's Javascript and LESS""") % 'npm run build:watch')
            warnings.warn(_("The `ignore_minified_js` flag is deprecated and will be removed in Notebook 6.0"), DeprecationWarning)

        now = utcnow()
        
        root_dir = contents_manager.root_dir
        home = py3compat.str_to_unicode(os.path.expanduser('~'), encoding=sys.getfilesystemencoding()) 
        if root_dir.startswith(home + os.path.sep):
            # collapse $HOME to ~
            root_dir = '~' + root_dir[len(home):]

        settings = dict(
            # basics
            log_function=log_request,
            base_url=base_url,
            default_url=default_url,
            template_path=template_path,
            static_path=jupyter_app.static_file_path,
            static_custom_path=jupyter_app.static_custom_path,
            static_handler_class = FileFindHandler,
            static_url_prefix = url_path_join(base_url,'/static/'),
            static_handler_args = {
                # don't cache custom.js
                'no_cache_paths': [url_path_join(base_url, 'static', 'custom')],
            },
            version_hash=version_hash,
            ignore_minified_js=jupyter_app.ignore_minified_js,

            # rate limits
            iopub_msg_rate_limit=jupyter_app.iopub_msg_rate_limit,
            iopub_data_rate_limit=jupyter_app.iopub_data_rate_limit,
            rate_limit_window=jupyter_app.rate_limit_window,

            # authentication
            cookie_secret=jupyter_app.cookie_secret,
            login_url=url_path_join(base_url,'/login'),
            login_handler_class=jupyter_app.login_handler_class,
            logout_handler_class=jupyter_app.logout_handler_class,
            password=jupyter_app.password,
            xsrf_cookies=True,
            disable_check_xsrf=jupyter_app.disable_check_xsrf,
            allow_remote_access=jupyter_app.allow_remote_access,
            local_hostnames=jupyter_app.local_hostnames,

            # managers
            kernel_manager=kernel_manager,
            contents_manager=contents_manager,
            session_manager=session_manager,
            kernel_spec_manager=kernel_spec_manager,
            config_manager=config_manager,

            # handlers
            extra_services=extra_services,

            # Jupyter stuff
            started=now,
            # place for extensions to register activity
            # so that they can prevent idle-shutdown
            last_activity_times={},
            jinja_template_vars=jupyter_app.jinja_template_vars,
            nbextensions_path=jupyter_app.nbextensions_path,
            websocket_url=jupyter_app.websocket_url,
            mathjax_url=jupyter_app.mathjax_url,
            mathjax_config=jupyter_app.mathjax_config,
            shutdown_button=jupyter_app.quit_button,
            config=jupyter_app.config,
            config_dir=jupyter_app.config_dir,
            allow_password_change=jupyter_app.allow_password_change,
            server_root_dir=root_dir,
            jinja2_env=env,
            terminals_available=False,  # Set later if terminals are available
        )

        # allow custom overrides for the tornado web app.
        settings.update(settings_overrides)
        return settings

    def init_handlers(self, settings):
        """Load the (URL pattern, handler) tuples for each component."""

        # Order matters. The first handler to match the URL will handle the request.
        handlers = []
        # load extra services specified by users before default handlers
        for service in settings['extra_services']:
            handlers.extend(load_handlers(service))
        handlers.extend(load_handlers('notebook.tree.handlers'))
        handlers.extend([(r"/login", settings['login_handler_class'])])
        handlers.extend([(r"/logout", settings['logout_handler_class'])])
        handlers.extend(load_handlers('notebook.files.handlers'))
        handlers.extend(load_handlers('notebook.view.handlers'))
        handlers.extend(load_handlers('notebook.notebook.handlers'))
        handlers.extend(load_handlers('notebook.nbconvert.handlers'))
        handlers.extend(load_handlers('notebook.bundler.handlers'))
        handlers.extend(load_handlers('notebook.kernelspecs.handlers'))
        handlers.extend(load_handlers('notebook.edit.handlers'))
        handlers.extend(load_handlers('notebook.services.api.handlers'))
        handlers.extend(load_handlers('notebook.services.config.handlers'))
        handlers.extend(load_handlers('notebook.services.kernels.handlers'))
        handlers.extend(load_handlers('notebook.services.contents.handlers'))
        handlers.extend(load_handlers('notebook.services.sessions.handlers'))
        handlers.extend(load_handlers('notebook.services.nbconvert.handlers'))
        handlers.extend(load_handlers('notebook.services.kernelspecs.handlers'))
        handlers.extend(load_handlers('notebook.services.security.handlers'))
        handlers.extend(load_handlers('notebook.services.shutdown'))
        handlers.extend(settings['contents_manager'].get_extra_handlers())

        handlers.append(
            (r"/nbextensions/(.*)", FileFindHandler, {
                'path': settings['nbextensions_path'],
                'no_cache_paths': ['/'], # don't cache anything in nbextensions
            }),
        )
        handlers.append(
            (r"/custom/(.*)", FileFindHandler, {
                'path': settings['static_custom_path'],
                'no_cache_paths': ['/'], # don't cache anything in custom
            })
        )
        # register base handlers last
        handlers.extend(load_handlers('notebook.base.handlers'))
        # set the URL that will be redirected from `/`
        handlers.append(
            (r'/?', RedirectWithParams, {
                'url' : settings['default_url'],
                'permanent': False, # want 302, not 301
            })
        )

        # prepend base_url onto the patterns that we match
        new_handlers = []
        for handler in handlers:
            pattern = url_path_join(settings['base_url'], handler[0])
            new_handler = tuple([pattern] + list(handler[1:]))
            new_handlers.append(new_handler)
        # add 404 on the end, which will catch everything that falls through
        new_handlers.append((r'(.*)', Template404))
        return new_handlers

    def last_activity(self):
        """Get a UTC timestamp for when the server last did something.

        Includes: API activity, kernel activity, kernel shutdown, and terminal
        activity.
        """
        sources = [
            self.settings['started'],
            self.settings['kernel_manager'].last_kernel_activity,
        ]
        try:
            sources.append(self.settings['api_last_activity'])
        except KeyError:
            pass
        try:
            sources.append(self.settings['terminal_last_activity'])
        except KeyError:
            pass
        sources.extend(self.settings['last_activity_times'].values())
        return max(sources)


class NotebookPasswordApp(JupyterApp):
    """Set a password for the notebook server.

    Setting a password secures the notebook server
    and removes the need for token-based authentication.
    """
    
    description = __doc__

    def _config_file_default(self):
        return os.path.join(self.config_dir, 'jupyter_notebook_config.json')

    def start(self):
        from .auth.security import set_password
        set_password(config_file=self.config_file)
        self.log.info("Wrote hashed password to %s" % self.config_file)

def shutdown_server(server_info, timeout=5, log=None):
    """Shutdown a notebook server in a separate process.

    *server_info* should be a dictionary as produced by list_running_servers().

    Will first try to request shutdown using /api/shutdown .
    On Unix, if the server is still running after *timeout* seconds, it will
    send SIGTERM. After another timeout, it escalates to SIGKILL.

    Returns True if the server was stopped by any means, False if stopping it
    failed (on Windows).
    """
    from tornado.httpclient import HTTPClient, HTTPRequest
    url = server_info['url']
    pid = server_info['pid']
    req = HTTPRequest(url + 'api/shutdown', method='POST', body=b'', headers={
        'Authorization': 'token ' + server_info['token']
    })
    if log: log.debug("POST request to %sapi/shutdown", url)
    HTTPClient().fetch(req)

    # Poll to see if it shut down.
    for _ in range(timeout*10):
        if check_pid(pid):
            if log: log.debug("Server PID %s is gone", pid)
            return True
        time.sleep(0.1)

    if sys.platform.startswith('win'):
        return False

    if log: log.debug("SIGTERM to PID %s", pid)
    os.kill(pid, signal.SIGTERM)

    # Poll to see if it shut down.
    for _ in range(timeout * 10):
        if check_pid(pid):
            if log: log.debug("Server PID %s is gone", pid)
            return True
        time.sleep(0.1)

    if log: log.debug("SIGKILL to PID %s", pid)
    os.kill(pid, signal.SIGKILL)
    return True  # SIGKILL cannot be caught


class NbserverStopApp(JupyterApp):
    version = __version__
    description="Stop currently running notebook server for a given port"

    port = Integer(8888, config=True,
        help="Port of the server to be killed. Default 8888")

    def parse_command_line(self, argv=None):
        super(NbserverStopApp, self).parse_command_line(argv)
        if self.extra_args:
            self.port=int(self.extra_args[0])

    def shutdown_server(self, server):
        return shutdown_server(server, log=self.log)

    def start(self):
        servers = list(list_running_servers(self.runtime_dir))
        if not servers:
            self.exit("There are no running servers")
        for server in servers:
            if server['port'] == self.port:
                print("Shutting down server on port", self.port, "...")
                if not self.shutdown_server(server):
                    sys.exit("Could not stop server")
                return
        else:
            print("There is currently no server running on port {}".format(self.port), file=sys.stderr)
            print("Ports currently in use:", file=sys.stderr)
            for server in servers:
                print("  - {}".format(server['port']), file=sys.stderr)
            self.exit(1)


class NbserverListApp(JupyterApp):
    version = __version__
    description=_("List currently running notebook servers.")
    
    flags = dict(
        jsonlist=({'NbserverListApp': {'jsonlist': True}},
              _("Produce machine-readable JSON list output.")),
        json=({'NbserverListApp': {'json': True}},
              _("Produce machine-readable JSON object on each line of output.")),
    )
    
    jsonlist = Bool(False, config=True,
          help=_("If True, the output will be a JSON list of objects, one per "
                 "active notebook server, each with the details from the "
                 "relevant server info file."))
    json = Bool(False, config=True,
          help=_("If True, each line of output will be a JSON object with the "
                  "details from the server info file. For a JSON list output, "
                  "see the NbserverListApp.jsonlist configuration value"))

    def start(self):
        serverinfo_list = list(list_running_servers(self.runtime_dir))
        if self.jsonlist:
            print(json.dumps(serverinfo_list, indent=2))
        elif self.json:
            for serverinfo in serverinfo_list:
                print(json.dumps(serverinfo))
        else:
            print("Currently running servers:")
            for serverinfo in serverinfo_list:
                url = serverinfo['url']
                if serverinfo.get('token'):
                    url = url + '?token=%s' % serverinfo['token']
                print(url, "::", serverinfo['notebook_dir'])

#-----------------------------------------------------------------------------
# Aliases and Flags
#-----------------------------------------------------------------------------

flags = dict(base_flags)
flags['no-browser']=(
    {'NotebookApp' : {'open_browser' : False}},
    _("Don't open the notebook in a browser after startup.")
)
flags['pylab']=(
    {'NotebookApp' : {'pylab' : 'warn'}},
    _("DISABLED: use %pylab or %matplotlib in the notebook to enable matplotlib.")
)
flags['no-mathjax']=(
    {'NotebookApp' : {'enable_mathjax' : False}},
    """Disable MathJax
    
    MathJax is the javascript library Jupyter uses to render math/LaTeX. It is
    very large, so you may want to disable it if you have a slow internet
    connection, or for offline use of the notebook.
    
    When disabled, equations etc. will appear as their untransformed TeX source.
    """
)

flags['allow-root']=(
    {'NotebookApp' : {'allow_root' : True}},
    _("Allow the notebook to be run from root user.")
)

# Add notebook manager flags
flags.update(boolean_flag('script', 'FileContentsManager.save_script',
               'DEPRECATED, IGNORED',
               'DEPRECATED, IGNORED'))

aliases = dict(base_aliases)

aliases.update({
    'ip': 'NotebookApp.ip',
    'port': 'NotebookApp.port',
    'port-retries': 'NotebookApp.port_retries',
    'transport': 'KernelManager.transport',
    'keyfile': 'NotebookApp.keyfile',
    'certfile': 'NotebookApp.certfile',
    'client-ca': 'NotebookApp.client_ca',
    'notebook-dir': 'NotebookApp.notebook_dir',
    'browser': 'NotebookApp.browser',
    'pylab': 'NotebookApp.pylab',
})

#-----------------------------------------------------------------------------
# NotebookApp
#-----------------------------------------------------------------------------

class NotebookApp(JupyterApp):

    name = 'jupyter-notebook'
    version = __version__
    description = _("""The Jupyter HTML Notebook.
    
    This launches a Tornado based HTML Notebook Server that serves up an HTML5/Javascript Notebook client.""")
    examples = _examples
    aliases = aliases
    flags = flags
    
    classes = [
        KernelManager, Session, MappingKernelManager,
        ContentsManager, FileContentsManager, NotebookNotary,
        KernelSpecManager,
    ]
    flags = Dict(flags)
    aliases = Dict(aliases)
    
    subcommands = dict(
        list=(NbserverListApp, NbserverListApp.description.splitlines()[0]),
        stop=(NbserverStopApp, NbserverStopApp.description.splitlines()[0]),
        password=(NotebookPasswordApp, NotebookPasswordApp.description.splitlines()[0]),
    )

    _log_formatter_cls = LogFormatter

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

    @observe('webapp_settings') 
    def _update_webapp_settings(self, change):
        self.log.warning(_("\n    webapp_settings is deprecated, use tornado_settings.\n"))
        self.tornado_settings = change['new']
    
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

    base_project_url = Unicode('/', config=True, help=_("""DEPRECATED use base_url"""))

    @observe('base_project_url')
    def _update_base_project_url(self, change):
        self.log.warning(_("base_project_url is deprecated, use base_url"))
        self.base_url = change['new']

    extra_nbextensions_path = List(Unicode(), config=True,
        help=_("""extra paths to look for Javascript notebook extensions""")
    )

    extra_services = List(Unicode(), config=True,
        help=_("""handlers that should be loaded at higher priority than the default services""")
    )
    
    @property
    def nbextensions_path(self):
        """The path to look for Javascript notebook extensions"""
        path = self.extra_nbextensions_path + jupyter_path('nbextensions')
        # FIXME: remove IPython nbextensions path after a migration period
        try:
            from IPython.paths import get_ipython_dir
        except ImportError:
            pass
        else:
            path.append(os.path.join(get_ipython_dir(), 'nbextensions'))
        return path

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


    @default('notebook_dir')
    def _default_notebook_dir(self):
        if self.file_to_run:
            return os.path.dirname(os.path.abspath(self.file_to_run))
        else:
            return py3compat.getcwd()

    @validate('notebook_dir')
    def _notebook_dir_validate(self, proposal):
        value = proposal['value']
        # Strip any trailing slashes
        # *except* if it's root
        _, path = os.path.splitdrive(value)
        if path == os.sep:
            return value
        value = value.rstrip(os.sep)
        if not os.path.isabs(value):
            # If we receive a non-absolute path, make it absolute.
            value = os.path.abspath(value)
        if not os.path.isdir(value):
            raise TraitError(trans.gettext("No such notebook dir: '%r'") % value)
        return value

    @observe('notebook_dir')
    def _update_notebook_dir(self, change):
        """Do a bit of validation of the notebook dir."""
        # setting App.notebook_dir implies setting notebook and kernel dirs as well
        new = change['new']
        self.config.FileContentsManager.root_dir = new
        self.config.MappingKernelManager.root_dir = new

    # TODO: Remove me in notebook 5.0
    server_extensions = List(Unicode(), config=True,
        help=(_("DEPRECATED use the nbserver_extensions dict instead"))
    )

    nbserver_extensions = Dict({}, config=True,
        help=(_("Dict of Python modules to load as notebook server extensions."
              "Entry values can be used to enable and disable the loading of"
              "the extensions. The extensions will be loaded in alphabetical "
              "order."))
    )

    def parse_command_line(self, argv=None):
        super(NotebookApp, self).parse_command_line(argv)

        if self.extra_args:
            arg0 = self.extra_args[0]
            f = os.path.abspath(arg0)
            self.argv.remove(arg0)
            if not os.path.exists(f):
                self.log.critical(_("No such file or directory: %s"), f)
                self.exit(1)
            
            # Use config here, to ensure that it takes higher priority than
            # anything that comes from the config dirs.
            c = Config()
            if os.path.isdir(f):
                c.NotebookApp.notebook_dir = f
            elif os.path.isfile(f):
                c.NotebookApp.file_to_run = f
            self.update_config(c)

    def init_webapp(self):
        """initialize tornado webapp and httpserver"""


    @catch_config_error
    def initialize(self, argv=None):
        super(NotebookApp, self).initialize(argv)


    def start(self):
        """ Start the Notebook server app, after initialization
        
        This method takes no arguments so all configuration and initialization
        must be done prior to calling this method."""

        super(NotebookApp, self).start()

    def stop(self):
        """"""

main = launch_new_instance = NotebookApp.launch_instance
