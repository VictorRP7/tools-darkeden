#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leitor/gravador do sistema de SKILLS (o lado CLIENTE - qual animacao cada
skill dispara) do DarkEden - `Data\\Info\\Action.inf`.

Autor: VictorRP7

IMPORTANTE - o que este arquivo NAO tem: dano, custo de MP, cooldown,
requisito de nivel etc - isso e' TUDO server-side/banco de dados (ver
`tools\\client_editor` -> aba "Skills" do site local, que edita direto o
banco). `Action.inf` so' guarda o lado VISUAL/ANIMACAO: nome interno,
tempos de quadro de casting/repeticao, e o mais importante pra' esta
ferramenta - **qual EffectSpriteType (o mesmo sistema de
darkeden_effect.py) toca quando a skill e' usada**.

Confirmado: "SkillID == indice em Action.inf" e' literal (mesmo indice
usado em Skill/SkillBalance no servidor) - client-master/Client/SkillDef.h.
Cada skill pode ter uma segunda tabela ligada, o "resultado"/impacto,
no indice `SkillID + MinResultActionInfo` (mesma tabela Action.inf) -
ver `MActionResultNodeActionInfo::Execute`, `MActionResult.cpp:162`.

Formato confirmado lendo client-master/Client/MActionInfoTable.h/.cpp
(`MActionInfoTable::LoadFromFile`, `MActionInfo::LoadFromFile`,
`ACTION_INFO_NODE::LoadFromFile`) e client-master/Client/CTypeTable.h -
e verificado por leitura completa do arquivo real (188070 bytes, 1191
registros, offset final bate EXATO com o tamanho do arquivo).

===========================================================================
FORMATO BINARIO EXATO (little-endian)
===========================================================================

Action.inf (cabecalho):
    int32  min_result_action_info   ; indice onde comecam os "resultados"
    int32  max_result_action_info   ; (nao usado por esta ferramenta)
    int32  count
    count x MActionInfo

MActionInfo (tamanho VARIAVEL por registro):
    MString name                     ; int32 length + length bytes (sem NUL)
    BYTE   action                    ; m_Action - categoria da acao
    WORD   action_effect_sprite_type          ; EDITAVEL - efeito de CASTING
    WORD   action_effect_sprite_type_female   ; EDITAVEL - variante feminina
    BYTE   use_repeat_frame          ; bool
    int32  start_frame[3]            ; por raca (Slayer/Vampire/Ousters)
    int32  casting_start_frame[3]
    int32  casting_frames[3]
    int32  repeat_start_frame[3]
    int32  repeat_end_frame[3]
    WORD   repeat_limit
    BYTE   casting_effect_to_self    ; bool
    DWORD  casting_action_info_raw   ; BUG real do jogo: soh os 16 bits
                                     ; baixos sao validos (0xFFFF=nenhum) -
                                     ; os 16 altos vazam lixo do heap do
                                     ; C++ original (MActionInfoTable.cpp:383)
    BYTE   casting_action            ; bool
    BYTE   range
    BYTE   f_target
    BYTE   f_start
    BYTE   f_user_type
    WORD   f_weapon_type
    BYTE   f_current_weapon
    BYTE   f_option
    int32  plus_action_info
    BYTE   packet_type
    WORD   delay
    int32  value
    WORD   sound_id
    int32  main_node
    WORD   action_result_id
    int32  action_result_value
    WORD   effect_status
    BYTE   attack                    ; bool
    BYTE   select_creature
    BYTE   flag                      ; bit0x2 = use_action_step
    if flag & 0x2:
        WORD action_step[5]          ; SO' presente se o bit estiver ligado!
    WORD   parent
    BYTE   mastery_skill_step
    BYTE   ignore_fail_delay         ; bool
    int32  num_nodes
    num_nodes x ACTION_INFO_NODE

