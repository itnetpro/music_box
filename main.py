#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import Queue
import math
import moc
import re
from time import sleep
from datetime import datetime
from PySide import QtGui
from PySide import QtCore
from subprocess import Popen, PIPE, check_output
from threading import Thread
from keyboard import Main as Keyboard

from pleer_api import Pleer, SoundCloundPleer
from utils import load_config

ini = load_config()
PRICE = int(ini.get('main', 'price'))


class BalanceUpdate(QtCore.QObject):
        sig = QtCore.Signal(int)


class AcceptorThread(QtCore.QThread):

    def __init__(self, parent=None):
        super(AcceptorThread, self).__init__(parent)
        self.exiting = False
        self.signal = BalanceUpdate()

    def run(self):
        self.billPath = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'bill_acceptor.py')

        self.billProc = Popen(
            ['sudo', 'python', self.billPath],
            stdout=PIPE,
            close_fds=True,
            universal_newlines=True
        )
        self.billQueue = Queue.Queue()
        self.bill = Thread(target=self.enqueue_output,
                           args=(self.billProc.stdout, self.billQueue))
        self.bill.daemon = False
        self.bill.start()

        while not self.exiting:
            try:
                line = self.billQueue.get_nowait()
                amount = int(line)
                if amount:
                    self.signal.sig.emit(amount)
            except Queue.Empty:
                pass
            sleep(0.2)

        self.billProc.terminate()
        self.billProc.wait()

    def enqueue_output(self, out, queue):
        while True:
            line = out.readline()
            if line:
                queue.put(line.strip())
            else:
                break
        out.close()


class SongAddSignal(QtCore.QObject):
        sig = QtCore.Signal(dict)


class SongAddThread(QtCore.QThread):

    def __init__(self, func=None, parent=None):
        super(SongAddThread, self).__init__(parent)
        self.exiting = False
        self.func = func
        self.signal = SongAddSignal()

    def run(self):
        if not self.func:
            return

        for data in self.func():
            if self.exiting:
                break

            self.signal.sig.emit(data)


class TimerSignal(QtCore.QObject):
    sig = QtCore.Signal(int)


class SongEndSignal(QtCore.QObject):
    sig = QtCore.Signal()


class PlayerThread(QtCore.QThread):

    def __init__(self, parent=None, volume=100):
        super(PlayerThread, self).__init__(parent)
        self.signal = TimerSignal()
        self.songEndSignal = SongEndSignal()
        self.exiting = False
        self.volume = volume
        self.volume_to = volume
        self.needStop = False
        self.start_song = None
        self.start_song_dt = None

    def run(self):
        while not self.exiting:
            if self.volume != self.volume_to:
                delta = abs(self.volume - self.volume_to)
                if self.volume < self.volume_to:
                    moc.volume_up(delta)
                else:
                    moc.volume_down(delta)
                self.volume = self.volume_to

            now = datetime.now()
            if self.start_song:
                moc.clear_playlist()
                moc.quickplay([self.start_song.data['stream_link']])
                self.start_song = None
                self.start_song_dt = now
                continue

            if self.needStop:
                moc.stop()
                moc.clear_playlist()
                self.needStop = False
                continue

            if moc.is_playing():
                self.signal.sig.emit(int(moc.get_info().get('currentsec', 0)))
            elif self.start_song_dt and (now - self.start_song_dt).total_seconds() > 5:
                self.songEndSignal.sig.emit()
                continue


class HeadWidget(QtGui.QWidget):

    def __init__(self, *args, **kwargs):
        super(HeadWidget, self).__init__(*args, **kwargs)

        self.initUI()
        self.initStyle()

    def initUI(self):
        self._layout = QtGui.QGridLayout()
        self.searchField = QtGui.QLineEdit()
        self.searchButton = QtGui.QPushButton()
        self.balanceLabel = QtGui.QLabel()
        self.balanceLabel._format = u'Баланс: <b>%s</b> руб.'
        self.balanceLabel.setWordWrap(True)

        self._layout.addWidget(self.searchField, 0, 0, 1, 9)
        self._layout.addWidget(self.searchButton, 0, 0, 1, 9)
        self._layout.addWidget(self.balanceLabel, 0, 9, 1, 1,
                               alignment=QtCore.Qt.AlignRight)
        self.setLayout(self._layout)

    def initStyle(self):
        img_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'img/search-bg.png')
        self.searchField.setStyleSheet(
            "QLineEdit {"
            "background: url(" + img_path + ");"
            "border: none;"
            "min-height: 36px;}")
        self.searchButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.searchButton.setStyleSheet(
            "QPushButton {"
            "background: url(" + img_path + ");"
            "border: none;"
            "min-height: 36px;}"
        )

        self.balanceLabel.setStyleSheet(
            "QLabel{font-size: 18px;}"
        )

    def setButton(self):
        self.searchButton.show()

    def setTextField(self):
        self.searchButton.hide()


