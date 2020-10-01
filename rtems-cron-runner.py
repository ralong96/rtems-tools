#! /usr/bin/python

"""
  Example Usage:
  
    - python rtems-cron-runner.py -v -f -w
    
      - build it verbosely, force build with default version (6 in this case)
      
    - python rtems-cron-runner.py -v -f -g -V 5
      
      - build it verbosely, force build, do git update, use version 5
"""

from __future__ import print_function

import datetime
import logging
import os
import subprocess
import sys
import time

from shutil import rmtree
from optparse import OptionParser

starting_directory = os.getcwd()
sys.path.insert(1, starting_directory + '/rtemstoolkit')

from rtemstoolkit import git

script_start = datetime.datetime.now()
  
description = '''Runs all of the build tests'''

# if build bsp fails, there will be a b.log that needs to be mailed
parser = OptionParser(
  usage='usage: %prog [OPTIONS]',
  description=description,
  add_help_option=False
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
  action='store_true',
  default=False,
  help='force build (default=no)'
)
parser.add_option(
  '-g',
  '--git-update',
  dest='git',
  action='store_true',
  default=False,
  help='do git update (default=no)'
)
parser.add_option(
  '-D',
  dest='top',
  default=os.environ['HOME']+'/rtems-cron',
  help='Top directory (default=${HOME}/rtems-cron'
)
parser.add_option(
  '-V',
  dest='version',
  default='6',
  help='RTEMS Version (default=6)'
)
parser.add_option(
  '-w',
  '--waf-build',
  dest='waf_build',
  default=False,
  action='store_true',
  help='Build using the WAF build system (default=no)'
)
parser.add_option(
  '-m',
  '--send-email',
  dest='send_email',
  action='store_true',
  default=False,
  help='send email (default=no)'
)
parser.add_option(
  '-F',
  dest='from_addr',
  default='joel@rtems.org',
  help='From address (default=joel@rtems.org)'
)
parser.add_option(
  '-T',
  dest='to_addr',
  default='build@rtems.org',
  help='To address (default=build@rtems.org)'
)
parser.add_option(
  '-S',
  dest='build_in_steps',
  default=False,
  action='store_true',
  help='Build in steps (default=no)'
)
parser.add_option(
  '-s',
  dest='start_step',
  default=1,
  help='Step to start executing at (default=1)'
)
parser.add_option(
  '-e',
  dest='end_step',
  default=1,
  help='Step to stop executing at (default=1)'
)
parser.add_option(
  '-l',
  dest='log_path',
  default=os.environ['HOME'] + '/rtems-cron',
  help='Path to log file (default=$HOME/rtems-cron)'
)
parser.add_option(
  '-h',
  '--help',
  dest='help',
  default=False,
  action='store_true'
)
parser.add_option(
  '-z',
  dest='testing',
  default=False,
  action='store_true',
)

(options, args) = parser.parse_args(sys.argv)

# if the user wants to see the help menu
if options.help:
  print('Usage: rtems-cron-runner [OPTIONS]\n')
  print('Options:')
  print('  -h, --help         Show this help message and exit')
  print('  -v, --verbose      Verbose (default=no)')
  print('  -f, --force-build  Force build (default=no)')
  print('  -g, --git-update   Do git update (default=no)')
  print('  -D TOP             Top directory (default=${HOME}/rtems-cron)')
  print('  -V VERSION         RTEMS Version (default=6)')
  print('  -w, --waf-build    Build using the WAF build system (default=no)')
  print('  -m, --send-email   Send email (default=no)')
  print('  -T TO_ADDR         To address (default=build@rtems.org)')
  print('  -F FROM_ADDR       From address (default=joel@rtems.org)')
  print('  -l LOG_PATH        Path to log file (default-${HOME}/rtems-cron)')
  print('  -S BUILD_IN_STEPS  Build in steps (default=no)')
  print('  -s START_STEP      Step to start executing at (default=1)')
  print('  -e END_STEP        Step to stop executing at (default=1)\n\n')
  print('Steps:')
  print('  1. Build basic cross compilation tools')
  print('  2. Build device tree compiler')
  print('  3. Build Spike RISC-V simulator')
  print('  4. Build Qemu4 Simulator')
  print('  5. Bootstrap')
  print('  6. Test the BSPs')
  print('  7. Build the bsets')
  print('  8. Build the BSPs')
  print('\nNOTE: Some steps may be skipped if the \'-f\' option is not used.')
  sys.exit(0)
  
