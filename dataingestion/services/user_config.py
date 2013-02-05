import os
import ConfigParser

#Fields in the configuration file.
CONFIG_SECTION = 'iDigBio'
DISABLE_CHECK = "devmode_disable_startup_service_check"
IDIGBIOPROVIDEDBYGUID = 'accountuuid'
RECORDSET_ID = 'rsguid'
IMAGE_LICENSE = 'imagelicense'
MEDIACONTENT_KEYWORD = 'mediaContentKeyword'
IDIGBIO_PROVIDER_GUID = 'iDigbioProviderGUID'
IDIGBIO_PUBLISHER_GUID = 'iDigbioPublisherGUID'
FUNDING_SOURCE = 'fundingSource'
FUNDING_PURPOSE = 'fundingPurpose'

config = None

def setup(config_file):
    global config
    config = UserConfig(config_file)
    config.reload()

def get_user_config(name):
    # TODO: check whether the name is in the allowed list.
    return getattr(config, name)

def set_user_config(name, value):
    setattr(config, name, value)

def rm_user_config():
    if os.path.exists(config.config_file):
        os.remove(config.config_file)
    config.config = ConfigParser.ConfigParser()

def try_get_user_config(name):
    try:
        return getattr(config, name)
    except AttributeError:
        return None

class UserConfig(object):
    """
    The class with the user config values.
    """
    def __init__(self, config_file):
        self.config = ConfigParser.ConfigParser()
        self.config_file = config_file

    def reload(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)

        if not self.config.has_section(CONFIG_SECTION):
            self.config.add_section(CONFIG_SECTION)

    def __getattr__(self, name):
        self.reload()

        if self.config.has_option(CONFIG_SECTION, name):
            return self.config.get(CONFIG_SECTION, name)
        else:
            raise AttributeError()

    def __setattr__(self, name, value):
        if name == 'config' or name == 'config_file':
            self.__dict__[name] = value
            return

        self.config.set(CONFIG_SECTION, name, value)
        with open(self.config_file, 'wb') as f:
            self.config.write(f)

    # Check if the authentication check is disabled.
    def check_disabled(self):
        self.reload()

        if self.config.has_option(CONFIG_SECTION, DISABLE_CHECK):
            return self.config.get(CONFIG_SECTION, DISABLE_CHECK)
        else:
            return False

def main():
    import tempfile
    f = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    f_path = f.name
    print f_path
    f.close()
    conf = UserConfig(f_path)
    conf.account_uuid = 'id1'
    conf.api_key = 'key1'
    assert getattr(conf, 'api_key') == 'key1'

if __name__ == '__main__':
    main()


 