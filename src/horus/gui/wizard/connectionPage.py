# -*- coding: utf-8 -*-
# This file is part of the Horus Project

__author__ = 'Jesús Arroyo Torrens <jesus.arroyo@bq.com>'
__copyright__ = 'Copyright (C) 2014-2015 Mundo Reader S.L.'
__license__ = 'GNU General Public License v2 http://www.gnu.org/licenses/gpl2.html'

import time
import wx._core

from horus.gui.util.imageView import ImageView

from horus.gui.wizard.wizardPage import WizardPage

from horus.util import profile, resources

from horus.engine.driver.driver import Driver
from horus.engine.driver.board import WrongFirmware, BoardNotConnected
from horus.engine.driver.camera import WrongCamera, CameraNotConnected, InvalidVideo
from horus.engine.calibration.pattern import Pattern
from horus.engine.calibration.autocheck import Autocheck, PatternNotDetected, \
    WrongMotorDirection, LaserNotDetected
from horus.engine.algorithms.image_capture import ImageCapture
from horus.engine.algorithms.image_detection import ImageDetection


class ConnectionPage(WizardPage):

    def __init__(self, parent, buttonPrevCallback=None, buttonNextCallback=None):
        WizardPage.__init__(self, parent,
                            title=_("Connection"),
                            buttonPrevCallback=buttonPrevCallback,
                            buttonNextCallback=buttonNextCallback)

        self.parent = parent
        self.driver = Driver()
        self.autocheck = Autocheck()
        self.image_capture = ImageCapture()
        self.image_detection = ImageDetection()

        self.connectButton = wx.Button(self.panel, label=_("Connect"))
        self.settingsButton = wx.Button(self.panel, label=_("Edit settings"))

        self.patternLabel = wx.StaticText(self.panel, label=_(
            "Put the pattern on the platform as shown in the picture and press \"Auto check\""))
        self.patternLabel.Wrap(400)
        self.imageView = ImageView(self.panel, quality=wx.IMAGE_QUALITY_HIGH)
        self.imageView.setImage(wx.Image(resources.getPathForImage("pattern-position.png")))
        self.autoCheckButton = wx.Button(self.panel, label=_("Auto check"))
        self.gauge = wx.Gauge(self.panel, range=100, size=(-1, 30))
        self.resultLabel = wx.StaticText(self.panel, size=(-1, 30))

        self.connectButton.Enable()
        self.settingsButton.Enable()
        self.patternLabel.Disable()
        self.imageView.Disable()
        self.autoCheckButton.Disable()
        self.skipButton.Disable()
        self.nextButton.Disable()
        self.resultLabel.Hide()
        self.enableNext = False

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.connectButton, 1, wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.settingsButton, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(hbox, 0, wx.ALL | wx.EXPAND, 2)
        vbox.Add(self.patternLabel, 0, wx.ALL | wx.CENTER, 5)
        vbox.Add(self.imageView, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(self.resultLabel, 0, wx.ALL | wx.CENTER, 5)
        vbox.Add(self.gauge, 0, wx.ALL | wx.EXPAND, 5)
        vbox.Add(self.autoCheckButton, 0, wx.ALL | wx.EXPAND, 5)
        self.panel.SetSizer(vbox)

        self.Layout()

        self.connectButton.Bind(wx.EVT_BUTTON, self.onConnectButtonClicked)
        self.settingsButton.Bind(wx.EVT_BUTTON, self.onSettingsButtonClicked)
        self.autoCheckButton.Bind(wx.EVT_BUTTON, self.onAutoCheckButtonClicked)
        self.Bind(wx.EVT_SHOW, self.onShow)

        self.videoView.setMilliseconds(10)
        self.videoView.setCallback(self.get_image)
        self.updateStatus(self.driver.is_connected)

    def onShow(self, event):
        if event.GetShow():
            self.updateStatus(self.driver.is_connected)
        else:
            try:
                self.videoView.stop()
            except:
                pass

    def get_image(self):
        if self.autocheck._is_calibrating:
            image = self.autocheck.image
        else:
            image = self.image_capture.capture_pattern()
            image = self.image_detection.detect_pattern(image)
        return image

    def onUnplugged(self):
        self.videoView.stop()
        self.autocheck.cancel()
        self.afterAutoCheck()

    def onConnectButtonClicked(self, event):
        self.driver.set_callbacks(
            lambda: wx.CallAfter(self.beforeConnect),
            lambda r: wx.CallAfter(self.afterConnect, r))
        self.driver.connect()

    def onSettingsButtonClicked(self, event):
        SettingsWindow(self)

    def beforeConnect(self):
        self.settingsButton.Disable()
        self.breadcrumbs.Disable()
        self.connectButton.Disable()
        self.prevButton.Disable()
        self.videoView.stop()
        self.driver.board.set_unplug_callback(None)
        self.driver.camera.set_unplug_callback(None)
        self.waitCursor = wx.BusyCursor()

    def afterConnect(self, response):
        ret, result = response

        if not ret:
            if isinstance(result, WrongFirmware):
                dlg = wx.MessageDialog(
                    self,
                    _("Board has a wrong firmware or an invalid Baud Rate.\n"
                      "Please select your Board and press Upload Firmware"),
                    _(result), wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
                self.updateStatus(False)
                self.GetParent().parent.onPreferences(None)
            elif isinstance(result, BoardNotConnected):
                dlg = wx.MessageDialog(
                    self,
                    _("Board is not connected.\n"
                      "Please connect your board and select a valid Serial Name"),
                    _(result), wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
                self.updateStatus(False)
                self.GetParent().parent.onPreferences(None)
            elif isinstance(result, WrongCamera):
                dlg = wx.MessageDialog(
                    self,
                    _("You probably have selected a wrong camera.\n"
                      "Please select other Camera Id"),
                    _(result), wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
                self.updateStatus(False)
                self.GetParent().parent.onPreferences(None)
            elif isinstance(result, CameraNotConnected):
                dlg = wx.MessageDialog(
                    self, _("Please plug your camera and try to connect again"),
                    _(result), wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()
            elif isinstance(result, InvalidVideo):
                dlg = wx.MessageDialog(
                    self, _("Unplug and plug your camera USB cable and try to connect again"),
                    _(result), wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()

        self.updateStatus(self.driver.is_connected)
        self.settingsButton.Enable()
        self.breadcrumbs.Enable()
        self.prevButton.Enable()
        del self.waitCursor

    def onAutoCheckButtonClicked(self, event):
        if profile.settings['adjust_laser']:
            profile.settings['adjust_laser'] = False
            dlg = wx.MessageDialog(
                self,
                _("It is recomended to adjust line lasers vertically.\n"
                  "You need to use the allen wrench.\nDo you want to adjust it now?"),
                _("Manual laser adjustment"), wx.YES_NO | wx.ICON_QUESTION)
            result = dlg.ShowModal() == wx.ID_YES
            dlg.Destroy()
            if result:
                self.driver.board.lasers_on()
        else:
            # Perform auto check
            self.autocheck.set_callbacks(lambda: wx.CallAfter(self.beforeAutoCheck),
                                         lambda p: wx.CallAfter(self.progressAutoCheck, p),
                                         lambda r: wx.CallAfter(self.afterAutoCheck, r))
            self.autocheck.start()

    def beforeAutoCheck(self):
        self.settingsButton.Disable()
        self.breadcrumbs.Disable()
        self.autoCheckButton.Disable()
        self.prevButton.Disable()
        self.skipButton.Disable()
        self.nextButton.Disable()
        self.enableNext = False
        self.gauge.SetValue(0)
        self.resultLabel.Hide()
        self.gauge.Show()
        self.waitCursor = wx.BusyCursor()
        self.Layout()

    def progressAutoCheck(self, progress):
        self.gauge.SetValue(progress)

    def afterAutoCheck(self, result):
        if result:
            self.resultLabel.SetLabel(str(result))
            if isinstance(result, PatternNotDetected):
                dlg = wx.MessageDialog(
                    self, _("Please, put the pattern on the platform"),
                    _(result), wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()
            elif isinstance(result, WrongMotorDirection):
                dlg = wx.MessageDialog(
                    self, _(
                        'Please, go to "Edit settings" and select "Invert the motor direction"'),
                    _(result), wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()
            elif isinstance(result, LaserNotDetected):
                dlg = wx.MessageDialog(
                    self, _("Please, check the lasers connection"),
                    _(result), wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()
        else:
            self.resultLabel.SetLabel(_("All OK. Please press next to continue"))
            dlg = wx.MessageDialog(
                self, _("Autocheck executed correctly"),
                _("Success!"), wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()

        if result:
            self.skipButton.Enable()
            self.nextButton.Disable()
        else:
            self.skipButton.Disable()
            self.nextButton.Enable()

        self.settingsButton.Enable()
        self.breadcrumbs.Enable()
        self.enableNext = True
        self.resultLabel.Show()
        self.autoCheckButton.Enable()
        self.prevButton.Enable()
        self.gauge.Hide()
        if hasattr(self, 'waitCursor'):
            del self.waitCursor
        self.panel.Fit()
        self.panel.Layout()
        self.Layout()

    def updateStatus(self, status):
        if status:
            self.driver.board.set_unplug_callback(
                lambda: wx.CallAfter(self.parent.onBoardUnplugged))
            self.driver.camera.set_unplug_callback(
                lambda: wx.CallAfter(self.parent.onCameraUnplugged))
            # if profile.settings['workbench'] != u'Calibration workbench':
            profile.settings['workbench'] = u'Calibration workbench'
            self.GetParent().parent.workbenchUpdate(False)
            self.videoView.play()
            self.connectButton.Disable()
            self.autoCheckButton.Enable()
            self.patternLabel.Enable()
            self.imageView.Enable()
            self.skipButton.Enable()
            self.enableNext = True
            self.driver.board.lasers_off()
        else:
            self.videoView.stop()
            self.gauge.SetValue(0)
            self.gauge.Show()
            self.resultLabel.Hide()
            self.resultLabel.SetLabel("")
            self.connectButton.Enable()
            self.skipButton.Disable()
            self.nextButton.Disable()
            self.enableNext = False
            self.autoCheckButton.Disable()
        self.Layout()


class SettingsWindow(wx.Dialog):

    def __init__(self, parent):
        super(SettingsWindow, self).__init__(
            parent, title=_('Settings'), size=(420, -1),
            style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        self.driver = Driver()
        self.pattern = Pattern()

        # Elements
        _choices = []
        choices = profile.settings.getPossibleValues('luminosity')
        for i in choices:
            _choices.append(_(i))
        self.initLuminosity = profile.settings['luminosity']
        self.luminosityDict = dict(zip(_choices, choices))
        self.luminosityText = wx.StaticText(self, label=_('Luminosity'))
        self.luminosityText.SetToolTip(wx.ToolTip(
            _('Change the luminosity until colored lines appear '
              'over the chess pattern in the video')))
        self.luminosityComboBox = wx.ComboBox(self, wx.ID_ANY,
                                              value=_(self.initLuminosity),
                                              choices=_choices,
                                              style=wx.CB_READONLY)
        invert = profile.settings['invert_motor']
        self.invertMotorCheckBox = wx.CheckBox(self, label=_("Invert the motor direction"))
        self.invertMotorCheckBox.SetValue(invert)
        tooltip = _("Minimum distance between the origin of the pattern "
                    "(bottom-left corner) and the pattern's base surface")
        self.image = wx.Image(
            resources.getPathForImage("pattern-distance.jpg"), wx.BITMAP_TYPE_ANY)

        self.patternDistance = float(profile.settings['pattern_origin_distance'])
        self.patternImage = wx.StaticBitmap(self, wx.ID_ANY, wx.BitmapFromImage(self.image))
        self.patternImage.SetToolTip(wx.ToolTip(tooltip))
        self.patternLabel = wx.StaticText(self, label=_('Pattern distance (mm)'))
        self.patternLabel.SetToolTip(wx.ToolTip(tooltip))
        self.patternTextbox = wx.TextCtrl(
            self, value=str(profile.settings['pattern_origin_distance']))
        self.okButton = wx.Button(self, label=_('OK'))
        self.cancelButton = wx.Button(self, label=_('Cancel'))

        # Events
        self.luminosityComboBox.Bind(wx.EVT_COMBOBOX, self.onLuminosityComboBoxChanged)
        self.invertMotorCheckBox.Bind(wx.EVT_CHECKBOX, self.onInvertMotor)
        self.patternTextbox.Bind(wx.EVT_TEXT, self.onTextBoxChanged)
        self.cancelButton.Bind(wx.EVT_BUTTON, self.onClose)
        self.okButton.Bind(wx.EVT_BUTTON, self.onOk)
        self.Bind(wx.EVT_CLOSE, self.onClose)

        # Layout
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.luminosityText, 0, wx.ALL, 7)
        hbox.Add(self.luminosityComboBox, 1, wx.ALL, 3)
        vbox.Add(hbox, 0, wx.ALL ^ wx.BOTTOM | wx.EXPAND, 7)
        vbox.Add(wx.StaticLine(self), 0, wx.ALL ^ wx.BOTTOM | wx.EXPAND, 10)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.invertMotorCheckBox, 0, wx.ALL, 10)
        vbox.Add(hbox)
        vbox.Add(wx.StaticLine(self), 0, wx.ALL ^ wx.BOTTOM ^ wx.TOP | wx.EXPAND, 10)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.patternLabel, 0, wx.ALL, 7)
        hbox.Add(self.patternTextbox, 1, wx.ALL, 3)
        vbox.Add(hbox, 0, wx.ALL ^ wx.BOTTOM | wx.EXPAND, 10)
        vbox.Add(self.patternImage, 0, wx.ALL | wx.CENTER, 10)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.cancelButton, 1, wx.ALL, 3)
        hbox.Add(self.okButton, 1, wx.ALL, 3)
        vbox.Add(hbox, 0, wx.ALL | wx.EXPAND, 10)
        self.SetSizer(vbox)
        self.Center()
        self.Fit()

        self.ShowModal()

    def onTextBoxChanged(self, event):
        try:
            value = float(self.patternTextbox.GetValue())
            if value >= 0:
                self.patternDistance = value
        except:
            pass

    def setPatternDistance(self, distance):
        profile.settings['pattern_origin_distance'] = distance
        self.pattern.distance = distance

    def setLuminosity(self, luminosity):
        profile.settings['luminosity'] = luminosity

        if luminosity == 'Low':
            luminosity = 32
        elif luminosity == 'Medium':
            luminosity = 16
        elif luminosity == 'High':
            luminosity = 8

        profile.settings['exposure_pattern'] = luminosity
        self.driver.camera.set_exposure(luminosity)

    def onLuminosityComboBoxChanged(self, event):
        value = self.luminosityDict[event.GetEventObject().GetValue()]
        self.setLuminosity(value)

    def onInvertMotor(self, event):
        invert = self.invertMotorCheckBox.GetValue()
        profile.settings['invert_motor'] = invert
        self.driver.board.motor_invert(invert)

    def onOk(self, event):
        self.setPatternDistance(self.patternDistance)
        self.EndModal(wx.ID_OK)
        self.Destroy()

    def onClose(self, event):
        self.setLuminosity(self.initLuminosity)
        self.EndModal(wx.ID_OK)
        self.Destroy()
