"""
darkeden_creature.py - DarkEden character appearance & animation reader/writer
================================================================================
Author: VictorRP7
Written: 2026-07-21

Reads and edits the DarkEden client's PLAYER/NPC "creature" data: who they are
(Creature.inf), which animation set they use (CreatureSprite.inf), the actual
per-Action/per-Direction/per-Frame animation data (Creature.cfpk and friends),
and the real pixel art (Creature.ispk and friends) - built on top of the
already-verified read-only reference `client_editor/creatureinf.py` (format
confirmed there directly from client-master/Client/MCreatureTable.cpp/.h,
MCreatureSpriteTable.cpp/.h and framelib/{CFrame.cpp,CFramePack.h,TArray.h}),
extended here with:
  - a proper class-based read/write API matching darkeden_effect.py /
    darkeden_skill.py's style, so darkeden_creature_editor.py can use it the
    same way those editors use their own modules,
  - real pixel decoding (every *.ispk file below is a CIndexSprite555 pack,
    the SAME per-sprite binary layout as Data\\Ui\\spk\\Item.ispk - confirmed
    both by an independent source-code re-check and empirically: decoding
    Creature.ispk sprite 0 through darkeden_sprite.SpritePack.decode() below
    produces a clean 32x77 humanoid sprite silhouette, not garbage),
  - the Slayer/Ousters-player "addon" (worn clothing) compositing system,
    which is the ONLY reason a player's on-screen body isn't just one direct
    Creature.cfpk lookup (see CreatureSystem.render_frame / AddonLayer below).

THE LOOKUP CHAIN
-----------------
    CreatureType (index in Creature.inf)
      -> CREATURETABLE_INFO.SpriteTypes[i]     (index in CreatureSprite.inf)
           -> CREATURESPRITETABLE_INFO.FrameID  (top-level index in a .cfpk)
                -> Action -> Direction(0-7) -> Frame -> CFrame(spriteID,cx,cy)
                     -> index in the matching .ispk (CIndexSprite555)

WHICH FILE PAIR TO USE (confirmed via Data\\Info\\FileDef.inf + MTopView.cpp
loading each with FileOpenBinary/LoadFromFileRunning, once each at startup -
there's no per-record file switch, so a Python tool must pick the pair itself
based on Tribe, exactly like the real client does):

    Tribe                                    ->  ispk/cfpk pair
    ---------------------------------------------------------------------
    NPC (2), most monsters                   ->  Creature.ispk / Creature.cfpk
    Vampire (1), normal case                 ->  Creature.ispk / Creature.cfpk
    Vampire (1) w/ SpriteTypes[0]==204        ->  Ousters.ispk  / Ousters.cfpk
      ("new class" vampire - renders through the Ousters body+action layout)
    Ousters (4) / Ousters NPC (5)             ->  Ousters.ispk  / Ousters.cfpk
    Slayer (0) / Slayer NPC (3)                ->  NO direct body frame -
      CreatureSprite.inf resolves these to FrameID 0xFFFF (confirmed: Creature
      index 0 "SlayerMale" -> SpriteType 0 -> FrameID 65535). Slayer bodies are
      built entirely from the addon/wear system below.

There's also `vampire.ispk`/`vampire.cfpk` (FILE_ISPRITE_NEW_CLASS_VAMPIRE),
a separate file pair used by MCreatureWear for certain equip-driven "new
class" vampire wear items - kept available via CreatureSystem.get_body_pack
("vampire_new") for completeness/future use, but ordinary creature rendering
never needs it (confirmed no CreatureSprite.inf FrameID resolves through it
in the normal Tribe-based lookup above).

THE SLAYER "ADDON" (WORN CLOTHING) SYSTEM
-------------------------------------------
A Slayer player is never drawn from a single body sprite - the client always
composites a COAT layer + a TROUSER layer, each its own independent animation
(own Action/Direction/Frame/spriteID/cx/cy), both from ONE shared, gender-
combined pack (confirmed directly from client-master/Client/MCreatureWear.cpp
and MTopViewDraw.cpp, correcting an earlier assumption that addonman.ispk/
addonwoman.ispk were involved here - those two are a SEPARATE, higher-tier
"Advancement Class" gear-overlay pack, gated by specific equipped ItemType
thresholds, and are simply never touched for a default/base-gear Slayer):

    addon.ispk / addon.cfpk   (ONE file pair, both genders, 50 top-level
                                FrameIDs = 25 male + 25 female, back-to-back)

When nothing is equipped the slot is never actually "empty" - it falls back
to a default naked-torso/underwear FrameID (AddonDef.h's combined enum,
confirmed empirically against the real addon.cfpk - 35 actions per FrameID,
matching ACTION_MAX_SLAYER exactly, and clean humanoid sprites decode at
every one of the 4 indices below):

    ADDONID_COAT0_MALE    = 20     ADDONID_COAT0_FEMALE    = 45
    ADDONID_TROUSER0_MALE = 21     ADDONID_TROUSER0_FEMALE = 46

Each layer's CFrame.cx/cy is an independent alignment offset for THAT layer
relative to one shared anchor point (confirmed empirically: same
action/direction, coat and trouser have different cx/cy per direction,
e.g. action0/dir0: coat=(5,-38) vs trouser=(14,-58) - they're drawn at
(anchor_x+cx, anchor_y+cy) each, not at a shared single offset). Composite
order confirmed body-then-overlay in MTopViewDraw.cpp (generic body draw
runs for every tribe first, then Slayer's coat/trouser draw on top at the
same anchor point) - for Slayer there's no separate body layer at all
(CreatureSprite.inf resolves Slayer's FrameID to NULL, see above), so the
two addon layers alone form the whole visible character; trouser is drawn
first, coat second, matching a jacket layering over trousers.

Skin tone (Creature.inf's ColorSet field, `m_ColorBody1`/`m_ColorBody2`) and
the default clothing dye (DEFAULT_COAT_COLOR = DEFAULT_TROUSER_COLOR = 377)
both resolve through the SAME 495-row recolor table as everything else built
on CIndexSprite555 (build_color_set() in darkeden_sprite.py, confirmed
directly against CIndexSprite::SetUsingColorSet/SpriteLib/CIndexSprite.cpp)
- a creature's "index" pixels are simply decoded against color_set[ColorSet]
instead of a hardcoded default, via the same index_slot_colorset mechanism
already used for Item.ispk.
"""
import os
import struct
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import darkeden_sprite as dsprite

