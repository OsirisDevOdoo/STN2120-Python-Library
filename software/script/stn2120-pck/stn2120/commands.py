

import logging

logger = logging.getLogger(__name__)


class STNCommand():
    def __init__(self, cmd, description, fast=None):
        self.cmd         = cmd
        self.description = description
        self.fast        = fast

    def __str__(self):
        return "%s: %s" % (self.command, self.desc)

    def __hash__(self):
        # needed for using commands as keys in a dict (see async.py)
        return hash(self.command)

    def __eq__(self, other):
        if isinstance(other, OBDCommand):
            return (self.command == other.command)
        else:
            return False

__ST__ = [
    #
    #
    # General ST Commands
    STNCommand("STBR"      , "baud	Switch UART baud rate in software-friendly way"),
    STNCommand("STBRT"     , "ms	Set UART baud rate switch timeout"),
    STNCommand("STSBR"     , "baud	Switch UART baud rate in terminal-friendly way"),
    STNCommand("STWBR"     , "Write current UART baud rate to NVM"),
    STNCommand("STRSTNVM"	, "Reset NVM to factory defaults"),
    STNCommand("STSAVCAL"	, "Save all calibration values"),
    #
    # Device ID ST Commands
    STNCommand("STDI"    ,  "Print device hardware ID string (e.g., “OBDLink r1.7”)") ,
    STNCommand("STI"	  ,  "Print firmware ID string (e.g., “STN1100 v1.2.3”)") ,
    STNCommand("STMFR"	  ,  "Print device manufacturer ID string") ,
    STNCommand("STSATI"  ,  "ascii  Set ATI device ID string") ,
    STNCommand("STSDI"   ,  "ascii	  Set device hardware ID string") ,
    STNCommand("STSN"	  ,  "Print device serial number") ,
    STNCommand("STS@1"   ,  "ascii	Set AT@1 device description string") ,
    #
    #  Voltage Reading ST Commands
    STNCommand("STVCAL@"  , "[volts [, offset]]	Calibrate voltage measurement"),
    STNCommand("STVR"     ,  "[precision] Read voltage in volts"),
    #
    #  OBD Protocol ST Commands
    STNCommand("STP" ,	      "Set current protocol") ,
    STNCommand("STPBR" ,    "*baud	Set current OBD protocol baud rate") ,
    STNCommand("STPBRR" ,   "Report actual OBD protocol baud rate") ,
    STNCommand("STPC" ,	 "Close current protocol") ,
    STNCommand("STPCB" ,    "*0/1") ,
    STNCommand("STPO" ,	 "Open current protocol") ,
    STNCommand("STPR" ,	 "Report current protocol number") ,
    STNCommand("STPRS" ,	 "Report current protocol string") ,
    STNCommand("STPTO" ,	 "Set OBD request timeout") ,
    #
    # ISO Specific ST Commands
    STNCommand("STIAT"   ,  "0	1") ,
    STNCommand("STIP"    ,  "N	E") ,
    STNCommand("STIP1X"  ,  "ms	Set maximum interbyte time for receiving messages (P1 max)") ,
    STNCommand("STIP4"   ,  "ms	Set interbyte time for transmitting messages (P4)") ,
    #
    # CAN Specific ST Commands
    STNCommand("STCFCPA"  ,   "ttt, rrr	Add flow control 11-bit ID pair") ,
    STNCommand("STCFCPC"  ,   "Clear all flow control 11-bit ID pairs") ,
    STNCommand("STCMM"    ,   "mode	Set CAN monitoring mode") ,
    STNCommand("STCSWM"   ,   "mode	Set Single Wire CAN transceiver mode") ,
    #
    # Monitoring ST Commands
    STNCommand("STM"  ,	"Monitor OBD bus using current filters") ,
    STNCommand("STMA" ,	"Monitor all messages on OBD bus") ,
    #
    # Filtering ST Commands
    STNCommand("STFA"  ,	  "Enable automatic filtering" ) ,
    STNCommand("STFAC"  ,	  "Clear all filters" ) ,
    STNCommand("STFBA"  ,     "[pattern] , [mask]	Add block filter" ) ,
    STNCommand("STFBC"  ,	  "Clear all block filters" ) ,
    STNCommand("STFFCA"  ,    "[pattern] , [mask]	Add CAN flow control filter" ) ,
    STNCommand("STFFCC"  ,	  "Clear all CAN flow control filters" ) ,
    STNCommand("STFPA"  ,     "[pattern] , [mask]	Add pass filter" ) ,
    STNCommand("STFPC"  ,	  "Clear all pass filters" ) ,
    STNCommand("STFPGA"  ,    "pgn [, tgt address]	Add SAE J1939 PGN filter" ) ,
    STNCommand("STFPGC"  ,	  "Clear all SAE J1939 PGN filters" ) ,
    #
    # PowerSave ST Commands
    STNCommand("STSLCS"	 ,  "Print active PowerSave configuration summary") ,
    STNCommand("STSLEEP"  ,  "[delay]	Enter sleep mode with optional delay") ,
    STNCommand("STSLLT"	 ,  "Report last sleep/wakeup triggers") ,
    STNCommand("STSLPCP"  ,  "0	1") ,
    STNCommand("STSLU"    ,  "sleep, wakeup	UART sleep/wakeup triggers on/off") ,
    STNCommand("STSLUIT"  ,  "sec	Set UART inactivity timeout") ,
    STNCommand("STSLUWP"   ,  "min, max	Set UART wakeup pulse timing") ,
    STNCommand("STSLVG"    ,  "on	off") ,
    STNCommand("STSLVGW"   ,  "[+	-]volts, ms") ,
    STNCommand("STSLVL"    ,  "sleep, wakeup	Voltage level sleep/wakeup triggers on/off") ,
    STNCommand("STSLVLS"   ,  "<	> volts") ,
    STNCommand("STSLVLW"   ,  "<	> volts") ,
    STNCommand("STSLX"     ,  "sleep, wakeup	External sleep trigger on/off") ,
    STNCommand("STSLXP"    ,  "0	1") ,
    STNCommand("STSLXS"	  ,  "Print external SLEEP input status") ,
    STNCommand("STSLXST"   ,  "ms	Set minimum active time for external sleep trigger before entering sleep") ,
    STNCommand("STSLXWT"   ,  "ms	Set minimum inactive time for external sleep trigger before wakeup") ,
    #
    # General Purpose I/O ST Commands
    STNCommand("STGPC" ,       "pin1:options [, …, pinN:options]	Configure I/O pins") ,
    STNCommand("STGPIR" ,      "pin1 [, …, pinN]	Read inputs") ,
    STNCommand("STGPIRH" ,     "pin1 [, …, pinN]	Read inputs, report value as hex") ,
    STNCommand("STGPOR" ,      "pin1 [, …, pinN]	Read output latches") ,
    STNCommand("STGPOW" ,      "pin1:state [, …, pinN:state]	Write output latches") ,
    #
    #
    STNCommand("STCFCPA"  ,   "Add CAN flow control 11-bit ID pair") ,
    STNCommand("STCFCPC"  ,   "Clear all CAN flow control 11-bit ID pairs") ,
    STNCommand("STFPA"  ,     "Add pass filter") ,
    STNCommand("STFBA"  ,     "Add block filter") ,
    STNCommand("STFFCA"  ,    "Add CAN flow control filter") ,
    STNCommand("STFPGA"  ,    "Add SAE J1939 PGN filter") ,
    STNCommand("STFAC"  ,     "Clear all filters") ,
    STNCommand("STFPC"  ,     "Clear all pass filters") ,
    STNCommand("STFBC"  ,     "Clear all block filters") ,
    STNCommand("STFFCC"  ,    "Clear all CAN flow control filters") ,
    STNCommand("STFPGC"  ,    "Clear all SAE J1939 PGN filters") ,
    STNCommand("STPBR"  ,     "Set ISO baud rate") ,
    STNCommand("STPCB"  ,     "Turn ISO manual checksum off/on") ,
    STNCommand("STPBRR"  ,    "Report actual OBD protocol baud rate") ,
]



class Commands ():
    """
    """
    def __init__(self):
        self.commands = [
            __ST__,
        ]
        for n in self.commands:
            self.__dict__[n.cmd] = n



    def __getitem__ (self, key):
        """
        """
        try:
            basestring
        except NameError:
            basestring = str

        if isinstance(key, int):
            return self.modes[key]
        elif isinstance(key, basestring):
            return self.__dict__[key]
        else:
            logger.warning("COMMANDS: OBD commands can only be retrieved by PID value or dict name")


    def has_command(self, c):
        """ checks for existance of a command by command object """
        return c in self.__dict__.values()



commands = Commands()
