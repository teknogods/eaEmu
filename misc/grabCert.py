#!/usr/bin/python
# Install python-tlslite in debian/ubuntu before using.
# Inspect the written cert with e.g.:
#   openssl x509 -noout -text -inform DER -in thecertfile.cer
from __future__ import print_function
import tlslite.TLSConnection
from tlslite.HandshakeSettings import HandshakeSettings
from socket import *
import sys

def getCert(host, port):
   settings = HandshakeSettings()
   settings.minKeySize = 512

   sock = socket(AF_INET, SOCK_STREAM)
   sock.connect((host, port))
   con = tlslite.TLSConnection.TLSConnection(sock)

   con.handshakeClientCert(settings=settings)
   return con.session.serverCertChain.x509List[0].writeBytes().tostring()

def main(argv=None):
   argv = argv or sys.argv

   if len(argv) != 3:
      print('Need serv and port as args', file=sys.stderr)
      return 1

   host, port = argv[1], int(argv[2])
   certFile = '{host}-{port}.cer'.format(**locals())
   data = getCert(host, port)
   print('Writing cert to: {0}'.format(certFile))
   open(certFile,'wb').write(data)

if __name__ == '__main__':
   sys.exit(main())
