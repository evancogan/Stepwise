#imports
import sys
import PySide6
from PySide6 import QtCore, QtWidgets, QtGui

# Main widget class for the tip calculator GUI
class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Initialize the GUI components for the tip calculator
        self.bill_amount_input = QtWidgets.QLineEdit()
        self.tip_percentage_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.tip_percentage_slider.setRange(1, 100)
        self.tip_percentage_slider.setValue(25)
        self.tip_percentage_label = QtWidgets.QLabel("Tip Percentage: 25%")
        self.tip_percentage_slider.valueChanged.connect(
            lambda value: self.tip_percentage_label.setText(f"Tip Percentage: {value}%"))
        self.calculate_button = QtWidgets.QPushButton("Calculate Tip")
        self.result_label = QtWidgets.QLabel("Result will be shown here",
                                             alignment=QtCore.Qt.AlignCenter)

        self.layout = QtWidgets.QVBoxLayout(self)
        # Text box for the bill amount, and slider for the tip percentage
        self.layout.addWidget(QtWidgets.QLabel("Bill Amount:"))
        self.layout.addWidget(self.bill_amount_input)
        self.layout.addWidget(self.tip_percentage_label)
        self.layout.addWidget(self.tip_percentage_slider)
        self.layout.addWidget(self.calculate_button)
        self.layout.addWidget(self.result_label)

        self.calculate_button.clicked.connect(self.calculate_tip)

    @QtCore.Slot()
    def calculate_tip(self):
        try:
            bill_amount = float(self.bill_amount_input.text())
            tip_percentage = self.tip_percentage_slider.value()
            tip_amount = bill_amount * (tip_percentage / 100)
            total_amount = bill_amount + tip_amount
            self.result_label.setText(f"Tip amount: {tip_amount}\nTotal amount: {total_amount}")
        except ValueError:
            self.result_label.setText("Please enter valid numbers.")

# Application execution
if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())