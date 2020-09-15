#! /usr/bin/python

import os
import sys
import time
import subprocess
from shutil import rmtree
from optparse import OptionParser

from __future__ import print_function

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
  default=os.environ['HOME']+'/rtems-cron',
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
  print('All of the directories are not present.', file=sys.stderr)
  print('Delete the directory and rerun rtems-cron-prepdir.py. Exiting...', file=sys.stderr)
  sys.exit(1)

if options.force_build:
  tools_updated = True
  rsb_updated = True
  rtems_updated = True
  if options.verbose:
    print('Forcing builds whether or not there are updates')

# if the user wants the results sent in an email
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

def do_rsb_build_tools(version):
  # Basic Cross-compilation Tools
  os.chdir(options.dir + 'rtems-source-builder/rtems')

  # clean the install point
  if os.path.isdir(options.dir + '/tools'):
    rmtree('./tools/' + version)

  with open('./config/' + version + '/rtems-all.bset') as f:
    rset = [line.rstrip() for line in f]  # remove the trailing '\n'

  # remove 'VERSION/rtems-' from the beginnging of each string
  for i in range(len(rset)):
    rset[i] = rset[i].split('-')[1]

  start_time = time.time()

  print(
    'time ../source-builder/sb-set-builder ' +\
    RSB_MAIL_ARGS +\
    '--keep-going' +\
    '--log=l-' + rcpu '-' + version + '.txt' +\
    '--prefix=' + options.dir + '/tools/' + version +\
    rset + '>o-' + rcpu '-' + version '.txt 2>&1' \
  )
  
  for rcpu in rset:
    call_beg_time = time.time()

    """
    # don't know if this will work yet
    result = subprocess.call([ \
      '../source-builder/sb-set-builder', \
      RSB_MAIL_ARGS, \
      '--keep-going', \
      '--log=l' + rcpu + '-' + version, \
      '--prefix=' + options.dir + '/tools/' + options.version, \
      'rset', \
      '>o-' + rcpi + '-' + version + '.txt'
    ])
    """

    print('building the tools for ' + rcpu + ' took ' + str(call_end_time - call_beg_time) + ' seconds...')

  end_time = time.time()
  print('\n\nBuilding all of the tools took ' + str(end_time - start_time) + ' seconds.')

  # if the basic cross-compilation of the tools failed
  if result != 0:
    print('RSB build of RTEMS ' + version + ' Tools failed. ', file=sys.stderr)
    sys.exit(1)

  # Device Tree Compiler
  start_time = time.time()

  os.chdir(options.dir + '/rtems-source-builder/bare')
  print(
    '../source-builder/sb-set-builder ' + \
    RSB_MAIL_ARGS +\
    ' --log=l-dtc-' + options.version +'.txt' +\
    '--prefix=' + options.dir + '/tools/' + version +\
    'devel/dtc >l-dtc-' + options.version + '.txt 2>&1'
  )

  result = subprocess.call([ \
      '../source-builder/sb-set-builder', \
      RSB_MAIL_ARGS, \
      '--log=l-dtc-' + version + '.txt', \
      '--prefix=' + options.dir + '/tools/' + version, \
      'rset', \
      '>o-' + rcpi + '-' + version + '.txt'
    ])

  # put that call in a subprocess call
  end_time = time.time()
  print('Running the device tree compiler took ' + str(end_time - start_time) + ' seconds.')

  # if building the device tree compiler failed
  if result != 0:
    print('Running the device tree compiler failed. ', file=sys.stderr)
    sys.exit(1)

  # Spike RISC-V Simulator
  start_time = time.time()

  os.chdir(options.dir + '/rtems-source-builder/bare')
  print(
    '../source-builder/sb-set-builder ' +\
    RSB_MAIL_ARGS +\
    '--log=l-spike-' + version + '.txt' +\
    '--prefix=' + options.dir + '/tools/' + version +\
    'devel/spike >l-spike-' + version + '.txt 2>&1'
  )

  result = subprocess.call([ \
      '../source-builder/sb-set-builder', \
      RSB_MAIL_ARGS, \
      '--log=l-spike-' + version + '.txt', \
      '--prefix=' + options.dir + '/tools/' + version, \
      'devel/spike', \
      '>l-spike-' + version + '.txt'
    ])

  end_time = time.time()
  print('Running the Spike RISC-V Simulator took ' + str(end_time - start_time) + ' seconds.')

  # if running the Spike RISC-V Simulator failed
  if result != 0:
    print('Running the Spike RISC-V Simulator failed. ', file=sys.stderr)
    sys.exit(1)

  # Qemu Simulator
  start_time = time.time()

  os.chdir(options.dir + '/rtems-source-builder/bare')
  print(
    '../source-builder/sb-set-builder ' +\
    RSB_MAIL_ARGS +\
    ' --log=l-qemu-' + version + '.txt' +\
    '--prefix=' + options.dir + '/tools/' + version +\
    'devel/qemu4 >l-qemu4-' + version + '.txt 2>&1'
  )

  result = subprocess.call([ \
      '../source-builder/sb-set-builder', \
      RSB_MAIL_ARGS, \
      '--log=l-qemu-' + version + '.txt', \
      '--prefix=' + options.dir + '/tools/' + version, \
      'devel/qemu4', \
      '>l-qemu4-' + version + '.txt'
    ])

  end_time = time.time()
  print('Running Qemu Simulator took ' + str(end_time - start_time) + ' seconds.')

  # if running the Qemu 4 simulator failed
  if result != 0:
    print('Running the Qemu 4 simulator failed. ', file=sys.stderr)
    sys.exit(1)

