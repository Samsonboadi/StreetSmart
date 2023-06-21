""" Show Help for Street Smart plugin """
import os
import webbrowser
from qgis.core import (QgsProject,  # pylint: disable=import-error
                       QgsVectorLayer, QgsDataSourceUri)
from PyQt5.QtWidgets import (  # pylint: disable=no-name-in-module
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QMessageBox,
    QVBoxLayout, QTabWidget, QPushButton, QCheckBox, QTextEdit,
)
from PyQt5.QtWebKitWidgets import QWebView  # pylint: disable=import-error
from PyQt5.QtCore import (Qt, QUrl)

from ..logger import Logger
from ..settings import Settings
from ..street_smart import AbstractCommand

logger = Logger(__name__).get()


class ShowHelpCommand(AbstractCommand):
    '''
    Class shows the help for the plugin
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
        return ':/plugins/street_smart/resources/mActionHelpContents.svg'

    def text(self):
        '''
        Text for the command to show
        '''
        return (super()
                .tr(u'Show help\nVersion {}\ngit sha: {}')
                .format("v1.4.0", "2624fa958dd3bd1c6729e36df552406ad92ad02b"))



    def parent(self):
        '''
        Parent
        '''
        return self.iface.mainWindow()

    def callback(self):
        '''
        Code to execute when command is clicked
        '''
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(cur_dir)
        html_file = os.path.join(parent_dir, "help", "index.html")
        url_as_string = r"file:///" + html_file
        print(url_as_string)
        webbrowser.open_new(url_as_string)


class ShowHelpDialog(QDialog):  # pylint: disable=too-few-public-methods
    """ Shows a QDialog for the help file """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Help Viewer")
        # self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(500)
        self.view = QWebView()
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.view)
        self.setLayout(mainLayout)
