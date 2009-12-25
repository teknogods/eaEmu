import distutils.core, py2exe
import sys, os, shutil
import os
from os.path import *

## TODO: right now, the build process on windows is very sloppy
## the following modules must be copied into the build dir in order
## for this makefile to work:
## django, ZSI, aspects.py

dirsToSearch = [
   'eaEmu',
   'django',
]

def main(argv=None):
    argv = argv or sys.argv
    pyFiles = []
    for dir in dirsToSearch:
       for dirpath, dirnames, filenames in os.walk(dir):
         pyFiles.extend((dirpath + os.sep + f[:-3]).replace(os.sep, '.') for f in filenames if f.endswith('.py'))
    pyFiles.extend([
    'aspects',
    'sqlite3',
    'ZSI.schema',
    'yaml',
    ])
    buildpy('eaEmu.tac', pyFiles)

def buildpy(py, includes=[]):
    path = abspath(py)
    name, ext = splitext(basename(path))
    distutils.core.setup(
        script_args = ['py2exe'],
        options = {'py2exe': {'compressed': 1,
                              'optimize': 2,
                              'bundle_files': 1,
                               'includes' : includes,
                              }
                   },
        console = [name + ext],
        #windows = [name + ext],
        zipfile = None,
    )
    shutil.move('dist/%s.exe' % name, join(dirname(path), name + '.exe'))

def cleanup():
    map(lambda x: shutil.rmtree(x, True), ['build', 'dist'])

if __name__ == '__main__':
    sys.exit(main())