FRAMEID_NULL = 0xFFFF

ACTION_STAND = 0
ACTION_MOVE = 1
ACTION_ATTACK = 2
ACTION_MAGIC = 3
ACTION_DAMAGED = 4
ACTION_DRAINED = 5
ACTION_DIE = 6

ACTION_NAMES = {
    0: "Parado", 1: "Andando", 2: "Ataque", 3: "Magia",
    4: "Dano recebido", 5: "Drenado", 6: "Morte",
}

CREATURETRIBE_SLAYER = 0
CREATURETRIBE_VAMPIRE = 1
CREATURETRIBE_NPC = 2
CREATURETRIBE_SLAYER_NPC = 3
CREATURETRIBE_OUSTERS = 4
CREATURETRIBE_OUSTERS_NPC = 5

TRIBE_NAMES = {
    0: "Slayer", 1: "Vampire", 2: "NPC", 3: "Slayer NPC",
    4: "Ousters", 5: "Ousters NPC",
}

ACTION_MAX_VAMPIRE = 11
ACTION_MAX_SLAYER = 35
ACTION_MAX_OUSTERS = 18
ACTION_MAX_NPC = 2

ADDONID_COAT0_MALE = 20
ADDONID_TROUSER0_MALE = 21
ADDONID_COAT0_FEMALE = 45
ADDONID_TROUSER0_FEMALE = 46
DEFAULT_COAT_COLOR = 377
DEFAULT_TROUSER_COLOR = 377
OUSTERS_DEFAULT_BODY_FRAME_ID = 1