testing = options.testing # don't run the code, just print out what would run

# Helps us do the build process in steps
step = int(options.start_step)

steps = {
  'build_tools' : [1, 'building tools'],
  'build_dtc' : [2, 'building device tree compiler'],
  'build_spike' : [3, 'building RISC-V Simulator'],
  'build_qemu' : [4, 'building Qemu4 Simulator'],
  'bootstrap' : [5, 'bootstrapping'],
  'test_bsps' : [6, 'testing the BSPs'],
  'build_bsets' : [7, 'buildings the bsets'],
  'build_bsps' : [8, 'building the BSPs']
}
  
# create log file
logging.basicConfig(
  filename=options.log_path,
  level=logging.DEBUG,
  format='%(levelname)s:%(asctime)s:%(message)s'
)
  
def info(string):
  logging.info(string)
  
def log(status, msg):
  if status == 0:
    logging.info('PASSED ' + msg)
  else:
    logging.error('FAILED(' + str(status) + ') ' + msg)

def vprint(string):
  if options.verbose:
    print(string)
  else:
    return
    
def step_done(key):
  try:
    vprint('Done with step {} ({})'.format(steps[key][0], steps[key][1]))
  except KeyError:
    output = '{} is not a key in the steps dictionary'.format(key)
    print(output, file=sys.stderr)
    info(output)

def cmd_exists(cmd):
    return any(
      os.access(os.path.join(path, cmd), os.X_OK) 
      for path in os.environ["PATH"].split(os.pathsep)
    )
    
def exedir():
  os.chdir(starting_directory)
  return os.getcwd()
  
def yes_or_no(val):
  if val:
    return 'yes'
  else:
    return 'no'

master_version = '6'

# verify that Top directory exists
if not os.path.isdir(options.top):
  print('The top directory, ' + options.top + \
        ', does not exist.', file=sys.stderr
  )
  print('Run rtems-cron-prepdir.py before this script!', file=sys.stderr)
  sys.exit(1)

os.chdir(options.top)

# verify that arguments make sense

# make sure that end step is not less than start steps
if options.build_in_steps and options.start_step >= options.end_step:
  print(
    'When building in steps, ensure that start step is less than end step!',
    file=sys.stderr
  )
  sys.exit(1)

# RTEMS5 did not have the WAF build system
if options.version == '5' and options.waf_build:
  print('WAF was not the build system used with RTEMS 5.', file=sys.stderr)
  sys.exit(1)

rsb_updated = False
rtems_updated = False

# this only works if it was created by rtems-cron-prepdir.py
if os.path.isdir(options.top + '/rtems') and \
   os.path.isdir(options.top + '/rtems-source-builder'):

  # if the directories were gotten from git, they may be updated
  if options.git:
    # ensure that git was used to get these directories
    if '.git' in os.listdir(options.top + '/rtems') and \
                 os.listdir(options.top + '/rtems-source-builder'):

      os.chdir('./rtems-source-builder')
      
      rsb_repo = git.repo(os.getcwd())
      
      # determine what branch we're on and determine if we need to checkout a 
      # different one
      if (rsb_repo.branch() != options.version) and \
         (options.version != master_version):
        try:
          rsb_repo.checkout(options.version)
        except:
          print('An error occured when trying to checkout branch ' + \
          options.version + '...'
          )
          sys.exit(1)
      
      rsb_repo.fetch()
      
      if options.version == master_version:
        result = rsb_repo._run(['rev-list', 'HEAD...master', '--count'])
      else:
        result = rsb_repo._run([
          'rev-list', 'HEAD...' + options.version, '--count'])
        
      result = int(result[1]) # the number of revisions behind
      
      info('RSB had {} revision(s) to update'.format(result))
      
      if result != 0:
        vprint('Pulling rtems_source_builder...')
        rsb_repo.pull()
        rsb_updated = True
        vprint('Done...')
        
      os.chdir('../rtems')

      rtems_repo = git.repo(os.getcwd())
      
      # determine what branch we're on and determine if we need to checkout a 
      # different one
      if (rtems_repo.branch() != options.version) and \
         (options.version != master_version):
        try:
          rtems_repo.checkout(options.version)
        except:
          print('An error occured when trying to checkout branch ' + \
                options.version + '...'
          )
          sys.exit(1)
      
      rtems_repo.fetch()
      
      if options.version == master_version:
        result = rtems_repo._run(['rev-list', 'HEAD...master', '--count'])
      else:
        result = rtems_repo._run([
          'rev-list', 'HEAD...' + options.version, '--count'])
        
      result = int(result[1]) # the number of revisions behind
      
      info('rtems had {} revision(s) to update'.format(result))
      
      if result != 0:
        vprint('Pulling rtems...')
        rtems_repo.pull()
        rtems_updated = True
        vprint('Done...')
        
      os.chdir('..')
      
    else:
      print(
        'All \'.git\' directories not present. Clean up and rerun prepdir!',
        file=sys.stderr
      )
      sys.exit(1)
    
