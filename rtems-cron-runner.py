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

# might just print out the date or something instead of giving seconds
script_start = time.time()

# everywhere where exedir was used, I might need to make a function to do what Joel did in his script
# directory where the script is run from
starting_directory = os.getcwd()

def exedir():
  os.chdir(starting_directory)
  return os.getcwd()

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
# implement mailer.py, I don't remember why. It looks like other scripts are handling arguments where this information is passed in
# need to ask what the default from and to email are supposed to be
# pretty sure the to email is fine, but I dont think the from is
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

def vprint(string):
  if options.verbose:
    print(string)
  else:
    return

def cmd_exists(cmd):
    return any(
      os.access(os.path.join(path, cmd), os.X_OK) 
      for path in os.environ["PATH"].split(os.pathsep)
    )

# check that TOP exists
if not os.path.isdir(options.dir):
  print(options.dir)
  print('TOP directory does not exist!', file=sys.stderr)
  print('Run rtems-cron-prepdir.py before this script!', file=sys.stderr)
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
        vprint('Pulling rtems_source_builder...')
        rtems_source_builder_repo.pull()
        rsb_updated = True
        vprint('Updated')

    os.chdir('..')

    tools_updated = False
    os.chdir('./rtems-tools')

    if os.path.isdir('./.git'):
      rtems_tools_repo = git.repo(os.getcwd())
      rtems_tools_repo.fetch()
      result = rtems_source_builder_repo._run(['rev-list', 'HEAD...master', '--count'])
      result = result[0]

      if result != 0:
        vprint('Pulling rtems-tools...')
        rtems_tools_repo.pull()
        tools_updated = True
        vprint('Updated')

    os.chdir('..')

    rtems_updated = False
    os.chdir('./rtems')

    if os.path.isdir('./.git'):
      rtems_repo = git.repo(os.getcwd())
      rtems_repo.fetch()
      result = rtems_repo._run(['rev-list', 'HEAD...master', '--count'])
      result = result[0]

      if result != 0:
        vprint('Pulling rtems...')
        rtems_repo.pull()
        rtems_updated = True
        vprint('Updated')

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
else:
  RSB_MAIL_ARGS = ''

def yes_or_no(val):
  if val:
    return 'yes'
  else:
    return 'no'

