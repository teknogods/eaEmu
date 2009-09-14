#last edited on: 2007.07.20
# builds all .py files in current directory as console executables

import distutils.core, py2exe
import sys, os, shutil
from os.path import *

def main(argv=None):
    argv = argv or sys.argv

    if not argv:
        return 1
    
    # no args: search current dir all .py and build them individually
    if len(argv) == 1:
        files = filter(lambda x: x.endswith('.py') and x != basename(argv[0]), os.listdir('.'))
        argv.extend(files)

    if len(argv) > 1:
        for py in argv[1:]:
            buildpy(py)
    cleanup()

def buildpy(py):
    path = abspath(py)
    name = basename(splitext(path)[0])
    distutils.core.setup(
        script_args = ['py2exe'],
        options = {'py2exe': {'compressed': 1,
                              'optimize': 2,
                              'bundle_files': 1}},
        console= [name + '.py'],
        zipfile = None,
    )
    shutil.move('dist/%s.exe' % name, join(dirname(path), name + '.exe'))

def cleanup():
    map(lambda x: shutil.rmtree(x, True), ['build', 'dist'])

if __name__ == '__main__':
    sys.exit(main())
