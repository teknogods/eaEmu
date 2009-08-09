from twisted.web.server import Site
from twisted.web.resource import Resource

# generate the classes with 'wsdl2py -wb http://redalert3pc.sake.gamespy.com/SakeStorageServer/StorageServer.asmx?WSDL'
from StorageServer_server import *
from StorageServer_server import StorageServer as StorageServerBase
class StorageServer(StorageServerBase):
   def soap_SearchForRecords(self, ps, **kw):
      #TODO: write helpers that will covert dict+lists into these calls
      request = ps.Parse(SearchForRecordsSoapIn.typecode)
      logging.getLogger('gamespy.sake').debug(request.__dict__)
      logging.getLogger('gamespy.sake').debug(request._ownerids.__dict__)
      logging.getLogger('gamespy.sake').debug(request._fields.__dict__)
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
      logging.getLogger('gamespy.sake').debug(response)
      r = StorageServerBase._writeResponse(self, response, request, status)
      return r
   
class SakeServer(Site):
   def __init__(self):
      root = Resource()
      sakeStorageServer = Resource()
      root.putChild('SakeStorageServer', sakeStorageServer)
      sakeStorageServer.putChild('StorageServer.asmx', StorageServer())
      Site.__init__(self, root)

