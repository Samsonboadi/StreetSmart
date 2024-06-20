''' Module to manage street smart settings '''
import os
import logging
from PyQt5.QtWidgets import (  # pylint: disable=no-name-in-module
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QMessageBox,
    QVBoxLayout, QTabWidget, QPushButton, QCheckBox, QTextEdit,
)
from qgis.PyQt.QtCore import (  # pylint: disable=import-error
    QCoreApplication,
)
from ..logger import Logger
from ..logger import log
from ..street_smart import AbstractCommand
from ..settings import Settings

logger = Logger(__name__).get()


class ManageSettingsCommand(AbstractCommand):
    '''
    Class for Manage Settings Command
    '''
    def __init__(self, iface, streetsmart):
        '''
        Constructor
        '''
        super().__init__(iface, streetsmart)

    @staticmethod
    def icon_path():
        '''
        Path for the icon
        '''
        return ':/plugins/street_smart/resources/mActionOptions.svg'

    def text(self):
        '''
        Text for the command to show
        '''
        return super().tr('Settings Street Smart Plugin')

    @staticmethod
    def callback():
        '''
        Code to execute when command is clicked
        '''
        dialog = SettingsDialog(Settings.getInstance())
        dialog.exec_()

    def parent(self):
        '''
        Parent
        '''
        return self.iface.mainWindow()


class SettingsDialogModel():
    ''' Model '''
    def __init__(self, settings: Settings):
        self.settings = settings

    def old_settings(self):
        ''' Original Settings '''

    def new_settings(self):
        ''' Changed Settings '''


def tr(message: str) -> str:
    return QCoreApplication.translate('StreetSmart', message)


