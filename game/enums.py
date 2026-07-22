"""
game/enums.py - Shared enumerations for Champion
=================================================
Defines all shared enum types used by the combat engine,
data models, and network protocol.
"""

from enum import Enum


class ActionType(Enum):
    """The six base combat actions."""
    STRIKE = "strike"
    BLOCK = "block"
    FEINT = "feint"
    COUNTER = "counter"
    CHARGE = "charge"
    AVOID = "avoid"


class Range(Enum):
    """Distance between combatants."""
    CLOSE = "close"
    MEDIUM = "medium"
    FAR = "far"


class Advantage(Enum):
    """Tactical advantage state of a combatant."""
    NEUTRAL = "neutral"
    OFFENSIVE = "offensive"
    DEFENSIVE = "defensive"


class BodySlot(Enum):
    """Equipment slots on a fighter's body."""
    HEAD = "head"
    EYES = "eyes"
    NECK = "neck"
    TORSO = "torso"
    BODY = "body"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    HANDS = "hands"
    RING1 = "ring1"
    RING2 = "ring2"
    WAIST = "waist"
    FEET = "feet"


class MatchPhase(Enum):
    """Phases of a match from lobby to conclusion."""
    LOBBY = "lobby"
    FIGHTER_SELECT = "fighter_select"
    TECHNIQUE_SELECT = "technique_select"
    ITEM_SELECT = "item_select"
    COMBAT = "combat"
    ROUND_END = "round_end"
    MATCH_END = "match_end"


class BuffType(Enum):
    """Types of passive buffs from items."""
    HEALTH = "health"
    POWER = "power"
    SPEED = "speed"
    DAMAGE_REDUCTION = "damage_reduction"
    RESIST_DEBUFF = "resist_debuff"
    INTELLECT = "intellect"
    SPEED_DIFF_DAMAGE = "speed_diff_damage"       # bonus damage per point of Speed over the opponent
    SPEED_DIFF_REDUCTION = "speed_diff_reduction" # damage reduction per point of Speed over the opponent


class DebuffType(Enum):
    """Types of debuffs that can be applied during combat."""
    WEAKENED = "weakened"       # reduced power
    SLOWED = "slowed"           # reduced speed
    VULNERABLE = "vulnerable"   # increased damage taken
    PREDICTABLE = "predictable" # easier to predict next actions
    DAZED = "dazed"             # reduced intellect
