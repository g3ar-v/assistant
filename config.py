import json
import os
import xdg.BaseDirectory

from xdg.BaseDirectory import xdg_config_home
from os.path import exists, isfile, dirname, join
from utils import ComboLock, get_temp_path, LOG, load_commented_json, merge_dict


DEFAULT_CONFIG = join(dirname(__file__), "device.conf")
USER_CONFIG = join(xdg_config_home, "vasco", "device.conf")


class LocalConf(dict):
    """Config dictionary from file."""

    _lock = ComboLock(get_temp_path("local-conf.lock"))

    def __init__(self, path):
        super(LocalConf, self).__init__()
        self.is_valid = True  # is loaded json valid, updated when load occurs
        if path:
            self.path = path
            self.load_local(path)

    def load_local(self, path):
        """Load local json file into self.

        Args:
            path (str): file to load
        """
        if exists(path) and isfile(path):
            try:
                config = load_commented_json(path)
                for key in config:
                    self.__setitem__(key, config[key])

                # LOG.debug("Configuration {} loaded".format(path))
            except Exception as e:
                LOG.error("Error loading configuration '{}'".format(path))
                LOG.error(repr(e))
                self.is_valid = False
        else:
            LOG.debug("Configuration '{}' not defined, skipping".format(path))

    def store(self, path=None, force=False):
        """Save config to disk.

        The cache will be used if the remote is unreachable to load settings
        that are as close to the user's as possible.

        path (str): path to store file to, if missing will use the path from
                    where the config was loaded.
        force (bool): Set to True if writing should occur despite the original
                      was malformed.

        Returns:
            (bool) True if save was successful, else False.
        """
        result = False
        with self._lock:
            path = path or self.path
            config_dir = dirname(path)
            if not exists(config_dir):
                os.makedirs(config_dir)

            if self.is_valid or force:
                with open(path, "w") as f:
                    json.dump(self, f, indent=2)
                result = True
            else:
                LOG.warning(
                    (
                        f'"{path}" was not a valid config file when '
                        "loaded, will not save config. Please correct "
                        "the json or remove it to allow updates."
                    )
                )
                result = False
        return result

    def merge(self, conf):
        merge_dict(self, conf)


class Configuration:
    """Namespace for operations on the configuration singleton."""

    __config = {}  # Cached config
    __patch = {}  # Patch config that skills can update to override config

    @staticmethod
    def get(configs=None):
        """Get configuration

        Returns cached instance if available otherwise builds a new
        configuration dict.

        Args:
            configs (list): List of configuration dicts

        Returns:
            (dict) configuration dictionary.
        """
        if Configuration.__config:
            return Configuration.__config
        else:
            return Configuration.load_config_stack(configs)

    @staticmethod
    def load_config_stack(configs=None):
        """Load a stack of config dicts into a single dict

        Args:
            configs (list): list of dicts to load
        Returns:
            (dict) merged dict of all configuration files
        """
        if not configs:
            configs = []

            # First use the patched config
            configs.append(Configuration.__patch)

            # Then use XDG config
            # This includes both the user config and
            # /etc/xdg/vasco/vasco.conf
            for conf_dir in xdg.BaseDirectory.load_config_paths("assistant"):
                configs.append(LocalConf(join(conf_dir, "device.conf")))

            # Then use the system config (/etc/vasco/vasco.conf)
            # configs.append(LocalConf(SYSTEM_CONFIG))

            # Then use the config that comes with the package
            configs.append(LocalConf(DEFAULT_CONFIG))

            # Make sure we reverse the array, as merge_dict will put every new
            # file on top of the previous one
            configs = reversed(configs)
        else:
            # Handle strings in stack
            for index, item in enumerate(configs):
                if isinstance(item, str):
                    configs[index] = LocalConf(item)

        # Merge all configs into one
        base = {}
        for c in configs:
            merge_dict(base, c)

        # copy into cache
        # if cache:
        #     Configuration.__config.clear()
        #     for key in base:
        #         Configuration.__config[key] = base[key]
        #     return Configuration.__config
        # else:
        return base

    # @staticmethod
    # def set_config_update_handlers(bus):
    #     """Setup websocket handlers to update config.

    #     Args:
    #         bus: Message bus client instance
    #     """
    #     bus.on("configuration.updated", Configuration.updated)
    #     bus.on("configuration.patch", Configuration.patch)
    #     bus.on("configuration.patch.clear", Configuration.patch_clear)

    @staticmethod
    def updated(message):
        """Handler for configuration.updated,

        Triggers an update of cached config.
        """
        Configuration.load_config_stack()

    @staticmethod
    def patch(message):
        """Patch the volatile dict usable by skills

        Args:
            message: Messagebus message should contain a config
                     in the data payload.
        """
        config = message.data.get("config", {})
        merge_dict(Configuration.__patch, config)
        Configuration.load_config_stack()

    @staticmethod
    def patch_clear(message):
        """Clear the config patch space.

        Args:
            message: Messagebus message should contain a config
                     in the data payload.
        """
        Configuration.__patch = {}
        Configuration.load_config_stack()