ACTION_INFO_NODE (14 bytes, passos extras de efeito - ex: projetil que
sai da mao e viaja ate' o alvo, separado do efeito de "cast" no personagem):
    WORD  effect_generator_id
    WORD  effect_sprite_type    ; EDITAVEL
    WORD  step
    WORD  count
    WORD  link_count
    WORD  sound_id
    BYTE  delay_node             ; bool
    BYTE  result_time            ; bool

Nenhum campo tem nome dentro do arquivo - o SkillID de verdade e' so' a
posicao (indice) dentro da lista de MActionInfo.
"""
import os
import json
import struct
from datetime import datetime

sys_path_dir = os.path.dirname(os.path.abspath(__file__))
import sys
if sys_path_dir not in sys.path:
    sys.path.insert(0, sys_path_dir)
import darkeden_truesprite as truesprite

EFFECTSPRITETYPE_NULL = 0xFFFF
ACTIONINFO_NULL = 0xFFFF

SKILL_ICON_MAP_PATH = os.path.join(os.path.dirname(sys_path_dir), "data", "skill_icons.json")


class ActionInfoNode:
    __slots__ = ("effect_generator_id", "effect_sprite_type", "step", "count",
                 "link_count", "sound_id", "delay_node", "result_time")

    def __init__(self, effect_generator_id, effect_sprite_type, step, count,
                 link_count, sound_id, delay_node, result_time):
        self.effect_generator_id = effect_generator_id
        self.effect_sprite_type = effect_sprite_type
        self.step = step
        self.count = count
        self.link_count = link_count
        self.sound_id = sound_id
        self.delay_node = delay_node
        self.result_time = result_time

    @classmethod
    def load(cls, buf, off):
        vals = struct.unpack_from("<HHHHHHBB", buf, off)
        off += 14
        (effect_generator_id, effect_sprite_type, step, count, link_count,
         sound_id, delay_node, result_time) = vals
        return cls(effect_generator_id, effect_sprite_type, step, count,
                    link_count, sound_id, bool(delay_node), bool(result_time)), off

    def save(self):
        return struct.pack("<HHHHHHBB", self.effect_generator_id, self.effect_sprite_type,
                            self.step, self.count, self.link_count, self.sound_id,
                            int(self.delay_node), int(self.result_time))


class ActionInfo:
    """Um registro de Action.inf = uma skill (ou um "resultado"/impacto, na
    mesma tabela, no indice skill_id + min_result_action_info). Todos os
    campos tem nome - nenhum e' guardado so' como bytes opacos - porque o
    formato inteiro foi conferido byte-a-byte contra o arquivo real (offset
    final bate exato com o tamanho do arquivo em todos os 1191 registros)."""

    __slots__ = (
        "name", "action", "action_effect_sprite_type", "action_effect_sprite_type_female",
        "use_repeat_frame", "start_frame", "casting_start_frame", "casting_frames",
        "repeat_start_frame", "repeat_end_frame", "repeat_limit", "casting_effect_to_self",
        "casting_action_info_raw", "casting_action", "range", "f_target", "f_start",
        "f_user_type", "f_weapon_type", "f_current_weapon", "f_option", "plus_action_info",
        "packet_type", "delay", "value", "sound_id", "main_node", "action_result_id",
        "action_result_value", "effect_status", "attack", "select_creature", "flag",
        "action_step", "parent", "mastery_skill_step", "ignore_fail_delay", "nodes",
    )

    @property
    def casting_action_info(self):
        v = self.casting_action_info_raw & 0xFFFF
        return None if v == ACTIONINFO_NULL else v

    @property
    def use_action_step(self):
        return bool(self.flag & 0x02)

    @classmethod
    def load(cls, buf, off):
        self = cls()
        (name_len,) = struct.unpack_from("<i", buf, off); off += 4
        self.name = buf[off:off + max(0, name_len)] if name_len > 0 else b""
        if name_len > 0:
            off += name_len

        self.action = buf[off]; off += 1
        (self.action_effect_sprite_type,) = struct.unpack_from("<H", buf, off); off += 2
        (self.action_effect_sprite_type_female,) = struct.unpack_from("<H", buf, off); off += 2
        self.use_repeat_frame = bool(buf[off]); off += 1

        self.start_frame = list(struct.unpack_from("<3i", buf, off)); off += 12
        self.casting_start_frame = list(struct.unpack_from("<3i", buf, off)); off += 12
        self.casting_frames = list(struct.unpack_from("<3i", buf, off)); off += 12
        self.repeat_start_frame = list(struct.unpack_from("<3i", buf, off)); off += 12
        self.repeat_end_frame = list(struct.unpack_from("<3i", buf, off)); off += 12

        (self.repeat_limit,) = struct.unpack_from("<H", buf, off); off += 2
        self.casting_effect_to_self = bool(buf[off]); off += 1
        (self.casting_action_info_raw,) = struct.unpack_from("<I", buf, off); off += 4
        self.casting_action = bool(buf[off]); off += 1

        self.range = buf[off]; off += 1
        self.f_target = buf[off]; off += 1
        self.f_start = buf[off]; off += 1
        self.f_user_type = buf[off]; off += 1
        (self.f_weapon_type,) = struct.unpack_from("<H", buf, off); off += 2
        self.f_current_weapon = buf[off]; off += 1
        self.f_option = buf[off]; off += 1
        (self.plus_action_info,) = struct.unpack_from("<i", buf, off); off += 4

        self.packet_type = buf[off]; off += 1
        (self.delay,) = struct.unpack_from("<H", buf, off); off += 2
        (self.value,) = struct.unpack_from("<i", buf, off); off += 4
        (self.sound_id,) = struct.unpack_from("<H", buf, off); off += 2
        (self.main_node,) = struct.unpack_from("<i", buf, off); off += 4

        (self.action_result_id,) = struct.unpack_from("<H", buf, off); off += 2
        (self.action_result_value,) = struct.unpack_from("<i", buf, off); off += 4

        (self.effect_status,) = struct.unpack_from("<H", buf, off); off += 2
        self.attack = bool(buf[off]); off += 1
        self.select_creature = buf[off]; off += 1

        self.flag = buf[off]; off += 1
        if self.flag & 0x02:
            self.action_step = list(struct.unpack_from("<5H", buf, off)); off += 10
        else:
            self.action_step = None

        (self.parent,) = struct.unpack_from("<H", buf, off); off += 2
        self.mastery_skill_step = buf[off]; off += 1
        self.ignore_fail_delay = bool(buf[off]); off += 1

        (num_nodes,) = struct.unpack_from("<i", buf, off); off += 4
        nodes = []
        for _ in range(num_nodes):
            node, off = ActionInfoNode.load(buf, off)
            nodes.append(node)
        self.nodes = nodes

        return self, off

    def save(self):
        out = bytearray()
        out += struct.pack("<i", len(self.name))
        out += self.name
        out += bytes((self.action,))
        out += struct.pack("<HH", self.action_effect_sprite_type, self.action_effect_sprite_type_female)
        out += bytes((int(self.use_repeat_frame),))
        out += struct.pack("<3i", *self.start_frame)
        out += struct.pack("<3i", *self.casting_start_frame)
        out += struct.pack("<3i", *self.casting_frames)
        out += struct.pack("<3i", *self.repeat_start_frame)
        out += struct.pack("<3i", *self.repeat_end_frame)
        out += struct.pack("<H", self.repeat_limit)
        out += bytes((int(self.casting_effect_to_self),))
        out += struct.pack("<I", self.casting_action_info_raw)
        out += bytes((int(self.casting_action),))
        out += bytes((self.range, self.f_target, self.f_start, self.f_user_type))
        out += struct.pack("<H", self.f_weapon_type)
        out += bytes((self.f_current_weapon, self.f_option))
        out += struct.pack("<i", self.plus_action_info)
        out += bytes((self.packet_type,))
        out += struct.pack("<H", self.delay)
        out += struct.pack("<i", self.value)
        out += struct.pack("<H", self.sound_id)
        out += struct.pack("<i", self.main_node)
        out += struct.pack("<H", self.action_result_id)
        out += struct.pack("<i", self.action_result_value)
        out += struct.pack("<H", self.effect_status)
        out += bytes((int(self.attack), self.select_creature, self.flag))
        if self.flag & 0x02:
            out += struct.pack("<5H", *self.action_step)
        out += struct.pack("<H", self.parent)
        out += bytes((self.mastery_skill_step, int(self.ignore_fail_delay)))
        out += struct.pack("<i", len(self.nodes))
        for node in self.nodes:
            out += node.save()
        return bytes(out)


class ActionInfoTable:
    """Data\\Info\\Action.inf inteiro - lista de ActionInfo. O SkillID de
    verdade e' o INDICE dentro de self.records (0-based) - "SkillID ==
    indice em Action.inf" e' literal (client-master/Client/SkillDef.h)."""

    def __init__(self):
        self.min_result_action_info = 0
        self.max_result_action_info = 0
        self.records = []
        self.path = None

    def load(self, path):
        with open(path, "rb") as f:
            buf = f.read()
        off = 0
        (self.min_result_action_info,) = struct.unpack_from("<i", buf, off); off += 4
        (self.max_result_action_info,) = struct.unpack_from("<i", buf, off); off += 4
        (count,) = struct.unpack_from("<i", buf, off); off += 4
        records = []
        for _ in range(count):
            rec, off = ActionInfo.load(buf, off)
            records.append(rec)
        self.records = records
        self.path = path

    def save(self, path=None):
        path = path or self.path
        out = bytearray()
        out += struct.pack("<iii", self.min_result_action_info, self.max_result_action_info,
                            len(self.records))
        for rec in self.records:
            out += rec.save()
        if os.path.exists(path):
            bak = path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(path, "rb") as fsrc, open(bak, "wb") as fdst:
                fdst.write(fsrc.read())
        with open(path, "wb") as f:
            f.write(bytes(out))
        self.path = path

    def result_index_for(self, skill_id):
        """Indice do registro de "resultado"/impacto de uma skill, na
        MESMA tabela (MActionResultNodeActionInfo::Execute,
        MActionResult.cpp:162) - ou None se fora do intervalo."""
        idx = skill_id + self.min_result_action_info
        if 0 <= idx < len(self.records):
            return idx
        return None


# ===========================================================================
# ICONE DE SKILL (Data\Ui\spk\SkillIcon.spk) - NAO faz parte do Action.inf,
# mas e' o pedaco visual mais obvio que faltava no editor: cada skill tem um
# indice de sprite fixo dentro de SkillIcon.spk, hardcoded no cliente
# original (MSkillInfoTable.cpp - so' chama .Set() pras skills que tem
# icone de verdade). Achado/extraido antes pelo site local
# (tools\client_editor\skill_icons.json, gerado direto do codigo-fonte) -
# esse mapeamento skill_id->indice foi copiado pra' skill_icons.json (ao
# lado deste arquivo) pra' esta ferramenta ser autossuficiente.
#
# Formato do SkillIcon.spk: confirmado que e' CSprite/CSprite565 comum
# (SEM paleta/tingimento - "normal" no jargao do site) - o MESMO formato
# ja' implementado em darkeden_truesprite.py pras' telas de UI (Title.spk
# etc), reaproveitado aqui sem nenhum codigo novo de formato. Verificado
# empiricamente: 647 icones, todos 36x36, totalmente opacos (retangulo
# solido - faz sentido pra' arte de icone com moldura propria).
# ===========================================================================

def load_skill_icon_map(path=None):
    """{skill_id: indice_do_sprite_em_SkillIcon.spk} - so' as skills que
    tem icone de verdade aparecem aqui (a maioria das ~1191 nao tem)."""
    path = path or SKILL_ICON_MAP_PATH
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {int(k): int(v) for k, v in raw.items()}


class SkillIconSystem:
    """Fachada: abre SkillIcon.spk sob demanda (Data\\Ui\\spk\\, achado a
    partir da pasta Data do cliente) + o mapeamento skill_id->indice."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.client_dir = os.path.dirname(data_dir)
        self.icon_map = load_skill_icon_map()
        self._pack = None
        self._map_dirty = False

    def get_pack(self):
        if self._pack is None:
            path = truesprite.find_ui_spk(self.client_dir, "SkillIcon.spk")
            if path is None:
                raise FileNotFoundError("SkillIcon.spk nao encontrado em Data\\Ui\\spk")
            self._pack = truesprite.TrueSpritePack(path)
            self._pack.dirty = False
        return self._pack

    def get_icon_index(self, skill_id):
        return self.icon_map.get(skill_id)

    def decode_icon(self, skill_id):
        """(width, height, rgb, mask) do icone desta skill, ou None se ela
        nao tem icone mapeado (a maioria das skills nao tem)."""
        idx = self.get_icon_index(skill_id)
        if idx is None:
            return None
        return self.get_pack().decode(idx)

    def assign_new_icon_slot(self, skill_id):
        """So' aloca (e guarda) um indice novo se essa skill ainda nao
        tiver nenhum - reaproveita uma sobra real de frame dentro do
        SkillIcon.spk (nunca aumenta o pack, so' usa espaco que ja' existe
        e nunca foi referenciado por nenhuma skill conhecida) - mesma
        logica ja' usada pelo site local. Devolve o indice (novo ou o que
        ja' existia)."""
        existing = self.get_icon_index(skill_id)
        if existing is not None:
            return existing
        used = set(self.icon_map.values())
        count = self.get_pack().count
        candidate = 0
        while candidate in used:
            candidate += 1
        if candidate >= count:
            raise ValueError("Nao sobrou nenhum indice livre em SkillIcon.spk")
        self.icon_map[skill_id] = candidate
        self._map_dirty = True
        return candidate

    def replace_icon_image(self, skill_id, image_path, resize_to_original=True):
        idx = self.get_icon_index(skill_id)
        assigned_here = idx is None
        if idx is None:
            idx = self.assign_new_icon_slot(skill_id)
        pack = self.get_pack()
        target_size = None
        original_size = len(pack.raw_sprite_bytes(idx))
        if resize_to_original:
            w, h, _rgb, _mask = pack.decode(idx)
            if w and h:
                target_size = (w, h)
        try:
            sprite_bytes, w, h = truesprite.encode_sprite_from_image(
                image_path, target_size=target_size)
        except Exception:
            if assigned_here:
                self.icon_map.pop(skill_id, None)
                self._map_dirty = False
            raise
        if len(sprite_bytes) > original_size:
            if assigned_here:
                self.icon_map.pop(skill_id, None)
                self._map_dirty = False
            raise ValueError(
                f"O icone codificado ocupa {len(sprite_bytes)} bytes, mas o slot "
                f"original so' tem {original_size} bytes; a troca aumentaria "
                "SkillIcon.spk e foi recusada.")
        pack.replace_sprite(idx, sprite_bytes)
        pack.dirty = True
        return w, h

    def is_dirty(self):
        return self._map_dirty or (self._pack is not None and getattr(self._pack, "dirty", False))

    def save(self):
        if self._pack is not None and getattr(self._pack, "dirty", False):
            self._pack.save()
            self._pack.dirty = False
        if self._map_dirty:
            with open(SKILL_ICON_MAP_PATH, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self.icon_map.items()}, f, ensure_ascii=False, indent=1)
            self._map_dirty = False
        return None