def addon_ids_for(b_male):
    """(coat_frame_id, trouser_frame_id) into the shared addon.cfpk/ispk for
    the default (nothing-equipped) Slayer appearance of the given gender."""
    if b_male:
        return ADDONID_COAT0_MALE, ADDONID_TROUSER0_MALE
    return ADDONID_COAT0_FEMALE, ADDONID_TROUSER0_FEMALE


def is_slayer_tribe(tribe):
    return tribe in (CREATURETRIBE_SLAYER, CREATURETRIBE_SLAYER_NPC)


def is_ousters_tribe(tribe):
    return tribe in (CREATURETRIBE_OUSTERS, CREATURETRIBE_OUSTERS_NPC)


def _get_action_max(tribe, sprite_types):
    if is_slayer_tribe(tribe):
        return ACTION_MAX_SLAYER
    if tribe == CREATURETRIBE_VAMPIRE:
        if sprite_types and sprite_types[0] == 204:
            return ACTION_MAX_OUSTERS
        return ACTION_MAX_VAMPIRE
    if is_ousters_tribe(tribe):
        return ACTION_MAX_OUSTERS
    if tribe == CREATURETRIBE_NPC:
        return ACTION_MAX_VAMPIRE
    return ACTION_MAX_VAMPIRE


def read_mstring(buf, off):
    (length,) = struct.unpack_from('<i', buf, off)
    off += 4
    if length <= 0:
        return b'', off
    data = buf[off:off + length]
    off += length
    return data, off


def write_mstring(data):
    if data is None:
        data = b''
    if isinstance(data, str):
        data = data.encode('cp949', errors='replace')
    return struct.pack('<i', len(data)) + data


# ------------------------------------------------------------------
# Creature.inf (CREATURETABLE_INFO)
# ------------------------------------------------------------------
class CreatureRecord:
    __slots__ = ('name', 'sprite_types', 'b_male', 'tribe', 'color_set',
                 'b_male_offset', 'color_set_offset', 'tail')

    def __init__(self, name, sprite_types, b_male, tribe, color_set, tail,
                 b_male_offset, color_set_offset):
        self.name = name
        self.sprite_types = sprite_types
        self.b_male = b_male
        self.tribe = tribe
        self.color_set = color_set
        self.tail = tail                    # raw bytes AFTER Name, verbatim
        self.b_male_offset = b_male_offset  # offset of bMale within `tail`
        self.color_set_offset = color_set_offset  # offset of ColorSet within `tail`

    @property
    def tribe_name(self):
        return TRIBE_NAMES.get(self.tribe, f"?{self.tribe}")

    def to_bytes(self):
        tail = bytearray(self.tail)
        struct.pack_into('<B', tail, self.b_male_offset, 1 if self.b_male else 0)
        struct.pack_into('<i', tail, self.color_set_offset, self.color_set)
        return write_mstring(self.name) + bytes(tail)


def _parse_creature_record(buf, off):
    record_start = off
    name, off = read_mstring(buf, off)
    tail_start = off

    (stcount,) = struct.unpack_from('<i', buf, off); off += 4
    sprite_types = list(struct.unpack_from('<%di' % stcount, buf, off)) if stcount else []
    off += stcount * 4

    b_male_offset = off - tail_start
    (b_male,) = struct.unpack_from('<B', buf, off); off += 1
    (tribe,) = struct.unpack_from('<B', buf, off); off += 1

    off += 1  # MoveTimes
    off += 1  # MoveRatio
    off += 1  # MoveTimesMotor
    off += 4  # Height
    off += 4  # DeadHeight
    off += 2  # DeadActionInfo (SIZE_ACTIONINFO)
    color_set_offset = off - tail_start
    (color_set,) = struct.unpack_from('<i', buf, off); off += 4
    off += 1  # bFlyingCreature
    off += 4  # FlyingHeight
    off += 4  # bHeadCut
    off += 4  # HPBarWidth
    off += 2  # ChangeColorSet (WORD)
    off += 2  # ShadowCount (serialized as 2 bytes despite being `int` in the class)

    action_max = _get_action_max(tribe, sprite_types)
    off += action_max * 2  # m_pActionSound[max] (TYPE_SOUNDID)
    off += action_max * 4  # m_pActionCount[max] (int)

    (b_exist_wear_info,) = struct.unpack_from('<B', buf, off); off += 1
    if b_exist_wear_info and not is_ousters_tribe(tribe):
        off += 23  # ITEM_WEARINFO (8x WORD + 7x BYTE)

    tail = bytes(buf[tail_start:off])
    rec = CreatureRecord(name, sprite_types, bool(b_male), tribe, color_set,
                          tail, b_male_offset, color_set_offset)
    return rec, off


