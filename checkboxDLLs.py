from PyQt5.QtWidgets import QInputDialog, QVBoxLayout, QWidget, QCheckBox, QDialog, QLabel, QDialogButtonBox

files = ['libssl-1_1-x64.dll', 'libcrypto-1_1-x64.dll']

# Create a custom dialog with checkboxes
class CheckboxDialog(QDialog):
    def __init__(self, options):
        super().__init__()
        self.options = options
        self.selected_files = []
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.setWindowTitle("Required DLLs")
        
        label_info = QLabel("Run Qgis as an Administrator and select files:")
        label = QLabel("Select files:")
        layout.addWidget(label_info)
        layout.addWidget(label)
        
        for file in self.options:
            checkbox = QCheckBox(file)
            checkbox.setChecked(False)  # Set the checkbox as checked by default
            checkbox.stateChanged.connect(self.handleCheckboxChange)
            layout.addWidget(checkbox)

        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def handleCheckboxChange(self, state):
        checkbox = self.sender()
        file = checkbox.text()
        if state == 2:  # 2 corresponds to a checked state
            self.selected_files.append(file)
        else:
            self.selected_files.remove(file)


