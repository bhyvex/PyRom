"""
#**************************************************************************
 *  Original Diku Mud copyright=C) 1990, 1991 by Sebastian Hammer,         *
 *  Michael Seifert, Hans Henrik St{rfeldt, Tom Madsen, and Katja Nyboe.   *
 *                                                                         *
 *  Merc Diku Mud improvments copyright=C) 1992, 1993 by Michael           *
 *  Chastain, Michael Quan, and Mitchell Tse.                              *
 *                                                                         *
 *  In order to use any part of this Merc Diku Mud, you must comply with   *
 *  both the original Diku license in 'license.doc' as well the Merc       *
 *  license in 'license.txt'.  In particular, you may not remove either of *
 *  these copyright notices.                                               *
 *                                                                         *
 *  Much time and thought has gone into this software and you are          *
 *  benefitting.  We hope that you share your changes too.  What goes      *
 *  around, comes around.                                                  *
 ***************************************************************************/

#**************************************************************************
*    ROM 2.4 is copyright 1993-1998 Russ Taylor                           *
*    ROM has been brought to you by the ROM consortium                    *
*        Russ Taylor=rtaylor@hypercube.org)                               *
*        Gabrielle Taylor=gtaylor@hypercube.org)                          *
*        Brian Moore=zump@rom.org)                                        *
*    By using this code, you have agreed to follow the terms of the       *
*    ROM license, in the file Rom24/doc/rom.license                       *
***************************************************************************/
#***********
 * Ported to Python by Davion of MudBytes.net
 * Using Miniboa https://code.google.com/p/miniboa/
 * Now using Python 3 version https://code.google.com/p/miniboa-py3/
 ************/
"""

import logging

logger = logging.getLogger()

from merc import *
import db
import game_utils
import handler_game
import save
import random
import update
import const
import effects
import handler_magic
import skills
import state_checks

# * Control the fights going on.
# * Called periodically by update_handler.
def violence_update( ):
    for ch in char_list[:]:
        if not ch.fighting or not ch.in_room:
            continue
        victim = ch.fighting
        if state_checks.IS_AWAKE(ch) and ch.in_room == victim.in_room:
            multi_hit( ch, victim, TYPE_UNDEFINED )
        else:
            stop_fighting( ch, False )
        if not ch.fighting:
            continue
        victim = ch.fighting
        #
        #* Fun for the whole family!
        #*/
        check_assist(ch,victim)
    return

# for auto assisting */
def check_assist( ch, victim):
    for rch in ch.in_room.people[:]:
        if state_checks.IS_AWAKE(rch) and rch.fighting == None:
            # quick check for ASSIST_PLAYER */
            if not state_checks.IS_NPC(ch) and state_checks.IS_NPC(rch) and state_checks.IS_SET(rch.off_flags,ASSIST_PLAYERS) and rch.level + 6 > victim.level:
                rch.do_emote("screams and attacks!")
                multi_hit(rch,victim,TYPE_UNDEFINED)
                continue
        # PCs next */
        if not state_checks.IS_NPC(ch) or state_checks.IS_AFFECTED(ch,AFF_CHARM):
            if( (not state_checks.IS_NPC(rch) and state_checks.IS_SET(rch.act,PLR_AUTOASSIST)) \
            or state_checks.IS_AFFECTED(rch,AFF_CHARM)) \
            and ch.is_same_group(rch) \
            and not is_safe(rch, victim):
                multi_hit (rch,victim,TYPE_UNDEFINED)
                continue
   
        # now check the NPC cases */
        if state_checks.IS_NPC(ch) and not state_checks.IS_AFFECTED(ch,AFF_CHARM):
            if (state_checks.IS_NPC(rch) and state_checks.IS_SET(rch.off_flags,ASSIST_ALL)) \
            or (state_checks.IS_NPC(rch) and rch.group and rch.group == ch.group) \
            or (state_checks.IS_NPC(rch) and rch.race == ch.race and state_checks.IS_SET(rch.off_flags,ASSIST_RACE)) \
            or (state_checks.IS_NPC(rch) and state_checks.IS_SET(rch.off_flags,ASSIST_ALIGN) \
                and ((state_checks.IS_GOOD(rch) and state_checks.IS_GOOD(ch)) or (state_checks.IS_EVIL(rch) and state_checks.IS_EVIL(ch)) \
                or (state_checks.IS_NEUTRAL(rch) and state_checks.IS_NEUTRAL(ch)))) \
            or (rch.pIndexData == ch.pIndexData and state_checks.IS_SET(rch.off_flags,ASSIST_VNUM)):
                if random.randint(0,1) == 0:
                    continue
        
                target = None
                number = 0
                for vch in ch.in_room.people:
                    if rch.can_see(vch) and vch.is_same_group(victim) and random.randint(0,number) == 0:
                        target = vch
                        number += 1
                if target:
                    rch.do_emote("screams and attacks!")
                    multi_hit(rch,target,TYPE_UNDEFINED)


# * Do one group of attacks.
def multi_hit( ch, victim, dt ):
    # decrement the wait */
    if ch.desc == None:
        ch.wait = max(0,ch.wait - PULSE_VIOLENCE)

    if ch.desc == None:
        ch.daze = max(0,ch.daze - PULSE_VIOLENCE) 


    # no attacks for stunnies -- just a check */
    if ch.position < POS_RESTING:
        return

    if state_checks.IS_NPC(ch):
        mob_hit(ch,victim,dt)
        return

    one_hit( ch, victim, dt )

    if ch.fighting != victim:
        return

    if state_checks.IS_AFFECTED(ch,AFF_HASTE):
        one_hit(ch,victim,dt)

    if ch.fighting != victim or dt == 'backstab':
        return

    chance = ch.get_skill('second attack') // 2

    if state_checks.IS_AFFECTED(ch,AFF_SLOW):
        chance //= 2

    if random.randint(1,99) < chance:
        one_hit( ch, victim, dt )
        skills.check_improve(ch,'second_attack',True,5)
        if ch.fighting != victim:
            return
    
    chance = ch.get_skill('third attack') // 4

    if state_checks.IS_AFFECTED(ch,AFF_SLOW):
        chance = 0

    if random.randint(1,99) < chance:
        one_hit( ch, victim, dt )
        skills.check_improve(ch,'third attack',True,6)
        if ch.fighting != victim:
            return
    return
