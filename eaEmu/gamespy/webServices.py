from __future__ import absolute_import

from ..util import aspects, getLogger

import warnings
with warnings.catch_warnings():
   warnings.simplefilter('ignore')
   # generate the classes with 'wsdl2py -wb http://redalert3pc.sake.gamespy.com/SakeStorageServer/StorageServer.asmx?WSDL'
   from .soap.StorageServer_server import *
   from .soap.AuthService_server import *
   from .soap.CompetitionService_server import *
StorageServerBase = StorageServer
AuthServiceBase = AuthService
CompetitionServiceBase = CompetitionService

from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.web.static import File
from twisted.web.error import NoResource

import re

class StorageServer(StorageServerBase):
   def soap_SearchForRecords(self, ps, **kw):
      #TODO: write helpers that will covert dict+lists into these calls
      request = ps.Parse(SearchForRecordsSoapIn.typecode)
      getLogger('gamespy.web.SakeStorage').debug(request.__dict__)
      getLogger('gamespy.web.SakeStorage').debug(request._ownerids.__dict__)
      getLogger('gamespy.web.SakeStorage').debug(request._fields.__dict__)
      result = SearchForRecordsSoapOut()
      result.SearchForRecordsResult = 'Success'
      result.Values = result.new_values()
      # TODO - return real vals. null just skips to login ;)
      # -- find out how to return null element... <value />
      '''
      result.Values.ArrayOfRecordValue = [result.Values.new_ArrayOfRecordValue()]
      result.Values.ArrayOfRecordValue[0].RecordValue = []
      for val in [1, 2, 2, 5]:
         container = result.Values.ArrayOfRecordValue[0].new_RecordValue()
         container.ShortValue = container.new_shortValue()
         container.ShortValue.Value = val
         result.Values.ArrayOfRecordValue[0].RecordValue.append(container)
      '''
      return request, result

   def _writeResponse(self, response, request, status=200):
      #response = response.replace('<SOAP-ENV:Header></SOAP-ENV:Header>', '')
      #response = response.replace('<ns1:values></ns1:values>', '<ns1:values />')
      #response = '<?xml version="1.0" encoding="utf-8"?>' + response
      getLogger('gamespy.web.sake').debug(response)
      r = StorageServerBase._writeResponse(self, response, request, status)
      return r

class AuthService(AuthServiceBase):
   def soap_LoginRemoteAuth(self, ps, **kw):
      request = ps.Parse(LoginRemoteAuthSoapIn.typecode)
      getLogger('gamespy.web.AuthService').debug(request.__dict__)
      result = LoginRemoteAuthSoapOut()
      result.LoginRemoteAuthResult = result.new_LoginRemoteAuthResult()
      result.LoginRemoteAuthResult.ResponseCode = 0
      result.LoginRemoteAuthResult.Certificate = result.LoginRemoteAuthResult.new_certificate()
      result.LoginRemoteAuthResult.Certificate.Length = 303
      result.LoginRemoteAuthResult.Certificate.Version = request.Version
      result.LoginRemoteAuthResult.Certificate.Partnercode = request.Partnercode
      result.LoginRemoteAuthResult.Certificate.Namespaceid = request.Namespaceid
      result.LoginRemoteAuthResult.Certificate.Userid =  '11111' # TODO
      result.LoginRemoteAuthResult.Certificate.Profileid = '22222' # TODO
      result.LoginRemoteAuthResult.Certificate.Expiretime = 0
      result.LoginRemoteAuthResult.Certificate.Profilenick = 'Jackalus'
      result.LoginRemoteAuthResult.Certificate.Uniquenick = 'Jackalus'
      result.LoginRemoteAuthResult.Certificate.Cdkeyhash = None
      result.LoginRemoteAuthResult.Certificate.Peerkeymodulus = '95375465E3FAC4900FC912E7B30EF7171B0546DF4D185DB04F21C79153CE091859DF2EBDDFE5047D80C2EF86A2169B05A933AE2EAB2962F7B32CFE3CB0C25E7E3A26BB6534C9CF19640F1143735BD0CEAA7AA88CD64ACEC6EEB037007567F1EC51D00C1D2F1FFCFECB5300C93D6D6A50C1E3BDF495FC17601794E5655C476819' #256 chars
      result.LoginRemoteAuthResult.Certificate.Peerkeyexponent = '010001'
      result.LoginRemoteAuthResult.Certificate.Serverdata = '908EA21B9109C45591A1A011BF84A18940D22E032601A1B2DD235E278A9EF131404E6B07F7E2BE8BF4A658E2CB2DDE27E09354B7127C8A05D10BB4298837F96518CCB412497BE01ABA8969F9F46D23EBDE7CC9BE6268F0E6ED8209AD79727BC8E0274F6725A67CAB91AC87022E5871040BF856E541A76BB57C07F4B9BE4C6316' #256 chars
      result.LoginRemoteAuthResult.Certificate.Signature = '181A4E679AC27D83543CECB8E1398243113EF6322D630923C6CD26860F265FC031C2C61D4F9D86046C07BBBF9CF86894903BD867E3CB59A0D9EFDADCB34A7FB3CC8BC7650B48E8913D327C38BB31E0EEB06E1FC1ACA2CFC52569BE8C48840627783D7FFC4A506B1D23A1C4AEAF12724DEB12B5036E0189E48A0FCB2832E1FB00' #256 chars
      result.LoginRemoteAuthResult.Certificate.Timestamp = 'U3VuZGF5LCBPY3RvYmVyIDE4LCAyMDA5IDE6MTk6NTMgQU0='

      result.LoginRemoteAuthResult.Peerkeyprivate = '8818DA2AC0E0956E0C67CA8D785CFAF3A11A9404D1ED9A6E580EA8569E087B75316B85D77B2208916BE2E0D37C7D7FD18EFD6B2E77C11CDA6E1B689BF460A40BBAF861D800497822004880024B4E7F98A020B1896F536D7219E67AB24B17D60A7BDD7D42E3501BB2FA50BB071EF7A80F29870FFD7C409C0B7BB7A8F70489D04D'

      return request, result