# if the user wants to force an update
if options.force_build:
  rsb_updated = True
  rtems_updated = True
  if options.verbose:
    print('Forcing builds whether or not there are updates')
  
vprint('Git Update: ' + yes_or_no(options.git))
vprint('Forced Update: ' + yes_or_no(options.force_build))
vprint('RSB Updated: ' + yes_or_no(rsb_updated))
vprint('RTEMS Updated: ' + yes_or_no(rtems_updated))

# nothing to be done if everything is up to date
if not options.force_build and \
   not rsb_updated and \
   not rtems_updated:
  print('No updates and forced build not requested -- NOACTION!')
  sys.exit(0)

# build the tools 
def do_rsb_build_tools(version):

  # Basic Cross-compilation Tools
  os.chdir(options.top + '/rtems-source-builder/rtems')

  # clean the install point
  if os.path.isdir(options.top + '/tools'):
    vprint('Removing tools...')
    rmtree(options.top + '/tools')

  if not os.path.isfile('./config/' + str(version) + '/rtems-all.bset'):
    print(options.top + '/rtems-source-builder/rtems/config/' + \
          str(version) + '/rtems-all.bset', end='', file=sys.stderr)
    print(' does not exist.', file=sys.stderr)
    sys.exit(1)

  # remove the trailing '\n'
  with open('./config/' + str(version) + '/rtems-all.bset') as f:
    rset = [line.rstrip() for line in f]

  # rset = [str(options.version) + '/rtems-sparc']

  start_time = time.time()
  
  result = 0
  
  for r in rset:
    call_beg_time = time.time()
    rcpu = r.split('-')[1]
    if testing:
      print(
      '\ntime ../source-builder/sb-set-builder ' +\
      '--mail --mail-to=' + options.to_addr + \
      ' --mail-from=' + options.from_addr + \
      ' --keep-going ' +\
      '--log=l-' + rcpu + '-' + version + '.txt ' +\
      '--prefix=' + options.top + '/tools/' + version + ' ' +\
      r + ' >o-' + rcpu + '-' + version + '.txt 2>&1\n' \
      )
    else:
      # if step is in range, or the build isn't being ran in steps
      if step <= steps['build_tools'] or not options.build_in_steps:
        vprint('Building the tools for ' + rcpu + '...')
        file_name = 'o-' + rcpu + '-' + str(version) + '.txt'
        outfile = open(file_name, 'w')
        if options.send_email:
          ARGS = [
            '../source-builder/sb-set-builder',
            '--mail',
            '--mail-to=' + options.to_addr,
            '--mail-from=' + options.from_addr,
            '--keep-going',
            '--log=l-' + rcpu + '-' + version,
            '--prefix=' + options.top + '/tools/' + version,
            r
          ]
        else:
          ARGS = [
            '../source-builder/sb-set-builder',
            '--keep-going',
            '--log=l-' + rcpu + '-' + version,
            '--prefix=' + options.top + '/tools/' + version,
            r
          ]
          
        result = subprocess.call(ARGS,stdout=outfile, stderr=outfile)
        outfile.close()
        log(result, 'RSB build of ' + r)

    call_end_time = time.time()
    vprint('Done...')
    vprint('Building the tools for ' + rcpu + ' took ' + \
           str(call_end_time - call_beg_time) + ' seconds...'
    )

  end_time = time.time()
  # figure out how to display this in minutes or something
  vprint('\n\nBuilding all of the tools took ' + \
          str(end_time - start_time) + ' seconds.'
  ) 

  # if the basic cross-compilation of the tools failed
  if result != 0:
    print('RSB build of RTEMS ' + version + ' Tools failed. ', file=sys.stderr)
    sys.exit(1)
  
  # if we are at the end step, end it, if not increase step
  if options.build_in_steps:
    step_done('build_tools')
    if step == options.end_step:
      sys.exit(0)
    else:
      step += 1

  # Device Tree Compiler
  start_time = time.time()

  os.chdir(options.top + '/rtems-source-builder/bare')
  
  if testing:
    print(
      '\n../source-builder/sb-set-builder ' + \
      '--mail --mail-to=' + options.to_addr + \
      '--mail-from=' + options.from_addr + \
      ' --log=l-dtc-' + options.version +'.txt' +\
      '--prefix=' + options.top + '/tools/' + version +\
      ' devel/dtc >l-dtc-' + options.version + '.txt 2>&1\n'
    )

  else:
    if step <= steps['build_dtc'] or not options.build_in_steps:
      vprint('Running the device tree compiler...')
      file_name = 'l-dtc' + version + '.txt'
      outfile = open(file_name, 'w')
      # if the user wants an email to be sent
      if options.send_email:
        ARGS = [
            '../source-builder/sb-set-builder',
            '--mail',
            '--mail-to=' + options.to_addr,
            '--mail-from=' + options.from_addr,
            '--log=l-dtc-' + version + '.txt',
            '--prefix=' + options.top + '/tools/' + version,
            'devel/dtc'
        ]
      else:
        ARGS = [
            '../source-builder/sb-set-builder',
            '--log=l-dtc-' + version + '.txt',
            '--prefix=' + options.top + '/tools/' + version,
            'devel/dtc'
        ]

      result = subprocess.call(ARGS ,stdout=outfile, stderr=outfile)
      outfile.close()
      log(result, 'RSB build of devel/dtc')

  end_time = time.time()
  vprint(
    'Running the device tree compiler took ' + \
    str(end_time - start_time) + ' seconds.'
  )

  # if building the device tree compiler failed
  if result != 0:
    print('Running the device tree compiler failed. ', file=sys.stderr)
    sys.exit(1)
  
  # if building in steps, check if the script needs to end or if step needs
  # incrementing
  if options.build_in_steps:
    step_done('build_dtc')
    if step == options.end_step:
      sys.exit(0)
    else:
      step += 1

  # Spike RISC-V Simulator
  start_time = time.time()

  os.chdir(options.top + '/rtems-source-builder/bare')
  if testing:
    print(
      '\n../source-builder/sb-set-builder ' + \
      '--mail --mail-to=' + options.to_addr + \
      '--mail-from=' + options.from_addr + \
      '--log=l-spike-' + version + '.txt' + \
      '--prefix=' + options.top + '/tools/' + version + \
      'devel/spike >l-spike-' + version + '.txt 2>&1\n'
    )

  else:
    if step <= steps['build_spike'] or not options.build_in_steps:
      vprint('Running the Spike RISC-V Simulator...')
      file_name = 'l-spike' + version + '.txt'
      outfile = open(file_name, 'w')
      if options.send_email:
        ARGS = [
            '../source-builder/sb-set-builder',
            '--mail',
            '--mail-to=' + options.to_addr,
            '--mail-from=' + options.from_addr,
            '--log=l-dtc-' + version + '.txt',
            '--prefix=' + options.top + '/tools/' + version,
            'devel/dtc'
        ]
      else:
        ARGS = [
          '../source-builder/sb-set-builder',
          '--log=l-spike-' + version + '.txt',
          '--prefix=' + options.top + '/tools/' + version,
          'devel/spike'
        ]
        
      result = subprocess.call(ARGS, stdout=outfile, stderr=outfile)
      outfile.close()
      log(result, 'RSB build of devel/spike')

  end_time = time.time()
  vprint(
    'Running the Spike RISC-V Simulator took ' + \
    str(end_time - start_time) + ' seconds.'
  )

  # if building the Spike RISC-V Simulator failed
  if result != 0:
    print('Running the Spike RISC-V Simulator failed. ', file=sys.stderr)
    sys.exit(1)
    
  if options.build_in_steps:
    step_done('build_spike')
    if step == options.end_step:
      sys.exit(0)
    else:
      step += 1

  # Qemu Simulator
  start_time = time.time()

  os.chdir(options.top + '/rtems-source-builder/bare')
  
  if testing:
    print(
      '\n../source-builder/sb-set-builder ' + \
      '--mail --mail-to=' + options.to_addr + \
      '--mail-from=' + options.from_addr + \
      ' --log=l-qemu-' + version + '.txt' + \
      '--prefix=' + options.top + '/tools/' + version + \
      'devel/qemu4 >l-qemu4-' + version + '.txt 2>&1\n'
    )
  
  else:
    if step <= steps['build_qemu'] or not options.build_in_steps:
      vprint('Running the Qemu Simulator...')
      file_name = 'l-qemu4-' + version + '.txt'
      outfile = open(file_name, 'w')
      if options.send_email:
        ARGS = [
            '../source-builder/sb-set-builder',
            '--mail',
            '--mail-to=' + options.to_addr,
            '--mail-from=' + options.from_addr,
            '--log=l-qemu-' + version + '.txt',
            '--prefix=' + options.top + '/tools/' + version,
            'devel/qemu4'
        ]
      else:
        ARGS = [
            '../source-builder/sb-set-builder',
            '--log=l-qemu-' + version + '.txt',
            '--prefix=' + options.top + '/tools/' + version,
            'devel/qemu4'
        ]

      result = subprocess.call(ARGS, stdout=outfile, stderr=outfile)
      outfile.close()
      log(result, 'RSB build of devel/qemu4')

  end_time = time.time()
  vprint(
    'Running Qemu Simulator took ' + \
    str(end_time - start_time) + ' seconds.'
  )

  # if building the Qemu 4 simulator failed
  if result != 0:
    print('Running the Qemu 4 simulator failed. ', file=sys.stderr)
    sys.exit(1)
    
  if options.build_in_steps:
    step_done('build_qemu')
    if step == options.end_step:
      sys.exit(0)
    else:
      step += 1

