#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import sys
from PySide import QtCore, QtGui


class KeyboardEnter(QtCore.QObject):
        sig = QtCore.Signal(unicode)


class KeyboardEsc(QtCore.QObject):
        sig = QtCore.Signal()


class ShiftPress(QtCore.QObject):
    sig = QtCore.Signal(unicode)


class BaseKeyButton(QtGui.QPushButton):
    def __init__(self, key, value, _input, width, *args, **kwargs):
        super(BaseKeyButton, self).__init__(*args, **kwargs)
        self.key = key
        self.value = value
        self.input = _input
        self.width = width
        self.init_ui()
        self.init_style()
        self.init_action()

    def init_ui(self):
        self.setText(self.key)
        self.setMinimumHeight(self.width)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def init_style(self):
        self.setStyleSheet('QPushButton {'
            'font-size: 15pt;'
            'font-weight: bold;'
            'background: #fbfaf9;'
            'color: #444444;}')

    def init_action(self):
        self.clicked.connect(self.on_click)

    def on_click(self):
        pass


class CharKeyButton(BaseKeyButton):

    def init_action(self):
        super(CharKeyButton, self).init_action()
        self.parent().main.signal_shift.sig.connect(self.on_press_shift)

    def on_click(self):
        text = self.input.text()
        position = self.input.cursorPosition()

        self.input.setText(u'%s%s%s' % (text[:position], self.value,
                                        text[position:]))
        self.input.setCursorPosition(position + 1)

    def on_press_shift(self, kind):
        if kind == 'on':
            self.key = self.key.upper()
            self.value = self.value.upper()
        elif kind == 'off':
            self.key = self.key.lower()
            self.value = self.value.lower()
        self.setText(self.key)


class NumKeyButton(BaseKeyButton):

    def on_click(self):
        text = self.input.text()
        position = self.input.cursorPosition()

        self.input.setText(u'%s%s%s' % (text[:position], self.value,
                                        text[position:]))
        self.input.setCursorPosition(position + 1)


class SignKeyButton(BaseKeyButton):

    def on_click(self):
        text = self.input.text()
        position = self.input.cursorPosition()

        self.input.setText(u'%s%s%s' % (text[:position], self.value,
                                        text[position:]))
        self.input.setCursorPosition(position + 1)


class NavKeyButton(BaseKeyButton):

    def on_click(self):
        position = self.input.cursorPosition()
        if self.value == 'left':
            position -= 1
        else:
            position += 1
        self.input.setCursorPosition(position)

old_text = ''
is_lower = True


class SystemKeyButton(BaseKeyButton):

    def __init__(self, *args, **kwargs):
        super(SystemKeyButton, self).__init__(*args, **kwargs)

    def on_click(self):
        if hasattr(self, 'on_%s' % self.value):
            getattr(self, 'on_%s' % self.value, None)()

    def on_backspace(self):
        self.input.backspace()

    def on_escape(self):
        self.parent().main.hide()
        self.input.setCursorPosition(0)
        self.parent().main.signal_esc.sig.emit()

    def on_enter(self):
        global old_text
        self.parent().main.hide()
        text = self.input.text()
        if old_text != text:
            self.parent().main.signal_enter.sig.emit(self.input.text())
        old_text = text

    def on_shift(self):
        global is_lower
        is_lower = not is_lower
        self.parent().main.signal_shift.sig.emit(
            'off' if is_lower else 'on')

    def on_lang(self):
        if isinstance(self.parent(), KeyboardRus):
            self.parent().manager.change_widget('eng')
        elif isinstance(self.parent(), KeyboardEng):
            self.parent().manager.change_widget('rus')


class Manager(QtGui.QStackedWidget):

    def __init__(self, *args, **kwargs):
        super(Manager, self).__init__(*args, **kwargs)
        self.screen = dict()
        self.init_ui()
        self.init_style()
        self.parent().manager = self

    def init_ui(self):
        self.screen.update(
            rus=KeyboardRus(main=self.parent(), manager=self),
            eng=KeyboardEng(main=self.parent(), manager=self),
        )
        for key, widget in self.screen.iteritems():
            self.addWidget(widget)
        self.change_widget('rus')

    def change_widget(self, key):
        self.setCurrentWidget(self.screen[key])

    def init_style(self):
        pass