class SongWidget(QtGui.QWidget):

    def __init__(self, data, *args, **kwargs):
        super(SongWidget, self).__init__(*args, **kwargs)
        self.data = data

        self.initUI()
        self.initStyle()

    def initUI(self):
        self._layout = QtGui.QGridLayout(self)
        self._layout.setVerticalSpacing(4)
        w = self.width() / 4
        h = self.height() / 2
        image_w = w - 8

        img = QtGui.QImage(self.data['image_link'])
        pixmap = QtGui.QPixmap(img.scaled(image_w, image_w))
        self.image = QtGui.QLabel(self)
        self.image.setPixmap(pixmap)
        self.image.setMinimumWidth(image_w)
        self.image.setMinimumHeight(image_w)

        metrics = QtGui.QFontMetrics(self.font())

        self.trackLabel = QtGui.QLabel(metrics.elidedText(
            self.data['track'], QtCore.Qt.ElideRight, w - 16))

        self.artistLabel = QtGui.QLabel(metrics.elidedText(
            self.data['artist'], QtCore.Qt.ElideRight, w - 10))

        self.priceLabel = QtGui.QLabel(u'%s руб.' % PRICE)
        self.timeLabel = QtGui.QLabel(self.data['time'])
        self._layout.addWidget(self.image, 0, 0, 1, 2)
        self._layout.addWidget(self.trackLabel, 1, 0, 1, 2)
        self._layout.addWidget(self.artistLabel, 2, 0, 1, 2)
        self._layout.addWidget(self.priceLabel, 3, 0, 1, 1)
        self._layout.addWidget(self.timeLabel, 3, 1, 1, 1,
                               alignment=QtCore.Qt.AlignRight)

        self.setLayout(self._layout)
        self.setMaximumWidth(w)
        self.setMinimumWidth(w)
        self.setMaximumHeight(h)
        self.setMinimumHeight(h)

    def initStyle(self):
        self.image.setStyleSheet(
            "QLabel {"
            "border: 2px solid #cecece;"
            "padding: 2px;}")

        self.trackLabel.setStyleSheet(
            "QLabel {"
            "font-weight: bold;"
            "color: #414242;}")

        self.artistLabel.setStyleSheet(
            "QLabel {color: #868686;}"
        )

        self.priceLabel.setStyleSheet(
            "QLabel {"
            "background: #a5a5a5;"
            "border: 2px solid #dddcdc;"
            "color: #ffffff;"
            "font-size: 12px;"
            "padding: 2px;}"
        )


class SongPageWidget(QtGui.QWidget):

    def __init__(self, *args, **kwargs):
        super(SongPageWidget, self).__init__(*args, **kwargs)
        self.initUI()
        self.el_in_line = 4
        self.els = 0
        self.el_max = 8
        self.row = 0
        self.col = 0

    def initUI(self):
        self._layout = QtGui.QGridLayout()

        self._layout.addWidget(QtGui.QLabel(), 0, 0, 1, 4)

        self.setLayout(self._layout)

    def addSong(self, song):
        if self.els >= self.el_max:
            return
        self._layout.addWidget(
            song, self.row, self.col, 1, 1,
            alignment=QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.els += 1
        self.col += 1
        if self.col >= self.el_in_line:
            self.col = 0
            self.row += 1

        return True


class PageButton(QtGui.QPushButton):
    enable_icon = None
    disable_icon = None

    def enable(self):
        self.setIcon(QtGui.QIcon(self.enable_icon))

    def disable(self):
        self.setIcon(QtGui.QIcon(self.disable_icon))


class PlayListWidget(QtGui.QGroupBox):

    def __init__(self, parent=None):
        super(PlayListWidget, self).__init__(parent)
        self.initUI()
        self.songs = list()

    def initUI(self):
        self._layout = QtGui.QGridLayout()
        self._layout.setSpacing(0)
        self._layout.setAlignment(QtCore.Qt.AlignTop)
        self.widget = QtGui.QWidget()
        self.layout = QtGui.QVBoxLayout(self.widget)
        self.layout.setSpacing(0)
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.scroll = QtGui.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.widget)
        self.scroll.setMinimumHeight(522)
        self.scroll.setMinimumWidth(200)
        self._layout.addWidget(self.scroll, 0, 0, alignment=QtCore.Qt.AlignLeft)
        self.setLayout(self._layout)

    def addSong(self, song, is_need_add=True):
        widget = PlayListSongWidget(song)
        self.layout.addWidget(widget,
                              alignment=QtCore.Qt.AlignTop)
        if is_need_add:
            self.songs.append(song)

    def deleteSong(self, song):
        index = self.songs.index(song)
        self.songs.pop(index)
        clean_layout(self.layout)
        for song in self.songs:
            self.addSong(song, False)


