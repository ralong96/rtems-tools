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
            - pip install backports.lzma

  Examples:
    - pulling code with git
      - python rtems-cron-predir.py -g
    - With release tars
      - python rtems-cron-predir.py -v -r -R https://ftp.rtems.org/pub/rtems/releases/5/5.0.0/5.0.0-m2005-1 -t 5.0.0-m2005-1
"""

from __future__ import print_function

import os
import sys
import time
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
  dest='from_git',
  action='store_true',
  default=True,
  help='prep from git'
)
parser.add_option(
  '-r',
  '--release',
  dest='from_git',
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
if not options.from_git:
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

if options.from_git:
  for directory in ['rtems-source-builder', 'rtems', 'rtems-examples']:
    vprint('Cloning ' + directory + '...')
    start_time = time.time()
    try:
      rtems_repo.clone('git://git.rtems.org/' + directory + '.git', options.dir+'/'+directory)
    except:
      sys.exit(1)
    else:
      vprint(directory + ' succesfully cloned...')
    end_time = time.time()
    print('Cloning took ' + str(end_time - start_time) + ' seconds.')
else:
  import wget
  import tarfile

  # if using python2
  if (sys.version_info < (3,0)):
    from backports import lzma
    from contextlib import closing

  for directory in ['rtems-source-builder', 'rtems', 'rtems-examples']:
    vprint('Downloading '+options.release_url + '/sources/' + directory+'-' + options.tag + '.tar.xz...')
    wget.download(options.release_url + '/sources/' + directory+'-' + options.tag + '.tar.xz',options.dir)
    vprint('Done...')
    vprint('Unpacking ' + options.dir + '/' + directory + '-' + options.tag + '.tar.xz...')

    # if using python3
    if (sys.version_info > (3,0)):
      with tarfile.open(options.dir + '/' + directory + '-' + options.tag + '.tar.xz') as f:
        f.extractall('.')

    else:
      with closing(lzma.open(options.dir + '/' + directory + '-' + options.tag + '.tar.xz')) as xz:
        with tarfile.open(fileobj=xz) as f:
          f.extractall('.')

    vprint('Done...')
    os.remove(options.dir + '/' + directory + '-' + options.tag + '.tar.xz')
    os.rename(options.dir + '/' + directory + '-' + options.tag, options.dir + '/' + directory)

vprint('\n\nScript finished successfully...')
sys.exit(0)