class BaseKeyboard(QtGui.QWidget):
    def __init__(self, main, manager, *args, **kwargs):
        super(BaseKeyboard, self).__init__(*args, **kwargs)
        self.main = main
        self.manager = manager
        self.init_ui()

    def init_ui(self):
        self._layout = QtGui.QVBoxLayout()
        self._layout.setSpacing(0)
        self.setLayout(self._layout)

        button_cls = dict(
            char=CharKeyButton,
            sign=SignKeyButton,
            num=NumKeyButton,
            system=SystemKeyButton,
            nav=NavKeyButton,
            dummy=BaseKeyButton
        )
        for row, data in enumerate(self.keys):
            layout = QtGui.QGridLayout()
            layout.setHorizontalSpacing(0)
            col = 0
            for el in data:
                if not el:
                    continue
                widget = button_cls[el.get('type')](
                    key=el.get('key'), value=el.get('value'),
                    _input=self.main.input, size=el.get('size', 1),
                    width=self.main.el_width, parent=self)
                size = int(el.get('size', 1) * 2)
                layout.addWidget(widget, 0, col, 1, size)
                col += size
            self._layout.addLayout(layout)


class KeyboardEng(BaseKeyboard):
    keys = [
        [
            dict(key='Esc', value='escape', type='system'),
            dict(key='`', value='`', type='sign'),
            dict(key='1', value='1', type='num'),
            dict(key='2', value='2', type='num'),
            dict(key='3', value='3', type='num'),
            dict(key='4', value='4', type='num'),
            dict(key='5', value='5', type='num'),
            dict(key='6', value='6', type='num'),
            dict(key='7', value='7', type='num'),
            dict(key='8', value='8', type='num'),
            dict(key='9', value='9', type='num'),
            dict(key='0', value='0', type='num'),
            dict(key='-', value='-', type='sign'),
            dict(key='=', value='=', type='sign'),
            dict(key='Bksp', value='backspace', type='system'),
        ],
        [
            dict(key=None, value=None, type='dummy', size=1.5),
            dict(key='q', value='q', type='char'),
            dict(key='w', value='w', type='char'),
            dict(key='e', value='e', type='char'),
            dict(key='r', value='r', type='char'),
            dict(key='t', value='t', type='char'),
            dict(key='y', value='y', type='char'),
            dict(key='u', value='u', type='char'),
            dict(key='i', value='i', type='char'),
            dict(key='o', value='o', type='char'),
            dict(key='p', value='p', type='char'),
            dict(key=';', value=';', type='sign'),
            dict(key='#', value='#', type='sign'),
            dict(key='\\', value='\\', type='sign', size=1.5),
        ],
        [
            dict(key=None, value=None, type='dummy', size=2),
            dict(key='a', value='a', type='char'),
            dict(key='s', value='s', type='char'),
            dict(key='d', value='d', type='char'),
            dict(key='f', value='f', type='char'),
            dict(key='g', value='g', type='char'),
            dict(key='h', value='h', type='char'),
            dict(key='j', value='j', type='char'),
            dict(key='k', value='k', type='char'),
            dict(key='l', value='l', type='char'),
            dict(key=';', value='#', type='sign'),
            dict(key='}', value='}', type='sign'),
            dict(key='Enter', value='enter', type='system', size=2),
        ],
        [
            dict(key='Shift', value='shift', type='system', size=2.5),
            dict(key='z', value='z', type='char'),
            dict(key='x', value='x', type='char'),
            dict(key='c', value='c', type='char'),
            dict(key='v', value='v', type='char'),
            dict(key='b', value='b', type='char'),
            dict(key='n', value='n', type='char'),
            dict(key='m', value='m', type='char'),
            dict(key=',', value=',', type='sign'),
            dict(key='.', value='.', type='sign'),
            dict(key='/', value='/', type='sign'),
            dict(key=None, value=None, type='dummy', size=2.5),
        ],
        [
            dict(key=u'Рус', value='lang', type='system', size=3.5),
            dict(key=None, value=' ', type='sign', size=6.5),
            dict(key='@', value='@', type='sign'),
            dict(key='<', value='left', type='nav', size=2),
            dict(key='>', value='right', type='nav', size=2),
        ]
    ]


