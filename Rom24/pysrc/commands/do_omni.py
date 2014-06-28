import logging

logger = logging.getLogger()

import merc
import interp
import state_checks

def do_omni(ch, argument):
    if state_checks.IS_SET(ch.act, merc.PLR_OMNI):
        ch.send("Omnimode removed\n")
        ch.act = state_checks.REMOVE_BIT(ch.act, merc.PLR_OMNI)
    else:
        ch.send("Omnimode enabled.\n")
        ch.act = state_checks.SET_BIT(ch.act, merc.PLR_OMNI)


interp.register_command(interp.cmd_type('omni', do_omni, merc.POS_DEAD, merc.IM, merc.LOG_NORMAL, 1))
