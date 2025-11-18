import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QTabWidget, QAction, QVBoxLayout, QWidget, QFileDialog, QFontDialog, QToolBar, QSpinBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

class NotepadPlusPlus(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Notepad++ Version 2')
        self.setGeometry(100, 100, 800, 600)

        # Create tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        # Add file operations actions
        self.create_file_actions()

        self.show()  

    def create_file_actions(self):
        new_file_action = QAction(QIcon('new.png'), 'New', self)
        new_file_action.triggered.connect(self.new_file)
        self.toolbar.addAction(new_file_action)

        open_file_action = QAction(QIcon('open.png'), 'Open', self)
        open_file_action.triggered.connect(self.open_file)
        self.toolbar.addAction(open_file_action)

        save_file_action = QAction(QIcon('save.png'), 'Save', self)
        save_file_action.triggered.connect(self.save_file)
        self.toolbar.addAction(save_file_action)

        font_action = QAction('Font', self)
        font_action.triggered.connect(self.select_font)
        self.toolbar.addAction(font_action)

        zoom_in_action = QAction('Zoom In', self)
        zoom_in_action.triggered.connect(self.zoom_in)
        self.toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction('Zoom Out', self)
        zoom_out_action.triggered.connect(self.zoom_out)
        self.toolbar.addAction(zoom_out_action)

    def new_file(self):
        text_edit = QTextEdit()
        self.tabs.addTab(text_edit, 'Untitled')

    def open_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open File', '', 'Text Files (*.txt);;Python Files (*.py);;All Files (*)', options=options)
        if file_name:
            with open(file_name, 'r') as f:
                text_edit = QTextEdit()
                text_edit.setText(f.read())
                self.tabs.addTab(text_edit, file_name)

    def save_file(self):
        current_tab = self.tabs.currentWidget()
        if current_tab:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, 'Save File', '', 'Text Files (*.txt);;Python Files (*.py);;All Files (*)', options=options)
            if file_name:
                with open(file_name, 'w') as f:
                    f.write(current_tab.toPlainText())

    def select_font(self):
        font, ok = QFontDialog.getFont()
        if ok:
            self.tabs.currentWidget().setFont(font)

    def zoom_in(self):
        current_tab = self.tabs.currentWidget()
        if current_tab:
            font_size = current_tab.fontPointSize() + 1
            current_tab.setFontPointSize(font_size)

    def zoom_out(self):
        current_tab = self.tabs.currentWidget()
        if current_tab:
            font_size = current_tab.fontPointSize() - 1
            current_tab.setFontPointSize(font_size)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    notepad = NotepadPlusPlus()
    sys.exit(app.exec_())