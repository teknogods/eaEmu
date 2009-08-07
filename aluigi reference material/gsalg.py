#################################################################################
## GameSpy PYTHON Masterserver Class v1.0
##
## Written by:
##  Thomas Reiser alias FiRe^
##  <www.mg34.net/code - fire_1@gmx.de>
##
## Orginal code by:
##  Luigi Auriemma
##  <aluigi.altervista.org - aluigi@autistici.org> 
##
## GPL LICENSE:
##  This program is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program; if not, write to the Free Software
##  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
##
##  http://www.gnu.org/licenses/gpl.txt
##
## NOTE:
##  The GPL requires you the release your project's source code with the
##  compiled stuff!
#################################################################################

import socket
import string
import select

class GameSpy_Master:
    def __init__(self, host='master.gamespy.com', port=28900):
        self.addr = (host, port)
    
    
    def GetServers(self, gamename, handoff, filter=''):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(self.addr)
        except:
            return False

        secure = sock.recv(32)
        print secure
        secure = string.split(secure[1:-1], '\\', 3)[3]

        validate = self._MakeValidate(secure, handoff)
        if validate == False:
            return False

        sock.send('\\gamename\\%s\\enctype\\0\\validate\\%s\\final\\\\queryid\\1.1' \
                  '\\list\\cmp\\gamename\\%s\\where\\%s\\final\\' % \
                  (gamename, validate, gamename, filter))

        servers = ''
        while select.select([sock], [], [], 1)[0]:
            data = sock.recv(2048)
            if data == '':
                break
            elif string.find(data, '\\final\\') >= 0:
                break
            else:
                servers += data

        sock.close()

        if servers == '':
            return False
        elif servers == '\\final\\':
            return []
        else:
            servers = string.replace(servers, '\\final\\', '')

        return self._ParseCompressedIPs(servers)
    

    def _MakeValidate(self, secure, handoff):
        if len(secure) < 6:
            return False
        
        length = len(handoff)
        if length == 6:
            hoMax = 6
            start = 0
            jump = 1
        elif (length >= 13) or (length > 6 and length < 13):
            hoMax = 13
            start = 2
            jump = 2
        else:
            return False

        gamekey = {}
        j = 0
        for i in xrange(start, hoMax, jump):
            gamekey[j] = ord(handoff[i])
            j += 1

        print gamekey

        table = {}
        for i in xrange(256):
            table[i] = i

        temp = {0: 0, 1: 0, 2: 0, 3: 0}
        for i in xrange(256):
            temp[0] = (temp[0] + table[i] + gamekey[i % 6]) & 255
            temp[1] = table[temp[0]]
            
            table[temp[0]] = table[i]
            table[i] = temp[1]
        
        temp[0] = 0

        securekey = {}
        for i in xrange(6):
            securekey[i] = ord(secure[i])
            
            temp[0] = (temp[0] + securekey[i] + 1) & 255
            temp[1] = table[temp[0]]
            temp[2] = (temp[2] + temp[1]) & 255
            temp[3] = table[temp[2]]
            
            securekey[i] ^= table[(temp[1] + temp[3]) & 255]
            
            table[temp[0]] = temp[3]
            table[temp[2]] = temp[1]

        i = 0
        validate = ''
        for j in xrange(2):
            temp[1] = securekey[i]
            temp[3] = securekey[i + 1]
            
            validate += self._CreateChar(temp[1] >> 2)
            validate += self._CreateChar(((temp[1] & 3) << 4) | (temp[3] >> 4))

            temp[1] = securekey[i + 2]
            
            validate += self._CreateChar(((temp[3] & 15) << 2) | (temp[1] >> 6))
            validate += self._CreateChar(temp[1] & 63)

            i += 3

        return validate
    

    def _CreateChar(self, number):
        if number < 26:
            return chr(number + 65)
        elif number < 52:
            return chr(number + 71)
        elif number < 62:
            return chr(number - 4)
        elif number == 62:
            return '+'
        elif number == 63:
            return '/'

    def _ParseCompressedIPs(self, data):
        servers = []

        if len(data) < 6:
            return False
        else:
            bytes = len(data)

        i = 0
        while bytes - i >= 6:
            servers.append((str(ord(data[i])) + '.' + str(ord(data[i + 1])) + '.' + \
                            str(ord(data[i + 2])) + '.' + str(ord(data[i + 3])), \
                            (ord(data[i + 4]) * 256) + ord(data[i + 5])))
            i += 6

        return servers
            
        
if __name__ == '__main__':
    print '*' * 32
    print 'GameSpy Masterserver Class v1.0'
    print 'Copyright (c) 2005 Thomas Reiser'
    print 'www.mg34.net - fire_1@gmx.de'
    print '*' * 32
    print '\nYou can find the list of games here: www.mg34.net/research/gs_gamelist.txt\n'
    gsmaster = GameSpy_Master('207.38.11.14', 28910)
    
    gamename = 'menofwarpcd'
    handoff = 'z4L7mK'

    servers = gsmaster.GetServers(gamename, handoff)
    if servers == False:
        print '\nError retrieving serverlist!!'
    else:
        print '\nServers:'
        for server in servers:
            print '-%s:%d' % (server[0], server[1])
        
