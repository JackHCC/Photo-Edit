import sys
import ntpath

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *

from functools import partial

from img_modifier import img_helper
from img_modifier import color_filter

from PIL import ImageQt

from logging.config import fileConfig
import logging

logger = logging.getLogger()

# original img, can't be modified
_img_original = None
_img_preview = None

# constants
THUMB_BORDER_COLOR_ACTIVE = "#3893F4"
THUMB_BORDER_COLOR = "#ccc"
BTN_MIN_WIDTH = 120
ROTATION_BTN_SIZE = (70, 30)
THUMB_SIZE = 120

SLIDER_MIN_VAL = -100
SLIDER_MAX_VAL = 100
SLIDER_DEF_VAL = 0


class Operations:
    def __init__(self):
        self.color_filter = None

        self.flip_left = False
        self.flip_top = False
        self.rotation_angle = 0

        self.size = None

        self.brightness = 0
        self.sharpness = 0
        self.contrast = 0

    def reset(self):
        self.color_filter = None

        self.brightness = 0
        self.sharpness = 0
        self.contrast = 0

        self.size = None

        self.flip_left = False
        self.flip_top = False
        self.rotation_angle = 0

    def has_changes(self):
        return self.color_filter or self.flip_left\
                or self.flip_top or self.rotation_angle\
                or self.contrast or self.brightness\
                or self.sharpness or self.size

    def __str__(self):
        return f"size: {self.size}, filter: {self.color_filter}, " \
               f"b: {self.brightness} c: {self.contrast} s: {self.sharpness}, " \
               f"flip-left: {self.flip_left} flip-top: {self.flip_top} rotation: {self.rotation_angle}"


operations = Operations()


def _get_ratio_height(width, height, r_width):
    return int(r_width/width*height)


def _get_ratio_width(width, height, r_height):
    return int(r_height/height*width)


def _get_converted_point(user_p1, user_p2, p1, p2, x):

    r = (x - user_p1) / (user_p2 - user_p1)
    return p1 + r * (p2 - p1)


def _get_img_with_all_operations():
    logger.debug(operations)

    b = operations.brightness
    c = operations.contrast
    s = operations.sharpness

    img = _img_preview
    if b != 0:
        img = img_helper.brightness(img, b)

    if c != 0:
        img = img_helper.contrast(img, c)

    if s != 0:
        img = img_helper.sharpness(img, s)

    if operations.rotation_angle:
        img = img_helper.rotate(img, operations.rotation_angle)

    if operations.flip_left:
        img = img_helper.flip_left(img)

    if operations.flip_top:
        img = img_helper.flip_top(img)

    if operations.size:
        img = img_helper.resize(img, *operations.size)

    return img


class ActionTabs(QTabWidget):
    """Action tabs widget"""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.filters_tab = FiltersTab(self)
        self.adjustment_tab = AdjustingTab(self)
        self.modification_tab = ModificationTab(self)
        self.rotation_tab = RotationTab(self)

        self.addTab(self.filters_tab, "滤镜")
        self.addTab(self.adjustment_tab, "调整")
        self.addTab(self.modification_tab, "尺寸")
        self.addTab(self.rotation_tab, "旋转")

        self.setMaximumHeight(190)


