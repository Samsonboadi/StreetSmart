""" Street Smart Settings """
import copy
import logging
import unittest


try:
    from .logger import log
except ImportError:
    from logger import log


SETTING_GROUP = "streetsmart"

try:
    from qgis.core import QgsProject  # pylint: disable=import-error
    from qgis.core import QgsSettings
except ImportError:

    class QgsProject():
        """ Class for test purpose """
        # pylint: disable=missing-function-docstring
        def __init__(self):
            self.__entry_count_written = 0
            self.__entries = {}

        def __del__(self):
            del self.__entries
            del self.__entry_count_written

        @classmethod
        def instance(cls):
            return QgsProject()

        def writeEntry(self, group, key, value):
            if group not in self.__entries:
                self.__entries[group] = {}
            self.__entries[group][key] = value
            self.__entry_count_written = self.__entry_count_written + 1

        def readEntry(self, group, key, default):
            result = default
            type_conversion_ok = True
            if (group in self.__entries
                and key in self.__entries[group]):
                    result = self.__entries[group][key]

            return (result, type_conversion_ok)

        def entry_count_written(self):
            return self.__entry_count_written

    class QgsSettings():
        """Class for test purpose"""
        def setValue(self, setting, value):
            """Sets value of a setting

            Meant for testing purpose"""

        def value(self, setting, default):
            """Gets value of a setting

            Meant for testing purpose"""


class Setting():
    """ Setting class """
    def __init__(self, group, default, value):
        self.__group = group
        self.__value = value
        self.__default = default

    def __str__(self):
        return "{} {} {}".format(self.group, self.value, self.default)

    def __repr__(self):
        return self.__str__()

    @property
    def group(self):
        """ Group to which the user parameter belongs """
        return self.__group

    @property
    def default(self):
        """ Default value of the user parameter """
        return self.__default

    @property
    def value(self):
        """ Current value of the user parameter """
        return self.__value


