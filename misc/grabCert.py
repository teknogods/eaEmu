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
   return ''.join(map(chr, con.session.serverCertChain.x509List[0].writeBytes())))

def main(argv=None):
   argv = argv or sys.argv

   if len(argv) != 3:
      print('need serv and port as args', file=sys.stderr)
      return 1

   host, port = argv[1], int(argv[2])
   open('%s-%s.cer' % (host, port),'wb').write(getCert(host, port))

if __name__ == '__main__':
   sys.exit(main())