class CompetitionService(CompetitionServiceBase):
   def soap_SetReportIntention(self, ps, **kw):
      request = ps.Parse(SetRemoteIntentionSoapIn.typecode)
      getLogger('gamespy.web.CompetitionService').debug(request.__dict__)
      result = SetReportIntentionSoapOut()
      result.SetReportIntentionResult = result.new_SetReportIntentionResult()
      result.SetReportIntentionResult.Result = 0
      result.SetReportIntentionResult.Message = None
      result.SetReportIntentionResult.Csid = 'c0788b6f-d126-4ccc-9c5f-cebc129c1f9d'
      result.SetReportIntentionResult.Ccid = '28e99a35-1564-4b33-b253-35adf67f4242'

      return request, result

class VirtualFile(File):
   _virtualLinks = {
      ## map all patchinfos to current.patchinfo
      re.compile(r'(?P<game>.*)_(?P<lang>.*)_(?P<version>.*)\.patchinfo') : 'current.patchinfo',
      ## map all motd to english
      re.compile(r'MOTD-(?P<lang>.*).txt') : 'MOTD-english.txt',
   }
   def getChild(self, path, request):
      resource = File.getChild(self, path, request)
      for pat, repl in self._virtualLinks.iteritems():
         newPath = pat.sub(repl, path)
         if newPath != path:
            resource = File.getChild(self, newPath, request)
            break
      return resource

class WebServer(Site):
   def __init__(self):
      root = Resource()

      ## downloads server -- client grabs patch info from here
      root.putChild('u', VirtualFile('webRoot/downloads/u'))

      ## MOST OF THE BELOW DONT WORK SO ARE COMMENTED OUT

      ## redalert3pc.sake.gamespy.com
      sakeStorageServer = Resource()
      sakeStorageServer.putChild('StorageServer.asmx', StorageServer())
      #root.putChild('SakeStorageServer', sakeStorageServer)

      ## redalert3pc.auth.pubsvs.gamespy.com -- used to auth before reporting results
      authService = Resource()
      authService.putChild('AuthService.asmx', AuthService())
      #root.putChild('AuthService', authService)

      ## redalert3pc.comp.pubsvs.gamespy.com -- used to report match results
      compSvc = Resource()
      compSvc.putChild('competitionservice.asmx', CompetitionService())
      #compSvc.putChild('CompetitionService.asmx', CompetitionService())
      root.putChild('competitionservice', compSvc)
      #root.putChild('CompetitionService', compSvc)

      ## TODO: psweb.gamespy.com -- SOAP service that serves Clan-related requests
      ## TODO: redalert3services.gamespy.com -- HTTP GET requests that serve rank icons
      ## /GetPlayerRankIcon.aspx?gp=fgErop[sap9faZeJJELRac__&pid=<pid of player> retrieves that player's rank icon
      ## /GetPlayerLadderRatings.aspx?gp=fgErop[sap9faZeJJELRac__ retrieves CSV of ladder ratings


      Site.__init__(self, root)