class Settings:
    """ Settings class """
    myvar = ''
    # Constants
    USERNAME = "username"
    PASSWORD = "password"
    API_KEY = "api_key"
    LANGUAGE = "language"
    USE_DEFAULT_CONFIGURATION_URL = "use_default_configuration_url"
    CONFIGURATION_URL = "configuration_url"
    USE_DEFAULT_STREETSMART_LOCATION = "use_default_streetmart_location"
    STREETSMART_LOCATION = "streetmart_location"
    STREETSMART_SRS = "streetmart_srs"
    USE_DEFAULT_RECORDING_WFS_LOCATION = "use_default_recording_wfs_location"
    RECORDING_WFS_LOCATION = "recording_wfs_location"
    USE_PROXY_SERVER = "use_proxy_server"
    PROXY_SERVER_TYPE = "proxy_server_type"
    PROXY_EXCLUDED_URLS = "proxy_excluded_urls"
    PROXY_NO_PROXY_URLS = "proxy_no_proxy_urls"
    PROXY_ADDRESS = "proxy_address"
    PROXY_PORT = "proxy_port"
    BYPASS_PROXY_FOR_LOCAL_ADDRESSES = "bypass_proxy_for_local_addresses"
    USE_DEFAULT_PROXY_CREDENTIALS = "use_default_proxy_credentials"
    PROXY_USERNAME = "proxy_username"
    PROXY_PASSWORD = "proxy_password"
    PROXY_DOMAIN = "proxy_domain"
    LATITUDE_PRECISION = 0
    LONGITUDE_PRECISION = 0
    HEIGHT_PRECISION = 0
    ALL = [
        USERNAME, PASSWORD, API_KEY, LANGUAGE, USE_DEFAULT_CONFIGURATION_URL,
        CONFIGURATION_URL, USE_DEFAULT_STREETSMART_LOCATION,
        STREETSMART_LOCATION, USE_DEFAULT_RECORDING_WFS_LOCATION,
        RECORDING_WFS_LOCATION, USE_PROXY_SERVER, PROXY_SERVER_TYPE,
        PROXY_EXCLUDED_URLS, PROXY_NO_PROXY_URLS, PROXY_ADDRESS, PROXY_PORT,
        BYPASS_PROXY_FOR_LOCAL_ADDRESSES, USE_DEFAULT_PROXY_CREDENTIALS,
        PROXY_USERNAME, PROXY_PASSWORD, PROXY_DOMAIN,LATITUDE_PRECISION,
        LONGITUDE_PRECISION,HEIGHT_PRECISION,
    ]
    _parameter_to_defaults = {
        # pylint: disable=line-too-long
        USERNAME: ["username", "login", None],
        PASSWORD: ["password", "login", None],
        API_KEY: ["api_key", "login", "C_Y52jQdajQVWzgFivgVSLop2PM1iPUx2TAVq78da3IJiLM9i_MVuvkhCToZyXAp"],
        LANGUAGE: ["language", "login", "en-us"],
        USE_DEFAULT_CONFIGURATION_URL: ["use_default_configuration_url", "login", True],  # noqa: E501
        CONFIGURATION_URL: ["configuration_url", "login", 'https://atlas.cyclomedia.com/configuration'],
        USE_DEFAULT_STREETSMART_LOCATION: ["use_default_streetmart_location", "login", True],  # noqa: E501
        STREETSMART_LOCATION: ["streetmart_location", "login", "https://streetsmart.cyclomedia.com/api/v22.14/StreetSmartApi.js"], #v22.12  v23.2.0  v22.14 #v22.14 #22.20.2 https://streetsmart.cyclomedia.com/api/v22.20/api.html
        STREETSMART_SRS: ["streetmart_srs", "login", 'EPSG:28992'], # https://streetsmart.cyclomedia.com/api/v23.3/StreetSmartApi.js
        USE_DEFAULT_RECORDING_WFS_LOCATION: ["use_default_recording_wfs_location", "login", True],
        RECORDING_WFS_LOCATION: ["recording_wfs_location", "login", "https://atlas.cyclomedia.com/recordings/wfs"], #https://atlasapi.cyclomedia.com/staging/recording/wfs?SERVICE=WFS&request=GetCapabilities  https://atlas.cyclomedia.com/recordings/wfs
        USE_PROXY_SERVER: ["use_proxy_server", "login", False],
        PROXY_SERVER_TYPE: ["proxy_server_type", "login", None],
        PROXY_EXCLUDED_URLS: ["proxy_excluded_urls", "login", None],
        PROXY_NO_PROXY_URLS: ["proxy_no_proxy_urls", "login", None],
        PROXY_ADDRESS: ["proxy_address", "login", None],
        PROXY_PORT: ["proxy_port", "login", None],
        BYPASS_PROXY_FOR_LOCAL_ADDRESSES: ["bypass_proxy_for_local_addresses", "login", False],  # noqa: E501
        USE_DEFAULT_PROXY_CREDENTIALS: ["use_default_proxy_credentials", "login", True],  # noqa: E501
        PROXY_USERNAME: ["proxy_username", "login", None],
        PROXY_PASSWORD: ["proxy_password", "login", None],
        PROXY_DOMAIN: ["proxy_domain", "login", None],
        LATITUDE_PRECISION: ["latitude_precision","login",0.001 ], # Make the settings persist
        LONGITUDE_PRECISION:["longitude_precision","login", 0.001 ],
        HEIGHT_PRECISION:["height_precision","login", 0.001],
    }

    __instance = None
    @staticmethod
    def getInstance():
        """ Static access method. """
        if Settings.__instance is None:
            Settings(QgsSettings())
        return Settings.__instance

    @staticmethod
    def delInstance():
        """ Delete instance

        Only used in test cases where singleton is not desirable
        """
        Settings.__instance = None

    def __del__(self):
        del self.__project
        del self.__settings
        del self.__is_dirty

        Settings.__instance = None

    def __get_or_default_value(self, settings, group, attribute, default):
        """ Create a Setting for the parameter """
        current_value = self.__get_setting(settings, attribute, default)
        return Setting(group, default, current_value)

    @log(print_return=True)
    def __init_settings(self, qt_setting):
        """ Create a Setting for all user parameters """
        settings = {}
        for key in Settings._parameter_to_defaults:
            group = Settings._parameter_to_defaults[key][1]
            default = Settings._parameter_to_defaults[key][2]
            setting = self.__get_or_default_value(qt_setting,
                                                  group, key, default)
            settings[key] = setting

        return settings

    @log(print_args=True)
    def __init__(self, project=None):
        """ Virtually private constructor. """
        if Settings.__instance is not None:
            raise RuntimeError("This class is a singleton!")

        self.__project = project
        self.__settings = self.__init_settings(project)
        self.__is_dirty = False

        Settings.__instance = self

    def restore_defaults(self):
        """ Restore default settings """
        for key in self.__settings:
            self.__settings[key].value = self.__settings[key].default

    @property
    def project(self):
        """ Return QgsProject

        For test purposes
        """
        return self.__project

    def update_setting(self, attribute, new_value):
        """ Update a Setting """
        if new_value != self.__settings[attribute]:
            old_setting = self.__settings[attribute]
            group = old_setting.group
            default_value = old_setting.default
            new_setting = Setting(group, default_value, new_value)
            self.__settings[attribute] = new_setting
            self.__is_dirty = True

    @property
    def settings(self):
        """ Returns a copy of the settings """
        # Read the settings from the project. As the project can be changed,
        # the settings are possibly not the correct ones.
        self.__settings = self.__init_settings(self.__project)
        return copy.deepcopy(self.__settings)

    @property
    def is_dirty(self):
        """ is dirty """
        return self.__is_dirty

    @staticmethod
    @log(logging.DEBUG, print_return=True, print_args=True)
    def __get_setting(setting, attribute, default_value):
        """ Read setting """
        value = setting.value(_create_setting_key(attribute),
                              str(default_value))

        if isinstance(value, str):
            if value.lower() == 'none':
                value = None
            elif value.lower() == 'false':
                value = False
            elif value.lower() == 'true':
                value = True

        return value

    @staticmethod
    @log(logging.DEBUG, print_return=True, print_args=True)
    def __write_setting(setting, attribute, value):
        """Write a setting"""
        setting.setValue(_create_setting_key(attribute), value)

    @log(logging.DEBUG, print_return=True, print_args=True)
    def __save_setting(self, setting, attribute):
        """Saves a setting """
        default = self.__settings[attribute].default
        value = self.__settings[attribute].value

        if default != value:
            self.__write_setting(setting, attribute, value)

    def save(self):
        """ save """
        if self.__is_dirty:
            qgis_settings = self.__project
            for key in self.__settings:
                self.__save_setting(qgis_settings, key)
            self.__is_dirty = False
        else:
            print("Settings are not dirty -> do not save")

    @staticmethod
    @log(print_return=True)
    def getRecordingLayerName():
        """Returns the layername for the recordings layer."""
        return "CycloMedia Recording"

    
    @staticmethod
    @log(print_return=True)
    def retrieve_All_Querry_filter_on_location(filter_querry): #TODO
        """ Returns the filter to apply to the Atlas WFS """

        Settings.myvar = filter_querry
        return filter_querry


    @staticmethod
    @log(print_return=True)
    def getAtlasWFSFilter(): #TODO
        """ Returns the filter to apply to the Atlas WFS """
        #"expiredAt is null"

        
        if Settings.myvar == "":
            Settings.myvar = "expiredAt is null"
        return Settings.myvar

    @staticmethod
    def getAtlasSRSName():
        """ Returns the SRS to apply to the Atlas WFS """
        return "EPSG:4326"

    @staticmethod
    def get_cone_height():
        """ Size of the cone in screen meters """
        return 0.005

    @staticmethod
    def get_cone_angle():
        """
        Half of the angle between the two equal size legs of the triangle """
        return 45

    @staticmethod
    def get_timer_interval():
        """ Returns time between reading command queue in QGIS """
        return 0.1

    @staticmethod
    def get_overlay_search_radius():
        """Returns the radius in which features will be send to an overlay.

        This value is in meter and will be transformed to a value which
        corresponds to the projection which is used in the QGIS project."""
        return 60

    @staticmethod
    def get_log_filename():
        """ Returns the log filename """
        return "streetsmart.log"

    @staticmethod
    def get_streetsmart_locales():
        """Returns a list of supported languages in StreetSmart"""
        return ['de', 'en_GB', 'en_US', 'fi', 'fr', 'nl', 'tr']

    @staticmethod
    def get_default_streetsmart_locale():
        """Returns the default locale"""
        return 'en_US'


