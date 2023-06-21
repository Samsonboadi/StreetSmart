''' Handles the Window loaded message '''
import json


class WindowLoadedHandler():  # pylint: disable=too-few-public-methods
    ''' Cone Handler '''

    def __init__(self, streetsmart, settings):
        self.streetsmart = streetsmart
        self.settings = settings

    def __get_locale(self):
        """Returns a changed version of the QGIS locale

        Returned value is understood by StreetSmart
        """
        qgis_settings = self.settings.settings
        locale = qgis_settings[self.settings.LANGUAGE].value
        if not locale.startswith("en"):
            locale = locale[0:2]
        if locale not in self.settings.get_streetsmart_locales():
            locale = self.settings.get_default_streetsmart_locale()
        return locale.replace("_", "-")

    def handle(self, _):
        """ Handle Window Loaded command

        Sends the settings for the Street Smart api to the browser window
        """
        qgis_settings = self.settings.settings
        settings = {}
        userSettings = {}
        userSettings["username"] = qgis_settings[self.settings.USERNAME].value
        userSettings["password"] = qgis_settings[self.settings.PASSWORD].value
        userSettings["apiKey"] = qgis_settings[self.settings.API_KEY].value
        settings["userSettings"] = userSettings

        addressSettings = {}
        addressSettings["locale"] = "en"
        addressSettings["database"] = "Nokia"
        settings["addressSettings"] = addressSettings

        configSettings = {}
        project_srs = self.streetsmart.iface.mapCanvas().mapSettings().destinationCrs().authid()
        configSettings["srs"] = project_srs  # qgis_settings[self.settings.STREETSMART_SRS].value

        locale = self.__get_locale()

        configSettings["locale"] = locale
        configSettings["configUrl"] = qgis_settings[self.settings.CONFIGURATION_URL].value
        configSettings["streetsmartApiUrl"] = qgis_settings[self.settings.STREETSMART_LOCATION].value
        settings["configSettings"] = configSettings

        message_load = json.dumps(settings)
        self.streetsmart.sendToViewer("initapi|{}".format(message_load))