class CreatureTable:
    """Creature.inf: one variable-length record per CreatureType (the array
    index itself IS the CreatureType id referenced everywhere else - spawns,
    quests, etc - so records are only ever appended at the end or removed
    from the end, never reordered or removed from the middle)."""

    def __init__(self):
        self.records = []
        self.path = None

    def load(self, path):
        with open(path, 'rb') as fh:
            buf = fh.read()
        (count,) = struct.unpack_from('<i', buf, 0)
        off = 4
        records = []
        for _ in range(count):
            rec, off = _parse_creature_record(buf, off)
            records.append(rec)
        self.records = records
        self.path = path
        self._true_content_end = off
        self._trailing_junk = buf[off:]

    def save(self, path=None):
        path = path or self.path
        backup = path + '.bak_before_save'
        if os.path.exists(path) and not os.path.exists(backup):
            shutil.copyfile(path, backup)
        out = bytearray()
        out += struct.pack('<i', len(self.records))
        for rec in self.records:
            out += rec.to_bytes()
        out += self._trailing_junk
        with open(path, 'wb') as fh:
            fh.write(out)

    def clone_record(self, source_index, name, b_male=None, color_set=None):
        """Appends a new CreatureType at the end, cloning body/tribe/
        SpriteTypes from `source_index` (same appearance skeleton) with a new
        Name and, optionally, gender/skin-tone. Returns the new CreatureType."""
        src = self.records[source_index]
        new_rec = CreatureRecord(
            name=name if isinstance(name, bytes) else name.encode('cp949', errors='replace'),
            sprite_types=list(src.sprite_types),
            b_male=src.b_male if b_male is None else bool(b_male),
            tribe=src.tribe,
            color_set=src.color_set if color_set is None else color_set,
            tail=src.tail,
            b_male_offset=src.b_male_offset,
            color_set_offset=src.color_set_offset,
        )
        self.records.append(new_rec)
        return len(self.records) - 1

    def delete_last(self):
        if not self.records:
            raise ValueError("Nao ha nenhum personagem pra apagar")
        self.records.pop()
        return len(self.records)


# ------------------------------------------------------------------
# CreatureSprite.inf (CREATURESPRITETABLE_INFO) - fixed 19-byte records
# ------------------------------------------------------------------
class CreatureSpriteEntry:
    __slots__ = ('frame_id', 'creature_type_flags')

    def __init__(self, frame_id, creature_type_flags):
        self.frame_id = frame_id
        self.creature_type_flags = creature_type_flags


class CreatureSpriteTable:
    RECORD_SIZE = 19

    def __init__(self):
        self.entries = []
        self.path = None

    def load(self, path):
        with open(path, 'rb') as fh:
            buf = fh.read()
        (count,) = struct.unpack_from('<i', buf, 0)
        off = 4
        entries = []
        for _ in range(count):
            (frame_id,) = struct.unpack_from('<H', buf, off)
            (creature_type_flags,) = struct.unpack_from('<B', buf, off + 18)
            entries.append(CreatureSpriteEntry(frame_id, creature_type_flags))
            off += self.RECORD_SIZE
        self.entries = entries
        self.path = path

    def frame_id_for(self, sprite_type):
        if sprite_type is None or not (0 <= sprite_type < len(self.entries)):
            return None
        return self.entries[sprite_type].frame_id


