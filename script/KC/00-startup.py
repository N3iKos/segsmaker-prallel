from KANDANG import HOMEPATH, PYV
from IPython import get_ipython
from pathlib import Path
import json
import sys
import os

iRON = os.environ

MRK = Path(HOMEPATH) / 'gutris1/marking.py'
JS = Path(HOMEPATH) / 'gutris1/marking.json'

PY = Path('/GUTRIS1')
BIN = str(PY / 'bin')
PKG = str(PY / f'lib/python{PYV}/site-packages')

sys.path.append('/root/.ipython/profile_default/startup')

if PY.exists():
    sys.path.insert(0, PKG)
    if BIN not in iRON['PATH']: iRON['PATH'] = BIN + ':' + iRON['PATH']
    if PKG not in iRON['PYTHONPATH']: iRON['PYTHONPATH'] = PKG + ':' + iRON['PYTHONPATH']

if MRK.exists():
    get_ipython().run_line_magic('run', str(MRK))