class KeyboardRus(BaseKeyboard):
    keys = [
        [
            dict(key='Esc', value='escape', type='system'),
            dict(key='`', value='`', type='sign'),
            dict(key='1', value='1', type='num'),
            dict(key='2', value='2', type='num'),
            dict(key='3', value='3', type='num'),
            dict(key='4', value='4', type='num'),
            dict(key='5', value='5', type='num'),
            dict(key='6', value='6', type='num'),
            dict(key='7', value='7', type='num'),
            dict(key='8', value='8', type='num'),
            dict(key='9', value='9', type='num'),
            dict(key='0', value='0', type='num'),
            dict(key='-', value='-', type='sign'),
            dict(key='=', value='=', type='sign'),
            dict(key='Bksp', value='backspace', type='system'),
        ],
        [
            dict(key=None, value=None, type='dummy', size=1.5),
            dict(key=u'й', value=u'й', type='char'),
            dict(key=u'ц', value=u'ц', type='char'),
            dict(key=u'у', value=u'у', type='char'),
            dict(key=u'к', value=u'к', type='char'),
            dict(key=u'е', value=u'е', type='char'),
            dict(key=u'н', value=u'н', type='char'),
            dict(key=u'г', value=u'г', type='char'),
            dict(key=u'ш', value=u'ш', type='char'),
            dict(key=u'щ', value=u'щ', type='char'),
            dict(key=u'з', value=u'з', type='char'),
            dict(key=u'х', value=u'х', type='char'),
            dict(key=u'ъ', value=u'ъ', type='char'),
            dict(key='\\', value='\\', type='sign', size=1.5),
        ],
        [
            dict(key=None, value=None, type='dummy', size=2),
            dict(key=u'ф', value=u'ф', type='char'),
            dict(key=u'ы', value=u'ы', type='char'),
            dict(key=u'в', value=u'в', type='char'),
            dict(key=u'а', value=u'а', type='char'),
            dict(key=u'п', value=u'п', type='char'),
            dict(key=u'р', value=u'р', type='char'),
            dict(key=u'о', value=u'о', type='char'),
            dict(key=u'л', value=u'л', type='char'),
            dict(key=u'д', value=u'д', type='char'),
            dict(key=u'ж', value=u'ж', type='char'),
            dict(key=u'э', value=u'э', type='char'),
            dict(key='Enter', value='enter', type='system', size=2),
        ],
        [
            dict(key='Shift', value='shift', type='system', size=2.5),
            dict(key=u'я', value=u'я', type='char'),
            dict(key=u'ч', value=u'ч', type='char'),
            dict(key=u'с', value=u'с', type='char'),
            dict(key=u'м', value=u'м', type='char'),
            dict(key=u'и', value=u'и', type='char'),
            dict(key=u'т', value=u'т', type='char'),
            dict(key=u'ь', value=u'ь', type='char'),
            dict(key=u'б', value=u'б', type='char'),
            dict(key=u'ю', value=u'ю', type='char'),
            dict(key=u'.', value=u'.', type='sign'),
            dict(key=None, value=None, type='dummy', size=2.5),
        ],
        [
            dict(key=u'Eng', value='lang', type='system', size=3.5),
            dict(key=None, value=' ', type='sign', size=6.5),
            dict(key='@', value='@', type='sign'),
            dict(key='<', value='left', type='nav', size=2),
            dict(key='>', value='right', type='nav', size=2),
        ]
    ]


class Main(QtGui.QWidget):
    def __init__(self, width, height, input, *args, **kwargs):
        super(Main, self).__init__(*args, **kwargs)
        self.w = width
        self.h = height
        self.input = input
        self.init_ui()
        self.init_style()

    def init_ui(self):
        self.desktop = QtGui.QApplication.desktop()
        self._layout = QtGui.QVBoxLayout()
        self._layout.setSpacing(0)
        self.setLayout(self._layout)
        #self.input = QtGui.QLineEdit()
        width = self.w
        self.el_width = width / 15
        height = self.el_width * 5
        self.signal_enter = KeyboardEnter()
        self.signal_esc = KeyboardEsc()
        self.signal_shift = ShiftPress()
        self.manager = Manager(parent=self)
        #self._layout.addWidget(self.input)
        self._layout.addWidget(self.manager)
        #self._layout.addWidget(self.input, 0, 0, 1, self._layout.columnCount())
        self.setWindowTitle('Keyboard')

        self.setGeometry(0, self.h - height, width, height)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
        #self.show()

    def init_style(self):
        self.setStyleSheet('QWidget {'
            'background: #eeeeee;}')

    def closeEvent(self, event):
        event.accept()


def main():
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Keyboard')
    ex = Main()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
