#!/usr/bin/env python
#
#  check_as_paths: queries a route server for AS paths to your prefixes
#
#  Copyright (c) 2014 Andrew Wentzell
#  https://github.com/awentzell/check-as-path
#

#### DEFAULTS: change if you want, or override on command line

server = 'route-views.routeviews.org'
username = 'rviews'
password = False

####

import getopt
import pexpect
import re
import sys

def usage():
    sys.stderr.write('usage: %s [-hv] [-s server] [-u username] [-P password]\n\
          -a <list of ASNs> -p <list of prefixes>\n\n\
Options:\n\
  -a, --asns=LIST           list of AS numbers to look for in AS paths\n\
  -h, --help                show this help message\n\
  -P, --password=PASSWORD   password to use for login, if prompted\n\
  -p, --prefixes=LIST       list of prefixes to query\n\
  -s, --server=SERVER       route server to query\n\
  -u, --username=USERNAME   username to use for login, if prompted\n\
  -v, --verbose             print more info about AS paths\n' % sys.argv[0])

try:
    opts, args = getopt.getopt(sys.argv[1:], 'a:hP:p:s:u:v', ['asns=', 'help', 'password=', 'prefixes=', 'server=', 'username=', 'verbose'])
except getopt.GetoptError as err:
    # print help information and exit:
    print str(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(1)

asns = []
prefixes = []
verbose = False

for o, a in opts:
    if o in ("-a", "--asns"):
        asns = a.split(',')
    elif o in ("-h", "--help"):
        usage()
        sys.exit()
    elif o in ("-P", "--password"):
        password = a
    elif o in ("-p", "--prefixes"):
        prefixes = a.split(',')
    elif o in ("-s", "--server"):
        server = a
    elif o in ("-u", "--username"):
        username = a
    elif o in ("-v", "--verbose"):
        verbose = True
    else:
        assert False, "unhandled option"

if asns == [] and prefixes == []:
    usage()
    sys.exit(1)

if verbose:
    print "server:", server
    print "username:", username
    print "password:", password
    print "asns:", asns
    print "prefixes:", prefixes

logged_in = False
#logfile = open ('check_as_paths.log', 'w')
child = pexpect.spawn('telnet %s' % server)
#child.logfile = logfile

while 1:
    i = child.expect([pexpect.EOF, pexpect.TIMEOUT, '(?i)username: ', '(?i)password: ', 'Permission denied', 'Connection closed', '>[ ]*$', '#[ ]*$'])
    if i == 0: # EOF
        print 'ERROR!'
        print 'Got EOF. Here is what the child process said:'
        print child.before, child.after
        sys.exit(2)
    elif i == 1: # Timeout
        print 'ERROR!'
        print 'Connection timed out. Here is what the child process said:'
        print child.before, child.after
        sys.exit(2)
    elif i == 2: # Username prompt
        child.sendline(username)
    elif i == 3: # Password prompt
        if password:
            child.sendline(password)
        else:
            print 'ERROR!'
            print 'Server asked for password, but none set. Here is what the child process said:'
            print child.before, child.after
            sys.exit(2)
    elif i == 4 or i == 5: # Connection closed before we finished
        child.close()
        child = pexpect.spawn('telnet %s' % server)
        #child.logfile = logfile
    elif i == 6 or i == 7: # '>' or '#' prompt
        break
    else:
        print 'ERROR!'
        print 'expect returned an unexpected value.'
        print child.before, child.after
        sys.exit(2)

# disable the pager
child.sendline('terminal length 0')
child.expect('>')

for prefix in prefixes:
    child.sendline('show ip bgp %s' % prefix)
    child.expect('>')
    lines = child.before.splitlines()
    for asn in asns:
        as_matches = 0
        for line in lines:
            if re.match("^  (?:\d+ )*%s(?: \d+)*" % asn, line):
                as_matches += 1
        if as_matches == 0:
            print " *** ALERT ***  %s paths to %s via ASN %s" % (as_matches, prefix, asn)
        elif verbose:
            print "%s paths to %s via ASN %s" % (as_matches, prefix, asn)

child.sendline('quit')
child.close()