def do_bsp_builder():
  start_time = time.time()

  if testing:
    print(
      '\n' + options.top + '/rtems-tools/tester/rtems-bsp-builder ' + \
      '--rtems=' + options.top + '/rtems ' + \
      '--build-path=' + options.top + '/build ' + \
      '--prefix=' + options.top + '/tools/' + options.version + '/bsps ' + \
      '--log=build.log ' + \
      '--warnings-report=warnings.log ' + \
      '--mail --mail-to=' + options.to_addr + \
      '--mail-from=' + options.from_addr + \
      ' --profiles=everything'
    )
  
  else:
    vprint('Running BSP builder...')
    result = subprocess.call([
      options.top + '/rtems-tools/tester/rtems-bsp-builder',
      '--rtems=' + options.top + '/rtems',
      '--build-path=' + options.top + '/build',
      '--prefix=' + options.top + '/tools/' + options.version + '/bsps',
      '--log=build.log',
      '--warnings-report=warnings.log',
      '--mail',
      '--mail-to=' + options.to_addr,
      '--mail-from=' + options.from_addr,
      '--profiles=everything',
    ])

  end_time = time.time()
  vprint('BSP builder took ' + str(end_time - start_time) + ' seconds.')
  log(result, 'rtems-bsp-builder build of everything')

  if result != 0:
    print('BSP builder failed. ', file=sys.stderr)
    sys.exit(1)

