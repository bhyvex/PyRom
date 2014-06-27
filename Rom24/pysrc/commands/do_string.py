import logging

logger = logging.getLogger()

import merc
import interp
import special


def do_string(ch, argument):
    argument, type = merc.read_word(argument)
    argument, arg1 = merc.read_word(argument)
    argument, arg2 = merc.read_word(argument)
    arg3 = argument

    if not type or not arg1 or not arg2 or not arg3:
        ch.send("Syntax:\n")
        ch.send("  string char <name> <field> <string>\n")
        ch.send("    fields: name short long desc title spec\n")
        ch.send("  string obj  <name> <field> <string>\n")
        ch.send("    fields: name short long extended\n")
        return
    if "mobile".startswith(type) or "character".startswith(type):
        victim = ch.get_char_world(arg1)
        if not victim:
            ch.send("They aren't here.\n")
            return
        # clear zone for mobs
        victim.zone = None
        # string something
        if "name".startswith(arg2):
            if not merc.IS_NPC(victim):
                ch.send("Not on PC's.\n")
                return
            victim.name = arg3
            return
        if "description".startswith(arg2):
            victim.description = arg3
            return
        if "short".startswith(arg2):
            victim.short_descr = arg3
            return
        if "long".startswith(arg2):
            victim.long_descr = arg3 + "\n"
            return
        if "title".startswith(arg2):
            if merc.IS_NPC(victim):
                ch.send("Not on NPC's.\n")
                return
            merc.set_title(victim, arg3)
            return
        if "spec".startswith(arg2):
            if not merc.IS_NPC(victim):
                ch.send("Not on PC's.\n")
                return
            spec = merc.prefix_lookup(special.spec_table, arg3)
            if not spec:
                ch.send("No such spec fun.\n")
                return
            victim.spec_fun = spec
            ch.send("spec_fun set.\n")
            return
    if "object".startswith(type):
        # string an obj
        obj = ch.get_obj_world(arg1)
        if not obj:
            ch.send("Nothing like that in heaven or earth.\n")
            return
        if "name".startswith(arg2):
            obj.name = arg3
            return
        if "short".startswith(arg2):
            obj.short_descr = arg3
            return
        if "long".startswith(arg2):
            obj.description = arg3
            return
        if "extended".startswith(arg2) or "ed".startswith(arg2):
            argument, arg3 = merc.read_word(argument)
            if argument == None:
                ch.send("Syntax: oset <object> ed <keyword> <string>\n")
                return
            argument += "\n"
            ed = merc.EXTRA_DESCR_DATA()
            ed.keyword = arg3
            ed.description = argument
            obj.extra_descr.append(ed)
            return
    # echo bad use message
    ch.do_string("")


interp.register_command(interp.cmd_type('string', do_string, merc.POS_DEAD, merc.L5, merc.LOG_ALWAYS, 1))
