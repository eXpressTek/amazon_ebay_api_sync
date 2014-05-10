import os
from ConfigParser import SafeConfigParser

CONFIG_FILES = [
    'db.conf'
]

def load_file_config(path=None):
    """
    Loads configuration from file with following content::

    :param path: path to config file. If not specified, locations
    ``/etc/amazon-product-api.cfg`` and ``~/.amazon-product-api`` are tried.
    """
    config = SafeConfigParser()
    if path is None:
        config.read([os.path.expanduser(path) for path in CONFIG_FILES])
    else:
        config.read(path)

    if not config.has_section('Credentials'):
        return {}

    return dict(
        (key, val)
        for key, val in config.items('Credentials')
    )
