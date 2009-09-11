from OpenSSL.crypto import *

cert = load_certificate(FILETYPE_ASN1, open('fesl.cer', 'rb').read())

myCert = load_certificate(FILETYPE_ASN1, open('ra3.cer', 'rb').read())
pub = myCert.get_pubkey()
#print dump_privatekey(FILETYPE_ASN1, pub)

priv = load_privatekey(FILETYPE_PEM, open('ra3.key', 'rb').read())

cert.set_pubkey(pub)
cert.sign(priv, 'md5')
open('forged.cer', 'wb').write(dump_certificate(FILETYPE_ASN1, cert))
