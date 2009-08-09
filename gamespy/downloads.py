from twisted.web.server import Site


# It's pretty awesome how simple this is...
class DownloadsServerFactory(Site):
   def __init__(self):
      Site.__init__(self, File('.'))