class SettingsDialog(QDialog):  # pylint: disable=too-few-public-methods
    ''' Manage settings GUI '''
    def __init__(self, settings):
        super(SettingsDialog, self).__init__()
        self.setWindowTitle(tr("Manage Settings"))

        self._settings = settings
        self._old_settings = self.__get_settings(settings)
        self._new_settings = {}
        self.__configuration_url_widget = None
        self.__streetsmart_location_widget = None
        self.__streetsmart_recordings_wfs_location_widget = None
        self.__proxy_server_domain_widget = None
        self.__proxy_server_password_widget = None
        self.__proxy_server_username_widget = None
        self.__proxy_server_port_widget = None
        self.__proxy_server_address_widget = None

        self.setMinimumWidth(600)
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.__create_tab_widget())
        mainLayout.addWidget(self.__create_button_box())
        self.setLayout(mainLayout)

    def __create_button_box(self):
        """ Creates the buttons for the user interface """
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok
                                     | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self._accept_settings)
        buttonBox.rejected.connect(self._reject_settings)

        return buttonBox

    def __create_tab_widget(self):
        ''' Create Tab '''
        tabs = QTabWidget()
        tabs.addTab(self._create_login_tab(), tr("Login"))
        # tabs.addTab(self._create_language_tab(), tr("Language"))
        tabs.addTab(self.__create_configuration_tab(), tr("Configuration"))
        tabs.addTab(self._create_about_tab(), tr("About"))
        tabs.addTab(self._create_agreement_tab(), tr("Agreement"))

        return tabs

    @staticmethod
    def __get_settings(settings):
        ''' Save Settings '''
        result = {}
        for key in Settings.ALL:
            print("Keep track of attribute {} with value {}".format(key, settings.settings[key].value))
            result[key] = settings.settings[key].value

        return result

    def __save_settings(self):
        ''' Save the changed settings '''
        for key in self._new_settings:
            logger.debug(f"Update setting, test {key}, new: {self._new_settings[key]},was: {self._old_settings[key]}")
            if self._new_settings[key] != self._old_settings[key]:
                logger.debug("Update setting %s %s -> %s", key, self._old_settings[key], self._new_settings[key])
                self._settings.update_setting(key, self._new_settings[key])
        self._settings.save()

    def _create_login_tab(self):
        ''' Login '''
        username = self._old_settings[Settings.USERNAME]
        password = self._old_settings[Settings.PASSWORD]
        groupbox = QGroupBox(tr("Login"))
        layout = QFormLayout()
        e = QLineEdit(username)
        # e.setText(username)
        e.textChanged.connect(self.__username_changed)
        layout.addRow(QLabel(tr("Username:")), e)
        pwd_edit = QLineEdit(password)
        pwd_edit.setEchoMode(QLineEdit.Password)
        # pwd_edit.setText(password)
        pwd_edit.textChanged.connect(self.__password_changed)
        layout.addRow(QLabel(tr("Password:")), pwd_edit)
        # status_label = QLabel(tr("Status not checked"))
        # layout.addRow(QLabel(tr("Status:")), status_label)
        # check_button = QPushButton(tr("Check"))
        # check_button.clicked.connect(self.check_clicked)
        # layout.addRow(None, check_button)
        groupbox.setLayout(layout)
        return groupbox

    def __username_changed(self, text):
        ''' h '''
        self._new_settings[Settings.USERNAME] = text
        print(text)

    def __password_changed(self, text):
        ''' h '''
        self._new_settings[Settings.PASSWORD] = text
        print(text)

    @staticmethod
    def check_clicked():
        ''' button check slot '''
        raise NotImplementedError("Check is not yet implemented")

    def _create_language_tab(self):
        ''' Language '''
        groupbox = QGroupBox(tr("Language"))
        layout = QFormLayout()
        e = QComboBox()
        e.addItems(["en-us", "nl-BE", "nl-NL"])
        e.setCurrentText("en-us")
        e.currentIndexChanged.connect(self.__language_changed)
        layout.addRow(QLabel(tr("Language:")), e)
        groupbox.setLayout(layout)
        return groupbox

    def __language_changed(self, text):
        ''' Language changed '''
        self._new_settings[Settings.LANGUAGE] = text
        print("Language changed: ", text)

    @staticmethod
    @log(logging.DEBUG, print_args=True)
    def __set_widget_enable_state(widget, enable):
        """ Sets the enabled state for a widget """
        print("Set widget enabled to ", enable)
        widget.setEnabled(enable)
        print("Enabled state is ", widget.isEnabled())

    def __create_configuration_box(self):
        """ Returns streetsmart configuration groupbox """

        def __configuration_url_changed(text):
            ''' h '''
            self._new_settings[Settings.CONFIGURATION_URL] = text
            logger.debug(f"Configuration URL in box changed: f{text}")

        @log(logging.DEBUG, print_args=True)
        def __use_default_url_changed(state):
            ''' Default url changed '''
            logger.debug(f"Use Default Configuration Checkbox State changed {state}")
            self._new_settings[Settings.USE_DEFAULT_CONFIGURATION_URL] = state
            if int(state) == 2:
                self._new_settings[Settings.CONFIGURATION_URL] = None
            self.__set_widget_enable_state(self.__configuration_url_widget,
                                           not state)

        config_groupbox = QGroupBox(tr("Config URL"))
        layout = QFormLayout()
        chk = QCheckBox()
        chk.stateChanged.connect(__use_default_url_changed)
        le = QLineEdit()
        le.textChanged.connect(__configuration_url_changed)
        self.__configuration_url_widget = le
        layout.addRow(chk, QLabel(tr("Use default")))
        layout.addRow(QLabel(tr("Location")), le)
        config_groupbox.setLayout(layout)

        # Set Initial Values
        use_default_configuration_url = self._old_settings[Settings.USE_DEFAULT_CONFIGURATION_URL]  # pylint: disable=line-too-long
        configuration_url = self._old_settings[Settings.CONFIGURATION_URL]
        if use_default_configuration_url:
            chk.setCheckState(2)
            le.setText("")
        else:
            chk.setCheckState(0)
            le.setText(configuration_url)

        return config_groupbox

    def __create_api_location_box(self):
        """ Returns streetsmart location configuration groupbox """

        def __use_default_location_changed(state):
            ''' Default streetsmart location checkbox changed '''
            self._new_settings[Settings.USE_DEFAULT_STREETSMART_LOCATION] = state
            if state == 2:
                self._new_settings[Settings.STREETSMART_LOCATION] = None
            self.__set_widget_enable_state(self.__streetsmart_location_widget,
                                           not state)

        def __location_url_changed(text):
            ''' h '''
            self._new_settings[Settings.STREETSMART_LOCATION] = text
            print(text)

        streetsmart_groupbox = QGroupBox(tr("StreetSmart URL"))
        layout = QFormLayout()
        chk = QCheckBox()
        chk.stateChanged.connect(__use_default_location_changed)
        le = QLineEdit()
        le.textChanged.connect(__location_url_changed)
        self.__streetsmart_location_widget = le
        layout.addRow(chk, QLabel(tr("Use default")))
        layout.addRow(QLabel(tr("Location")), le)
        streetsmart_groupbox.setLayout(layout)

        # Set Initial Values
        use_default_streetsmart_loc = self._old_settings[Settings.USE_DEFAULT_STREETSMART_LOCATION]  # pylint: disable=line-too-long
        streetsmart_location = self._old_settings[Settings.STREETSMART_LOCATION]
        if use_default_streetsmart_loc:
            chk.setCheckState(2)
            le.setText("")
        else:
            chk.setCheckState(0)
            le.setText(streetsmart_location)

        return streetsmart_groupbox

    def __create_recording_location_box(self):
        """ Returns recordings wgfs location configuration groupbox """

        def __use_default_recordings_wfs_location_changed(state):
            ''' Default recordings wfs location checkbox changed '''
            self._new_settings[Settings.USE_DEFAULT_RECORDING_WFS_LOCATION] = state
            if state == 2:
                self._new_settings[Settings.RECORDING_WFS_LOCATION] = None
            self.__set_widget_enable_state(self.__streetsmart_recordings_wfs_location_widget,
                                           not state)

        def __recordings_wfs_location_url_changed(text):
            ''' h '''
            self._new_settings[Settings.RECORDING_WFS_LOCATION] = text
            print(text)

        recording_wfs_groupbox = QGroupBox(tr("Recordings WFS URL"))
        layout = QFormLayout()
        chk = QCheckBox()
        chk.stateChanged.connect(__use_default_recordings_wfs_location_changed)
        le = QLineEdit()
        le.textChanged.connect(__recordings_wfs_location_url_changed)
        self.__streetsmart_recordings_wfs_location_widget = le
        layout.addRow(chk, QLabel(tr("Use default")))
        layout.addRow(QLabel(tr("Location")), le)
        recording_wfs_groupbox.setLayout(layout)

        # Set Initial Values
        use_default_recordings_wfs_loc = self._old_settings[Settings.USE_DEFAULT_RECORDING_WFS_LOCATION]  # pylint: disable=line-too-long
        recordings_wfs_location = self._old_settings[Settings.RECORDING_WFS_LOCATION]
        if use_default_recordings_wfs_loc:
            chk.setCheckState(2)
            le.setText("")
        else:
            chk.setCheckState(0)
            le.setText(recordings_wfs_location)

        return recording_wfs_groupbox

    def __create_proxy_box(self):
        """ Returns proxy server configuration groupbox """
        proxy_groupbox = QGroupBox(tr("Proxy Server"))
        layout = QFormLayout()
        chk = QCheckBox()
        chk.stateChanged.connect(self.__use_proxy_server_changed)
        layout.addRow(chk, QLabel(tr("Use a proxy server")))
        le_address = QLineEdit()
        layout.addRow(QLabel(tr("Address")), le_address)
        self.__proxy_server_address_widget = le_address
        le_port = QLineEdit()
        layout.addRow(QLabel(tr("Port")), le_port)
        self.__proxy_server_port_widget = le_port

        # Set Initial Values
        use_proxy_server = self._old_settings[Settings.USE_PROXY_SERVER]  # pylint: disable=line-too-long
        proxy_address = self._old_settings[Settings.PROXY_ADDRESS]
        proxy_port = self._old_settings[Settings.PROXY_PORT]
        if use_proxy_server:
            chk.setCheckState(0)
            le_address.setText("")
            le_port.setText("")
        else:
            chk.setCheckState(2)
            le_address.setText(proxy_address)
            le_port.setText(proxy_port)

        chk = QCheckBox()
        chk.stateChanged.connect(self.__bypass_proxy_local_changed)
        layout.addRow(chk, QLabel(tr("Bypass proxy for local addresses")))
        # Set Initial Values
        bypass_local_addresses = self._old_settings[Settings.BYPASS_PROXY_FOR_LOCAL_ADDRESSES]  # pylint: disable=line-too-long
        if bypass_local_addresses:
            chk.setCheckState(2)
        else:
            chk.setCheckState(0)

        chk = QCheckBox()
        chk.stateChanged.connect(self.__use_default_proxy_credentials_changed)
        layout.addRow(chk, QLabel(tr("Use default credentials")))
        le_username = QLineEdit()
        layout.addRow(QLabel(tr("Username")), le_username)
        self.__proxy_server_username_widget = le_username
        le_password = QLineEdit()
        layout.addRow(QLabel(tr("Password")), le_password)
        self.__proxy_server_password_widget = le_password
        le_domain = QLineEdit()
        layout.addRow(QLabel(tr("Domain")), le_domain)
        self.__proxy_server_domain_widget = le_domain

        # Set Initial Values
        use_default_proxy_credentials = self._old_settings[Settings.USE_DEFAULT_PROXY_CREDENTIALS]  # pylint: disable=line-too-long
        proxy_username = self._old_settings[Settings.PROXY_USERNAME]
        proxy_password = self._old_settings[Settings.PROXY_PASSWORD]
        proxy_domain = self._old_settings[Settings.PROXY_DOMAIN]
        if use_default_proxy_credentials:
            chk.setCheckState(2)
            le_username.setText("")
            le_password.setText("")
            le_domain.setText("")
        else:
            chk.setCheckState(0)
            le_username.setText(proxy_username)
            le_password.setText(proxy_password)
            le_domain.setText(proxy_domain)
        proxy_groupbox.setLayout(layout)
        return proxy_groupbox

    def __create_configuration_tab(self):
        ''' Configuration '''
        main_groupbox = QGroupBox(tr("Configuration"))
        main_layout = QVBoxLayout()

        main_layout.addWidget(self.__create_configuration_box())
        main_layout.addWidget(self.__create_api_location_box())
        main_layout.addWidget(self.__create_recording_location_box())
        # main_layout.addWidget(self.__create_proxy_box())

        main_groupbox.setLayout(main_layout)
        return main_groupbox

    def __use_proxy_server_changed(self, state):
        ''' Default url changed '''
        self._new_settings[Settings.USE_PROXY_SERVER] = state
        self.__set_widget_enable_state(self.__proxy_server_port_widget,
                                       not state)
        self.__set_widget_enable_state(self.__proxy_server_address_widget,
                                       not state)

    def __use_default_proxy_credentials_changed(self, state):
        ''' Default url changed '''
        self._new_settings[Settings.USE_PROXY_SERVER] = state
        self.__set_widget_enable_state(self.__proxy_server_username_widget,
                                       not state)
        self.__set_widget_enable_state(self.__proxy_server_password_widget,
                                       not state)
        self.__set_widget_enable_state(self.__proxy_server_domain_widget,
                                       not state)

    def __bypass_proxy_local_changed(self, state):
        ''' Default url changed '''
        self._new_settings[Settings.BYPASS_PROXY_FOR_LOCAL_ADDRESSES] = state

    @staticmethod
    def _create_about_tab():
        ''' About '''
        about_html = "<p>Street Smart for QGIS</p>"
        about_html += "<p>Copyright &copy; Merkator 2020</p>"
        about_html += "<p>version v3.0.6.1.120.2</p>"
        about_html += "<p>git sha 2624fa958dd3bd1c6729e36df552406ad92ad02b</p>"  
        about_html += "<p>http://www.merkator.com</p>"
        e = QTextEdit()
        e.setHtml(about_html)
        e.setReadOnly(True)
        return e

    @staticmethod
    def _create_agreement_tab():
        ''' Agreement '''
        current_path = os.path.dirname(os.path.abspath(__file__))
        parent_directory = os.path.dirname(current_path)
        agreement_file = os.path.join(parent_directory, "agreement.txt")
        with open(agreement_file, "r") as f:
            gpl_license_html = f.readlines()

        gpl_license_html = "".join(gpl_license_html)
        e = QTextEdit()
        e.setHtml(gpl_license_html)
        e.setReadOnly(True)
        return e

    def _is_dirty(self):
        ''' Returns true if there were changes made in the UI '''
        for key in self._new_settings:
            if key in self._old_settings:  # Should always be the case
                if self._old_settings[key] != self._new_settings[key]:
                    return True
        return False

    def _accept_settings(self):
        ''' Accept the changes in the settings '''
        if self._is_dirty():
            try:
                btn_reply = QMessageBox.question(self, tr('Manage Settings'),
                                                tr("Are you sure?"),
                                                QMessageBox.Yes | QMessageBox.No,
                                                QMessageBox.No)
                if btn_reply == QMessageBox.Yes:
                    if logger:
                        logger.debug("Save settings")
                    self.__save_settings()
            except Exception as ex:
                if logger:
                    logger.exception("Error occurred saving settings")
                QMessageBox.information(self, tr('Manage Settings'),
                                        tr("Something went wrong.") + str(ex),
                                        QMessageBox.Ok)
                print(ex)
        else:
            QMessageBox.information(self, tr('Manage Settings'),
                                    tr("No changes need to be saved"),
                                    QMessageBox.Ok)
        super().accept()

    def _reject_settings(self):
        ''' Reject changes in the settings '''
        QMessageBox.information(self, tr('Manage Settings'),
                                tr("Settings will not be saved!"),
                                QMessageBox.Ok)
        super().reject()
