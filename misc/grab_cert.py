import tlslite.TLSConnection
from tlslite.HandshakeSettings import HandshakeSettings
from socket import *

settings = HandshakeSettings()
settings.minKeySize = 512

sock = socket(AF_INET, SOCK_STREAM)
sock.connect(('pcburnout08.ea.com', 21841))
con = tlslite.TLSConnection.TLSConnection(sock)

con.handshakeClientCert(settings=settings)

open('pcburnout08.cer','wb').write(''.join(map(chr, con.session.serverCertChain.x509List[0].writeBytes())))
