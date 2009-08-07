#last edited on: 2007.07.20
import distutils.core, py2exe
import sys, os, shutil
from os.path import *

def main(argv=None):
    argv = argv or sys.argv
    includes = [x.rsplit('.', 1)[0] for x in os.listdir(os.path.dirname(argv[0])) if x.endswith('.py') and x != os.path.basename(argv[0])]
    buildpy('main.py', includes)

def buildpy(py, includes=[]):
    path = abspath(py)
    name = basename(splitext(path)[0])
    distutils.core.setup(
        script_args = ['py2exe'],
        options = {'py2exe': {'compressed': 1,
                              'optimize': 2,
                              'bundle_files': 1,
                               'includes' : includes,
                              }
                   },
        windows = [name + '.py'],
        zipfile = None,
    )
    shutil.move('dist/%s.exe' % name, join(dirname(path), name + '.exe'))

def cleanup():
    map(lambda x: shutil.rmtree(x, True), ['build', 'dist'])

if __name__ == '__main__':
    sys.exit(main())
