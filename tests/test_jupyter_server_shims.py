import warnings
import importlib

import pytest

from notebook.jupyter_server_shim import shim_message


module_to_shim = [
    'notebook.auth',
    'notebook.auth.login',
    'notebook.auth.logout',
    'notebook.base',
    'notebook.auth.security',
    'notebook.base.handlers',
    'notebook.base.zmqhandlers',
    'notebook.edit',
    'notebook.edit.handlers',
    'notebook.files',
    'notebook.files.handlers',
    'notebook.gateway',
    'notebook.gateway.handlers',
    'notebook.gateway.managers',
    'notebook.kernelspecs',
    'notebook.kernelspecs.handlers',
    'notebook.nbconvert',
    'notebook.nbconvert.handlers',
    'notebook.prometheus',
    'notebook.prometheus.log_functions',
    'notebook.prometheus.metrics',
    'notebook.services',
    'notebook.services.shutdown',
    'notebook.services.api',
    'notebook.services.api.handlers',
    'notebook.services.config',
    'notebook.services.config.handlers',
    'notebook.services.config.manager',
    'notebook.services.contents',
    'notebook.services.contents.handlers',
    'notebook.services.contents.manager',
    'notebook.services.contents.checkpoints',
    'notebook.services.contents.filecheckpoints',
    'notebook.services.contents.fileio',
    'notebook.services.contents.filemanager',
    'notebook.services.contents.largefilemanager',
    'notebook.services.kernels',
    'notebook.services.kernels.handlers',
    'notebook.services.kernels.kernelmanager',
    'notebook.services.kernelspecs',
    'notebook.services.kernelspecs.handlers',
    'notebook.services.nbconvert',
    'notebook.services.nbconvert.handlers',
    'notebook.services.security',
    'notebook.services.security.handlers',
    'notebook.services.sessions',
    'notebook.services.sessions.handlers',
    'notebook.services.sessions.sessionmanager',
    'notebook.terminal',
    'notebook.terminal.api_handlers',
    'notebook.terminal.handlers',
    'notebook.view',
    'notebook.view.handlers',
    'notebook.config_manager',
    'notebook.log',
    'notebook.serverextensions',
    'notebook.utils'
]

shimmed_module = [mod.replace('notebook', 'jupyter_server') for mod in module_to_shim]


@pytest.mark.parametrize(
    'module,shim',
    zip(module_to_shim, shimmed_module)
)
def test_shimmed_module(module, shim, recwarn):
    # Deprecation warnings are ignored by default.
    # This test should change the filter to NOT ignore
    # this warnings
    warnings.simplefilter("always")

    # Import module
    mod = importlib.import_module(module)

    # Assert only one warning was raised.
    assert len(recwarn) == 1 
    assert str(recwarn[0].message) == shim_message(module, shim)

