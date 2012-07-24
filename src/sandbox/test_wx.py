# border.py

import wx

ID_NEW = 1
ID_RENAME = 2
ID_CLEAR = 3
ID_DELETE = 4

class Example(wx.Frame):
  
    def __init__(self, parent, title):
        super(Example, self).__init__(parent, title=title, 
            size=(260, 180))
            
        self.InitUI()
        self.Centre()
        self.Show()     
        
    def InitUI(self):
    
        panel = wx.Panel(self)

        panel.SetBackgroundColour('#4f5049')
        #hbox = wx.BoxSizer(wx.HORIZONTAL)

        #vbox = wx.BoxSizer(wx.VERTICAL)

        lbox = wx.BoxSizer(wx.VERTICAL)

        listbox = wx.ListBox(panel, -1, size=(100,50))


        #add button panel and its sizer
        btnPanel  = wx.Panel(panel, -1, size= (30,30))
        bbox = wx.BoxSizer(wx.HORIZONTAL)
        new       = wx.Button(btnPanel, ID_NEW, '+', size=(24, 24))
        ren       = wx.Button(btnPanel, ID_RENAME, '-', size=(24, 24))
        #dlt = wx.Button(btnPanel, ID_DELETE, 'D', size=(30, 30))
        #clr = wx.Button(btnPanel, ID_CLEAR, 'C', size=(30, 30))

        #hbox5 = wx.BoxSizer(wx.HORIZONTAL)
        #btn1 = wx.Button(panel, label='Ok', size=(70, 30))
        #hbox5.Add(btn1)
        #btn2 = wx.Button(panel, label='Close', size=(70, 30))
        #hbox5.Add(btn2, flag=wx.LEFT|wx.BOTTOM, border=5)
        #vbox.Add(hbox5, flag=wx.ALIGN_RIGHT|wx.RIGHT, border=10)

        #self.Bind(wx.EVT_BUTTON, self.NewItem, id=ID_NEW)
        #self.Bind(wx.EVT_BUTTON, self.OnRename, id=ID_RENAME)
        #self.Bind(wx.EVT_BUTTON, self.OnDelete, id=ID_DELETE)
        #self.Bind(wx.EVT_BUTTON, self.OnClear, id=ID_CLEAR)
        #self.Bind(wx.EVT_LISTBOX_DCLICK, self.OnRename)

        bbox.Add(new, flag= wx.LEFT, border=2)
        bbox.Add(ren, flag= wx.LEFT, border=2)
        #buttonbox.Add(dlt)
        #buttonbox.Add(clr)

        btnPanel.SetSizer(bbox)
        lbox.Add(listbox, 1, wx.EXPAND | wx.ALL, 1)
        lbox.Add(btnPanel, 0, wx.EXPAND | wx.ALL, 1)
        #lbox.Add(buttonbox, 1, wx.EXPAND | wx.ALL, 1)

        #hbox.Add(lbox, 1, wx.EXPAND | wx.ALL, 7)

        #midPan = wx.Panel(panel)
        #midPan.SetBackgroundColour('#ededed')

        #midPan1 = wx.Panel(panel)
        #midPan1.SetBackgroundColour('#ededed')

        #vbox.Add(midPan, 1, wx.EXPAND | wx.ALL, 5)
        #vbox.Add(midPan1, 1, wx.EXPAND | wx.ALL, 5)

        #hbox.Add(vbox, 1,  wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(lbox)


if __name__ == '__main__':
  
    app = wx.App()
    Example(None, title='Gmvault-test')
    app.MainLoop()
