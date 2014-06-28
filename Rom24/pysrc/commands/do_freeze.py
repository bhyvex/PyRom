import logging

logger = logging.getLogger()

import merc
import interp
import save
import game_utils
import handler_game
import state_checks


def do_freeze(ch, argument):
    argument, arg = game_utils.read_word(argument)
    if not arg:
        ch.send("Freeze whom?\n")
        return
    victim = ch.get_char_world(arg)
    if not victim:
        ch.send("They aren't here.\n")
        return
    if state_checks.IS_NPC(victim):
        ch.send("Not on NPC's.\n")
        return
    if victim.get_trust() >= ch.get_trust():
        ch.send("You failed.\n")
        return
    if state_checks.IS_SET(victim.act, merc.PLR_FREEZE):
        victim.act = state_checks.REMOVE_BIT(victim.act, merc.PLR_FREEZE)
        victim.send("You can play again.\n")
        ch.send("FREEZE removed.\n")
        handler_game.wiznet("$N thaws %s." % victim.name, ch, None, merc.WIZ_PENALTIES, merc.WIZ_SECURE, 0)
    else:
        victim.act = state_checks.SET_BIT(victim.act, merc.PLR_FREEZE)
        victim.send("You can't do ANYthing!\n")
        ch.send("FREEZE set.\n")
        handler_game.wiznet("$N puts %s in the deep freeze." % victim.name, ch, None, merc.WIZ_PENALTIES,
                            merc.WIZ_SECURE, 0)

    save.save_char_obj(victim)
    return


interp.register_command(interp.cmd_type('freeze', do_freeze, merc.POS_DEAD, merc.L4, merc.LOG_ALWAYS, 1))