class PlayListSongWidget(QtGui.QWidget):

    def __init__(self, song, parent=None):
        self.song = song
        super(PlayListSongWidget, self).__init__(parent)
        self.initUI()
        self.initStyle()

    def initUI(self):
        self._layout = QtGui.QHBoxLayout()
        self._layout.setSpacing(4)
        self.metrics = QtGui.QFontMetrics(self.font())
        img = QtGui.QImage(self.song.data['image_link'])
        pixmap = QtGui.QPixmap(img.scaled(36, 36))
        self.image = QtGui.QLabel(self)
        self.image.setPixmap(pixmap)
        self.image.setMinimumWidth(36)
        self.image.setMaximumWidth(36)
        self.trackLabel = QtGui.QLabel(self.song.data['track'])
        self.artistLabel = QtGui.QLabel(self.song.data['artist'])
        self.vbox1 = QtGui.QVBoxLayout()
        self.vbox1.setSpacing(0)
        self.vbox2 = QtGui.QVBoxLayout()
        self.vbox2.setSpacing(0)

        self.vbox1.addWidget(self.image)
        self.vbox2.addWidget(self.trackLabel)
        self.vbox2.addWidget(self.artistLabel)

        self._layout.addLayout(self.vbox1)
        self._layout.addLayout(self.vbox2)

        self.setMaximumHeight(60)
        self.setMaximumWidth(180)

        self.setLayout(self._layout)

    def initStyle(self):
        self.trackLabel.setStyleSheet(
            "QLabel {"
            "font-weight: bold;"
            "color: #414242;}")

        self.artistLabel.setStyleSheet(
            "QLabel {"
            "color: #868686;}"
        )


class ContentWidget(QtGui.QWidget):

    def __init__(self, *args, **kwargs):
        super(ContentWidget, self).__init__(*args, **kwargs)

        self.initUI()
        self.initStyle()
        self.initAction()
        self.pages = list()
        self.currentPageNum = 0

    def initUI(self):
        self._layout = QtGui.QGridLayout()
        self.pageUpButton = PageButton()
        self.pageDownButton = PageButton()
        self.contentWidget = QtGui.QStackedWidget()
        self.queueWidget = PlayListWidget()

        self._layout.addWidget(self.contentWidget, 0, 0, 3, 8)
        self._layout.addWidget(self.pageUpButton, 0, 8, 1, 1)
        self._layout.addWidget(self.pageDownButton, 2, 8, 1, 1)
        self._layout.addWidget(self.queueWidget, 0, 9, 3, 2)

        self.pageUpButton.enable_icon = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'img/arrow_up.png')
        self.pageUpButton.disable_icon = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'img/arrow_up_d.png')
        self.pageUpButton.disable()

        self.pageDownButton.enable_icon = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'img/arrow_down.png')
        self.pageDownButton.disable_icon = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'img/arrow_down_d.png')
        self.pageDownButton.disable()

        self.contentWidget.setMinimumWidth(676)
        self.setMinimumHeight(522)
        self.setLayout(self._layout)

    def initStyle(self):
        self.pageUpButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.pageUpButton.setStyleSheet(
            "QPushButton {"
            "background: none;"
            "border: none;"
            "min-height: 36px;}")

        self.pageDownButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.pageDownButton.setStyleSheet(
            "QPushButton {"
            "background: none;"
            "border: none;"
            "min-height: 36px;}")

    def initAction(self):
        self.pageDownButton.clicked.connect(lambda: self.onPageDown())
        self.pageUpButton.clicked.connect(lambda: self.onPageUp())

    def createPage(self):
        page = SongPageWidget()
        self.contentWidget.addWidget(page)
        self.pages.append(page)
        return page

    def getLastPage(self):
        if not self.pages:
            self.createPage()
        return self.pages[-1]

    def getCurrentPage(self):
        if not self.pages:
            return
        return self.contentWidget.indexOf(self.currentPageNum)

    def getPageCount(self):
        return self.contentWidget.count()

    def cleanPages(self):
        self.contentWidget.setCurrentIndex(0)
        self.currentPageNum = 0
        for page in self.pages:
            self.contentWidget.removeWidget(page)
        self.pages = list()

    def onPageUp(self):
        if self.currentPageNum <= 0:
            return
        self.contentWidget.setCurrentIndex(
            self.contentWidget.currentIndex() - 1)
        self.currentPageNum -= 1
        self.updateButton()

    def onPageDown(self):
        if self.currentPageNum >= self.getPageCount() - 1:
            return
        self.contentWidget.setCurrentIndex(
            self.contentWidget.currentIndex() + 1)
        self.currentPageNum += 1
        self.updateButton()

    def updateButton(self):
        if self.currentPageNum + 1 >= self.getPageCount():
            self.pageDownButton.disable()
        else:
            self.pageDownButton.enable()

        if self.currentPageNum == 0:
            self.pageUpButton.disable()
        else:
            self.pageUpButton.enable()


