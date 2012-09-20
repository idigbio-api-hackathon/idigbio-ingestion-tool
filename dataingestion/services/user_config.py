import os
import ConfigParser

CONFIG_SECTION = 'iDigBio'

config = None

def setup(config_file):
    global config
    config = UserConfig(config_file)


class UserConfig(object):
    """
    The class with the user config values.
    """
    def __init__(self, config_file):
        self.config = ConfigParser.ConfigParser()
        self.config_file = config_file

        if os.path.exists(config_file):
            self.config.read(config_file)

        if not self.config.has_section(CONFIG_SECTION):
            self.config.add_section(CONFIG_SECTION)

    def __getattr__(self, name):
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


