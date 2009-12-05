import sys

from twisted.application.service import MultiService

from twisted.internet import wxreactor
wxreactor.install()

import wx
from wxServerManager import *

class ServerManagerFrameImpl(ServerManagerFrame):
   def __init__(self, *args, **kw):
      super(self.__class__, self).__init__(*args, **kw)
      
      #self.hostsDialog = HostsDialogImpl(self)
      
      #servers = dict([((gethostbyname(k[0]), k[1]), v) for k, v in servers.iteritems()])
      
      # TODO?: make this Service a serialized Application then load from XML
      self.services = MultiService()
      for klass, addresses in servers.iteritems():
         module, klass = klass.rsplit('.', 1)
         self.services.addService(__import__(module).__dict__[klass](addresses))
      
      # setup log window
      class Redirect(object):
         def write(inner, *args, **kw):
            self.text_ctrl_log.AppendText(args[0])
         def flush(self, *args, **kw): pass
      log.startLogging(Redirect())
         
   def isValidClick(self, button, other):
      if other.GetValue():
         button.SetValue(True)
         other.SetValue(False)
         return True
      else:
         button.SetValue(not button.GetValue())
         return False

   def StartServer(self, event):
      # NOTE: button is already flipped by the time we get here
      button = self.button_start
      other = self.button_stop
      if not self.isValidClick(button, other):
         return
      self.services.startService()

   def StopServer(self, event):
      # NOTE: button is already flipped by the time we get here
      button = self.button_stop
      other = self.button_start
      if not self.isValidClick(button, other):
         return
      self.services.stopService()
   
   def OnHostsButton(self, event):
      self.hostsDialog.Show(not self.hostsDialog.IsShown())
      
class HostsDialogImpl(HostsDialog):
   #TODO:   # tri-state group checkboxes.
   # save IP address by looking up first or adding 'teknohost' entry
   # remove or activate enable/disable buttons
   # Get exceptions dialog working!! maybe make bugreport form too
   hostsPath = r'C:\Windows\System32\drivers\etc\hosts'
   def __init__(self, *args, **kw):
      super(self.__class__, self).__init__(*args, **kw)
      
      # unset readonly flag on hosts file if unwriteable
      if not os.access(self.hostsPath, os.W_OK):
         os.chmod(self.hostsPath, 0777)
      
      # groupSelections is a mapping of groupname to list of indexes that are
      # currently selected.
      self.groupSelections = {}
      # set selections to what's already in hosts file
      for k in servers:
         self.groupSelections[k] = [i for i in range(len(servers[k])) if self.IsEntryInHosts(servers[k][i][0])]
         
      # populate groups list, check those that have all entries in hosts file already
      for i, (k, v) in enumerate(servers.iteritems()):
         self.list_box_groups.Append(k)
         if len(self.groupSelections[k]) == len(v):
            self.list_box_groups.Check(i, True)
         
      self.Bind(wx.EVT_CHECKLISTBOX, self.OnGroupCheck, self.list_box_groups)
      self.Bind(wx.EVT_CHECKLISTBOX, self.OnHostCheck, self.list_box_hosts)
   
   def IsEntryInHosts(self, host):
      '''
      Checks for the presence of an entry in the hosts file
      for the provided host.
      '''
      with open(self.hostsPath, 'rb') as f:
         data = f.read()
         return not not re.search('^\s*[\d.]+\s+{0}'.format(host), data, re.M)
         
   def OnGroupClick(self, event):
      self.list_box_hosts.Clear()
      self.list_box_hosts.AppendItems([v[0] for v in servers[self.list_box_groups.GetStringSelection()]])
      
      for x in self.groupSelections[self.list_box_groups.GetStringSelection()]:
         self.list_box_hosts.Check(x, True)

   def OnGroupCheck(self, event):
      # simulate a group click as well
      self.list_box_groups.SetSelection(event.GetSelection())
      self.OnGroupClick(event)
      
      #enable or disable all hosts in that group
      for i, item in enumerate(self.list_box_hosts.GetItems()):
         #if event.IsChecked(): #doesnt work!!?
         if self.list_box_groups.IsChecked(event.GetSelection()):
            self.EnableHost(i)
         else:
            self.DisableHost(i)
      
      #FIXME: selections all messed up, TODO: implement actual hosts writing.
      # remember to turn off readonly file attribute!
   
   def OnHostCheck(self, event):
      # event.IsChecked() doesn't seem to be correct
      # so using instead self.list_box_hosts.IsChecked(event.GetSelection())
      if self.list_box_hosts.IsChecked(event.GetSelection()):
         self.EnableHost(event.GetSelection())
      else:
         self.DisableHost(event.GetSelection())
   
   def EnableHost(self, index):
      sel = self.groupSelections[self.list_box_groups.GetStringSelection()]
      if index not in sel:
         sel.append(index)
      self.list_box_hosts.Check(index, True)
      with open(self.hostsPath, 'rb+') as f:
         data = f.read()
         for host in [self.list_box_hosts.GetString(x) for x in sel]:
            line = r'{0} {1}'.format(self.text_ctrl_ip.GetValue(), host)
            data, num = re.subn(r'(#*[\d.]+\s+)({0})'.format(host), line, data)
            if num < 1:
               data = data + line + '\r\n'
         f.seek(0, 0)
         f.truncate()
         f.write(data)
      
   def DisableHost(self, index):
      sel = self.groupSelections[self.list_box_groups.GetStringSelection()]
      if index in sel:
         sel.remove(index)
      self.list_box_hosts.Check(index, False)
      notsel = [x for x in range(len(self.list_box_hosts.GetItems())) if x not in sel]
      with open(self.hostsPath, 'rb+') as f:
         data = f.read()
         for host in [self.list_box_hosts.GetString(x) for x in notsel]:
            data, num = re.subn('(#*[\d.]+\s+)({0})\r\n'.format(host), '', data)
         f.seek(0, 0)
         f.truncate()
         f.write(data)

def exceptionHandler(type, value, tb):
   #FIXME: always getting null exceptions?!
   msg = traceback.format_exc()
   wx.MessageBox(msg)
   print msg
sys.excepthook = exceptionHandler

def main(argv=None):
   argv = argv or sys.argv
   
   app = wx.PySimpleApp(0)
   wx.InitAllImageHandlers()
   frame_main = ServerManagerFrameImpl(None, -1, "")
   app.SetTopWindow(frame_main)
   frame_main.Show()
   reactor.registerWxApp(app)
   reactor.run()