# ------------------------------------------------------------------
# *.cfpk / *.cfpki (CCreatureFramePack / CAddonFramePack - same layout):
#   WORD numFrameID
#   numFrameID x {
#     BYTE numAction
#     numAction x { BYTE numDirection
#       numDirection x { WORD numFrame
#         numFrame x CFrame(WORD spriteID, short cx, short cy) } } }
# ------------------------------------------------------------------
class FramePack:
    """One .cfpk file: FrameID -> Action -> Direction -> [(spriteID,cx,cy)]."""

    def __init__(self):
        self.frames = []   # frames[frame_id][action][direction] = [(sid,cx,cy),...]
        self.path = None

    def load(self, path):
        with open(path, 'rb') as fh:
            (outer_count,) = struct.unpack('<H', fh.read(2))
            all_frames = []
            for _ in range(outer_count):
                (num_action,) = struct.unpack('<B', fh.read(1))
                actions = []
                for _a in range(num_action):
                    (num_direction,) = struct.unpack('<B', fh.read(1))
                    directions = []
                    for _d in range(num_direction):
                        (num_frame,) = struct.unpack('<H', fh.read(2))
                        frames = []
                        for _f in range(num_frame):
                            sid, cx, cy = struct.unpack('<Hhh', fh.read(6))
                            frames.append([sid, cx, cy])
                        directions.append(frames)
                    actions.append(directions)
                all_frames.append(actions)
        self.frames = all_frames
        self.path = path

    def get(self, frame_id, action, direction):
        if frame_id is None or not (0 <= frame_id < len(self.frames)):
            return None
        actions = self.frames[frame_id]
        if not (0 <= action < len(actions)):
            return None
        directions = actions[action]
        if not (0 <= direction < len(directions)):
            return None
        return directions[direction]

    def append_frame(self, frame_id, action, direction, sprite_id, cx, cy):
        frames = self.get(frame_id, action, direction)
        if frames is None:
            raise ValueError(f"FrameID {frame_id} Acao {action} Direcao {direction} fora do intervalo")
        frames.append([sprite_id, cx, cy])
        return len(frames) - 1

    def remove_last_frame(self, frame_id, action, direction):
        frames = self.get(frame_id, action, direction)
        if not frames:
            raise ValueError("Essa direcao nao tem nenhum frame pra apagar")
        frames.pop()
        return len(frames)

    def save(self, path=None):
        path = path or self.path
        backup = path + '.bak_before_save'
        if os.path.exists(path) and not os.path.exists(backup):
            shutil.copyfile(path, backup)
        out = bytearray()
        out += struct.pack('<H', len(self.frames))
        for actions in self.frames:
            out += struct.pack('<B', len(actions))
            for directions in actions:
                out += struct.pack('<B', len(directions))
                for frames in directions:
                    out += struct.pack('<H', len(frames))
                    for sid, cx, cy in frames:
                        out += struct.pack('<Hhh', sid, cx, cy)
        with open(path, 'wb') as fh:
            fh.write(out)
        # keep the .cfpki fast-seek index in sync if present (best-effort -
        # the client only reads it as a shortcut; regenerating from scratch
        # here is always safe since it's pure derived data)
        cfpki_path = os.path.splitext(path)[0] + os.path.splitext(path)[1] + 'i'
        if os.path.isfile(cfpki_path):
            self._rewrite_index(cfpki_path)

    def _rewrite_index(self, cfpki_path):
        backup = cfpki_path + '.bak_before_save'
        if not os.path.exists(backup):
            shutil.copyfile(cfpki_path, backup)
        offsets = []
        pos = 2
        for actions in self.frames:
            offsets.append(pos)
            pos += 1
            for directions in actions:
                pos += 1
                for frames in directions:
                    pos += 2 + len(frames) * 6
        out = struct.pack('<H', len(offsets)) + b''.join(struct.pack('<i', o) for o in offsets)
        with open(cfpki_path, 'wb') as fh:
            fh.write(out)