vprint('Git Update: ' + yes_or_no(options.git))
vprint('Forced Update: ' + yes_or_no(options.force_build))
vprint('Tools Updated: ' + yes_or_no(tools_updated))
vprint('RSB Updated: ' + yes_or_no(rsb_updated))
vprint('RTEMS Updated: ' + yes_or_no(rtems_updated))

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
    vprint('Removing ./tools/version ...')
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
    vprint('Building the tools for ' + rcpu + '...')
    result = subprocess.call([
      '../source-builder/sb-set-builder',
      RSB_MAIL_ARGS,
      '--keep-going',
      '--log=l' + rcpu + '-' + version,
      '--prefix=' + options.dir + '/tools/' + options.version,
      'rset',
      '>o-' + rcpi + '-' + version + '.txt',
      '2>&1'
    ])
    """
    call_end_time = time.time()
    vprint('Building the tools for ' + rcpu + ' took ' + str(call_end_time - call_beg_time) + ' seconds...') # ask about making all statements like these vprints

  end_time = time.time()
  vprint('\n\nBuilding all of the tools took ' + str(end_time - start_time) + ' seconds.')

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

  """
  vprint('Running the device tree compiler...')
  result = subprocess.call([ \
      '../source-builder/sb-set-builder',
      RSB_MAIL_ARGS,
      '--log=l-dtc-' + version + '.txt',
      '--prefix=' + options.dir + '/tools/' + version,
      'rset',
      '>o-' + rcpi + '-' + version + '.txt',
      '2>&1'
    ])
  """

  # put that call in a subprocess call
  end_time = time.time()
  vprint('Running the device tree compiler took ' + str(end_time - start_time) + ' seconds.')

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

  """
  vprint('Running the Spike RISC-V Simulator...')
  result = subprocess.call([
      '../source-builder/sb-set-builder',
      RSB_MAIL_ARGS,
      '--log=l-spike-' + version + '.txt',
      '--prefix=' + options.dir + '/tools/' + version,
      'devel/spike',
      '>l-spike-' + version + '.txt',
      '2>&1'
    ])
  """

  end_time = time.time()
  vprint('Running the Spike RISC-V Simulator took ' + str(end_time - start_time) + ' seconds.')

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
  """
  vprint('Running the Qemu Simulator...')
  result = subprocess.call([
      '../source-builder/sb-set-builder',
      RSB_MAIL_ARGS,
      '--log=l-qemu-' + version + '.txt',
      '--prefix=' + options.dir + '/tools/' + version,
      'devel/qemu4',
      '>l-qemu4-' + version + '.txt',
      '2>&1'
    ])
  """
  end_time = time.time()
  vprint('Running Qemu Simulator took ' + str(end_time - start_time) + ' seconds.')

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
  """
  vprint('Running BSP builder...')
  result = subprocess.call([
    options.dir + '/rtems-tools/tester/rtems-bsp-builder',
    '--rtems=' + options.dir + '/rtems',
    '--build-path=' + options.dir + '/build',
    '--prefix=' + options.dir + '/tools/' + options.version + '/bsps',
    '--log=build.log',
    '--warnings-report=warnings.log',
      RSB_MAIL_ARGS,
      '--profiles=everything',
  ])
  """
  end_time = time.time()
  vprint('BSP builder took ' + str(end_time - start_time) + ' seconds.')

  if result != 0:
    print('BSP builder failed. ', file=sys.stderr)
    sys.exit(1)

os.environ['PATH'] = options.dir + '/tools/' + options.version + '/bin' + os.environ['PATH']

# Build RTEMS ${version}.x tools if needed
if rsb_updated:
  do_rsb_build_tools(options.version)

if rtems_updated:
  os.chdir(options.dir + '/rtems')
  
  subprocess.call(['./bootstrap', '-c'])

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

def test_single_bsp(cpu, bsp, SMP_ARGS=''):
  if cmd_exists(cpu + '-rtems' + options.version + '-gcc'):
    subprocess.call([
      exedir() + '/build_bsp',
      '-V',
      options.version,
      BB_ARGS,
      SMP_ARGS,
      cpu,
      bsp
    ])
    result = subprocess.call([
      exedir() + '/build_bsp',
      '-V',
      options.version,
      BB_ARGS,
      SMP_ARGS,
      '-D'
      cpu,
      bsp
    ])

    if result == 0:
      rmtree('b-' + bsp)

  else:
    print('WARNING - no gcc for ' + cpu + ' ' + bsp)

if rsb_updated or rtems_updated:
  start_time = time.time()

  os.chdir(options.dir)

  test_single_bsp('sparc', 'erc32-sis')
  test_single_bsp('sparc', 'leon2-sis')
  test_single_bsp('sparc', 'leon3-sis')
  test_single_bsp('powerpc', 'psim')
  test_single_bsp('mips', 'jmr3904')
  test_single_bsp('riscv', 'griscv-sis')
  test_single_bsp('sparc', 'leon3-sis', '-S')

  # Make sure Spike is available for these BSPs
  if cmd_exists('spike'):
    bsps = ['rv32iac_spike', 'rv32imac_spike', 'rv32imafc_spike', \
    'rv32imafdc_spike', 'rv32imafd_spike', 'rv32im_spike', 'rv32i_spike', \
    'rv64imac_medany_spike', 'rv64imac_spike', 'rv64imafdc_medany_spike', \
    'rv64imafdc_spike', 'rv64imafd_medany', 'rv64imafd_medany_spike', \
    'rv64imafd_spike'
    ]

    for bsp in bsps:
      test_single_bsp('riscv', bsp)

    # Now build all supported BSP bset stacks
    os.chdir(options.dir + '/rtems-source-builder/rtems')

    bsets = ['atsamv', 'beagleboneblack', 'erc32', 'gr712rc', 'gr740', 'imx7',\
     'pc', 'qoriq_e500', 'qoriq_e6500_32', 'qoriq_e6500_64', 'raspberrypi2', \
      'xilinx_zynq_zc702', 'xilinx_zynq_zc706', 'xilinx_zynq_zedboard']

    for bset in bsets:
      bset_start_time = time.time()

      subprocess.call([
        '../source-builder/sb-set-builder',
        RSB_MAIL_ARGS,
        '--log=l-' + bset + '-' + options.version + '.txt',
        '--prefix=' + options.dir + '/tools/' + options.version,
        options.version + '/bsps/' + bset,
        '>o-' + bset + '-' + options.version + '.txt',
        '2>&1'
        ])

      bset_end_time = time.time()
      print('Building all supported BSP bset stacks took' + str(bset_end_time - bset_start_time) + ' seconds.')

      do_bsp_builder()

script_end = time.time()
vprint('START: ' + str(script_start))
vprint('END: ' + str(script_end))
sys.exit(0)