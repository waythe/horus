# -*- coding: utf-8 -*-
# This file is part of the Horus Project

__author__ = 'Jesús Arroyo Torrens <jesus.arroyo@bq.com>'
__copyright__ = 'Copyright (C) 2014-2015 Mundo Reader S.L.'
__license__ = 'GNU General Public License v2 http://www.gnu.org/licenses/gpl2.html'

import wx._core

from horus.util import resources, profile, system as sys

from horus.gui.util.imageView import VideoView
from horus.gui.util.sceneView import SceneView
from horus.gui.util.customPanels import ExpandableControl

from horus.gui.workbench.workbench import WorkbenchConnection
from horus.gui.workbench.scanning.panels import ScanParameters, RotatingPlatform, \
    PointCloudROI, PointCloudColor

from horus.engine.scan.ciclop_scan import CiclopScan
from horus.engine.scan.current_video import CurrentVideo
from horus.engine.algorithms.image_capture import ImageCapture
from horus.engine.algorithms.image_detection import ImageDetection
from horus.engine.algorithms import point_cloud_roi


class ScanningWorkbench(WorkbenchConnection):

    def __init__(self, parent):
        WorkbenchConnection.__init__(self, parent)

        self.scanning = False
        self.showVideoViews = False

        self.ciclop_scan = CiclopScan()
        self.current_video = CurrentVideo()
        self.image_capture = ImageCapture()
        self.image_detection = ImageDetection()
        self.point_cloud_roi = point_cloud_roi.PointCloudROI()

        # Toolbar Configuration
        self.playTool = self.toolbar.AddLabelTool(
            wx.NewId(), _("Play"),
            wx.Bitmap(resources.getPathForImage("play.png")), shortHelp=_("Play"))
        self.stopTool = self.toolbar.AddLabelTool(
            wx.NewId(), _("Stop"),
            wx.Bitmap(resources.getPathForImage("stop.png")), shortHelp=_("Stop"))
        self.pauseTool = self.toolbar.AddLabelTool(
            wx.NewId(), _("Pause"),
            wx.Bitmap(resources.getPathForImage("pause.png")), shortHelp=_("Pause"))
        self.toolbar.Realize()

        # Disable Toolbar Items
        self.enableLabelTool(self.playTool, False)
        self.enableLabelTool(self.stopTool, False)
        self.enableLabelTool(self.pauseTool, False)

        # Bind Toolbar Items
        self.Bind(wx.EVT_TOOL, self.onPlayToolClicked, self.playTool)
        self.Bind(wx.EVT_TOOL, self.onStopToolClicked, self.stopTool)
        self.Bind(wx.EVT_TOOL, self.onPauseToolClicked, self.pauseTool)

        self.scrollPanel = wx.lib.scrolledpanel.ScrolledPanel(self._panel, size=(-1, -1))
        self.scrollPanel.SetupScrolling(scroll_x=False, scrollIntoView=False)
        self.scrollPanel.SetAutoLayout(1)

        self.controls = ExpandableControl(self.scrollPanel)

        self.controls.addPanel('scan_parameters', ScanParameters(self.controls))
        self.controls.addPanel('rotating_platform', RotatingPlatform(self.controls))
        self.controls.addPanel('point_cloud_roi', PointCloudROI(self.controls))
        self.controls.addPanel('point_cloud_color', PointCloudColor(self.controls))

        self.splitterWindow = wx.SplitterWindow(self._panel)

        self.videoView = VideoView(self.splitterWindow, self.get_image, 10)
        self.videoView.SetBackgroundColour(wx.BLACK)

        self.scenePanel = wx.Panel(self.splitterWindow)
        self.sceneView = SceneView(self.scenePanel)
        self.gauge = wx.Gauge(self.scenePanel, size=(-1, 30))
        self.gauge.Hide()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.sceneView, 1, wx.ALL | wx.EXPAND, 0)
        vbox.Add(self.gauge, 0, wx.ALL | wx.EXPAND, 0)
        self.scenePanel.SetSizer(vbox)

        self.splitterWindow.SplitVertically(self.videoView, self.scenePanel)
        self.splitterWindow.SetMinimumPaneSize(200)

        # Layout
        vsbox = wx.BoxSizer(wx.VERTICAL)
        vsbox.Add(self.controls, 0, wx.ALL | wx.EXPAND, 0)
        self.scrollPanel.SetSizer(vsbox)
        vsbox.Fit(self.scrollPanel)
        self.scrollPanel.SetMinSize((self.scrollPanel.GetSize()[0], -1))

        self.controls.initPanels()

        self.addToPanel(self.scrollPanel, 0)
        self.addToPanel(self.splitterWindow, 1)

        # Video View Selector
        _choices = []
        choices = profile.settings.getPossibleValues('video_scanning')
        for i in choices:
            _choices.append(_(i))
        self.videoViewsDict = dict(zip(_choices, choices))

        self.buttonShowVideoViews = wx.BitmapButton(self.videoView, wx.NewId(), wx.Bitmap(
            resources.getPathForImage("views.png"), wx.BITMAP_TYPE_ANY), (10, 10))
        self.comboVideoViews = wx.ComboBox(self.videoView,
                                           value=_(profile.settings['video_scanning']),
                                           choices=_choices, style=wx.CB_READONLY, pos=(60, 10))

        self.buttonShowVideoViews.Hide()
        self.comboVideoViews.Hide()

        self.buttonShowVideoViews.Bind(wx.EVT_BUTTON, self.onShowVideoViews)
        self.comboVideoViews.Bind(wx.EVT_COMBOBOX, self.onComboBoVideoViewsSelect)

        self.pointCloudTimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onPointCloudTimer, self.pointCloudTimer)

        self.updateCallbacks()
        self.Layout()

    def updateCallbacks(self):
        self.controls.updateCallbacks()

    def enableRestore(self, value):
        self.controls.enableRestore(value)

    def onShow(self, event):
        if event.GetShow():
            self.updateStatus(self.driver.is_connected)
            self.pointCloudTimer.Stop()
        else:
            try:
                self.pointCloudTimer.Stop()
                self.videoView.stop()
            except:
                pass

    def onShowVideoViews(self, event):
        self.showVideoViews = not self.showVideoViews
        if self.showVideoViews:
            self.comboVideoViews.Show()
        else:
            self.comboVideoViews.Hide()

    def onComboBoVideoViewsSelect(self, event):
        value = self.videoViewsDict[self.comboVideoViews.GetValue()]
        self.current_video.mode = value
        profile.settings['video_scanning'] = value

    def get_image(self):
        if self.scanning:
            self.image_capture.stream = False
            return self.current_video.capture()
        else:
            self.image_capture.stream = True
            image = self.image_capture.capture_texture()
            if profile.settings['video_scanning']:
                image = self.point_cloud_roi.draw_roi(image)
            return image

    def onPointCloudTimer(self, event):
        p, r = self.ciclop_scan.get_progress()
        self.gauge.SetRange(r)
        self.gauge.SetValue(p)
        pointCloud = self.ciclop_scan.get_point_cloud_increment()
        if pointCloud is not None:
            if pointCloud[0] is not None and pointCloud[1] is not None:
                if len(pointCloud[0]) > 0:
                    pointCloud = self.point_cloud_roi.mask_point_cloud(*pointCloud)
                    self.sceneView.appendPointCloud(pointCloud[0], pointCloud[1])

    def onPlayToolClicked(self, event):
        if self.ciclop_scan._inactive:
            # Resume
            self.enableLabelTool(self.pauseTool, True)
            self.enableLabelTool(self.playTool, False)
            self.ciclop_scan.resume()
            self.pointCloudTimer.Start(milliseconds=50)
        else:
            result = True
            if self.sceneView._object is not None:
                dlg = wx.MessageDialog(self,
                                       _("Your current model will be erased.\n"
                                         "Do you really want to do it?"),
                                       _("Clear Point Cloud"), wx.YES_NO | wx.ICON_QUESTION)
                result = dlg.ShowModal() == wx.ID_YES
                dlg.Destroy()
            if result:
                self.gauge.SetValue(0)
                self.gauge.Show()
                self.scenePanel.Layout()
                self.Layout()
                self.ciclop_scan.set_callbacks(self.beforeScan,
                                               None, lambda r: wx.CallAfter(self.afterScan, r))
                self.ciclop_scan.start()

    def beforeScan(self):
        self.scanning = True
        self.buttonShowVideoViews.Show()
        self.enableLabelTool(self.disconnectTool, False)
        self.enableLabelTool(self.playTool, False)
        self.enableLabelTool(self.stopTool, True)
        self.enableLabelTool(self.pauseTool, True)
        self.sceneView.createDefaultObject()
        self.sceneView.setShowDeleteMenu(False)
        self.videoView.setMilliseconds(200)
        self.combo.Disable()
        self.GetParent().menuFile.Enable(self.GetParent().menuLaunchWizard.GetId(), False)
        self.GetParent().menuFile.Enable(self.GetParent().menuLoadModel.GetId(), False)
        self.GetParent().menuFile.Enable(self.GetParent().menuSaveModel.GetId(), False)
        self.GetParent().menuFile.Enable(self.GetParent().menuClearModel.GetId(), False)
        self.GetParent().menuFile.Enable(self.GetParent().menuOpenCalibrationProfile.GetId(), False)
        self.GetParent().menuFile.Enable(self.GetParent().menuSaveCalibrationProfile.GetId(), False)
        self.GetParent().menuFile.Enable(self.GetParent().menuResetCalibrationProfile.GetId(), False)
        self.GetParent().menuFile.Enable(self.GetParent().menuOpenScanProfile.GetId(), False)
        self.GetParent().menuFile.Enable(self.GetParent().menuSaveScanProfile.GetId(), False)
        self.GetParent().menuFile.Enable(self.GetParent().menuResetScanProfile.GetId(), False)
        self.GetParent().menuFile.Enable(self.GetParent().menuExit.GetId(), False)
        self.GetParent().menuEdit.Enable(self.GetParent().menuPreferences.GetId(), False)
        self.GetParent().menuHelp.Enable(self.GetParent().menuWelcome.GetId(), False)
        panel = self.controls.panels['rotating_platform']
        section = panel.sections['rotating_platform']
        section.disable('motor_speed_scanning')
        section.disable('motor_acceleration_scanning')
        self.enableRestore(False)
        self.pointCloudTimer.Start(milliseconds=50)

    def afterScan(self, response):
        ret, result = response
        if ret:
            dlg = wx.MessageDialog(self,
                                   _("Scanning has finished. If you want to save your "
                                     "point cloud go to File > Save Model"),
                                   _("Scanning finished!"), wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            self.scanning = False
            self.onScanFinished()

    def onStopToolClicked(self, event):
        paused = self.ciclop_scan._inactive
        self.ciclop_scan.pause()
        dlg = wx.MessageDialog(self,
                               _("Your current scanning will be stopped.\n"
                                 "Do you really want to do it?"),
                               _("Stop Scanning"), wx.YES_NO | wx.ICON_QUESTION)
        result = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()

        if result:
            self.scanning = False
            self.ciclop_scan.stop()
            self.onScanFinished()
        else:
            if not paused:
                self.ciclop_scan.resume()

    def onScanFinished(self):
        self.buttonShowVideoViews.Hide()
        self.comboVideoViews.Hide()
        self.enableLabelTool(self.disconnectTool, True)
        self.enableLabelTool(self.playTool, True)
        self.enableLabelTool(self.stopTool, False)
        self.enableLabelTool(self.pauseTool, False)
        self.sceneView.setShowDeleteMenu(True)
        self.combo.Enable()
        self.GetParent().menuFile.Enable(self.GetParent().menuLaunchWizard.GetId(), True)
        self.GetParent().menuFile.Enable(self.GetParent().menuLoadModel.GetId(), True)
        self.GetParent().menuFile.Enable(self.GetParent().menuSaveModel.GetId(), True)
        self.GetParent().menuFile.Enable(self.GetParent().menuClearModel.GetId(), True)
        self.GetParent().menuFile.Enable(self.GetParent().menuOpenCalibrationProfile.GetId(), True)
        self.GetParent().menuFile.Enable(self.GetParent().menuSaveCalibrationProfile.GetId(), True)
        self.GetParent().menuFile.Enable(self.GetParent().menuResetCalibrationProfile.GetId(), True)
        self.GetParent().menuFile.Enable(self.GetParent().menuOpenScanProfile.GetId(), True)
        self.GetParent().menuFile.Enable(self.GetParent().menuSaveScanProfile.GetId(), True)
        self.GetParent().menuFile.Enable(self.GetParent().menuResetScanProfile.GetId(), True)
        self.GetParent().menuFile.Enable(self.GetParent().menuExit.GetId(), True)
        self.GetParent().menuEdit.Enable(self.GetParent().menuPreferences.GetId(), True)
        self.GetParent().menuHelp.Enable(self.GetParent().menuWelcome.GetId(), True)
        panel = self.controls.panels['rotating_platform']
        section = panel.sections['rotating_platform']
        section.enable('motor_speed_scanning')
        section.enable('motor_acceleration_scanning')
        self.enableRestore(True)
        self.pointCloudTimer.Stop()
        self.videoView.setMilliseconds(10)
        self.gauge.SetValue(0)
        self.gauge.Hide()
        self.scenePanel.Layout()
        self.Layout()

    def onPauseToolClicked(self, event):
        self.enableLabelTool(self.pauseTool, False)
        self.enableLabelTool(self.playTool, True)
        self.ciclop_scan.pause()
        self.pointCloudTimer.Stop()

    def updateToolbarStatus(self, status):
        if status:
            if self.IsShown():
                self.videoView.play()
            self.enableLabelTool(self.playTool, True)
            self.enableLabelTool(self.stopTool, False)
            self.enableLabelTool(self.pauseTool, False)
            self.controls.enableContent()
        else:
            self.videoView.stop()
            self.enableLabelTool(self.playTool, False)
            self.enableLabelTool(self.stopTool, False)
            self.enableLabelTool(self.pauseTool, False)
            self.controls.disableContent()

    def updateProfileToAllControls(self):
        self.controls.updateProfile()
