import logging

logger = logging.getLogger()

import merc
import interp
import save
import comm


def do_reboot(ch, argument):
    if ch.invis_level < merc.LEVEL_HERO:
        ch.do_echo("Reboot by %s." % ch.name)
    merc_down = True  # TODO:  This needs to eventually be fixed
    for d in merc.descriptor_list[:]:
        vch = merc.CH(d)
        if vch:
            save.save_char_obj(vch)
            comm.close_socket(d)


interp.register_command(interp.cmd_type('reboot', do_reboot, merc.POS_DEAD, merc.L1, merc.LOG_ALWAYS, 1))
