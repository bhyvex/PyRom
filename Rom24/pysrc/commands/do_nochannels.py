import logging

logger = logging.getLogger()

import merc
import interp
import game_utils
import handler_game
import state_checks


# RT nochannels command, for those spammers
def do_nochannels(ch, argument):
    argument, arg = game_utils.read_word(argument)
    if not arg:
        ch.send("Nochannel whom?")
        return
    victim = ch.get_char_world(arg)
    if not victim:
        ch.send("They aren't here.\n")
        return
    if victim.get_trust() >= ch.get_trust():
        ch.send("You failed.\n")
        return
    if state_checks.IS_SET(victim.comm, merc.COMM_NOCHANNELS):
        victim.comm = state_checks.REMOVE_BIT(victim.comm, merc.COMM_NOCHANNELS)
        victim.send("The gods have restored your channel priviliges.\n")
        ch.send("NOCHANNELS removed.\n")
        handler_game.wiznet("$N restores channels to %s" % victim.name, ch, None, merc.WIZ_PENALTIES, merc.WIZ_SECURE, 0)
    else:
        victim.comm = state_checks.SET_BIT(victim.comm, merc.COMM_NOCHANNELS)
        victim.send("The gods have revoked your channel priviliges.\n")
        ch.send("NOCHANNELS set.\n")
        handler_game.wiznet("$N revokes %s's channels." % victim.name, ch, None, merc.WIZ_PENALTIES, merc.WIZ_SECURE, 0)
    return


interp.register_command(interp.cmd_type('nochannels', do_nochannels, merc.POS_DEAD, merc.L5, merc.LOG_ALWAYS, 1))
