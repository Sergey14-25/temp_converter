import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from ui_main import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('converter.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("TemperatureConverter")
        app.setApplicationVersion("1.0")

        app.setFont(QFont("Segoe UI", 10))

        window = MainWindow()
        window.show()

        logger.info("Приложение запущено успешно")

        sys.exit(app.exec_())

    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()