# double check this
addition = options.top + '/tools/' + str(options.version) + '/bin:'
os.environ['PATH'] = addition + os.environ['PATH']

# Build RTEMS ${version}.x tools if needed
if rsb_updated:
  do_rsb_build_tools(str(options.version)) # I don't think I need this, double-check

if rtems_updated:
  os.chdir(options.top + '/rtems')
  
  if testing:
    print('./bootstrap -c')
  else:
    if step <= steps['bootstrap'] or not options.build_in_steps:
      result = subprocess.call(['./bootstrap', '-c'])
    
      if result != 0:
        print('The bootstrapping of RTEMS failed.')
        log(result, 'The bootstrapping of RTEMS failed')
        sys.exit(1)

# Ensure this is after the RSB has built tools and PATH is updated
# Check that rtems-bootstrap exists, is readable, and executable
if  not os.path.isfile('./rtems-bootstrap') or \
    not os.access('./rtems-bootstrap', os.R_OK) or \
    not os.access('./rtems-bootstrap', os.X_OK):
  print('This is not an RTEMS version this script supports.')
  sys.exit(0)
else:
  
  if testing:
    print('./rtems-bootstrap')
  
  else:
    result = subprocess.call(['./rtems-bootstrap'])
    
    log(result, 'rtems-bootstrap')
  
    if result != 0:
      print('rtems-bootstrap failed. ', file=sys.stderr)
      sys.exit(1)
      
    if options.build_in_steps:
      step_done('bootstrap')
      if step == options.end_step:
        sys.exit(0)
      else:
        step += 1