# ------------------------------------------------------------------
# Body/addon pack registry - real filenames confirmed against
# Data\Info\FileDef.inf and the actual Data\Image folder contents.
# ------------------------------------------------------------------
BODY_PACKS = {
    'creature': ('Creature.ispk', 'Creature.cfpk'),
    'ousters': ('Ousters.ispk', 'Ousters.cfpk'),
    'vampire_new': ('vampire.ispk', 'vampire.cfpk'),
    # 'Advancement Class' higher-tier gear overlay, gated by specific
    # equipped ItemType thresholds in MTopViewDraw.cpp - NOT the default
    # naked-Slayer appearance (that's ADDON_PACK below). Kept here for
    # completeness/future use; ordinary preview/editing never needs it.
    'addon_man': ('AddonMan.ispk', 'AddonMan.cfpk'),
    'addon_woman': ('AddonWoman.ispk', 'AddonWoman.cfpk'),
}
# The SINGLE shared, gender-combined pack used for a base Slayer's default
# (nothing-equipped) coat+trouser - see addon_ids_for() above.
ADDON_PACK = ('addon.ispk', 'addon.cfpk')


class BodyPack:
    """One ispk+cfpk pair, lazily loaded (Creature.ispk alone is ~340MB)."""

    def __init__(self, image_dir, ispk_name, cfpk_name):
        self.ispk_path = os.path.join(image_dir, ispk_name)
        self.cfpk_path = os.path.join(image_dir, cfpk_name)
        self._sprites = None
        self._cfpk = None

    @property
    def sprites(self):
        if self._sprites is None:
            self._sprites = dsprite.SpritePack(self.ispk_path)
        return self._sprites

    @property
    def cfpk(self):
        if self._cfpk is None:
            self._cfpk = FramePack()
            self._cfpk.load(self.cfpk_path)
        return self._cfpk


class DrawLayer:
    """One decoded, positioned sprite ready to composite: rgb/mask are the
    same format darkeden_sprite.SpritePack.decode() returns."""
    __slots__ = ('width', 'height', 'rgb', 'mask', 'cx', 'cy')

    def __init__(self, width, height, rgb, mask, cx, cy):
        self.width = width
        self.height = height
        self.rgb = rgb
        self.mask = mask
        self.cx = cx
        self.cy = cy


