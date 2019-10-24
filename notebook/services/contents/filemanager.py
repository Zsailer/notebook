from notebook.jupyter_server_shim import jupyter_server_shim
from jupyter_server.services.contents.filemanager import (
    datetime,
    errno,
    io,
    os,
    shutil,
    stat,
    sys,
    warnings,
    mimetypes,
    nbformat,
    send2trash,
    web,
    FileCheckpoints,
    FileManagerMixin,
    ContentsManager,
    exists,
    import_item,
    Any,
    Unicode,
    Bool,
    TraitError,
    observe,
    default,
    validate,
    tz,
    is_hidden,
    is_file_hidden,
    to_api_path,
    AuthenticatedFileHandler,
    _,
    samefile,
    # Defined in this module.
    _script_exporter,
    FileContentsManager
)

from ipython_genutils.py3compat import getcwd, string_types

jupyter_server_shim()



def _post_save_script(model, os_path, contents_manager, **kwargs):
    """convert notebooks to Python script after save with nbconvert
    replaces `jupyter notebook --script`
    """
    from nbconvert.exporters.script import ScriptExporter
    warnings.warn("`_post_save_script` is deprecated and will be removed in Notebook 5.0", DeprecationWarning)

    if model['type'] != 'notebook':
        return

    global _script_exporter
    if _script_exporter is None:
        _script_exporter = ScriptExporter(parent=contents_manager)
    log = contents_manager.log

    base, ext = os.path.splitext(os_path)
    script, resources = _script_exporter.from_filename(os_path)
    script_fname = base + resources.get('output_extension', '.txt')
    log.info("Saving script /%s", to_api_path(script_fname, contents_manager.root_dir))
    with io.open(script_fname, 'w', encoding='utf-8') as f:
        f.write(script)