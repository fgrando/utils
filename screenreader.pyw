import os
import sys
import pyautogui
import pytesseract

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QTextEdit,
)
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPixmap, QPen, QImage
import time

"""
    This script captures a region of the screen, extracts the text from it using OCR, and displays a popup with the extracted text.
"""

if getattr(sys, "frozen", False):
    THIS_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(THIS_DIR, "tmp")
os.makedirs(TMP_DIR, exist_ok=True)


class ScreenshotAnnotator(QWidget):
    def __init__(self, filename, callback):
        super().__init__()
        self.callback = callback
        self.setWindowTitle("Annotate Screenshot")
        qimage = QImage()
        if not qimage.load(filename):
            raise ValueError(f"Failed to load image from file: {filename}")
        self.resize(qimage.width(), qimage.height())

        # Graphics view and scene
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setGeometry(0, 0, qimage.width(), qimage.height())

        # Display the screenshot
        pixmap = QPixmap.fromImage(qimage)
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)

        # Rectangle drawing setup
        self.start_point = None
        self.current_rect_item = None
        self.pen = QPen(Qt.red, 2)

        self.view.setMouseTracking(True)
        self.view.viewport().installEventFilter(self)

        self.showFullScreen()

    def eventFilter(self, source, event):
        if source == self.view.viewport():
            if event.type() == event.MouseButtonPress:
                self.start_point = self.view.mapToScene(event.pos())
                self.current_rect_item = QGraphicsRectItem()
                self.current_rect_item.setPen(self.pen)
                self.scene.addItem(self.current_rect_item)
            elif event.type() == event.MouseMove and self.start_point:
                end_point = self.view.mapToScene(event.pos())
                rect = QRectF(self.start_point, end_point).normalized()
                self.current_rect_item.setRect(rect)
            elif event.type() == event.MouseButtonRelease and self.start_point:
                end_point = self.view.mapToScene(event.pos())
                rect = QRectF(self.start_point, end_point).normalized()
                self.start_point = None
                self.extract_text_from_rect(rect)
        return super().eventFilter(source, event)

    def extract_text_from_rect(self, rect):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        temp_filename = os.path.join(TMP_DIR, f"temp_screenshot_{timestamp}.png")
        # Convert QRectF to region coordinates
        x, y, w, h = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())
        cropped_image = self.pixmap_item.pixmap().toImage().copy(x, y, w, h)
        cropped_image.save(temp_filename, "PNG")
        text = pytesseract.image_to_string(temp_filename)
        self.callback(text)
        self.close()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Text Extractor")
        self.setGeometry(0, 0, 300, 50)

        # Layout and buttons
        self.layout = QVBoxLayout()

        self.screenshot_button = QPushButton("Take Screenshot")
        self.screenshot_button.clicked.connect(self.take_screenshot)

        self.cleanup_button = QPushButton("Cleanup PNGs")
        self.cleanup_button.clicked.connect(self.cleanup_pngs)

        # Add widgets to layout
        self.layout.addWidget(self.screenshot_button)
        self.layout.addWidget(self.cleanup_button)
        self.setLayout(self.layout)

    def handle_text_extracted(self, text):
        self.show()
        text_popup = QWidget(self, Qt.Window)
        text_popup.setWindowTitle("Extracted Text")
        text_popup.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()
        text_area = QTextEdit()
        text_area.setPlainText(text)
        layout.addWidget(text_area)
        text_popup.setLayout(layout)
        text_popup.show()
        # text_popup.keyPressEvent = lambda event: text_popup.close() if event.key() == Qt.Key_Escape else None

    def take_screenshot(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        temp_filename = os.path.join(TMP_DIR, f"full_screenshot_{timestamp}.png")
        screenshot = pyautogui.screenshot(imageFilename=temp_filename)
        screenshot = screenshot.convert("RGB")
        self.annotator = ScreenshotAnnotator(temp_filename, self.handle_text_extracted)

    def cleanup_pngs(self):
        for filename in os.listdir(TMP_DIR):
            if filename.endswith(".png"):
                os.remove(os.path.join(TMP_DIR, filename))


if __name__ == "__main__":
    os.environ["TESSDATA_PREFIX"] = os.path.join(THIS_DIR, "Tesseract-OCR", "tessdata")
    pytesseract.pytesseract.tesseract_cmd = os.path.join(
        THIS_DIR, "Tesseract-OCR", "tesseract.exe"
    )
    if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
        raise FileNotFoundError(
            f"Tesseract executable not found at {pytesseract.pytesseract.tesseract_cmd}"
        )
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