class CreatureSystem:
    """Facade tying Creature.inf + CreatureSprite.inf + the tribe-appropriate
    body/addon packs together, given a DarkEden Data folder."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        info_dir = os.path.join(data_dir, 'Info')
        image_dir = os.path.join(data_dir, 'Image')
        self.image_dir = image_dir

        self.creatures = CreatureTable()
        self.creatures.load(os.path.join(info_dir, 'Creature.inf'))
        self.creature_sprites = CreatureSpriteTable()
        self.creature_sprites.load(os.path.join(info_dir, 'CreatureSprite.inf'))

        self._body_packs = {}
        self._addon_pack = None
        self._color_set = None

    def get_body_pack(self, key):
        pack = self._body_packs.get(key)
        if pack is None:
            ispk_name, cfpk_name = BODY_PACKS[key]
            pack = BodyPack(self.image_dir, ispk_name, cfpk_name)
            self._body_packs[key] = pack
        return pack

    def get_addon_pack(self):
        if self._addon_pack is None:
            ispk_name, cfpk_name = ADDON_PACK
            self._addon_pack = BodyPack(self.image_dir, ispk_name, cfpk_name)
        return self._addon_pack

    @property
    def color_set(self):
        if self._color_set is None:
            self._color_set = dsprite.build_color_set()
        return self._color_set

    def body_pack_key_for(self, creature):
        """Which BODY_PACKS key (if any) a creature's own body comes from.
        Returns None for Slayer/Slayer-NPC, which have no direct body frame
        at all (addon-only, see render_frame). Vampire with sprite_types[0]
        ==204 ("new class"/Ousters-flavoured vampire) still resolves through
        the regular Creature.ispk/cfpk pair via its own CreatureSprite.inf
        FrameID (confirmed empirically: frame_id 199 - a real example seen
        with this flag - only exists in Creature.cfpk's 287 top-level
        entries, NOT in Ousters.cfpk's 5; only its Action-table SIZE follows
        the Ousters convention, via _get_action_max, not its sprite file)."""
        if is_slayer_tribe(creature.tribe):
            return None
        if is_ousters_tribe(creature.tribe):
            return 'ousters'
        return 'creature'

    def frame_id_for(self, creature, sprite_type_index=0):
        """CreatureSprite.inf-resolved FrameID for a creature's SpriteTypes
        entry - NOT used for Ousters/Ousters-NPC, whose body FrameID is
        always the hardcoded OUSTERS_DEFAULT_BODY_FRAME_ID regardless of
        SpriteTypes (MCreatureWear::SetCreatureType, confirmed empirically:
        real Ousters creatures' own resolved FrameID is 0xFFFF/out-of-range,
        while FrameID 1 in Ousters.cfpk decodes a clean 34x77 body sprite)."""
        if is_ousters_tribe(creature.tribe):
            return OUSTERS_DEFAULT_BODY_FRAME_ID
        if not creature.sprite_types:
            return None
        sprite_type = creature.sprite_types[sprite_type_index] if sprite_type_index < len(creature.sprite_types) else creature.sprite_types[0]
        return self.creature_sprites.frame_id_for(sprite_type)

    def action_count(self, creature):
        pack_key = self.body_pack_key_for(creature)
        if pack_key is not None:
            fid = self.frame_id_for(creature)
            if fid is not None and fid != FRAMEID_NULL:
                frames = self.get_body_pack(pack_key).cfpk.frames
                if 0 <= fid < len(frames):
                    return len(frames[fid])
        if is_slayer_tribe(creature.tribe):
            coat_id, _trouser_id = addon_ids_for(creature.b_male)
            addon = self.get_addon_pack().cfpk
            if 0 <= coat_id < len(addon.frames):
                return len(addon.frames[coat_id])
        return 0

    def direction_count(self, creature, action):
        pack_key = self.body_pack_key_for(creature)
        if pack_key is not None:
            fid = self.frame_id_for(creature)
            cfpk = self.get_body_pack(pack_key).cfpk
            if fid is not None and fid != FRAMEID_NULL and 0 <= fid < len(cfpk.frames):
                actions = cfpk.frames[fid]
                if 0 <= action < len(actions):
                    return len(actions[action])
        if is_slayer_tribe(creature.tribe):
            coat_id, _trouser_id = addon_ids_for(creature.b_male)
            addon = self.get_addon_pack().cfpk
            if 0 <= coat_id < len(addon.frames) and 0 <= action < len(addon.frames[coat_id]):
                return len(addon.frames[coat_id][action])
        return 0

    def render_frame(self, creature, action, direction, frame_index):
        """Returns a list of DrawLayer (bottom-to-top order) for the given
        creature/action/direction/frame. Empty list if out of range/no data.
        Direct-body tribes (NPC/Vampire/Ousters) return exactly one layer;
        Slayer/Slayer-NPC return two (trouser then coat)."""
        layers = []
        pack_key = self.body_pack_key_for(creature)
        color_set = self.color_set

        if pack_key is not None:
            fid = self.frame_id_for(creature)
            if fid is not None and fid != FRAMEID_NULL:
                pack = self.get_body_pack(pack_key)
                fr_list = pack.cfpk.get(fid, action, direction)
                if fr_list and 0 <= frame_index < len(fr_list):
                    sid, cx, cy = fr_list[frame_index]
                    w, h, rgb, mask = pack.sprites.decode(sid, color_set, (creature.color_set, creature.color_set))
                    layers.append(DrawLayer(w, h, rgb, mask, cx, cy))
            return layers

        if is_slayer_tribe(creature.tribe):
            coat_id, trouser_id = addon_ids_for(creature.b_male)
            addon = self.get_addon_pack()
            for addon_id, dye_color in ((trouser_id, DEFAULT_TROUSER_COLOR),
                                         (coat_id, DEFAULT_COAT_COLOR)):
                fr_list = addon.cfpk.get(addon_id, action, direction)
                if fr_list and 0 <= frame_index < len(fr_list):
                    sid, cx, cy = fr_list[frame_index]
                    w, h, rgb, mask = addon.sprites.decode(sid, color_set, (dye_color, dye_color))
                    layers.append(DrawLayer(w, h, rgb, mask, cx, cy))
            return layers

        return layers
