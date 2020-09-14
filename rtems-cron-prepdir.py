#! /usr/bin/python

"""
  requirements:
    - must install 'wget' module
      - pip install wget

    if using python 2.7
      - if using a RedHat or CentOS system run
          - sudo dnf install xz-devel
      OR
      - if using a Debian based Linux distribution
          - sudo apt-get install liblzma-dev

      Then
        - install backports.lzma like so
            - pip install pip install pyliblzma
"""

import os
import sys
from optparse import OptionParser

sys.path.insert(1, os.getcwd()+'/rtemstoolkit')

from rtemstoolkit import git

description = '''Prepares a directory for testing using git or unpacking a tar package'''

parser = OptionParser(
  usage='usage: %prog [OPTIONS]',
  description=description
)
parser.add_option(
  '-D',
  '--directory',
  dest='dir',
  default=os.environ['HOME']+'/rtems-cron',
  help='top directory (default={$HOME}/rtems-cron)'
)
parser.add_option(
  '-g',
  '--git',
  dest='method',
  action='store_true',
  default=True,
  help='prep from git'
)
parser.add_option(
  '-r',
  '--release',
  dest='method',
  action='store_false',
  help='prep from release'
)
parser.add_option(
  '-R',
  '--release-url',
  dest='release_url',
  default=None,
  help='the URL of the release'
)
parser.add_option(
  '-t',
  '--tag',
  dest='tag',
  default=None,
  help='release tag/version (e.g. rtems-TAG.tar.xz)'
)
parser.add_option(
  '-v',
  '--verbose',
  dest='verbose',
  action='store_true',
  default=False,
  help='verbose (default=no)'
)
parser.add_option(
  '-V',
  dest='version',
  default=5,
  help='RTEMS version (default=5)'
)

# options contains values for each of the arguments passed in
# args contains positional arguments leftover afer parsing options
(options, args) = parser.parse_args(sys.argv)

def vprint(string):
  if options.verbose:
    print(string)
  return

if os.path.isdir(options.dir):
  print('TOP directory already exists -- ' + options.dir)
  print('Clean up before running prep!')
  sys.exit(1)

# if prepping from release, ensure we have the necessary arguments
if not options.method:
  if not options.release_url:
    print('release URL not set')
    sys.exit(1)
  if not options.tag:
    print('release tag not set')
    sys.exit(1)

# done checking arguments
os.mkdir(options.dir)

vprint('\nPreparing ' + options.dir + '...\n')
os.chdir(options.dir)

rtems_repo = git.repo(os.getcwd())

if options.method:
  for directory in ['rtems', 'rtems-tools', 'rtems-source-builder']:
    vprint('Cloning ' + directory + '...') # maybe add something that tells how long it took?
    try:
      rtems_repo.clone('git://git.rtems.org/' + directory + '.git', options.dir+'/'+directory)
    except:
      sys.exit(1)
    else:
      vprint(directory + ' succesfully cloned...')
else:
  import wget
  import tarfile

  # if using python3
  if (sys.version_info > (3,0)):

    for directory in ['rtems', 'rtems-tools', 'rtems-source-builder']:
      vprint('Downloading '+options.release_url + '/sources/' + directory+'-' + options.tag + '.tar.xz...')
      wget.download(options.release_url + '/sources/' + directory+'-' + options.tag + '.tar.xz',options.dir)
      vprint('Done...')
      vprint('Unpacking ' + options.dir + '/' + directory + '-' + options.tag + '.tar.xz...')
      with tarfile.open(options.dir + '/' + directory + '-' + options.tag + '.tar.xz') as f:
        f.extractall('.')
      vprint('Done...')
      os.remove(options.dir + '/' + directory + '-' + options.tag + '.tar.xz')
      os.rename(options.dir + '/' + directory + '-' + options.tag, options.dir + '/' + directory)

  # if using python2
  else:
    import contextlib
    import lzma
    
    for directory in ['rtems', 'rtems-tools', 'rtems-source-builder']:
      vprint('Downloading '+ options.release_url + '/sources/' + directory +'-' + options.tag + '.tar.xz...')
      wget.download(options.release_url + '/sources/' + directory + '-' + options.tag + '.tar.xz',options.dir)
      vprint('Done...')
      vprint('Unpacking ' + options.dir + '/' + directory + '-' + options.tag + '.tar.xz...')
      with contextlib.closing(lzma.LZMAFile(options.dir + '/' + directory+'-' + options.tag + '.tar.xz')) as xz:
        with tarfile.open(fileobj=xz) as f:
          f.extractall('.')
      vprint('Done...')
      os.remove(options.dir + '/' + directory + '-' + options.tag + '.tar.xz')
      os.rename(options.dir + '/' + directory + '-' + options.tag, options.dir + '/' + directory)

vprint('\n\nScript finished successfully...')
sys.exit(0)