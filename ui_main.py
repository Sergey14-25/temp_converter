"""
Модуль главного окна приложения "Конвертер температур".
Реализует интерфейс, сигналы/слоты и логику UI.
"""
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QPushButton, QLabel, QDoubleSpinBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QSplitter, QGroupBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage
from PIL import Image
import database

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Главное окно приложения конвертера температур."""

    def __init__(self):
        """Инициализация главного окна."""
        super().__init__()
        self.setWindowTitle("Конвертер температур v1.0")
        self.resize(1050, 650)
        self.setMinimumSize(850, 500)

        # Инициализация БД
        self.db = database.DatabaseManager()
        self.db.init_db()

        # Путь к текущему изображению термометра
        self.current_image_path = ""

        # Таймер для задержки пересчёта (требование задания: QTimer)
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._recalculate_temperatures)

        # Центральная часть окна
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 1. Верстка интерфейса
        self._setup_ui()
        # 2. Привязка событий (сигналы/слоты)
        self._bind_signals()
        # 3. Загрузка начальных данных в таблицу
        self._refresh_table()

        logger.info("Главное окно инициализировано")

    def _setup_ui(self):
        """Верстка через менеджеры компоновки (без setGeometry/move)."""
        main_layout = QHBoxLayout()
        self.centralWidget().setLayout(main_layout)

        # === ЛЕВАЯ ПАНЕЛЬ: Ввод и результаты ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Группа ввода температуры
        input_group = QGroupBox("Ввод температуры")
        input_layout = QFormLayout()

        # QDoubleSpinBox — виджет для ввода дробных чисел (требование задания)
        self.spin_celsius = QDoubleSpinBox()
        self.spin_celsius.setRange(-273.15, 1000.0)
        self.spin_celsius.setDecimals(2)
        self.spin_celsius.setValue(25.0)
        self.spin_celsius.setSuffix(" °C")
        self.spin_celsius.setSingleStep(1.0)
        input_layout.addRow("Температура (°C):", self.spin_celsius)

        input_group.setLayout(input_layout)
        left_layout.addWidget(input_group)

        # Группа результатов (3 цветных блока)
        result_group = QGroupBox("Результаты конвертации")
        result_layout = QGridLayout()

        self.lbl_celsius = QLabel("25.00 °C")
        self.lbl_celsius.setStyleSheet(
            "background-color: #ffebee; color: #c62828; "
            "font-size: 24px; font-weight: bold; "
            "padding: 15px; border-radius: 8px;"
        )
        self.lbl_celsius.setAlignment(Qt.AlignCenter)

        self.lbl_fahrenheit = QLabel("77.00 °F")
        self.lbl_fahrenheit.setStyleSheet(
            "background-color: #e3f2fd; color: #1565c0; "
            "font-size: 24px; font-weight: bold; "
            "padding: 15px; border-radius: 8px;"
        )
        self.lbl_fahrenheit.setAlignment(Qt.AlignCenter)

        self.lbl_kelvin = QLabel("298.15 K")
        self.lbl_kelvin.setStyleSheet(
            "background-color: #e8f5e9; color: #2e7d32; "
            "font-size: 24px; font-weight: bold; "
            "padding: 15px; border-radius: 8px;"
        )
        self.lbl_kelvin.setAlignment(Qt.AlignCenter)

        result_layout.addWidget(self.lbl_celsius, 0, 0)
        result_layout.addWidget(self.lbl_fahrenheit, 0, 1)
        result_layout.addWidget(self.lbl_kelvin, 0, 2)

        result_group.setLayout(result_layout)
        left_layout.addWidget(result_group)

        # Отображение формулы
        self.lbl_formula = QLabel("F = C × 9/5 + 32  |  K = C + 273.15")
        self.lbl_formula.setStyleSheet(
            "font-size: 14px; font-style: italic; "
            "padding: 10px; background-color: #f5f5f5; border-radius: 5px;"
        )
        self.lbl_formula.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.lbl_formula)

        # Поле для заметок
        notes_group = QGroupBox("Заметки")
        notes_layout = QVBoxLayout()
        self.le_notes = QLineEdit()
        self.le_notes.setPlaceholderText("Введите заметку...")
        notes_layout.addWidget(self.le_notes)
        notes_group.setLayout(notes_layout)
        left_layout.addWidget(notes_group)

        # Кнопка сохранения
        self.btn_save = QPushButton("Сохранить в историю")
        self.btn_save.setStyleSheet(
            "background-color: #4caf50; color: white; "
            "font-size: 14px; padding: 10px; border-radius: 5px;"
        )
        left_layout.addWidget(self.btn_save)

        left_layout.addStretch()

        # === ПРАВАЯ ПАНЕЛЬ: Таблица и изображение ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Таблица истории конвертаций
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["°C", "°F", "K", "Формула", "Заметки"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.table)

        # Кнопки управления таблицей
        table_btn_layout = QHBoxLayout()
        self.btn_delete = QPushButton("Удалить выбранную запись")
        self.btn_export = QPushButton("Экспорт в CSV")
        self.btn_clear = QPushButton("Очистить историю")

        self.btn_delete.setStyleSheet(
            "background-color: #f44336; color: white; "
            "padding: 8px 16px; border-radius: 5px;"
        )
        self.btn_export.setStyleSheet(
            "background-color: #2196f3; color: white; "
            "padding: 8px 16px; border-radius: 5px;"
        )
        self.btn_clear.setStyleSheet(
            "background-color: #9e9e9e; color: white; "
            "padding: 8px 16px; border-radius: 5px;"
        )

        table_btn_layout.addWidget(self.btn_delete)
        table_btn_layout.addWidget(self.btn_export)
        table_btn_layout.addWidget(self.btn_clear)
        right_layout.addLayout(table_btn_layout)

        # Область для изображения термометра
        self.lbl_image = QLabel("Фото термометра")
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setMinimumHeight(200)
        self.lbl_image.setStyleSheet(
            "background-color: #fafafa; border: 2px dashed #bbb; border-radius: 8px;"
        )
        right_layout.addWidget(self.lbl_image)

        # Кнопка загрузки изображения
        self.btn_load_img = QPushButton("Загрузить фото термометра")
        self.btn_load_img.setStyleSheet(
            "background-color: #ff9800; color: white; "
            "padding: 10px; border-radius: 5px;"
        )
        right_layout.addWidget(self.btn_load_img)

        # Разделитель между левой и правой панелями
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 550])

        main_layout.addWidget(splitter)

    def _bind_signals(self):
        """Привязка сигналов к слотам через .connect() (требование задания)."""
        # При изменении температуры запускаем таймер (неблокирующая работа)
        self.spin_celsius.valueChanged.connect(self._on_temp_value_changed)

        # Кнопки
        self.btn_save.clicked.connect(self._on_save)
        self.btn_load_img.clicked.connect(self._on_load_image)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_clear.clicked.connect(self._on_clear_history)

        # Выбор строки в таблице
        self.table.itemSelectionChanged.connect(self._on_select_row)

        logger.info("Сигналы привязаны")

    def _on_temp_value_changed(self):
        """Обработчик изменения значения — запускает таймер на 300 мс."""
        self.update_timer.start(300)

    def _recalculate_temperatures(self):
        """Пересчёт температур по формулам F=C*9/5+32 и K=C+273.15."""
        try:
            celsius = self.spin_celsius.value()

            # Валидация: температура не может быть ниже абсолютного нуля
            if celsius < -273.15:
                logger.warning(f"Температура ниже абсолютного нуля: {celsius}")
                return

            # Формулы конвертации
            fahrenheit = celsius * 9 / 5 + 32
            kelvin = celsius + 273.15

            # Обновляем метки
            self.lbl_celsius.setText(f"{celsius:.2f} °C")
            self.lbl_fahrenheit.setText(f"{fahrenheit:.2f} °F")
            self.lbl_kelvin.setText(f"{kelvin:.2f} K")

            logger.info(f"Конвертация: {celsius}°C = {fahrenheit}°F = {kelvin}K")
        except Exception as e:
            logger.error(f"Ошибка конвертации: {e}")

    def _on_save(self):
        """Сохранение конвертации в историю (БД)."""
        logger.info("Начало сохранения записи")
        try:
            celsius = self.spin_celsius.value()
            fahrenheit = celsius * 9 / 5 + 32
            kelvin = celsius + 273.15

            data = {
                "temp_c": celsius,
                "temp_f": fahrenheit,
                "temp_k": kelvin,
                "formula": "F = C × 9/5 + 32",
                "notes": self.le_notes.text().strip(),
                "image_path": self.current_image_path
            }

            self.db.insert_record(data)
            self._refresh_table()
            self.le_notes.clear()

            QMessageBox.information(
                self, "Успех", "Конвертация сохранена в историю!"
            )
            logger.info(f"Запись сохранена: {celsius}°C")
        except ValueError as e:
            logger.error(f"Ошибка валидации: {e}")
            QMessageBox.critical(
                self, "Ошибка валидации", f"Некорректные данные:\n{e}"
            )
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось сохранить запись:\n{e}"
            )

    def _on_delete(self):
        """Удаление выбранной записи из БД."""
        try:
            selected = self.table.selectionModel().selectedRows()
            if not selected:
                QMessageBox.warning(
                    self, "Внимание", "Выберите запись для удаления."
                )
                return

            if QMessageBox.question(
                self, "Подтверждение", "Удалить выбранную запись?"
            ) == QMessageBox.Yes:
                row = selected[0].row()
                record_id = self.table.item(row, 0).data(Qt.UserRole)
                self.db.delete_record(record_id)
                self._refresh_table()
                logger.info(f"Запись {record_id} удалена")
                QMessageBox.information(self, "Успех", "Запись удалена!")
        except Exception as e:
            logger.error(f"Ошибка удаления: {e}")
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось удалить запись:\n{e}"
            )

    def _on_export(self):
        """Экспорт всех записей в CSV файл."""
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт в CSV", "", "CSV files (*.csv)"
            )
            if not path:
                return

            records = self.db.get_all()
            with open(path, 'w', encoding='utf-8') as f:
                # Записываем заголовок
                f.write("temp_c,temp_f,temp_k,formula,notes,image_path\n")
                # Записываем данные
                for rec in records:
                    f.write(
                        f"{rec['temp_c']},{rec['temp_f']},{rec['temp_k']},"
                        f"{rec['formula']},{rec['notes']},{rec['image_path']}\n"
                    )

            QMessageBox.information(
                self, "Успех", f"Данные экспортированы в {path}"
            )
            logger.info(f"Экспорт в {path} завершен ({len(records)} записей)")
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось экспортировать данные:\n{e}"
            )

    def _on_clear_history(self):
        """Очистка всей истории конвертаций."""
        try:
            if QMessageBox.question(
                self, "Подтверждение", "Вы уверены, что хотите удалить ВСЮ историю?"
            ) == QMessageBox.Yes:
                self.db.clear_all()
                self._refresh_table()
                logger.info("История очищена пользователем")
                QMessageBox.information(self, "Успех", "История полностью очищена!")
        except Exception as e:
            logger.error(f"Ошибка очистки истории: {e}")
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось очистить историю:\n{e}"
            )

    def _on_load_image(self):
        """Загрузка изображения термометра через Pillow."""
        try:
            path, _ = QFileDialog.getOpenFileName(
                self, "Выберите изображение", "",
                "Images (*.png *.jpg *.jpeg)"
            )
            if not path:
                return

            # Интеграция Pillow: загрузка и масштабирование
            img = Image.open(path).convert("RGBA")
            img.thumbnail((200, 200), Image.LANCZOS)

            # Конвертация Pillow → Qt (QImage → QPixmap)
            qt_img = QImage(
                img.tobytes(), img.width, img.height,
                QImage.Format_RGBA8888
            )
            pixmap = QPixmap.fromImage(qt_img)

            self.lbl_image.setPixmap(pixmap)
            self.current_image_path = path
            self.lbl_image.setStyleSheet(
                "background-color: #fff; border: 2px solid #999; border-radius: 8px;"
            )
            logger.info(f"Изображение загружено: {path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки изображения: {e}")
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось загрузить изображение:\n{e}"
            )

    def _on_select_row(self):
        """Заполнение полей при клике на строку таблицы."""
        try:
            selected = self.table.selectionModel().selectedRows()
            if not selected:
                return

            row = selected[0].row()
            celsius = float(self.table.item(row, 0).text())
            self.spin_celsius.setValue(celsius)
            self.le_notes.setText(self.table.item(row, 4).text())
        except ValueError:
            pass
        except Exception as e:
            logger.error(f"Ошибка выбора строки: {e}")

    def _refresh_table(self):
        """Обновление таблицы из БД."""
        try:
            self.table.setRowCount(0)
            records = self.db.get_all()

            for i, rec in enumerate(records):
                self.table.insertRow(i)
                self.table.setItem(i, 0, QTableWidgetItem(f"{rec['temp_c']:.2f}"))
                self.table.setItem(i, 1, QTableWidgetItem(f"{rec['temp_f']:.2f}"))
                self.table.setItem(i, 2, QTableWidgetItem(f"{rec['temp_k']:.2f}"))
                self.table.setItem(i, 3, QTableWidgetItem(rec['formula']))
                self.table.setItem(i, 4, QTableWidgetItem(rec['notes'] or ""))
                # Сохраняем ID в невидимой роли для дальнейших операций
                self.table.item(i, 0).setData(Qt.UserRole, rec['id'])

            logger.info(f"Таблица обновлена: {len(records)} записей")
        except Exception as e:
            logger.error(f"Ошибка обновления таблицы: {e}")

    def closeEvent(self, event):
        """Переопределение закрытия окна (требование задания)."""
        logger.info("Запрос на закрытие приложения")
        reply = QMessageBox.question(
            self, "Выход",
            "Вы уверены, что хотите закрыть приложение?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.db.close()  # Гарантированное закрытие БД
                logger.info("Приложение закрыто корректно")
                event.accept()
            except Exception as e:
                logger.error(f"Ошибка при закрытии БД: {e}")
                event.accept()
        else:
            logger.info("Закрытие отменено пользователем")
            event.ignore()