# procedure for all mobile attacks */
def mob_hit (ch, victim, dt):
    one_hit(ch,victim,dt)
    if ch.fighting != victim:
        return
    # Area attack -- BALLS nasty! */
    if state_checks.IS_SET(ch.off_flags,OFF_AREA_ATTACK):
        for vch in ch.in_room.people[:]:
            if vch != victim and vch.fighting == ch:
                one_hit(ch,vch,dt)

    if state_checks.IS_AFFECTED(ch,AFF_HASTE) or (state_checks.IS_SET(ch.off_flags,OFF_FAST) and not state_checks.IS_AFFECTED(ch,AFF_SLOW)):
        one_hit(ch,victim,dt)

    if ch.fighting != victim or dt == 'backstab':
        return

    chance = ch.get_skill("second attack") // 2

    if state_checks.IS_AFFECTED(ch,AFF_SLOW) and not state_checks.IS_SET(ch.off_flags,OFF_FAST):
        chance //= 2

    if random.randint(1,99) < chance:
        one_hit(ch,victim,dt)
        if ch.fighting != victim:
            return
    chance = ch.get_skill('third attack') // 4

    if state_checks.IS_AFFECTED(ch,AFF_SLOW) and not state_checks.IS_SET(ch.off_flags,OFF_FAST):
        chance = 0

    if random.randint(1,99) < chance:
        one_hit(ch,victim,dt)
        if ch.fighting != victim:
            return

    # oh boy!  Fun stuff! */
    if ch.wait > 0:
        return

    number = random.randint(0,2)

    if number == 1 and state_checks.IS_SET(ch.act,ACT_MAGE):
        pass
        #  { mob_cast_mage(ch,victim) return } */ 

    if number == 2 and state_checks.IS_SET(ch.act,ACT_CLERIC):
        pass
        # { mob_cast_cleric(ch,victim) return } */ 

    # now for the skills */

    number = random.randint(0,8)

    if number == 0:
       if state_checks.IS_SET(ch.off_flags,OFF_BASH):
            ch.do_bash("")
    elif number == 1:
        if state_checks.IS_SET(ch.off_flags,OFF_BERSERK) and not state_checks.IS_AFFECTED(ch,AFF_BERSERK):
            ch.do_berserk("")
    elif number == 2:
        if state_checks.IS_SET(ch.off_flags,OFF_DISARM) \
        or (ch.get_weapon_sn() != 'hand_to_hand' \
        and (state_checks.IS_SET(ch.act,ACT_WARRIOR) \
        or  state_checks.IS_SET(ch.act,ACT_THIEF))):
            ch.do_disarm("")
    elif number == 3:
        if state_checks.IS_SET(ch.off_flags,OFF_KICK):
            ch.do_kick("")
    elif number == 4:
        if state_checks.IS_SET(ch.off_flags,OFF_KICK_DIRT):
            ch.do_dirt("")
    elif number == 5:
        if state_checks.IS_SET(ch.off_flags,OFF_TAIL):
            pass  # do_function(ch, &do_tail, "") */ 
    elif number == 6:
        if state_checks.IS_SET(ch.off_flags,OFF_TRIP):
            ch.do_trip("")
    elif number == 7:
        if state_checks.IS_SET(ch.off_flags,OFF_CRUSH):
            pass # do_function(ch, &do_crush, "") */ 
    elif number == 8:
        if state_checks.IS_SET(ch.off_flags,OFF_BACKSTAB):
            ch.do_backstab("")