def generate_arguments(build_system, cpu_and_bsp, SMP_ARG):
  BB_ARGS = [build_system, '-T', options.top, '-v', '-r']
  
  # add the mailing flag
  if options.send_email:
    BB_ARGS.append('-m')

  BB_ARGS.append('-t')
  ARGS1 = [exedir() + '/build_bsp', '-V', options.version] + BB_ARGS
  
  SMP = "NOSMP"
  
  # if SMP arg is given, add it
  if SMP_ARG != '':
    ARGS1 += SMP_ARG
    SMP = 'SMP'

  ARGS2 = ARGS1.copy()
  ARGS1 += cpu_and_bsp
  ARGS2.append('-D')
  ARGS2 += cpu_and_bsp
  
  ARGS = [ARGS1, ARGS2]
  
  return ARGS

def test_single_bsp(cpu, bsp, SMP_ARG=''):
  if SMP_ARG != ''

  if cmd_exists(cpu + '-rtems' + options.version + '-gcc') or testing:
  
    arch_and_bsp = [cpu, bsp]
      
    # (NO DEBUG) if this RTEMS version has a autoconf build, then build it that way
    if 'configure.ac' in os.listdir(options.top + '/rtems'):
      AC_ARGS = generate_arguments('-a', arch_and_bsp, SMP_ARG)
      if testing:
        for arg in AC_ARGS[0]:
          print(arg, end=' ')
        print()
          
      else:
        result = subprocess.call(AC_ARGS[0])
        log(result, 'autoconf build of {} {} ({}/NODEBUG)'.format(cpu, bsp, SMP))

    # (NO DEBUG) if this RTEMS version has a waf build, then build it that way
    if 'waf' in os.listdir(options.top + '/rtems'):
      WAF_ARGS = generate_arguments('-w', arch_and_bsp, SMP_ARG)
      if testing:
        for arg in WAF_ARGS[0]:
          print(arg, end=' ')
        print()
          
      else:
        result = subprocess.call(WAF_ARGS[0])
        log(result, 'waf build of {} {} ({}/NODEBUG)'.format(cpu, bsp, SMP))
      
    # (DEBUG) if this RTEMS version has a autoconf build, then build it that way
    if 'configure.ac' in os.listdir(options.top + '/rtems'):
      if testing:
        for arg in AC_ARGS[1]:
          print(arg, end=' ')
        print()
          
      else:
        result = subprocess.call(AC_ARGS[1])
        log(result, 'autoconf build of {} {} ({}/DEBUG)'.format(cpu, bsp, SMP))
      
    # (DEBUG) if this RTEMS version has a waf build, then build it that way
    if 'waf' in os.listdir(options.top + '/rtems'):
      if testing:
        for arg in WAF_ARGS[1]:
          print(arg, end=' ')
        print()
      else:
        result = subprocess.call(WAF_ARGS[1])
        log(result, 'waf build of {} {} ({}/DEBUG)'.format(cpu, bsp, SMP))
      
        if result == 0:
          prev_dir = os.getcwd()
          os.chdir(options.top + '/rtems')
          subprocess.call(['./waf', 'distclean'])
          os.chdir(prev_dir)

  else:
    print('WARNING - no gcc for ' + cpu + ' ' + bsp)

