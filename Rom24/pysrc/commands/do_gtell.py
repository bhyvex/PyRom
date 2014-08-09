import logging

logger = logging.getLogger()

import merc
import interp


def do_gtell(ch, argument):
    if not argument:
        ch.send("Tell your group what?\n")
        return
    if ch.comm.is_set(merc.COMM_NOTELL):
        ch.send("Your message didn't get through!\n")
        return
    for gch in merc.characters.values():
        if gch.is_same_group(ch):
            act("$n tells the group '$t'", ch, argument, gch, merc.TO_VICT, merc.POS_SLEEPING)
    return


interp.register_command(interp.cmd_type('gtell', do_gtell, merc.POS_DEAD, 0, merc.LOG_NORMAL, 1))
interp.register_command(interp.cmd_type(';', do_gtell, merc.POS_DEAD, 0, merc.LOG_NORMAL, 0))
