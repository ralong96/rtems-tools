#! /usr/bin/python

import os
import sys
from optparse import OptionParser

sys.path.insert(1, os.getcwd()+'/rtemstoolkit')

from rtemstoolkit import git

description = '''Runs all of the build tests'''

parser = OptionParser(
  usage='usage: %prog [OPTIONS]',
  description=description
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
  '-f',
  '--force-build',
  dest='force_build',
  default=False,
  help='force build (default=no)'
)
parser.add_option(
  '-g',
  '--git-update',
  dest='git',
  default=True,
  help='do git update (default=yes)'
)
parser.add_option(
  '-D',
  '--top-directory',
  dest='dir',
  default=os.environ['HOME']+'/rtems-cron2',
  help='Top directory (default=${HOME}/rtems-cron'
)
parser.add_option(
  '-V',
  '--version',
  dest='version',
  default=5,
  help='RTEMS Version (default=5)'
)
parser.add_option(
  '-m',
  '--send-email',
  dest='send_email',
  default=True,
  help='send email (default=yes)'
)
# implement mailer.py
parser.add_option(
  '-F',
  '--from-address',
  dest='from_addr',
  default='joel@rtems.org',
  help='From address (default=joel@rtems.org)'
)
parser.add_option(
  '-T',
  '--to-address',
  dest='to_addr',
  default='build@rtems.org',
  help='To address (default=build@rtems.org)'
)

(options, args) = parser.parse_args(sys.argv)

# check that TOP exists
if not os.path.isdir(options.dir):
  print(options.dir)
  print('TOP directory does not exist!')
  print('Run rtems-cron-prepdir.py before this script!')
  sys.exit(1)

os.chdir(options.dir)

# ask Joel about the do on line 85 of cron-runner
# check the internal directories
# need to add verbose statements
if os.path.isdir(options.dir + '/rtems') and \
   os.path.isdir(options.dir + '/rtems-source-builder') and \
   os.path.isdir(options.dir + '/rtems-tools'):

  if options.git:
    rsb_updated = False
    os.chdir('./rtems-source-builder')

    if os.path.isdir('./.git'):
      rtems_source_builder_repo = git.repo(os.getcwd())
      rtems_source_builder_repo.fetch()
      result = rtems_source_builder_repo._run(['rev-list', 'HEAD...master', '--count'])
      result = int(result[1]) # the number of revisions behind

      if result != 0:
        rtems_source_builder_repo.pull()
        rsb_updated = True

    os.chdir('..')

    tools_updated = False
    os.chdir('./rtems-tools')

    if os.path.isdir('./.git'):
      rtems_tools_repo = git.repo(os.getcwd())
      rtems_tools_repo.fetch()
      result = rtems_source_builder_repo._run(['rev-list', 'HEAD...master', '--count'])
      result = result[0]

      if result != 0:
        rtems_tools_repo.pull()
        tools_updated = True

    os.chdir('..')

    rtems_updated = False
    os.chdir('./rtems')

    if os.path.isdir('./.git'):
      rtems_repo = git.repo(os.getcwd())
      rtems_repo.fetch()
      result = rtems_repo._run(['rev-list', 'HEAD...master', '--count'])
      result = result[0]

      if result != 0:
        rtems_repo.pull()
        rtems_updated = True

else:
  print('All of the directories are not present.')
  print('Delete the directory and rerun rtems-cron-prepdir.py. Exiting...')
  sys.exit(1)

if options.force_build:
  tools_updated = True
  rsb_updated = True
  rtems_updated = True
  if options.verbose:
    print('Forcing builds whether or not there are updates')

# 
if options.send_email:
  RSB_MAIL_ARGS = '-- mail --mail-to=' + options.to_addr + ' --mail-from=' + options.from_addr

def yes_or_no(val):
  if val:
    return 'yes'
  else:
    return 'no'

if options.verbose:
  print('Git Update: ' + yes_or_no(options.git))
  print('Forced Update: ' + yes_or_no(options.force_build))
  print('Tools Updated: ' + yes_or_no(tools_updated))
  print('RSB Updated: ' + yes_or_no(rsb_updated))
  print('RTEMS Updated: ' + yes_or_no(rtems_updated))

if not options.force_build and \
   not tools_updated and \
   not rsb_updated and \
   not rtems_updated:
  print('No updates and forced build not requested -- NOACTION!')
  sys.exit(0)

# define builder functions here
