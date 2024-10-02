import tempfile
from configparser import ConfigParser


def setup_config():
    config_file = tempfile.NamedTemporaryFile()
    with open(config_file.name, "w") as f:
        custom_conf = ConfigParser()
        custom_conf.add_section("User-Agent")
        custom_conf.set("User-Agent", "name", "libmozdata")
        custom_conf.write(f)
        f.seek(0)

    from libmozdata import config

    config.set_config(config.ConfigIni(config_file.name))


setup_config()