# * Hit one guy once.
# */
def one_hit( ch, victim, dt ):
    sn = -1
    # just in case */
    if victim == ch or ch == None or victim == None:
        return
    #* Can't beat a dead char!
    #* Guard against weird room-leavings.
    if victim.position == POS_DEAD or ch.in_room != victim.in_room:
        return

     #* Figure out the type of damage message.
    wield = ch.get_eq(WEAR_WIELD)
    if dt == TYPE_UNDEFINED:
        dt = TYPE_HIT
        if wield and wield.item_type == ITEM_WEAPON:
            dt += wield.value[3]
        else :
            dt += ch.dam_type

    if dt < TYPE_HIT:
        if wield:
            dam_type = const.attack_table[wield.value[3]].damage
        else:
            dam_type = const.attack_table[ch.dam_type].damage
    else:
        dam_type = const.attack_table[dt - TYPE_HIT].damage

    if dam_type == -1:
        dam_type = DAM_BASH

    # get the weapon skill */
    sn = ch.get_weapon_sn()
    skill = 20 + ch.get_weapon_skill(sn)

    #* Calculate to-hit-armor-guild-0 versus armor.
    if state_checks.IS_NPC(ch):
        thac0_00 = 20
        thac0_32 = -4   # as good as a thief */ 
        if state_checks.IS_SET(ch.act,ACT_WARRIOR):
            thac0_32 = -10
        elif state_checks.IS_SET(ch.act,ACT_THIEF):
            thac0_32 = -4
        elif state_checks.IS_SET(ch.act,ACT_CLERIC):
            thac0_32 = 2
        elif state_checks.IS_SET(ch.act,ACT_MAGE):
            thac0_32 = 6
    else:
        thac0_00 = ch.guild.thac0_00
        thac0_32 = ch.guild.thac0_32
    
    thac0  = game_utils.interpolate( ch.level, thac0_00, thac0_32 )

    if thac0 < 0:
        thac0 = thac0 // 2

    if thac0 < -5:
        thac0 = -5 + (thac0 + 5) // 2

    thac0 -= state_checks.GET_HITROLL(ch) * skill // 100
    thac0 += 5 * (100 - skill) // 100

    if dt == 'backstab':
        thac0 -= 10 * (100 - ch.get_skill('backstab'))

    if dam_type == DAM_PIERCE: victim_ac = state_checks.GET_AC(victim,AC_PIERCE) // 10
    elif dam_type == DAM_BASH: victim_ac = state_checks.GET_AC(victim,AC_BASH) // 10
    elif dam_type == DAM_SLASH: victim_ac = state_checks.GET_AC(victim,AC_SLASH) // 10
    else: victim_ac = state_checks.GET_AC(victim,AC_EXOTIC) // 10
    
    if victim_ac < -15:
        victim_ac = (victim_ac + 15) // 5 - 15
     
    if not ch.can_see(victim):
        victim_ac -= 4

    if victim.position < POS_FIGHTING:
        victim_ac += 4
 
    if victim.position < POS_RESTING:
        victim_ac += 6

     #* The moment of excitement!
    diceroll = random.randint(0,20)
    if diceroll == 0 or ( diceroll != 19 and diceroll < thac0 - victim_ac ):
        # Miss. */
        damage( ch, victim, 0, dt, dam_type, True )
        return
     # Hit.
     # Calc damage.
    if state_checks.IS_NPC(ch) and (not ch.pIndexData.new_format or wield == None):
        if not ch.pIndexData.new_format:
            dam = random.randint( ch.level // 2, ch.level * 3 // 2 )
            if wield != None:
                dam += dam // 2
        else:
            dam = game_utils.dice(ch.damage[DICE_NUMBER],ch.damage[DICE_TYPE])
    else:
        if sn != -1:
            skills.check_improve(ch,sn,True,5)
        if wield:
            if wield.pIndexData.new_format:
                dam = game_utils.dice(wield.value[1],wield.value[2]) * skill // 100
            else:
                dam = random.randint( wield.value[1] * skill // 100, wield.value[2] * skill // 100)

            if ch.get_eq(WEAR_SHIELD) == None:  # no shield = more */
                dam = dam * 11 // 10
            # sharpness! */
            if state_checks.IS_WEAPON_STAT(wield,WEAPON_SHARP):
                percent = random.randint(1,99)
                if percent <= (skill // 8):
                    dam = 2 * dam + (dam * 2 * percent // 100)
        else:
            low = 1 + 4 * skill // 100
            high = 2 * ch.level // 3 * skill // 100
            if low <= high:
                dam = random.randint(low, high)
            else:
                dam = low
    #
    # * Bonuses.
    if ch.get_skill('enhanced damage') > 0:
        diceroll = random.randint(1,99)
        if diceroll <= ch.get_skill('enhanced_damage'):
            skills.check_improve(ch,'enhanced damage',True,6)
            dam += 2 * ( dam * diceroll // 300)
    if not state_checks.IS_AWAKE(victim):
        dam *= 2
    elif victim.position < POS_FIGHTING:
        dam = dam * 3 // 2

    if dt == 'backstab' and wield:
        if wield.value[0] != 2:
            dam *= 2 + (ch.level // 10) 
        else:
            dam *= 2 + (ch.level // 8)
    dam += state_checks.GET_DAMROLL(ch) * min(100,skill) // 100

    if dam <= 0:
        dam = 1

    result = damage( ch, victim, dam, dt, dam_type, True )
    
    # but do we have a funky weapon? */
    if result and wield != None:

        if ch.fighting == victim and state_checks.IS_WEAPON_STAT(wield,WEAPON_POISON):
            poison = state_checks.affect_find(wield.affected,'poison')
            if poison:
                level = wield.level
            else:
                level = poison.level
            if not handler_magic.saves_spell(level // 2,victim,DAM_POISON):
                victim.send("You feel poison coursing through your veins.")
                handler_game.act("$n is poisoned by the venom on $p.", victim,wield,None,TO_ROOM)
                af = handler_game.AFFECT_DATA()
                af.where     = TO_AFFECTS
                af.type      = 'poison'
                af.level     = level * 3 // 4
                af.duration  = level // 2
                af.location  = APPLY_STR
                af.modifier  = -1
                af.bitvector = AFF_POISON
                victim.affect_join(af)

            # weaken the poison if it's temporary */
            if poison:
                poison.level = max(0,poison.level - 2)
                poison.duration = max(0,poison.duration - 1)
                if poison.level == 0 or poison.duration == 0:
                    handler_game.act("The poison on $p has worn off.",ch,wield,None,TO_CHAR)

            if ch.fighting == victim and state_checks.IS_WEAPON_STAT(wield,WEAPON_VAMPIRIC):
                dam = random.randint(1, wield.level // 5 + 1)
                handler_game.act("$p draws life from $n.",victim,wield,None,TO_ROOM)
                handler_game.act("You feel $p drawing your life away.", victim,wield,None,TO_CHAR)
                damage(ch,victim,dam,0,DAM_NEGATIVE,False)
                ch.alignment = max(-1000,ch.alignment - 1)
                ch.hit += dam // 2
            if ch.fighting == victim and state_checks.IS_WEAPON_STAT(wield,WEAPON_FLAMING):
                dam = random.randint(1,wield.level // 4 + 1)
                handler_game.act("$n is burned by $p.",victim,wield,None,TO_ROOM)
                handler_game.act("$p sears your flesh.",victim,wield,None,TO_CHAR)
                effects.fire_effect(victim,wield.level // 2,dam,TARGET_CHAR)
                damage(ch,victim,dam,0,DAM_FIRE,False)
            if ch.fighting == victim and state_checks.IS_WEAPON_STAT(wield,WEAPON_FROST):
                dam = random.randint(1,wield.level // 6 + 2)
                handler_game.act("$p freezes $n.",victim,wield,None,TO_ROOM)
                handler_game.act("The cold touch of $p surrounds you with ice.",
                victim,wield,None,TO_CHAR)
                effects.cold_effect(victim,wield.level // 2,dam,TARGET_CHAR)
                damage(ch,victim,dam,0,DAM_COLD,False)
            if ch.fighting == victim and state_checks.IS_WEAPON_STAT(wield,WEAPON_SHOCKING):
                dam = random.randint(1,wield.level // 5 + 2)
                handler_game.act("$n is struck by lightning from $p.",victim,wield,None,TO_ROOM)
                handler_game.act("You are shocked by $p.",victim,wield,None,TO_CHAR)
                effects.shock_effect(victim,wield.level // 2,dam,TARGET_CHAR)
                damage(ch,victim,dam,0,DAM_LIGHTNING,False)
    return

# * Inflict damage from a hit.
def damage(ch,victim,dam,dt,dam_type,show):
    if victim.position == POS_DEAD:
        return False

    #Stop up any residual loopholes.
    if dam > 1200 and dt >= TYPE_HIT:
        logger.warn ("BUG: Damage: %d: more than 1200 points!", dam)
        dam = 1200
        if not state_checks.IS_IMMORTAL(ch):
            obj = ch.get_eq(WEAR_WIELD)
            ch.send("You really shouldn't cheat.\n")
            if obj:
                obj.extract()
    
    # damage reduction */
    if dam > 35:
        dam = (dam - 35) // 2 + 35
    if dam > 80:
        dam = (dam - 80) // 2 + 80 
  
    if victim != ch:
        # Certain attacks are forbidden.
        # Most other attacks are returned.
        if is_safe( ch, victim ):
            return False
        check_killer( ch, victim )

        if victim.position > POS_STUNNED:
            if not victim.fighting:
                set_fighting( victim, ch )
            if victim.timer <= 4:
                victim.position = POS_FIGHTING

        if victim.position > POS_STUNNED:
            if not ch.fighting:
                set_fighting( ch, victim )
        # More charm stuff.
        if victim.master == ch:
            handler_ch.stop_follower( victim )
    # * Inviso attacks ... not.
    if state_checks.IS_AFFECTED(ch, AFF_INVISIBLE):
        ch.affect_strip("invis")
        ch.affect_strip("mass invis")
        state_checks.REMOVE_BIT( ch.affected_by, AFF_INVISIBLE )
        handler_game.act( "$n fades into existence.", ch, None, None, TO_ROOM )

     # Damage modifiers.
    if dam > 1 and not state_checks.IS_NPC(victim) and victim.pcdata.condition[COND_DRUNK] > 10:
        dam = 9 * dam // 10
    if dam > 1 and state_checks.IS_AFFECTED(victim, AFF_SANCTUARY):
        dam //= 2

    if dam > 1 and ((state_checks.IS_AFFECTED(victim, AFF_PROTECT_EVIL) and state_checks.IS_EVIL(ch)) \
    or (state_checks.IS_AFFECTED(victim, AFF_PROTECT_GOOD) and state_checks.IS_GOOD(ch) )):
        dam -= dam // 4

    immune = False
     # Check for parry, and dodge.
    if type(dt) == int and dt >= TYPE_HIT and ch != victim:
        if check_parry( ch, victim ):
            return False
        if check_dodge( ch, victim ):
            return False
        if check_shield_block(ch,victim):
            return False
    imm = victim.check_immune(dam_type)

    if imm == IS_IMMUNE:
        immune = True
        dam = 0
    elif imm == IS_RESISTANT:
        dam -= dam // 3
    elif imm == IS_VULNERABLE:
        dam += dam // 2
    dam = int(dam)
    if show:
        dam_message( ch, victim, dam, dt, immune )

    if dam == 0:
        return False
     # Hurt the victim.
     # Inform the victim of his new state.
    victim.hit -= dam
    if not state_checks.IS_NPC(victim) and victim.level >= LEVEL_IMMORTAL and victim.hit < 1:
        victim.hit = 1
    update_pos( victim )

    if victim.position == POS_MORTAL:
        handler_game.act( "$n is mortally wounded, and will die soon, if not aided.", victim, None, None, TO_ROOM )
        victim.send("You are mortally wounded, and will die soon, if not aided.\n\r")
    elif victim.position == POS_INCAP:
        handler_game.act( "$n is incapacitated and will slowly die, if not aided.", victim, None, None, TO_ROOM )
        victim.send("You are incapacitated and will slowly die, if not aided.\n\r")
    elif victim.position == POS_STUNNED:
        handler_game.act( "$n is stunned, but will probably recover.", victim, None, None, TO_ROOM )
        victim.send("You are stunned, but will probably recover.\n\r")
    elif victim.position == POS_DEAD:
        handler_game.act( "$n is DEAD!!", victim, 0, 0, TO_ROOM )
        victim.send("You have been KILLED!!\n\r\n\r")
    else:
        if dam > victim.max_hit // 4:
            victim.send("That really did HURT!\n")
        if victim.hit < victim.max_hit // 4:
            victim.send("You sure are BLEEDING!\n")
    # Sleep spells and extremely wounded folks.
    if not state_checks.IS_AWAKE(victim):
        stop_fighting( victim, False )

    # Payoff for killing things.
    if victim.position == POS_DEAD:
        group_gain( ch, victim )

        if not state_checks.IS_NPC(victim):
            logger.warn ("%s killed by %s at %d", victim.name, ch.short_descr if state_checks.IS_NPC(ch) else ch.name, ch.in_room.vnum )
            # Dying penalty:
            # 2/3 way back to previous level.
            if victim.exp > victim.exp_per_level(victim.pcdata.points) * victim.level:
                update.gain_exp( victim, (2 * (victim.exp_per_level(victim.pcdata.points) * victim.level - victim.exp) // 3) + 50 )

        log_buf = "%s got toasted by %s at %s [room %d]" % ( victim.short_descr if state_checks.IS_NPC(victim) else victim.name,
            ch.short_descr if state_checks.IS_NPC(ch) else ch.name, ch.in_room.name, ch.in_room.vnum)
 
        if state_checks.IS_NPC(victim):
            handler_game.wiznet(log_buf,None,None,WIZ_MOBDEATHS,0,0)
        else:
            handler_game.wiznet(log_buf,None,None,WIZ_DEATHS,0,0)

        raw_kill( victim )
        # dump the flags */
        if ch != victim and not state_checks.IS_NPC(ch) and not ch.is_same_clan(victim):
            if state_checks.IS_SET(victim.act,PLR_KILLER):
                state_checks.REMOVE_BIT(victim.act,PLR_KILLER)
            else:
                state_checks.REMOVE_BIT(victim.act,PLR_THIEF)
            # RT new auto commands */
        corpse = ch.get_obj_list("corpse", ch.in_room.contents)

        if not state_checks.IS_NPC(ch) and corpse and corpse.item_type == ITEM_CORPSE_NPC and ch.can_see_obj(corpse):
            if state_checks.IS_SET(ch.act, PLR_AUTOLOOT) and corpse and corpse.contains: # exists and not empty */
                ch.do_get("all corpse")
            
            if state_checks.IS_SET(ch.act,PLR_AUTOGOLD) and corpse and corpse.contains and not state_checks.IS_SET(ch.act,PLR_AUTOLOOT):
                coins = ch.get_obj_list("gcash",corpse.contains)
                if coins: ch.do_get("all.gcash corpse")
            
            if state_checks.IS_SET(ch.act, PLR_AUTOSAC):
                if state_checks.IS_SET(ch.act,PLR_AUTOLOOT) and corpse and corpse.contains:
                    return True  # leave if corpse has treasure */
                else:
                    ch.do_sacrifice("corpse")
        return True
    
    if victim == ch:
        return True

     #* Take care of link dead people.
    if not state_checks.IS_NPC(victim) and victim.desc == None:
        if random.randint( 0, victim.wait ) == 0:
            victim.do_recall("")
            return True

    # * Wimp out?
    if state_checks.IS_NPC(victim) and dam > 0 and victim.wait < PULSE_VIOLENCE // 2:
        if (state_checks.IS_SET(victim.act, ACT_WIMPY) and random.randint(0,4) == 0 \
        and victim.hit < victim.max_hit // 5) \
        or ( state_checks.IS_AFFECTED(victim, AFF_CHARM) and victim.master \
        and victim.master.in_room != victim.in_room ):
            victim.do_flee("")

    if not state_checks.IS_NPC(victim) and victim.hit > 0 and victim.hit <= victim.wimpy and victim.wait < PULSE_VIOLENCE // 2:
        victim.do_flee("")
    return True

def is_safe(ch, victim):
    if victim.in_room == None or ch.in_room == None:
        return True
    if victim.fighting == ch or victim == ch:
        return False
    if state_checks.IS_IMMORTAL(ch) and ch.level > LEVEL_IMMORTAL:
        return False
    # killing mobiles */
    if state_checks.IS_NPC(victim):
        # safe room? */
        if state_checks.IS_SET(victim.in_room.room_flags,ROOM_SAFE):
            ch.send("Not in this room.\n")
            return True
        if victim.pIndexData.pShop:
            ch.send("The shopkeeper wouldn't like that.\n")
            return True
        # no killing healers, trainers, etc */
        if state_checks.IS_SET(victim.act,ACT_TRAIN) \
        or state_checks.IS_SET(victim.act,ACT_PRACTICE) \
        or state_checks.IS_SET(victim.act,ACT_IS_HEALER) \
        or state_checks.IS_SET(victim.act,ACT_IS_CHANGER):
            ch.send("I don't think Mota would approve.\n")
            return True
        if not state_checks.IS_NPC(ch):
            # no pets */
            if state_checks.IS_SET(victim.act,ACT_PET):
                handler_game.act("But $N looks so cute and cuddly...", ch,None,victim,TO_CHAR)
                return True

            # no charmed creatures unless owner */
            if state_checks.IS_AFFECTED(victim,AFF_CHARM) and ch != victim.master:
                ch.send("You don't own that monster.\n")
                return True
    # killing players */
    else:
        # NPC doing the killing */
        if state_checks.IS_NPC(ch):
            # safe room check */
            if state_checks.IS_SET(victim.in_room.room_flags,ROOM_SAFE):
                ch.send("Not in this room.\n")
                return True

            # charmed mobs and pets cannot attack players while owned */
            if state_checks.IS_AFFECTED(ch,AFF_CHARM) and ch.master and  ch.master.fighting != victim:
                ch.send("Players are your friends!\n")
                return True
        # player doing the killing */
        else:
            if not ch.is_clan():
                ch.send("Join a clan if you want to kill players.\n")
                return True

            if state_checks.IS_SET(victim.act,PLR_KILLER) or state_checks.IS_SET(victim.act,PLR_THIEF):
                return False

            if not victim.is_clan():
                ch.send("They aren't in a clan, leave them alone.\n")
                return True

            if ch.level > victim.level + 8:
                ch.send("Pick on someone your own size.\n")
                return True
    return False
 
def is_safe_spell(ch, victim, area ):
    if victim.in_room == None or ch.in_room == None:
        return True
    if victim == ch and area:
        return True
    if victim.fighting == ch or victim == ch:
        return False
    if state_checks.IS_IMMORTAL(ch) and ch.level > LEVEL_IMMORTAL and not area:
        return False
    # killing mobiles */
    if state_checks.IS_NPC(victim):
        # safe room? */
        if state_checks.IS_SET(victim.in_room.room_flags,ROOM_SAFE):
            return True
        if victim.pIndexData.pShop:
            return True
        # no killing healers, trainers, etc */
        if state_checks.IS_SET(victim.act,ACT_TRAIN) \
        or state_checks.IS_SET(victim.act,ACT_PRACTICE) \
        or state_checks.IS_SET(victim.act,ACT_IS_HEALER) \
        or state_checks.IS_SET(victim.act,ACT_IS_CHANGER):
            return True
        if not state_checks.IS_NPC(ch):
            # no pets */
            if state_checks.IS_SET(victim.act,ACT_PET):
                return True
            # no charmed creatures unless owner */
            if state_checks.IS_AFFECTED(victim,AFF_CHARM) and (area or ch != victim.master):
                return True
            # legal kill? -- cannot hit mob fighting non-group member */
            if victim.fighting != None and not ch.is_same_group(victim.fighting):
                return True
        else:
            # area effect spells do not hit other mobs */
            if area and not victim.is_same_group(ch.fighting):
                return True
    # killing players */
    else:
        if area and state_checks.IS_IMMORTAL(victim) and victim.level > LEVEL_IMMORTAL:
            return True

        # NPC doing the killing */
        if state_checks.IS_NPC(ch):
            # charmed mobs and pets cannot attack players while owned */
            if state_checks.IS_AFFECTED(ch,AFF_CHARM) and ch.master and ch.master.fighting != victim:
                return True
            # safe room? */
            if state_checks.IS_SET(victim.in_room.room_flags,ROOM_SAFE):
                return True

            # legal kill? -- mobs only hit players grouped with opponent*/
            if ch.fighting and not ch.fighting.is_same_group(victim):
                return True
        # player doing the killing */
        else:
            if not ch.is_clan():
                return True
            if state_checks.IS_SET(victim.act,PLR_KILLER) or state_checks.IS_SET(victim.act,PLR_THIEF):
                return False
            if not victim.is_clan():
                return True
            if ch.level > victim.level + 8:
                return True
    return False
#
# * See if an attack justifies a KILLER flag.
def check_killer( ch, victim ):
#     * Follow charm thread to responsible character.
#     * Attacking someone's charmed char is hostile!
    while state_checks.IS_AFFECTED(victim, AFF_CHARM) and victim.master != None:
        victim = victim.master

     # NPC's are fair game.
     # So are killers and thieves.
    if state_checks.IS_NPC(victim) or state_checks.IS_SET(victim.act, PLR_KILLER) or state_checks.IS_SET(victim.act, PLR_THIEF):
        return

     # Charm-o-rama.
    if state_checks.IS_SET(ch.affected_by, AFF_CHARM):
        if ch.master == None:
            logger.warn ("BUG: Check_killer: %s bad AFF_CHARM", ch.short_descr if state_checks.IS_NPC(ch) else ch.name )
            ch.affect_strip('charm person')
            state_checks.REMOVE_BIT(ch.affected_by, AFF_CHARM)
            return
    #    send_to_char( "*** You are now a KILLER!! ***\n", ch.master )
    #    SET_BIT(ch.master.act, PLR_KILLER)
        handler_ch.stop_follower( ch )
        return

     # NPC's are cool of course (as long as not charmed).
     # Hitting yourself is cool too (bleeding).
     # So is being immortal (Alander's idea).
     # And current killers stay as they are.
    if state_checks.IS_NPC(ch) or ch == victim or ch.level >= LEVEL_IMMORTAL \
    or not ch.is_clan() or state_checks.IS_SET(ch.act, PLR_KILLER) or ch.fighting == victim:
        return

    ch.send("*** You are now a KILLER!! ***\n")
    state_checks.SET_BIT(ch.act, PLR_KILLER)
    handler_game.wiznet("$N is attempting to murder %s" % victim.name,ch,None,WIZ_FLAGS,0,0)
    save.save_char_obj( ch )
    return
# Check for parry.
def check_parry( ch, victim ):
    if state_checks.IS_AWAKE(victim):
        return False
    chance = victim.get_skill('parry') // 2

    if victim.get_eq(WEAR_WIELD) == None:
        if state_checks.IS_NPC(victim):
            chance //= 2
        else:
            return False
    if not ch.can_see(victim):
        chance //= 2

    if random.randint(1,99) >= chance + victim.level - ch.level:
        return False

    handler_game.act( "You parry $n's attack.",  ch, None, victim, TO_VICT    )
    handler_game.act( "$N parries your attack.", ch, None, victim, TO_CHAR    )
    skills.check_improve(victim,'parry',True,6)
    return True

# Check for shield block.
def check_shield_block( ch, victim ):
    if not state_checks.IS_AWAKE(victim):
        return False
    chance = victim.get_skill('shield block') // 5 + 3
    if victim.get_eq(WEAR_SHIELD) == None:
        return False
    if random.randint(1,99) >= chance + victim.level - ch.level:
        return False
    handler_game.act( "You block $n's attack with your shield.",  ch, None, victim, TO_VICT)
    handler_game.act( "$N blocks your attack with a shield.", ch, None, victim, TO_CHAR)
    skills.check_improve(victim,'shield block',True,6)
    return True

# Check for dodge.
def check_dodge( ch, victim ):
    if not state_checks.IS_AWAKE(victim):
        return False
    chance = victim.get_skill('dodge') // 2
    if not victim.can_see(ch):
        chance //= 2
    if random.randint(1,99) >= chance + victim.level - ch.level:
        return False
    handler_game.act( "You dodge $n's attack.", ch, None, victim, TO_VICT    )
    handler_game.act( "$N dodges your attack.", ch, None, victim, TO_CHAR    )
    skills.check_improve(victim,'dodge',True,6)
    return True

# Set position of a victim.
def update_pos(victim):
    if victim.hit > 0:
        if victim.position <= POS_STUNNED:
            victim.position = POS_STANDING
        return
    if state_checks.IS_NPC(victim) and victim.hit < 1:
        victim.position = POS_DEAD
        return
    if victim.hit <= -11:
        victim.position = POS_DEAD
        return

    if victim.hit <= -6: victim.position = POS_MORTAL
    elif victim.hit <= -3: victim.position = POS_INCAP
    else: victim.position = POS_STUNNED

# Start fights.
def set_fighting( ch, victim ):
    if ch.fighting != None:
        logger.warn ("BUG: Set_fighting: already fighting")
        return

    if state_checks.IS_AFFECTED(ch, AFF_SLEEP):
        ch.affect_strip('sleep')

    ch.fighting = victim
    ch.position = POS_FIGHTING

# Stop fights.
def stop_fighting( ch, fBoth ):
    for fch in char_list:
        if fch == ch or ( fBoth and fch.fighting == ch ):
            fch.fighting = None
            fch.position = fch.default_pos if state_checks.IS_NPC(fch) else POS_STANDING
            update_pos( fch )
    return
#
# * Make a corpse out of a character.
def make_corpse(ch):
    from db import create_object
    if state_checks.IS_NPC(ch):
        name = ch.short_descr
        corpse      = create_object(obj_index_hash[OBJ_VNUM_CORPSE_NPC], 0)
        corpse.timer   = random.randint( 3, 6 )
        if ch.gold > 0:
            db.create_money(ch.gold, ch.silver).to_obj(corpse)
            ch.gold = 0
            ch.silver = 0
        corpse.cost = 0
    else:
        name = ch.name
        corpse = create_object(obj_index_hash[OBJ_VNUM_CORPSE_PC], 0)
        corpse.timer = random.randint(25, 40)
        state_checks.REMOVE_BIT(ch.act, PLR_CANLOOT)
        if not ch.is_clan():
            corpse.owner = ch.name
        else:
            corpse.owner = ""
            if ch.gold > 1 or ch.silver > 1:
                db.create_money(ch.gold // 2, ch.silver // 2).to_obj(corpse)
                ch.gold -= ch.gold // 2
                ch.silver -= ch.silver // 2
        corpse.cost = 0
    corpse.level = ch.level
    corpse.short_descr = corpse.short_descr % name
    corpse.description = corpse.description % name

    for obj in ch.carrying[:]:
        floating = False
        if obj.wear_loc == WEAR_FLOAT:
            floating = True
        obj.from_char()
        if obj.item_type == ITEM_POTION:
            obj.timer = random.randint(500,1000)
        if obj.item_type == ITEM_SCROLL:
            obj.timer = random.randint(1000,2500)
        if state_checks.IS_SET(obj.extra_flags,ITEM_ROT_DEATH) and not floating:
            obj.timer = random.randint(5,10)
            state_checks.REMOVE_BIT(obj.extra_flags,ITEM_ROT_DEATH)
        state_checks.REMOVE_BIT(obj.extra_flags,ITEM_VIS_DEATH)

        if state_checks.IS_SET( obj.extra_flags, ITEM_INVENTORY ):
            obj.extract()
        elif floating:
            if state_checks.IS_OBJ_STAT(obj,ITEM_ROT_DEATH): # get rid of it! */
                if obj.contains:
                    handler_game.act("$p evaporates,scattering its contents.", ch,obj,None,TO_ROOM)
                    for o in obj.contains[:]:
                        o.from_obj()
                        o.to_room(ch.in_room)
                else:
                    handler_game.act("$p evaporates.", ch,obj,None,TO_ROOM)
                obj.extract()
            else:
                handler_game.act("$p falls to the floor.",ch,obj,None,TO_ROOM)
                obj.to_room(ch.in_room)
        else:
            obj.to_obj(corpse)
    corpse.to_room(ch.in_room)
    return

#
# Improved Death_cry contributed by Diavolo.
def death_cry( ch ):
    from db import create_object
    vnum = 0
    msg = "You hear $n's death cry."
    num = random.randint(0,7)
    if num == 0: msg  = "$n hits the ground ... DEAD."
    elif num == 1: 
        if ch.material == 0:
            msg  = "$n splatters blood on your armor."     
    elif num == 2:                            
        if state_checks.IS_SET(ch.parts,PART_GUTS):
            msg = "$n spills $s guts all over the floor."
            vnum = OBJ_VNUM_GUTS
    elif num ==  3: 
        if state_checks.IS_SET(ch.parts,PART_HEAD):
            msg  = "$n's severed head plops on the ground."
            vnum = OBJ_VNUM_SEVERED_HEAD               
    elif num ==  4: 
        if state_checks.IS_SET(ch.parts,PART_HEART):
            msg  = "$n's heart is torn from $s chest."
            vnum = OBJ_VNUM_TORN_HEART             
    elif num ==  5: 
        if state_checks.IS_SET(ch.parts,PART_ARMS):
            msg  = "$n's arm is sliced from $s dead body."
            vnum = OBJ_VNUM_SLICED_ARM             
    elif num ==  6: 
        if state_checks.IS_SET(ch.parts,PART_LEGS):
            msg  = "$n's leg is sliced from $s dead body."
            vnum = OBJ_VNUM_SLICED_LEG             
    elif num == 7:
        if state_checks.IS_SET(ch.parts,PART_BRAINS):
            msg = "$n's head is shattered, and $s brains splash all over you."
            vnum = OBJ_VNUM_BRAINS
    handler_game.act( msg, ch, None, None, TO_ROOM )
    if vnum != 0:
        name = ch.short_descr if state_checks.IS_NPC(ch) else ch.name
        obj = create_object( obj_index_hash[vnum], 0 )
        obj.timer = random.randint( 4, 7 )

        obj.short_descr = obj.short_descr % name
        obj.description = obj.description % name
        if obj.item_type == ITEM_FOOD:
            if state_checks.IS_SET(ch.form,FORM_POISON):
                obj.value[3] = 1
            elif not state_checks.IS_SET(ch.form,FORM_EDIBLE):
                obj.item_type = ITEM_TRASH
            obj.to_room(ch.in_room)

    if state_checks.IS_NPC(ch):
        msg = "You hear something's death cry."
    else:
        msg = "You hear someone's death cry."

    was_in_room = ch.in_room
    for pexit in was_in_room.exit:
        if pexit and pexit.to_room and pexit.to_room != was_in_room:
            ch.in_room = pexit.to_room
            handler_game.act( msg, ch, None, None, TO_ROOM )
    ch.in_room = was_in_room
    return

def raw_kill( victim ):
    stop_fighting( victim, True )
    death_cry( victim )
    make_corpse( victim )

    if state_checks.IS_NPC(victim):
        victim.pIndexData.killed += 1
        #kill_table[max(0, min(victim.level, MAX_LEVEL-1))].killed += 1
        victim.extract(True)
        return

    victim.extract(False)
    for af in victim.affected[:]:
        victim.affect_remove(af)
    victim.affected_by = victim.race.aff
    victim.armor = [100 for i in range(4)]
    victim.position = POS_RESTING
    victim.hit = max( 1, victim.hit  )
    victim.mana = max( 1, victim.mana )
    victim.move = max( 1, victim.move )
#  save_char_obj( victim ) we're stable enough to not need this :) */
    return

def group_gain( ch, victim ):
    # Monsters don't get kill xp's or alignment changes.
    # P-killing doesn't help either.
    # Dying of mortal wounds or poison doesn't give xp to anyone!
    if victim == ch:
        return
    members = 0
    group_levels = 0
    for gch in ch.in_room.people:
        if gch.is_same_group(ch):
            members += 1
            group_levels += gch.level // 2 if state_checks.IS_NPC(gch) else gch.level

    if members == 0:
        logger.warn ("BUG: Group_gain: members. %s" , members)
        members = 1
        group_levels = ch.level 

    lch = ch.leader if ch.leader else ch

    for gch in ch.in_room.people:
        if not gch.is_same_group(ch) or state_checks.IS_NPC(gch):
            continue

        #Taken out, add it back if you want it
        if gch.level - lch.level >= 5:
            gch.send("You are too high for this group.\n")
            continue
        if gch.level - lch.level <= -5:
            gch.send("You are too low for this group.\n")
            continue
        #*/

        xp = xp_compute( gch, victim, group_levels )  
        gch.send("You receive %d experience points.\n" % xp)
        update.gain_exp( gch, xp )
        for obj in ch.carrying[:]:
            if obj.wear_loc == WEAR_NONE:
                continue
            if (state_checks.IS_OBJ_STAT(obj, ITEM_ANTI_EVIL) and state_checks.IS_EVIL(ch) ) \
            or (state_checks.IS_OBJ_STAT(obj, ITEM_ANTI_GOOD) and state_checks.IS_GOOD(ch) ) \
            or (state_checks.IS_OBJ_STAT(obj, ITEM_ANTI_NEUTRAL) and state_checks.IS_NEUTRAL(ch) ):
                handler_game.act( "You are zapped by $p.", ch, obj, None, TO_CHAR )
                handler_game.act( "$n is zapped by $p.",   ch, obj, None, TO_ROOM )
                obj.from_char()
                obj.to_room(ch.in_room)

 # Compute xp for a kill.
 # Also adjust alignment of killer.
 # Edit this function to change xp computations.
def xp_compute( gch, victim, total_levels ):
    level_range = victim.level - gch.level
    # compute the base exp */
    if level_range == -9 : base_exp = 1
    elif level_range == -8: base_exp = 2
    elif level_range == -7: base_exp = 5
    elif level_range == -6: base_exp = 9
    elif level_range == -5: base_exp = 11
    elif level_range == -4: base_exp = 22
    elif level_range == -3: base_exp = 33
    elif level_range == -2: base_exp = 50
    elif level_range == -1: base_exp = 66
    elif level_range == 0: base_exp = 83
    elif level_range == 1: base_exp = 99
    elif level_range == 2: base_exp = 121
    elif level_range == 3: base_exp = 143
    elif level_range == 4: base_exp = 165
    else: base_exp = 0
    
    if level_range > 4:
        base_exp = 160 + 20 * (level_range - 4)
    # do alignment computations */
    align = victim.alignment - gch.alignment
    if state_checks.IS_SET(victim.act,ACT_NOALIGN):
        pass    # no change */
    elif align > 500: # monster is more good than slayer */
        change = (align - 500) * base_exp // 500 * gch.level // total_levels 
        change = max(1,change)
        gch.alignment = max(-1000,gch.alignment - change)
    elif align < -500: # monster is more evil than slayer */
        change =  ( -1 * align - 500) * base_exp // 500 * gch.level // total_levels
        change = max(1,change)
        gch.alignment = min(1000,gch.alignment + change)
    else: # improve this someday */
        change =  gch.alignment * base_exp // 500 * gch.level // total_levels  
        gch.alignment -= change
    # calculate exp multiplier */
    if state_checks.IS_SET(victim.act,ACT_NOALIGN):
        xp = base_exp
    elif gch.alignment > 500:  # for goodie two shoes */
        if victim.alignment < -750:
            xp = (base_exp *4) // 3
        elif victim.alignment < -500:
            xp = (base_exp * 5) // 4
        elif victim.alignment > 750:
            xp = base_exp // 4
        elif victim.alignment > 500:
            xp = base_exp // 2
        elif victim.alignment > 250:
            xp = (base_exp * 3) // 4 
        else:
            xp = base_exp
    elif gch.alignment < -500:# for baddies */
        if victim.alignment > 750:
            xp = (base_exp * 5) // 4
        elif victim.alignment > 500:
            xp = (base_exp * 11) // 10 
        elif victim.alignment < -750:
            xp = base_exp // 2
        elif victim.alignment < -500:
            xp = (base_exp * 3) // 4
        elif victim.alignment < -250:
            xp = (base_exp * 9) // 10
        else:
            xp = base_exp
    elif gch.alignment > 200:  # a little good */
        if victim.alignment < -500:
            xp = (base_exp * 6) // 5
        elif victim.alignment > 750:
            xp = base_exp // 2
        elif victim.alignment > 0:
            xp = (base_exp * 3) // 4 
        else:
            xp = base_exp
    elif gch.alignment < -200: # a little bad */
        if victim.alignment > 500:
            xp = (base_exp * 6) // 5
        elif victim.alignment < -750:
            xp = base_exp // 2
        elif victim.alignment < 0:
            xp = (base_exp * 3) // 4
        else:
            xp = base_exp
    else: # neutral */
        if victim.alignment > 500 or victim.alignment < -500:
            xp = (base_exp * 4) // 3
        elif victim.alignment < 200 and victim.alignment > -200:
            xp = base_exp // 2
        else:
            xp = base_exp
    # more exp at the low levels */
    if gch.level < 6:
        xp = 10 * xp // (gch.level + 4)

    # less at high */
    if gch.level > 35:
        xp =  15 * xp // (gch.level - 25 )
    # reduce for playing time */
    # compute quarter-hours per level */
    time_per_level = 4 * (gch.played + (int) (current_time - gch.logon)) // 3600 // gch.level
    time_per_level = max(2, min(time_per_level,12))
    if gch.level < 15:  # make it a curve */
        time_per_level = max(time_per_level,(15 - gch.level))
    xp = xp * time_per_level // 12
    # randomize the rewards */
    xp = random.randint (int(xp * 3 // 4), int(xp * 5 // 4))
    # adjust for grouping */
    xp = xp * gch.level // ( max(1,total_levels -1) )
    return xp

def dam_message( ch, victim, dam, dt, immune ):
    if ch == None or victim == None:
        return

    if dam == 0: msg = {'vs':"miss", 'vp':"misses"}
    elif dam <= 4: msg = {'vs':"scratch", 'vp':"scratches"}
    elif dam <=   8: msg = {'vs':"graze", 'vp':"grazes"}
    elif dam <=  12: msg = {'vs':"hit", 'vp':"hits"}
    elif dam <=  16: msg = {'vs':"injure", 'vp':"injures"}
    elif dam <=  20: msg = {'vs':"wound", 'vp':"wounds"}
    elif dam <=  24: msg = {'vs':"maul", 'vp':"mauls"}
    elif dam <=  28: msg = {'vs':"decimate", 'vp':"decimates"}
    elif dam <=  32: msg = {'vs':"devastate", 'vp':"devastates"}
    elif dam <=  36: msg = {'vs':"maim", 'vp':"maims"}
    elif dam <=  40: msg = {'vs':"MUTILATE", 'vp':"MUTILATES"}
    elif dam <=  44: msg = {'vs':"DISEMBOWEL", 'vp':"DISEMBOWELS"}
    elif dam <=  48: msg = {'vs':"DISMEMBER", 'vp':"DISMEMBERS"}
    elif dam <=  52: msg = {'vs':"MASSACRE", 'vp':"MASSACRES"}
    elif dam <=  56: msg = {'vs':"MANGLE", 'vp':"MANGLES"}
    elif dam <=  60: msg = {'vs':"*** DEMOLISH ***", 'vp':"*** DEMOLISHES ***"}
    elif dam <=  75: msg = {'vs':"*** DEVASTATE ***", 'vp':"*** DEVASTATES ***"}
    elif dam <= 100: msg = {'vs':"=== OBLITERATE ===", 'vp':"=== OBLITERATES ==="}
    elif dam <= 125: msg = {'vs':">>> ANNIHILATE <<<", 'vp':">>> ANNIHILATES <<<"}
    elif dam <= 150: msg = {'vs':"<<< ERADICATE >>>", 'vp':"<<< ERADICATES >>>"}
    else: msg = {'vs':"do UNSPEAKABLE things to", 'vp':"does UNSPEAKABLE things to"}
    vs = msg['vs']
    vp = msg['vp']
    punct = '.' if dam <= 24 else '!'
    if dt == TYPE_HIT:
        if ch == victim:
            buf1 = "$n %s $melf%c" % (vp,punct)
            buf2 = "You %s yourself%c" % (vs, punct)
        else:
            buf1 = "$n %s $N%c" % ( vp, punct )
            buf2 = "You %s $N%c" % ( vs, punct )
            buf3 = "$n %s you%c" % ( vp, punct )
    else:
        if type(dt) == const.skill_type:
            attack  = dt.noun_damage
        elif dt >= TYPE_HIT and dt < TYPE_HIT + len(const.attack_table):
            attack = const.attack_table[dt - TYPE_HIT].noun
        else:
            logger.warn ("BUG: Dam_message: bad dt %d.")
            dt = TYPE_HIT
            attack  = const.attack_table[0].name
        if immune:
            if ch == victim:
                buf1 = "$n is unaffected by $s own %s." % attack
                buf2 = "Luckily, you are immune to that."
            else:
                buf1 = "$N is unaffected by $n's %s!" % attack
                buf2 = "$N is unaffected by your %s!" % attack
                buf3 = "$n's %s is powerless against you." % attack
        else:
            if ch == victim:
                buf1 = "$n's %s %s $m%c" % (attack,vp,punct)
                buf2 = "Your %s %s you%c" % (attack,vp,punct)
            else:
                buf1 = "$n's %s %s $N%c" % (attack, vp, punct)
                buf2 = "Your %s %s $N%c" %  (attack, vp, punct)
                buf3 = "$n's %s %s you%c" % (attack, vp, punct)

    if ch == victim:
        handler_game.act(buf1,ch,None,None,TO_ROOM)
        handler_game.act(buf2,ch,None,None,TO_CHAR)
    else:
        handler_game.act( buf1, ch, None, victim, TO_NOTVICT )
        handler_game.act( buf2, ch, None, victim, TO_CHAR )
        handler_game.act( buf3, ch, None, victim, TO_VICT )
    return

# * Disarm a creature.
# * Caller must check for successful attack.
def disarm( ch, victim ):
    obj = victim.get_eq(WEAR_WIELD)
    if not obj:
        ch.send("I think you're taking disarm a little too literally")
        return

    if state_checks.IS_OBJ_STAT(obj,ITEM_NOREMOVE):
        handler_game.act("$S weapon won't budge!",ch,None,victim,TO_CHAR)
        handler_game.act("$n tries to disarm you, but your weapon won't budge!", ch,None,victim,TO_VICT)
        handler_game.act("$n tries to disarm $N, but fails.",ch,None,victim,TO_NOTVICT)
        return
    handler_game.act( "$n DISARMS you and sends your weapon flying!", ch, None, victim, TO_VICT)
    handler_game.act( "You disarm $N!",  ch, None, victim, TO_CHAR    )
    handler_game.act( "$n disarms $N!",  ch, None, victim, TO_NOTVICT )
    obj.from_char()
    if state_checks.IS_OBJ_STAT(obj,ITEM_NODROP) or state_checks.IS_OBJ_STAT(obj,ITEM_INVENTORY):
        obj.to_char(victim)
    else:
        obj.to_room(victim.in_room)
        if state_checks.IS_NPC(victim) and victim.wait == 0 and victim.can_see_obj(obj):
            handler_obj.get_obj(victim,obj,None)
    return