class RotationTab(QWidget):
    """Rotation tab widget"""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        rotate_left_btn = QPushButton("↺ 90°")
        rotate_left_btn.setMinimumSize(*ROTATION_BTN_SIZE)
        rotate_left_btn.clicked.connect(self.on_rotate_left)

        rotate_right_btn = QPushButton("↻ 90°")
        rotate_right_btn.setMinimumSize(*ROTATION_BTN_SIZE)
        rotate_right_btn.clicked.connect(self.on_rotate_right)

        flip_left_btn = QPushButton("⇆")
        flip_left_btn.setMinimumSize(*ROTATION_BTN_SIZE)
        flip_left_btn.clicked.connect(self.on_flip_left)

        flip_top_btn = QPushButton("↑↓")
        flip_top_btn.setMinimumSize(*ROTATION_BTN_SIZE)
        flip_top_btn.clicked.connect(self.on_flip_top)

        rotate_lbl = QLabel("旋转")
        rotate_lbl.setAlignment(Qt.AlignCenter)
        rotate_lbl.setFixedWidth(140)

        flip_lbl = QLabel("翻转")
        flip_lbl.setAlignment(Qt.AlignCenter)
        flip_lbl.setFixedWidth(140)

        lbl_layout = QHBoxLayout()
        lbl_layout.setAlignment(Qt.AlignCenter)
        lbl_layout.addWidget(rotate_lbl)
        lbl_layout.addWidget(flip_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.addWidget(rotate_left_btn)
        btn_layout.addWidget(rotate_right_btn)
        btn_layout.addWidget(QVLine())
        btn_layout.addWidget(flip_left_btn)
        btn_layout.addWidget(flip_top_btn)

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(lbl_layout)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def on_rotate_left(self):
        logger.debug("rotate left")

        operations.rotation_angle = 0 if operations.rotation_angle == 270 else operations.rotation_angle + 90
        self.parent.parent.place_preview_img()

    def on_rotate_right(self):
        logger.debug("rotate left")

        operations.rotation_angle = 0 if operations.rotation_angle == -270 else operations.rotation_angle - 90
        self.parent.parent.place_preview_img()

    def on_flip_left(self):
        logger.debug("flip left-right")

        operations.flip_left = not operations.flip_left
        self.parent.parent.place_preview_img()

    def on_flip_top(self):
        logger.debug("flip top-bottom")

        operations.flip_top = not operations.flip_top
        self.parent.parent.place_preview_img()


class ModificationTab(QWidget):
    """Modification tab widget"""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.width_lbl = QLabel('宽度:', self)
        self.width_lbl.setFixedWidth(100)

        self.height_lbl = QLabel('高度:', self)
        self.height_lbl.setFixedWidth(100)

        self.width_box = QLineEdit(self)
        self.width_box.textEdited.connect(self.on_width_change)
        self.width_box.setMaximumWidth(100)

        self.height_box = QLineEdit(self)
        self.height_box.textEdited.connect(self.on_height_change)
        self.height_box.setMaximumWidth(100)

        self.unit_lbl = QLabel("px")
        self.unit_lbl.setMaximumWidth(50)

        self.ratio_check = QCheckBox('纵横比', self)
        self.ratio_check.stateChanged.connect(self.on_ratio_change)

        self.apply_btn = QPushButton("应用")
        self.apply_btn.setFixedWidth(90)
        self.apply_btn.clicked.connect(self.on_apply)

        width_layout = QHBoxLayout()
        width_layout.addWidget(self.width_box)
        width_layout.addWidget(self.height_box)
        width_layout.addWidget(self.unit_lbl)

        apply_layout = QHBoxLayout()
        apply_layout.addWidget(self.apply_btn)
        apply_layout.setAlignment(Qt.AlignRight)

        lbl_layout = QHBoxLayout()
        lbl_layout.setAlignment(Qt.AlignLeft)
        lbl_layout.addWidget(self.width_lbl)
        lbl_layout.addWidget(self.height_lbl)

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        main_layout.addLayout(lbl_layout)
        main_layout.addLayout(width_layout)
        main_layout.addWidget(self.ratio_check)
        main_layout.addLayout(apply_layout)

        self.setLayout(main_layout)

    def set_boxes(self):
        self.width_box.setText(str(_img_original.width))
        self.height_box.setText(str(_img_original.height))

    def on_width_change(self, e):
        logger.debug(f"type width {self.width_box.text()}")

        if self.ratio_check.isChecked():
            r_height = _get_ratio_height(_img_original.width, _img_original.height, int(self.width_box.text()))
            self.height_box.setText(str(r_height))

    def on_height_change(self, e):
        logger.debug(f"type height {self.height_box.text()}")

        if self.ratio_check.isChecked():
            r_width = _get_ratio_width(_img_original.width, _img_original.height, int(self.height_box.text()))
            self.width_box.setText(str(r_width))

    def on_ratio_change(self, e):
        logger.debug("ratio change")

    def on_apply(self, e):
        logger.debug("apply")

        operations.size = int(self.width_box.text()), int(self.height_box.text())

        self.parent.parent.update_img_size_lbl()
        self.parent.parent.place_preview_img()


class AdjustingTab(QWidget):
    """Adjusting tab widget"""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        contrast_lbl = QLabel("对比度")
        contrast_lbl.setAlignment(Qt.AlignCenter)

        brightness_lbl = QLabel("亮度")
        brightness_lbl.setAlignment(Qt.AlignCenter)

        sharpness_lbl = QLabel("锐化")
        sharpness_lbl.setAlignment(Qt.AlignCenter)

        self.contrast_slider = QSlider(Qt.Horizontal, self)
        self.contrast_slider.setMinimum(SLIDER_MIN_VAL)
        self.contrast_slider.setMaximum(SLIDER_MAX_VAL)
        self.contrast_slider.sliderReleased.connect(self.on_contrast_slider_released)
        self.contrast_slider.setToolTip(str(SLIDER_MAX_VAL))

        self.brightness_slider = QSlider(Qt.Horizontal, self)
        self.brightness_slider.setMinimum(SLIDER_MIN_VAL)
        self.brightness_slider.setMaximum(SLIDER_MAX_VAL)
        self.brightness_slider.sliderReleased.connect(self.on_brightness_slider_released)
        self.brightness_slider.setToolTip(str(SLIDER_MAX_VAL))

        self.sharpness_slider = QSlider(Qt.Horizontal, self)
        self.sharpness_slider.setMinimum(SLIDER_MIN_VAL)
        self.sharpness_slider.setMaximum(SLIDER_MAX_VAL)
        self.sharpness_slider.sliderReleased.connect(self.on_sharpness_slider_released)
        self.sharpness_slider.setToolTip(str(SLIDER_MAX_VAL))

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        main_layout.addWidget(contrast_lbl)
        main_layout.addWidget(self.contrast_slider)

        main_layout.addWidget(brightness_lbl)
        main_layout.addWidget(self.brightness_slider)

        main_layout.addWidget(sharpness_lbl)
        main_layout.addWidget(self.sharpness_slider)

        self.reset_sliders()
        self.setLayout(main_layout)

    def reset_sliders(self):
        self.brightness_slider.setValue(SLIDER_DEF_VAL)
        self.sharpness_slider.setValue(SLIDER_DEF_VAL)
        self.contrast_slider.setValue(SLIDER_DEF_VAL)

    def on_brightness_slider_released(self):
        logger.debug(f"brightness selected value: {self.brightness_slider.value()}")

        self.brightness_slider.setToolTip(str(self.brightness_slider.value()))

        factor = _get_converted_point(SLIDER_MIN_VAL, SLIDER_MAX_VAL, img_helper.BRIGHTNESS_FACTOR_MIN,
                                      img_helper.BRIGHTNESS_FACTOR_MAX, self.brightness_slider.value())
        logger.debug(f"brightness factor: {factor}")

        operations.brightness = factor

        self.parent.parent.place_preview_img()

    def on_sharpness_slider_released(self):
        logger.debug(self.sharpness_slider.value())

        self.sharpness_slider.setToolTip(str(self.sharpness_slider.value()))

        factor = _get_converted_point(SLIDER_MIN_VAL, SLIDER_MAX_VAL, img_helper.SHARPNESS_FACTOR_MIN,
                                      img_helper.SHARPNESS_FACTOR_MAX, self.sharpness_slider.value())
        logger.debug(f"sharpness factor: {factor}")

        operations.sharpness = factor

        self.parent.parent.place_preview_img()

    def on_contrast_slider_released(self):
        logger.debug(self.contrast_slider.value())

        self.contrast_slider.setToolTip(str(self.contrast_slider.value()))

        factor = _get_converted_point(SLIDER_MIN_VAL, SLIDER_MAX_VAL, img_helper.CONTRAST_FACTOR_MIN,
                                      img_helper.CONTRAST_FACTOR_MAX, self.contrast_slider.value())
        logger.debug(f"contrast factor: {factor}")

        operations.contrast = factor

        self.parent.parent.place_preview_img()


class FiltersTab(QWidget):
    """Color filters widget"""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.main_layout = QHBoxLayout()
        self.main_layout.setAlignment(Qt.AlignCenter)

        self.add_filter_thumb("none")
        for key, val in color_filter.ColorFilters.filters.items():
            self.add_filter_thumb(key, val)

        self.setLayout(self.main_layout)

    def add_filter_thumb(self, name, title=""):
        logger.debug(f"create lbl thumb for: {name}")

        thumb_lbl = QLabel()
        thumb_lbl.name = name
        thumb_lbl.setStyleSheet("border:2px solid #ccc;")

        if name != "none":
            thumb_lbl.setToolTip(f"Apply <b>{title}</b> filter")
        else:
            thumb_lbl.setToolTip('No filter')

        thumb_lbl.setCursor(Qt.PointingHandCursor)
        thumb_lbl.setFixedSize(THUMB_SIZE, THUMB_SIZE)
        thumb_lbl.mousePressEvent = partial(self.on_filter_select, name)

        self.main_layout.addWidget(thumb_lbl)

    def on_filter_select(self, filter_name, e):
        logger.debug(f"apply color filter: {filter_name}")

        global _img_preview
        if filter_name != "none":
            _img_preview = img_helper.color_filter(_img_original, filter_name)
        else:
            _img_preview = _img_original.copy()

        operations.color_filter = filter_name
        self.toggle_thumbs()

        self.parent.parent.place_preview_img()

    def toggle_thumbs(self):
        for thumb in self.findChildren(QLabel):
            color = THUMB_BORDER_COLOR_ACTIVE if thumb.name == operations.color_filter else THUMB_BORDER_COLOR
            thumb.setStyleSheet(f"border:2px solid {color};")


class MainLayout(QVBoxLayout):
    """Main layout"""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.img_lbl = QLabel("点击 <b>'上传'</b> 开始编辑<br>"
                              "<div style='margin: 30px 0'><img src='logo.jpg' /></div>"
                              "<b>made with hcc</b> <span style='color:red'>&#10084;</span>")
        self.img_lbl.setAlignment(Qt.AlignCenter)

        self.file_name = None

        self.img_size_lbl = None
        self.img_size_lbl = QLabel()
        self.img_size_lbl.setAlignment(Qt.AlignCenter)

        upload_btn = QPushButton("上传")
        upload_btn.setMinimumWidth(BTN_MIN_WIDTH)
        upload_btn.clicked.connect(self.on_upload)
        upload_btn.setStyleSheet("font-weight:bold;")

        self.reset_btn = QPushButton("重置")
        self.reset_btn.setMinimumWidth(BTN_MIN_WIDTH)
        self.reset_btn.clicked.connect(self.on_reset)
        self.reset_btn.setEnabled(False)
        self.reset_btn.setStyleSheet("font-weight:bold;")

        self.save_btn = QPushButton("保存")
        self.save_btn.setMinimumWidth(BTN_MIN_WIDTH)
        self.save_btn.clicked.connect(self.on_save)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("font-weight:bold;")

        self.addWidget(self.img_lbl)
        self.addWidget(self.img_size_lbl)
        self.addStretch()

        self.action_tabs = ActionTabs(self)
        self.addWidget(self.action_tabs)
        self.action_tabs.setVisible(False)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.addWidget(upload_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.save_btn)

        self.addLayout(btn_layout)

    def place_preview_img(self):
        img = _get_img_with_all_operations()

        preview_pix = ImageQt.toqpixmap(img)
        self.img_lbl.setPixmap(preview_pix)

    def on_save(self):
        logger.debug("open save dialog")
        new_img_path, _ = QFileDialog.getSaveFileName(self.parent, "QFileDialog.getSaveFileName()",
                                                      f"ez_pz_{self.file_name}",
                                                      "Images (*.png *.jpg)")

        if new_img_path:
            logger.debug(f"save output image to {new_img_path}")

            img = _get_img_with_all_operations()
            img.save(new_img_path)

    def on_upload(self):
        logger.debug("upload")
        img_path, _ = QFileDialog.getOpenFileName(self.parent, "Open image",
                                                  "/Users",
                                                  "Images (*.png *jpg)")

        if img_path:
            logger.debug(f"open file {img_path}")

            self.file_name = ntpath.basename(img_path)

            pix = QPixmap(img_path)
            self.img_lbl.setPixmap(pix)
            self.img_lbl.setScaledContents(True)
            self.action_tabs.setVisible(True)
            self.action_tabs.adjustment_tab.reset_sliders()

            global _img_original
            _img_original = ImageQt.fromqpixmap(pix)

            self.update_img_size_lbl()

            if _img_original.width < _img_original.height:
                w = THUMB_SIZE
                h = _get_ratio_height(_img_original.width, _img_original.height, w)
            else:
                h = THUMB_SIZE
                w = _get_ratio_width(_img_original.width, _img_original.height, h)

            img_filter_thumb = img_helper.resize(_img_original, w, h)

            global _img_preview
            _img_preview = _img_original.copy()

            for thumb in self.action_tabs.filters_tab.findChildren(QLabel):
                if thumb.name != "none":
                    img_filter_preview = img_helper.color_filter(img_filter_thumb, thumb.name)
                else:
                    img_filter_preview = img_filter_thumb

                preview_pix = ImageQt.toqpixmap(img_filter_preview)
                thumb.setPixmap(preview_pix)

            self.reset_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.action_tabs.modification_tab.set_boxes()

    def update_img_size_lbl(self):
        logger.debug("update img size lbl")

        self.img_size_lbl.setText(f"<span style='font-size:11px'>"
                                  f"图片大小 {operations.size[0] if operations.size else _img_original.width} × "
                                  f"{operations.size[1] if operations.size else _img_original.height}"
                                  f"</span>")

    def on_reset(self):
        logger.debug("reset all")

        global _img_preview
        _img_preview = _img_original.copy()

        operations.reset()

        self.action_tabs.filters_tab.toggle_thumbs()
        self.place_preview_img()
        self.action_tabs.adjustment_tab.reset_sliders()
        self.action_tabs.modification_tab.set_boxes()
        self.update_img_size_lbl()


class EasyPzUI(QWidget):
    """Main widget"""

    def __init__(self):
        super().__init__()

        self.main_layout = MainLayout(self)
        self.setLayout(self.main_layout)

        self.setMinimumSize(600, 500)
        self.setMaximumSize(900, 900)
        self.setGeometry(600, 600, 600, 600)
        self.setWindowTitle('简易photoEdit')
        self.center()
        self.show()

    def center(self):
        """align window center"""

        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event):
        logger.debug("close")

        if operations.has_changes():
            reply = QMessageBox.question(self, "",
                                         "您还没有保存<br>确定退出?", QMessageBox.Yes |
                                         QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()

    def resizeEvent(self, e):
        pass


class QVLine(QFrame):
    """Vertical line"""

    def __init__(self):
        super(QVLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)


if __name__ == '__main__':
    fileConfig('logging_config.ini')

    app = QApplication(sys.argv)
    win = EasyPzUI()
    sys.exit(app.exec_())

