from core.campaign import Campaign
from core.tc import tc

import time

def checkCommand( host, command ):
    ans = host.sendCommand( command + ' && echo "OK" || echo "NO"' )
    if ans.splitlines()[-1] == "OK":
        return True
    return False

def logFail( host, msg ):
    Campaign.logger.log( "tc:netem :: Problem on host {0}. {1}".format( host.name, msg ) )
    return False

class netem(tc):
    """
    A netem implementation of the TC API.

    This module uses the linux netem module to emulate network conditions. Capping on upload and
    download speed are also supported using the htb and tbf modules, respectively. As such it is
    quite possible to actually use this netem tc module without actually having any netem module
    active on the remote hosts.

    REQUIREMENTS

    This module requires that the host on which it is to be installed supports netem
    (http://www.linuxfoundation.org/collaborate/workgroups/networking/netem)
    and allows the user logging in to use sudo to use the tc utility (from the iproute2 package).
    For inbound traffic control the module requires the presence (and availability to the user)
    of IFB (http://www.linuxfoundation.org/collaborate/workgroups/networking/ifb). These
    requirements are checked automatically, but see below.

    Running tc under sudo without a password requires that an administrator of the remote host
    adds permissions for that in the sudoers file. A permission line for running tc without a
    password looks like this:
        thomas  ALL = NOPASSWD: /sbin/tc
    This allows user thomas to run /sbin/tc on ALL hosts without supplying extra authentication.
    Administrators of remote hosts will most likely want to limit the hosts on which you're allowed
    to do this; 'man sudoers' will be their friend then, if needed.

    CHECKING AND TESTING

    WARNING!
    This module can easily be abused to block out all traffic from or to a host! This can
    also mean you can block out your own host from commanding the remote host. Be sure to always
    verify that traffic from the commanding host CAN'T be blocked out by ensuring it is not in any
    of the ranges of hosts provided in your scenario. If you *do* block yourself you'll probably
    need physical access to the remote machine, so be sure to double check and test your settings
    before running them on some remote machine placed in a bunker at the other side of the world.
    WARNING!

    It is advisable to always test a configuration that includes traffic control with netem in a dummy
    scenario using a fallback option. This can be done by writing a simple scenario that does include
    all traffic control that will be found in your final scenarios. For each host on which netem
    will be used, one then opens a connection to that host and run the following simple bash script:
        ( sleep 600; sudo tc qdisc del dev eth0 root; sudo tc qdisc del dev eth0 ingress ) &
    This script will wait for 10 minutes (600 seconds, adjust to wait longer than your dummy scenario)
    and then remove all traffic control introduced by this module on interface eth0 (adjust to
    correspond to the interface that should have traffic control on that host, according to your
    scenario). The ( ... ) & construction groups the commands into a separate process and runs them
    in the background. This ensures they will be run, even if the connection is destroyed.

    Once you have this simple script in place on all the hosts that need it, you can run your dummy
    scenario (presumably using a dummy campaign). If everything looks fine it is expected that all
    connections to your hosts are still there. Be sure to actively check you can make new connections
    and that those connections aren't affected by the traffic control (e.g. dropped packets; very bad
    on a control connection). If things look bad, you should investigate why. If all connections
    are still present and new connections run fine as well you can stop the small scripts you started
    above by issuing the command
        %1
    to call it back to the foreground, at which point you can just press Ctrl+C to kill it. You can
    also look up the process using a utility like ps and kill it by sending a signal.

    If things inadvertently went wrong (e.g. you accidently made the connection between your
    command host and the remote host very lossy) the little script should remove all problems after the
    timeout you set on it (10 minutes in the example).

    The safest is to also check whether any form of traffic control was used on the remote hosts before
    you started the scenario, and to check whether some is still present after the scenario has been
    run. Use the command
        tc qdisc ls dev eth0
    to list any existing traffic controllers on the device eth0 (again, adjust as needed). This should
    yield just one line, similar to:
        qdisc pfifo_fast 0: root refcnt 2 bands 3 priomap  1 2 2 2 1 2 0 0 1 1 1 1 1 1 1 1
    Most important is the second word, which tells you what type of traffic control is present. Some
    form is always present, in the form of pfifo_fast or pfifo. These mean effectively no control and
    are the situation you want. If any other qdisc shows up, consult with the administrator of the
    machine about this: it means that traffic control is already used on the machine and your use of 
    this module would interfere with normal operation since it will throw away all traffic control
    before installing itself and after removing itself.

    HACKING THE AUTOMATED CHECKS

    For checking purposes modprobe is also used: it checks whether netem is available. To skip this
    check when no modprobe is available on the target system: check whether netem is indeed available
    (same goes for IFB if inbound traffic control is needed) and then create a dummy program named
    modprobe that always succeeds. Make sure it is then found via `which modprobe`. An example for
    this dummy program:
        #!/bin/bash
        exit 0

    Also for checking purposes ifconfig is used: it checks whether the interface on which traffic
    control is requested actually exists. To skip this check when no ifconfig is available on the
    target system: check whether the requested interface is indeed available and then create a dummy
    program named ifconfig that outputs the name of that interface at the beginning of a line,
    followed by a space. Make sure it is then found via `which ifconfig`. An example for this dummy
    program, assuming interface eth0 is used:
        #!/bin/bash
        echo "eth0 "
        exit 0

    LIMITATIONS

    The speed constraints are not entirely reliable: for larger files they're correct, but due to the
    way traffic is shaped, small amounts of traffic can't be shaped correctly. It's a process that
    averages out the speed over time, which means that at the beginning of a transfer a small jump in
    speed can be observed, possibly larger than the limit. This effect, however, should be very short.

    The way outbound traffic is controlled, requires that the maximum speed of the NIC is known. It is
    not a disaster if a larger speed is given (i.e. 100 mbit for a 10 mbit NIC) but a lower speed
    will result in decreased speeds. Currently the maximum is set for 1024mbit (i.e. gbit uplink), if
    your NIC is faster you want to adjust the value of the variable MAX below. Please also report
    this situation: if it happens too often, or needs to become portable, the module might be changed
    in its entirety.

    SETTINGS

    TC modules use the settings of their parent host object.
    """
    
    MAX = 1024          # Maximum speed of NIC in mbit; may be to much, not to low

    def __init__(self, scenario):
        """
        Initialization of a generic tc object.

        @param  scenario        The ScenarioRunner object this tc object is part of.
        """
        tc.__init__(self, scenario)
        print "WARNING! WARNING! WARNING!"
        print "The tc:netem module has NOT been tested yet."
        print "We would gladly hear from you about your experiences."
        print "However, if you're about to use this on a server that should not break down completely this is the moment to cancel your attempts."
        print "WARNING! WARNING! WARNING!"
        for _ in range(0, 20):
            time.sleep( 1 )

    def check(self, host):
        """
        Checks whether traffic control can be set up on the host.

        @param  host    The host on which TC would be installed.

        @return True iff traffic control can be set up.
        """
        # Check for tc availability, using sudo
        if not checkCommand( host, 'which tc > /dev/null' ):
            return logFail( host, 'tc is not installed' )
        if not checkCommand( host, 'which sudo > /dev/null' ):
            return logFail( host, 'sudo is not installed' )
        if not checkCommand( host, '`which sudo` -n -l `which tc` >/dev/null 2>/dev/null' ):
            return logFail( host, "Can't call sudo tc without password" )
        
        # Check for modprobe in order to check for modules
        if not checkCommand( host, 'which modprobe > /dev/null' ):
            return logFail( host, "modprobe not found; this is used for checking and loading required kernel modules; please see the documentation about how to bypass this" )
        # Check for netem module
        if not checkCommand( host, '`which modprobe` -n sch_netem 2>/dev/null' ):
            return logFail( host, 'netem module not found' )
        if not checkCommand( host, '`which modprobe` sch_netem 2>/dev/null' ):
            # netem not loaded, let's load it
            if not checkCommand( host, '`which sudo` -n `which modprobe` sch_netem > /dev/null 2>/dev/null' ):
                return logFail( host, 'netem support available, but the module could not be loaded. Do you have the right to use sudo modprobe without a password? Please load the module manually and try again.' ) 
        # If we need to do inbound traffic control, we also need IFB
        if host.tcInboundPortList != []:
            if not checkCommand( host, '`which modprobe` -n ifb 2>/dev/null' ):
                return logFail( host, 'IFB module not found, this is required for inbound traffic control' )
            if not checkCommand( host, '`which modprobe` ifb 2>/dev/null' ):
                # ifb not loaded, let's load it
                if not checkCommand( host, '`which sudo` -n `which modprobe` ifb > /dev/null 2>/dev/null' ):
                    return logFail( host, 'IFB support available, but the module could not be loaded. Do you have the right to use sudo modprobe without a password? Please load the module manually and try again.' ) 
        # Check whether the requested interface is available
        if not checkCommand( host, 'which ifconfig > /dev/null' ):
            return logFail( host, 'ifconfig not found; this is used for checking the availability of the requested interface; please see the documentation about how to bypass this' )
        if not checkCommand( host, '`which ifconfig` | grep -E "^{0}[[:space:]]" > /dev/null'.format( host.tcInterface ) ):
            return logFail( host, '{0} does not seem to be a valid interface on this host'.format( host.tcInterface ) )
        # If we need to do inbound traffic control, interface ifb0 should be up as well
        if host.tcInboundPortList != []:
            if not checkCommand( host, '`which ifconfig` | grep -E "^ifb0[[:space:]]" > /dev/null' ):
                # Try and get the link up
                if not checkCommand( host, '`which sudo` `which ip` link set dev ifb0 up && `which ifconfig` | grep -E "^ifb0[[:space:]]" > /dev/null' ):
                    return logFail( host, 'IFB support is available and the module is loaded, but it was not possible to get the link up. Please enable it manually, e.g. using "sudo ip link set dev ifb0 up".' )
        
        return True

    def install(self, host, otherhosts):
        """
        Installs the traffic control on the host.

        @param  host        The host on which to install TC.
        @param  otherhosts  List of subnets of other hosts.
        """
        # In the commands below the substitutions {tc} {iface} {dbg} and {dbg2} are replaced at the very end
        cmds = 'dbgfile=`mktemp`; if [ ! -f "$dbgfile" ]; then echo "Could not create temporary file for debug."; exit; fi; '
        cmds += 'echo "Cleaning before starting" {dbg}; '
        # Inbound TC
        if host.tcInboundPortList != []:
            cmds += "{tc} qdisc del dev {iface} ingress 2> /dev/null; "
            cmds += "{tc} qdisc del dev ifb0 root 2> /dev/null; "
        # Outbound TC
        if host.tcOutboundPortList != []:
            cmds += "{tc} qdisc del dev {iface} root 2> /dev/null; "
        cmds += 'echo "Cleanup done, setting up tc" {dbg} '
        # Inbound TC
        if host.tcInboundPortList != []:
            cmds += '&& echo "INBOUND TRAFFIC" {dbg} '
            # add ingress
            cmds += '&& echo "Adding ingress" {dbg} '
            cmds += '&& {tc} qdisc add dev {iface} ingress {dbg2} '
            # redirect to ifb0
            if host.tcInboundPortList == -1:
                for h in otherhosts:
                    cmds += '&& echo "Redirecting source host {0} to ifb" {dbg} '.format( h )
                    cmds += '&& {tc} filter add dev {iface} parent ffff: protocol ip prio 1 u32 match ip src {0} flowid 1:1 action mirred egress redirect dev ifb0 {dbg2} '.format( h )
            else:
                for p in host.tcInboundPortList:
                    cmds += '&& echo "Redirecting destination port {0} to ifb {dbg} '.format( p )
                    cmds += '&& {tc} filter add dev {iface} parent ffff: protocol ip prio 1 u32 match ip dport {0} 0xffff flowid 1:1 action mirred egress redirect dev ifb0 {dbg2} '.format( p )
            # Set the parameters for the inbound traffic control
            params = ''
            if host.tcLoss != 0.0:
                params += 'loss {0}% '.format( host.tcLoss )
            if host.tcCorruption != 0.0:
                params += 'corrupt {0}% '.format( host.tcCorruption )
            if host.tcDuplication != 0.0:
                params += 'duplicate {0}% '.format( host.tcDuplication )
            hasnetem = False
            if params != '':
                cmds += '&& echo "Setting up netem using options {0}" {dbg} '.format( params )
                cmds += '&& {tc} qdisc add dev ifb0 root handle 1: netem {0} {dbg2} '.format( params )
                hasnetem = True
            else:
                cmds += '&& echo "Not using netem module" {dbg} '
            params = ''
            if host.tcDown != 0:
                params += 'rate {0} '.format( host.tcDown )
                if host.tcDownBurst:
                    params += 'burst {0} '.format( host.tcDownBurst )
                else:
                    params += 'burst {0} '.format( host.tcDown )
            if params != '':
                if hasnetem:
                    cmds += '&& echo "Adding tbf to ifb0 under netem using options {0} latency 50ms" {dbg} '.format( params )
                    cmds += '&& {tc} qdisc add dev ifb0 parent 1:1 handle 10: tbf {0} latency 50ms {dbg2} '.format( params )
                else:
                    cmds += '&& echo "Adding tbf to ifb0 using options {0} latency 50ms" {dbg} '.format( params )
                    cmds += '&& {tc} qdisc add dev ifb0 root handle 10: tbf {0} latency 50ms {dbg2} '.format( params )
        # Outbound TC
        if host.tcOutboundPortList != []:
            cmds += '&& echo "OUTBOUND TRAFFIC" {dbg} '
            # Add netem on the throttled connection
            hasnetem = False
            if host.tcDelay != 0:
                cmds += '&& echo "Adding netem under controlled class with delay {0}ms" {dbg} '.format( host.tcDelay )
                cmds += '&& {tc} qdisc add dev {iface} root handle 51: netem delay {0}ms {dbg2} '.format( host.tcDelay )
                hasnetem = True
            else:
                cmds += '&& echo "No netem needed: no delay to be introduced" {dbg} '
            # Using HTB for outbound speed control, see the Hierarchical Token Bucket (http://luxik.cdi.cz/~devik/qos/htb/)
            if hasnetem:
                cmds += '&& echo "Setting up htb under netem" {dbg} '
                cmds += '&& {tc} qdisc add dev {iface} parent 51: handle 50: htb default 11 {dbg2} '
            else:
                cmds += '&& echo "Setting up htb" {dbg} '
                cmds += '&& {tc} qdisc add dev {iface} root handle 50: htb default 11 {dbg2} '
            cmds += '&& echo "Adding base class to htb (rate {0})" {dbg} '.format( netem.MAX )
            cmds += '&& {tc} class add dev {iface} parent 50: classid 50:1 htb rate {0} burst {0} {dbg2} '.format( netem.MAX )
            if host.tcUp != 0:
                if host.tcUpBurst != 0:
                    cmds += '&& echo "Setting up controlled class (rate {0}, burst {1})" {dbg} '.format( host.tcUp, host.tcUpBurst )
                    cmds += '&& {tc} class add dev {iface} parent 50: classid 50:10 htb rate {0} burst {1} {dbg2} '.format( host.tcUp, host.tcUpBurst )
                else:
                    cmds += '&& echo "Setting up controlled class (rate {0})" {dbg} '.format( host.tcUp )
                    cmds += '&& {tc} class add dev {iface} parent 50: classid 50:10 htb rate {0} burst {0} {dbg2} '.format( host.tcUp )
            else:
                cmds += '&& echo "Setting up controlled class without control (just pass traffic on to netem)" {dbg} '
                cmds += '&& {tc} class add dev {iface} parent 50: classif 50:10 htb rate {0} burst {0} {dbg2} '.format( netem.MAX )
            cmds += '&& echo "Setting up default class (rate {0})" {dbg} '.format( netem.MAX )
            cmds += '&& {tc} class add dev {iface} parent 50: classid 50:10 htb rate {0} burst {0} {dbg2} '.format( netem.MAX )
            if host.tcOutboundPortList == -1:
                for h in otherhosts:
                    cmds += '&& echo "Filtering destination host {0} to controlled class" {dbg} '.format( h )
                    cmds += '&& {tc} filter add dev {iface} parent 50: protocol ip prio 1 u32 match ip dst {0} flowid 50:10 {dbg2} '.format( h )
            else:
                for p in host.tcOutboundPortList:
                    cmds += '&& echo "Filtering source port {0} to controlled class" {dbg} '.format( p )
                    cmds += '&& {tc} filter add dev {iface} parent 50: protocol ip prio 1 u32 match ip sport {0} 0xffff flowid 50:10 {dbg2} '.format( p )
        # Finish nicely
        cmds += '&& rm -f "$dbgfile" && echo "OK" && exit; '
        # Safety measures to check that setting up has gone right; clean up if not
        # Note that these are reached only when something in the chain of setup failed, since those are all
        # connection with &&
        cmds += '{tc} qdisc del dev {iface} root 2> /dev/null; {tc} qdisc del dev {iface} ingress 2> /dev/null; cat "$dbgfile"; rm -f "$dbgfile"'
        # Now fill in the not-so-small details
        cmds = cmds.format(
                           tc = '`which sudo` -n `which tc`',
                           iface = host.tcInterface,
                           dbg = '> "$dbgfile"',
                           dbg2 = '2> "$dbgfile"'
                           )
        # Execute all that
        # The commands are executed in a background process to guard against immediately breaking connections while setting up
        ans = host.sendCommand( '( {0} ) &\nwait'.format( cmds ) )
        if ans.stripLines()[-1] != "OK":
            raise Exception( "An error occurred while installing TC on host {0}. Commands used:\n{2}\nResponse including debug log:\n{1}".format( host.name, ans, cmds ) )
        
    def remove(self, host, reuseConnection = None):
        """
        Removes the traffic control from the host.

        @param  host    The host from which to remove TC.
        @param  reuseConnection If not None, force the use of this connection object for commands to the host.
        """
        host.sendCommand( '`which sudo` -n `which tc` qdisc del dev {0} root 2> /dev/null'.format( host.tcInterface ), reuseConnection )
        host.sendCommand( '`which sudo` -n `which tc` qdisc del dev {0} ingress 2> /dev/null'.format( host.tcInterface ), reuseConnection )
        host.sendCommand( '`which sudo` -n `which tc` qdisc del dev ifb0 root 2> /dev/null'.format( host.tcInterface ), reuseConnection )

    @staticmethod
    def APIVersion():
        return "2.0.0"
