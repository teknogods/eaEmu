from _winreg import *
from win32api import *
import os
import re
from decimal import Decimal
from mmap import *
import os
import base64
import traceback
import struct

def getRa3():
   regKey = r'Software\Electronic Arts\Electronic Arts\Red Alert 3'
   regVal = 'Install Dir'
   path = RegQueryValueEx(RegOpenKey(HKEY_LOCAL_MACHINE, regKey), regVal)[0]
   pat = r'ra3_1.(\d+).game$'
   dataDir = os.path.join(path, 'Data')
   return os.path.join(dataDir, 'ra3_1.{0}.game'.format(sorted([Decimal(re.match(pat, x).group(1)) for x in os.listdir(dataDir) if re.match(pat, x)])[-1]))

def getMercs2():
   regKey = r'Software\EA Games\Mercenaries 2 World in Flames'
   regVal = 'Install Dir'
   return os.join.path(RegQueryValueEx(RegOpenKey(HKEY_LOCAL_MACHINE, regKey), regVal)[0], 'Mercenaries2.exe')

def main():
   try:

      #gameExe = getMercs2()
      gameExe = getRa3()




      try:
         hnd = os.open(gameExe, os.O_RDWR)
      except:
         gameExe = raw_input('Could not open "%s", provide the path to the exe:' % gameExe)
         hnd = os.open(gameExe, os.O_RDWR)
      gameFile = mmap(hnd, 0)
      oldKey = base64.b16decode('9275A15B080240B89B402FD59C71C4515871D8F02D937FD30C8B1C7DF92A0486F190D1310ACBD8D41412903B356A0651494CC575EE0A462980F0D53A51BA5D6A1937334368252DFEDF9526367C4364F156170EF167D5695420FB3A55935DD497BC3AD58FD244C59AFFCD0C31DB9D947CA66666FB4BA75EF8644E28B1A6B87395')
      newKey = base64.b16decode('DA02D380D0AB67886D2B11177EFF4F1FBA80A3070E8F036DEE9DC0F30BF8B80516164DC0D4827F47A48A3BCA129DD29D1961D8566147A588DC248F90C9A41CBFF857E02F47782EAE5A70E555BADD36E16C179331E4F92203816998C82EDFBE0E339DC3E0C0208552CD3F05F5CB412F6710916AD159DAC1233E71089F20D43D6D')
      
      dom = '.ea.com\0'
      subDom = '.fesl\0'
      #ip = '127.0.0.1'
      ip = '5.84.34.44'
      p1 = ip.split('.')[0]
      p2 = ip.split('.')[1]
      p3 = ip.split('.', 2)[-1]
      patches = [
                 (oldKey, newKey),
                 #(dom+subDom, struct.pack('{0}s{1}s'.format(len(dom), len(subDom)), '.'+p3, '.'+p2)),
                 #('cncra3-pc\0', '{0}'.format(p1)),
                 
                 # MERCS2 is broken -- patch works but then first octet gets sent as "clientString" value and client
                 # dc's self.
                 # There are two instances of "mercs2-pc"; the second is the right one and has a null before it
                 #('\0mercs2-pc', '\0{0}\0'.format(p1)),
                 
                ]
      for srch, repl in patches:
         gameFile.seek(0, 0)
         pos = gameFile.find(srch)
         if pos >= 0:
            gameFile.seek(pos, 0)
            gameFile.write(repl)
         else:
            print 'Patching failed. String could not be found in game file.'
      print 'Done processing %s.' % gameExe
      os.close(hnd)
   except:
      traceback.print_exc()
   raw_input('Press enter to exit...')

if __name__ == '__main__':
   main()