class PlayerWidget(QtGui.QWidget):

    def __init__(self, *args, **kwargs):
        super(PlayerWidget, self).__init__(*args, **kwargs)

        self.initUI()
        self.initStyle()

        self.currentLength = None
        self.songLength = None
        self.volume = 100

    def initUI(self):
        self._layout = QtGui.QGridLayout()

        img = QtGui.QImage(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'img/no-photo.png'))
        pixmap = QtGui.QPixmap(img.scaled(100, 100))

        self.stopButton = QtGui.QPushButton()
        self.stopButton.setMinimumWidth(100)
        self.stopButton.setMinimumHeight(100)
        self.stopButton.setMaximumHeight(100)
        self.stopButton.setMaximumWidth(100)

        self.image = QtGui.QLabel(self)
        self.image.setPixmap(pixmap)
        self.image.setMinimumWidth(100)
        self.image.setMinimumHeight(100)
        self.image.setMaximumHeight(100)
        self.image.setMaximumWidth(100)

        self.metrics = QtGui.QFontMetrics(self.font())

        self.trackLabel = QtGui.QLabel(u'Нечего не воспроизводиться')

        self.artistLabel = QtGui.QLabel(u'Некто не исполняет')

        self.dial = QtGui.QDial()
        self.dial.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.dial.setMaximum(100)
        self.dial.setSliderPosition(100)

        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.slider.setFocusPolicy(QtCore.Qt.NoFocus)
        self.timeWidget = QtGui.QLabel("--:--/--:--")
        self.slider.setDisabled(True)

        self.volumeLabel = QtGui.QLabel(u'Звук 100%')
        self.volumeLabel._format = u'Звук %s%%'

        self._layout.addWidget(self.stopButton, 0, 0, 3, 1)
        self._layout.addWidget(self.image, 0, 1, 3, 1, )
        self._layout.addWidget(self.trackLabel, 0, 2, 1, 6)
        self._layout.addWidget(self.artistLabel, 1, 2, 1, 6)
        self._layout.addWidget(self.slider, 2, 2, 1, 5)
        self._layout.addWidget(self.timeWidget, 2, 7, 1, 1)
        self._layout.addWidget(self.dial, 0, 8, 2, 1,
                               alignment=QtCore.Qt.AlignRight)
        self._layout.addWidget(self.volumeLabel, 2, 8, 1, 1,
                               alignment=QtCore.Qt.AlignRight)

        self.setLayout(self._layout)

    def initStyle(self):
        self.image.setStyleSheet(
            "QLabel {"
            "border: 2px solid #cecece;"
            "padding: 2px;}")

        self.trackLabel.setStyleSheet(
            "QLabel {"
            "font-weight: bold;"
            "font-size: 20px;"
            "color: #414242;}")

        self.artistLabel.setStyleSheet(
            "QLabel {"
            "color: #868686;"
            "font-size: 18px;}"
        )
        img_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'img/stop.png')
        self.stopButton.setStyleSheet(
             "QPushButton {"
             "border: none;"
             "background: url('" + img_path + "');}")
        self.stopButton.setFocusPolicy(QtCore.Qt.NoFocus)

    def playSong(self, song):
        img = QtGui.QImage(song.data['image_link'])
        pixmap = QtGui.QPixmap(img.scaled(100, 100))
        self.image.setPixmap(pixmap)

        self.trackLabel.setText(self.metrics.elidedText(
            song.data['track'], QtCore.Qt.ElideRight,
            self.trackLabel.width() - 10))
        self.artistLabel.setText(self.metrics.elidedText(
            song.data['artist'], QtCore.Qt.ElideRight,
            self.artistLabel.width() - 10))

        self.timeWidget.setText('00:00/%s' % song.data['time'])
        self.songLength = song.data['ttime']
        self.slider.setMaximum(self.songLength)

    def clean(self):
        self.currentLength = None
        self.songLength = None
        self.slider.setMaximum(100)
        self.slider.setSliderPosition(0)

        img = QtGui.QImage(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'img/no-photo.png'))
        pixmap = QtGui.QPixmap(img.scaled(100, 100))
        self.image.setPixmap(pixmap)

        self.trackLabel.setText(u'Нечего не воспроизводиться')

        self.artistLabel.setText(u'Некто не исполняет')
        self.timeWidget.setText("--:--/--:--")

    def updateTime(self, pos):
        if not self.songLength:
            pos = 0
        self.slider.setSliderPosition(pos)
        self.currentLength = pos
        if self.songLength:
            self.timeWidget.setText(u'%s/%s' % (
                self.get_track_time(self.currentLength),
                self.get_track_time(self.songLength))
            )

    def get_track_time(self, lenght):
        minute = math.floor(int(lenght) / 60.)
        second = int(lenght) - minute * 60
        return '%02d:%02d' % (minute, second)

    def updateVolume(self, vol):
        self.volumeLabel.setText(self.volumeLabel._format % vol)


