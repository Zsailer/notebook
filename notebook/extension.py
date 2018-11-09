from jupyter_server.serverapp import load_handlers
from notebook import DEFAULT_STATIC_FILES_PATH, DEFAULT_TEMPLATE_PATH_LIST
from notebook.notebookapp import NotebookApp

extension_configurables = [NotebookApp]

def load_jupyter_server_extension(server_app):
    """Load the legacy notebook as extension.
    """
    # Get Jupyter Web Application.
    web_app = server_app.web_app
    
    # Initialize the Notebook app and get config.
    notebookapp = NotebookApp(config=server_app.config)

    # Monkey Patch the setting with paths to Notebook Static files and Templates.
    web_app.settings['mathjax_url'] = notebookapp.mathjax_url
    web_app.settings['mathjax_config'] = notebookapp.mathjax_config
    web_app.settings['static_path'].append(DEFAULT_STATIC_FILES_PATH)
    web_app.settings['template_path'].extend(
        DEFAULT_TEMPLATE_PATH_LIST)

    # Add Notebook Handlers to Server Application
    host_pattern = '.*$'
    handlers = []
    handlers.extend(load_handlers('notebook.notebook.handlers'))
    handlers.extend(load_handlers('notebook.tree.handlers'))
    web_app.add_handlers(host_pattern, handlers)

    # Set the server_app to open a browser.
    server_app.open_browser = True
    server_app.base_url = '/tree'