if rsb_updated or rtems_updated:
  start_time = time.time()

  os.chdir(options.top)
  
  if step <= steps['test_bsps'] or not options.build_in_steps:
    test_single_bsp('sparc', 'erc32-sis')
    test_single_bsp('sparc', 'leon2-sis')
    test_single_bsp('sparc', 'leon3-sis')
    test_single_bsp('powerpc', 'psim')
    test_single_bsp('mips', 'jmr3904')
    test_single_bsp('riscv', 'griscv-sis')
    test_single_bsp('sparc', 'leon3-sis', '-S')

    # Make sure Spike is available for these BSPs
    if cmd_exists('spike'):
    
      bsps = ['rv32iac_spike', 'rv32imac_spike', 'rv32imafc_spike',
      'rv32imafdc_spike', 'rv32imafd_spike', 'rv32im_spike', 'rv32i_spike',
      'rv64imac_medany_spike', 'rv64imac_spike', 'rv64imafdc_medany_spike',
      'rv64imafdc_spike', 'rv64imafd_medany', 'rv64imafd_medany_spike',
      'rv64imafd_spike'
      ]

      for bsp in bsps:
        test_single_bsp('riscv', bsp)
        
      if options.build_in_steps:
        step_done('test_bsps')
        if step == options.end_step:
          sys.exit(0)
        else:
          step += 1

      # Now build all supported BSP bset stacks
      os.chdir(options.top + '/rtems-source-builder/rtems')

      bsets = ['atsamv', 'beagleboneblack', 'erc32', 'gr712rc', 'gr740', 'imx7',
       'pc', 'qoriq_e500', 'qoriq_e6500_32', 'qoriq_e6500_64', 'raspberrypi2',
        'xilinx_zynq_zc702', 'xilinx_zynq_zc706', 'xilinx_zynq_zedboard'
      ]

      for bset in bsets:
        bset_start_time = time.time()
        
        if testing:
          print( \
            '../source-builder/sb-set-builder ' + \
            '--mail --mail-to=' + options.to_addr + \
            '--mail-from=' + options.from_addr + \
            ' --log=l-' + bset + '-' + options.version + '.txt ' + \
            '--prefix=' + options.top + '/tools/' + options.version + ' ' + \
            options.version + '/bsps/' + bset + ' ' + \
            '>o-' + bset + '-' + options.version + '.txt' + ' 2>&1'
          )
          
        else:
          if step <= steps['build_bsets'] or not options.build_in_steps:
            file_name = 'o-' + bset + '-' + options.version + '.txt'
            outfile = open(file_name, 'w')
            result = subprocess.call([
              '../source-builder/sb-set-builder',
              '--mail',
              '--mail-to=' + options.to_addr,
              '--mail-from=' + options.from_addr,
              '--log=l-' + bset + '-' + options.version + '.txt',
              '--prefix=' + options.top + '/tools/' + options.version,
              options.version + '/bsps/' + bset],
              stdout=outfile,
              stderr=outfile
              )
              
            log(result, 'RSB build of bsps/' + bset)
            
            if options.build_in_steps:
              step_done('build_bsets')
              if step == options.end_step:
                sys.exit(0)
              else:
                step += 1

        bset_end_time = time.time()
        print(
          'Building all supported BSP bset stacks took' + \
          str(bset_end_time - bset_start_time) + ' seconds.'
        )

        if step <= steps['build_bsps'] or not options.build_in_steps:
          do_bsp_builder()
          if options.build_in_steps:
            step_done('build_bsps')

script_end = datetime.datetime.now()

log('START: {}'.format(script_start))
log('END:   {}'.format(script_end))

print('START: ', script_start)
print('END:   ', script_end)
sys.exit(0)