def do_bsp_builder():
  start_time = time.time()

  print(
    options.dir + '/rtems-tools/tester/rtems-bsp-builder' +\
    '--rtems=' + options.dir + '/rtems' +\
    '--build-path=' + options.dir + '/build' +\
    '--prefix=' + options.dir + '/tools/' + options.version + '/bsps' +\
    '--log=build.log' +\
    '--warnings-report=warnings.log' +\
    RSB_MAIL_ARGS +\
    '--profiles=everything'
  )

  result = subprocess.call([ \
    options.dir + '/rtems-tools/tester/rtems-bsp-builder', \
    '--rtems=' + options.dir + '/rtems', \
    '--build-path=' + options.dir + '/build', \
    '--prefix=' + options.dir + '/tools/' + options.version + '/bsps', \
    '--log=build.log', \
    '--warnings-report=warnings.log', \
      RSB_MAIL_ARGS, \
      '--profiles=everything'
  ])

  end_time = time.time()
  print('BSP builder took ' + str(end_time - start_time) + ' seconds.')

  if result != 0:
    print('BSP builder failed. ', file=sys.stderr)
    sys.exit(1)

os.environ['PATH'] = options.dir + '/tools/' + options.version + '/bin' + os.environ['PATH']

# Build RTEMS ${version}.x tools if needed
if rsb_updated:
  do_rsb_build_tools(options.version)

if rtems_updated:
  os.chdir(options.dir + '/rtems')
  # should I check for this first?
  subprocess.call(['bootstrap', '-c'])

# Ensure this is after the RSB has built tools and PATH is updated
# Check that rtems-bootstrap exists, is readable, and executable
if  not os.path.isfile('./rtems-bootstrap') or \
    not os.access('./rtems-bootstrap', os.R_OK) or \
    not os.access('./rtems-bootstrap', os.X_OK):
  print('This is not an RTEMS version this script supports.')
  sys.exit(0)
else:
  result = subprocess.call(['rtems-bootstrap'])
  
  if result != 0:
    print('rtems-bootstrap failed. ', file=sys.stderr)
    sys.exit(1)

if options.send_email:
  MAIL_ARG = '-m'
else:
  MAIL_ARG = ''

BB_ARGS = '-T ' + options.dir + '-v -r ' + MAIL_ARG + ' -t'

def cmd_exists(cmd):
    return any(
      os.access(os.path.join(path, cmd), os.X_OK) 
      for path in os.environ["PATH"].split(os.pathsep)
    )

def test_single_bsp(cpu, bsp):
  if cpu == 'smp':
    SMP_ARGS = '-S'
  else:
    SMP_ARGS = ''