qgis_settings_mapping = {
    Settings.LANGUAGE: "locale/userlocale",
    Settings.USE_PROXY_SERVER: "proxy/proxyEnabled",
    Settings.PROXY_SERVER_TYPE: "proxy/proxyType",
    Settings.PROXY_EXCLUDED_URLS: "proxy/proxyExcludedUrls",
    Settings.PROXY_NO_PROXY_URLS: "proxy/noProxyUrls",
    Settings.PROXY_ADDRESS: "proxy/proxyHost",
    Settings.PROXY_PORT: "proxy/proxyPort",
    Settings.PROXY_USERNAME: "proxy/proxyUser",
    Settings.PROXY_PASSWORD: "proxy/proxyPassword",
}


@log(level=logging.DEBUG, print_return=True)
def _create_setting_key(attribute):
    """Creates a qualified setting key"""
    default = "{}/{}".format(SETTING_GROUP, attribute)
    return qgis_settings_mapping.get(attribute, default)


class TestSettings(unittest.TestCase):
    """ TestCase for the Settings class """
    def setUp(self):
        self.settings = Settings.getInstance()

    def tearDown(self):
        self.settings.delInstance()
        del self.settings

    def test_fail_when_created(self):
        """ Test """
        self.assertRaises(Exception, Settings())

    def test_get_instance_when_instance_called(self):
        """ Test """
        settings = self.settings
        self.assertIsInstance(settings, Settings)

    def test_singleton(self):
        """ Test that multiple getInstance calls returns the same object """
        settings = self.settings
        second_instance = Settings.getInstance()
        self.assertIs(settings, second_instance)
        del second_instance

    def test_get_default_value(self):
        """ Test """
        # pylint: disable=protected-access
        settings = self.settings
        for key in Settings._parameter_to_defaults:
            self.assertEqual(settings.settings[key].value,
                             Settings._parameter_to_defaults[key][2])

    def test_set_username(self):
        """ Test setter """
        settings = self.settings
        new_username = "A Users Name"
        settings.settings[Settings.USERNAME] = new_username
        self.assertIsNone(settings.settings[Settings.USERNAME].value)

    def test_set_username_2(self):
        """ Test setter """
        settings = self.settings
        new_username = "A Users Name"
        settings.update_setting(Settings.USERNAME, new_username)
        self.assertEqual(settings.settings[Settings.USERNAME].value,
                         new_username)
        self.assertTrue(settings.is_dirty)

    def test_do_not_save_when_nothing_has_changed(self):
        """ Test save """
        settings = self.settings
        settings.save()
        self.assertEqual(settings.project.entry_count_written(), 0)

    def test_save_when_username_has_changed(self):
        """ Test save """
        settings = self.settings
        new_username = "A Second Users Name"
        settings.update_setting(Settings.USERNAME, new_username)
        settings.save()
        self.assertEqual(settings.project.entry_count_written(), 1)
        self.assertEqual(settings.settings[Settings.USERNAME].value,
                         new_username)
        self.assertFalse(settings.is_dirty)


if __name__ == "__main__":
    unittest.main()