class Main(QtGui.QWidget):

    def __init__(self):
        super(Main, self).__init__()

        self.initUI()
        self.initStyle()
        self.initAction()
        self.initPlayer()
        self.initThread()
        self.initAction()
        self.balance = 0
        self.contentType = None
        self.last_press_stop = datetime.now()
        self.last_start_song = datetime.now()
        self.loadPopulationSong()

    def initUI(self):
        self._layout = QtGui.QGridLayout()
        self._layout.setSpacing(2)

        self.headWidget = HeadWidget()
        self.contentWidget = ContentWidget()
        self.playerWidget = PlayerWidget()

        self._layout.addWidget(self.headWidget, 0, 0,
                               alignment=QtCore.Qt.AlignTop)
        self._layout.addWidget(self.contentWidget, 1, 0)
        self._layout.addWidget(self.playerWidget, 2, 0)
        self.setLayout(self._layout)

        self.setWindowTitle('Music Box')

        self.setWindowIcon(
            QtGui.QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'img/icon.png'))
        )
        desktop = QtGui.QApplication.desktop()
        rect = desktop.availableGeometry()
        self.setGeometry(0, 0, 1280, 996)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        #self.setWindowState(QtCore.Qt.WindowFullScreen)
        self.keyboard = Keyboard(width=self.width(), height=self.height(),
                                 input=self.headWidget.searchField)
        self.show()

    def initStyle(self):
        img_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'img/dlet-bg.png')
        tile = QtGui.QPixmap(img_path)
        palette = QtGui.QPalette()
        palette.setBrush(QtGui.QPalette.Background, tile)
        self.setPalette(palette)

    def initThread(self):
        self.acceptorThread = AcceptorThread()
        self.acceptorThread.signal.sig.connect(self.on_balance_update)
        self.acceptorThread.start()

        self.initSongThread()

        self.playerThread = PlayerThread(parent=self)
        self.playerThread.signal.sig.connect(self.on_timer_update)
        self.playerThread.songEndSignal.sig.connect(self.onSongEnd)
        self.playerThread.start()

    def initSongThread(self):
        self.addSongThread = SongAddThread()
        self.addSongThread.signal.sig.connect(self.on_add_song)

    def killSongThread(self):
        self.addSongThread.exiting = True
        self.addSongThread.wait()
        self.addSongThread.terminate()
        self.addSongThread = None

    def initPlayer(self):
        if ini.get('main', 'api') == 'pleer':
            self.player_api = Pleer()
        else:
            self.player_api = SoundCloundPleer()
        try:
            moc.stop_server()
        except moc.MocNotRunning:
            pass
        moc.start_server()
        moc.volume_up(100)
        self.song = None
        self.play_list = list()

    def killPlayer(self):
        try:
            moc.stop_server()
        except moc.MocNotRunning:
            pass

    def initAction(self):
        self.headWidget.searchField.returnPressed.connect(
            lambda: self.on_search())
        self.headWidget.searchButton.clicked.connect(lambda: self.onClickSearch())

        self.playerWidget.stopButton.clicked.connect(lambda: self.onPressStop())
        self.playerWidget.dial.valueChanged[int].connect(lambda: self.onChangeVolume())
        self.keyboard.signal_enter.sig.connect(self.on_keyboard_enter)
        self.keyboard.signal_esc.sig.connect(self.on_keyboard_esc)

    def closeEvent(self, event):
        self.keyboard.hide()
        self.killPlayer()
        self.acceptorThread.exiting = True
        self.acceptorThread.billProc.wait()
        if self.addSongThread:
            self.addSongThread.exiting = True
            self.addSongThread.wait()
        self.playerThread.exiting = True
        self.playerThread.wait()
        event.accept()

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        self._balance = value
        self.headWidget.balanceLabel.setText(
            self.headWidget.balanceLabel._format % value)

    def on_balance_update(self, data):
        self.balance += int(data)

    old_query = ''

    def on_search(self):
        query = self.headWidget.searchField.text()
        if not query or query == self.old_query:
            return
        self.killSongThread()
        self.contentWidget.cleanPages()
        self.old_query = query
        self.loadSearchSong(query)
        self.headWidget.searchField.setText('')

    def on_add_song(self, data):
        song = SongWidget(data=data)
        song.mouseReleaseEvent = lambda event: self.on_click_song(event, song)
        page = self.contentWidget.getLastPage()
        if not page.addSong(song):
            self.contentWidget.createPage().addSong(song)
        self.contentWidget.updateButton()

    def on_click_song(self, event, song):
        if self.balance < PRICE:
            return
        self.balance -= PRICE
        if self.contentType != 'population':
            self.killSongThread()
            self.contentWidget.cleanPages()
            self.loadPopulationSong()
        if moc.is_playing():
            self.play_list.append(song)
            self.contentWidget.queueWidget.addSong(song)
        else:
            self.playerThread.start_song = song
            self.song = song
            self.playerWidget.playSong(song)
            self.last_start_song = datetime.now()

    def loadPopulationSong(self):
        self.old_query = ''
        self.contentType = 'population'
        if not self.addSongThread:
            self.initSongThread()
        self.addSongThread.func = lambda: self.player_api.get_population()
        self.addSongThread.start()

    def onClickSearch(self):
        self.keyboard.show()
        self.headWidget.searchField.clear()
        self.headWidget.setTextField()

    def on_keyboard_esc(self):
        self.headWidget.searchField.clear()
        self.headWidget.setButton()

    def on_keyboard_enter(self, text):
        self.headWidget.setButton()
        if not text:
            return
        self.headWidget.searchField.setText(text)
        self.on_search()

    def loadSearchSong(self, query):
        self.headWidget.setButton()
        self.contentType = 'search'
        if not self.addSongThread:
            self.initSongThread()
        self.addSongThread.func = lambda: self.player_api.search(query)
        self.addSongThread.start()

    def on_timer_update(self,  position):
        if position:
            self.playerWidget.updateTime(position)

    def onPressStop(self):
        now = datetime.now()
        if (now - self.last_press_stop).total_seconds() < 3:
            return
        self.last_press_stop = now
        self.song = None
        self.playerThread.needStop = True
        self.playerWidget.clean()

    def onChangeVolume(self):
        self.playerThread.volume_to = self.playerWidget.dial.value()
        self.playerWidget.updateVolume(self.playerWidget.dial.value())

    def onSongEnd(self):
        now = datetime.now()
        if self.play_list:
            if self.playerThread.start_song:
                return
            self.song = self.play_list.pop(0)
            self.playerThread.start_song = self.song
            self.contentWidget.queueWidget.deleteSong(self.song)
            self.playerWidget.playSong(self.song)
            self.last_start_song = now
        elif (now - self.last_start_song).total_seconds() > 5:
            self.song = None
            self.playerWidget.clean()


def clean_layout(layout):
    if not layout.isEmpty():
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                clean_layout(item.layout())


def main():
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Music Box')
    ex = Main()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

