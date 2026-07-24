#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leitor/gravador do formato real do arquivo "UserSet\\<Nome>-<Dim>-<Mundo>.set"
do DarkEden - e' onde o cliente guarda, POR PERSONAGEM, a posicao de cada
janela da UI que o jogador arrastou (inventario, info/status, quickslot,
etc), pra' reabrir no mesmo lugar da proxima vez que loga.

Confirmado lendo client-master/VS_UI/src/VS_UI_GameCommon.cpp (a classe
C_VS_UI_WINDOW_MANAGER e' quem serializa isso, SaveToFile/LoadFromFile por
volta da linha 23522-23624) e client-master/VS_UI/src/header/VS_UI_GameCommon.h
(enum das janelas, linhas ~2604-2634). Verificado byte-a-byte contra os
arquivos .set reais encontrados no projeto (todos com exatamente 669 bytes).

Layout binario exato (little-endian, sem padding - MSVC `bool`=1 byte,
`enum` simples=4 bytes = int):

  offset   tamanho   campo
  ------   -------   -----
  0        4         DWORD flag (reservado, sempre 0 nos arquivos reais)
  4        1         BYTE hotkey_num (=8)
  5        1         BYTE grade_num (=4)
  6        128       int[hotkey_num * grade_num] (8*4=32 ints) - atalhos de hotkey
  134      1         BYTE filter_num (=7, CLD_TOTAL)
  135      7         bool[filter_num] - toggles de filtro de chat
  142      4         int window_num (=14, indice de QUEST_STATUS_WINDOW)
  146      294       BLOCO A: 14 janelas (indices 0..13), 21 bytes cada:
                        bool alpha(1) + int autohide(4) + Rect x,y,w,h (4 ints=16)
  440      4         bool hpbar_height, hpbar_small, quickitemslot_height,
                      effectstatus_height (1 byte cada)
  444      4         int m_i_main_tab
  448      210       BLOCO B: 10 janelas (indices 14..23), mesmo layout 21B/janela
  658      11        char m_SMS_MyNum[11] (so' 11 dos 12 bytes do campo real)
  ------
  669      TOTAL (confirmado em todos os .set reais encontrados no projeto)

Rect default (janela nunca aberta/movida) e' (-1,-1,-1,-1) - ver
C_VS_UI_WINDOW_MANAGER::SetDefault(), VS_UI_GameCommon.cpp:23461-23492.

Indice de cada janela (WINDOW_ID enum, VS_UI_GameCommon.h:2604-2634 - a
ORDEM importa, e' isso que da' o indice):
  0 HPBAR                    12 TRACE_WINDOW
  1 MINIMAP                  13 BLOOD_BIBLE_WINDOW      <- fim do Bloco A
  2 MAINMENU                 14 QUEST_STATUS_WINDOW     <- inicio do Bloco B
  3 CHATTING                 15 CTF_STATUS
  4 CHATTING_OLD             16 PET_INFO
  5 INVENTORY                17 NAMING_WINDOW
  6 GEAR                     18 QUEST_MANAGER_LIST
  7 INFO                     19 QUEST_MANAGER_DETAIL
  8 QUICKITEMSLOT            20 QUEST_MANAGER_MISSION
  9 PARTY                    21 QUEST_MANAGER_ITEM
  10 EFFECT_STATUS           22 INVENTORY_SUB
  11 OTHER_INFO              23 FRIEND_WINDOW

Esta ferramenta so' mexe nos 4 ints do Rect de cada janela - o resto do
arquivo (hotkeys, filtros, m_i_main_tab, SMS) e' preservado byte-a-byte
exatamente como estava, nunca reescrito/reinterpretado.

O NOME do personagem vem do proprio nome do arquivo (".../<Nome>-<Dim>-
<Mundo>.set"), codificado em cp949/euc-kr (client coreano) - por isso
aparece como "mojibake" se o Windows tentar ler com outro charset; essa
ferramenta tenta redecodificar pra' mostrar o nome de verdade.
"""
import os
import re
import struct
from datetime import datetime

WINDOW_NAMES = [
    "HPBAR", "MINIMAP", "MAINMENU", "CHATTING", "CHATTING_OLD",
    "INVENTORY", "GEAR", "INFO", "QUICKITEMSLOT", "PARTY",
    "EFFECT_STATUS", "OTHER_INFO", "TRACE_WINDOW", "BLOOD_BIBLE_WINDOW",
    "QUEST_STATUS_WINDOW", "CTF_STATUS", "PET_INFO", "NAMING_WINDOW",
    "QUEST_MANAGER_LIST", "QUEST_MANAGER_DETAIL", "QUEST_MANAGER_MISSION",
    "QUEST_MANAGER_ITEM", "INVENTORY_SUB", "FRIEND_WINDOW",
]
WINDOW_TOTAL = len(WINDOW_NAMES)  # 24
BLOCK_A_COUNT = 14   # indices 0..13
BLOCK_B_COUNT = 10   # indices 14..23
assert BLOCK_A_COUNT + BLOCK_B_COUNT == WINDOW_TOTAL

INVENTORY_INDEX = WINDOW_NAMES.index("INVENTORY")

HOTKEY_NUM = 8
GRADE_NUM = 4
FILTER_NUM = 7

_HEADER_SIZE = 4 + 1 + 1 + (HOTKEY_NUM * GRADE_NUM * 4) + 1 + FILTER_NUM + 4  # = 146
_BLOCK_A_OFFSET = _HEADER_SIZE                                                # 146
_WINDOW_ENTRY_SIZE = 1 + 4 + 4 * 4                                            # 21 (alpha+autohide+rect)
_MISC_OFFSET = _BLOCK_A_OFFSET + BLOCK_A_COUNT * _WINDOW_ENTRY_SIZE           # 440
_MISC_SIZE = 4 + 4                                                            # 8 (4 bools + main_tab)
_BLOCK_B_OFFSET = _MISC_OFFSET + _MISC_SIZE                                   # 448
_SMS_OFFSET = _BLOCK_B_OFFSET + BLOCK_B_COUNT * _WINDOW_ENTRY_SIZE            # 658
_SMS_SIZE = 11
EXPECTED_FILE_SIZE = _SMS_OFFSET + _SMS_SIZE                                  # 669

_FILENAME_RE = re.compile(r'^(?P<name>.+)-(?P<dim>-?\d+)-(?P<world>-?\d+)\.set$', re.IGNORECASE)


def decode_char_name(filename):
    """Tenta recuperar o nome de personagem de verdade a partir do nome do
    arquivo (".../<Nome>-<Dim>-<Mundo>.set"), que esta' em cp949/euc-kr no
    disco mas pode ter chegado aqui via Windows como mojibake latin-1/cp1252.
    Devolve (nome_decodificado, dim, mundo) - nome_decodificado cai de volta
    pro nome cru do arquivo se nenhuma tentativa de decodificacao ajudar."""
    base = os.path.basename(filename)
    m = _FILENAME_RE.match(base)
    if not m:
        return base, None, None
    raw_name = m.group("name")
    dim = int(m.group("dim"))
    world = int(m.group("world"))
    candidates = [raw_name]
    for enc_out in ("latin-1", "cp1252"):
        try:
            raw_bytes = raw_name.encode(enc_out)
        except Exception:
            continue
        for enc_in in ("cp949", "euc-kr"):
            try:
                candidates.append(raw_bytes.decode(enc_in))
            except Exception:
                pass
    # prefere a primeira candidata que pareca "normal" (sem caracteres de
    # substituicao/controle) - senao fica com o nome cru mesmo
    for c in candidates:
        if c and all(ch.isprintable() for ch in c):
            return c, dim, world
    return raw_name, dim, world


def find_userset_files(client_dir):
    """Lista todos os .set de personagem (ignora UserOption.set, que e' um
    arquivo/formato diferente - configuracoes gerais, nao janelas)."""
    userset_dir = os.path.join(client_dir, "UserSet")
    if not os.path.isdir(userset_dir):
        return []
    out = []
    for fname in os.listdir(userset_dir):
        if fname.lower() == "useroption.set":
            continue
        if fname.lower().endswith(".set"):
            out.append(os.path.join(userset_dir, fname))
    return out


class UserSetFile:
    """Um arquivo .set carregado - so' os 4 ints do Rect de cada janela sao
    editaveis (set_rect); todo o resto (hotkeys, filtros, SMS etc) fica
    intacto no buffer bruto, nunca reinterpretado."""

    def __init__(self):
        self.path = None
        self.raw = bytearray()
        self.windows = []  # lista de dicts, ver _parse_window

    def load(self, path):
        with open(path, "rb") as f:
            data = f.read()
        if len(data) != EXPECTED_FILE_SIZE:
            raise ValueError(
                f"tamanho inesperado: {len(data)} bytes (esperado {EXPECTED_FILE_SIZE}) - "
                f"pode ser de uma build do cliente diferente (WINDOW_TOTAL mudou)")
        self.path = path
        self.raw = bytearray(data)
        self._parse()

    def _parse(self):
        self.windows = []
        pos = _BLOCK_A_OFFSET
        for i in range(BLOCK_A_COUNT):
            self.windows.append(self._parse_window(i, pos))
            pos += _WINDOW_ENTRY_SIZE
        pos = _BLOCK_B_OFFSET
        for i in range(BLOCK_A_COUNT, WINDOW_TOTAL):
            self.windows.append(self._parse_window(i, pos))
            pos += _WINDOW_ENTRY_SIZE

    def _parse_window(self, index, offset):
        alpha = bool(self.raw[offset])
        autohide = struct.unpack_from('<i', self.raw, offset + 1)[0]
        x, y, w, h = struct.unpack_from('<4i', self.raw, offset + 5)
        return {
            "index": index,
            "name": WINDOW_NAMES[index],
            "alpha": alpha,
            "autohide": autohide,
            "x": x, "y": y, "w": w, "h": h,
            "_rect_offset": offset + 5,
            "_never_moved": (x, y, w, h) == (-1, -1, -1, -1),
        }

    def get_window(self, index_or_name):
        if isinstance(index_or_name, str):
            for e in self.windows:
                if e["name"] == index_or_name:
                    return e
            raise KeyError(index_or_name)
        return self.windows[index_or_name]

    def set_rect(self, index_or_name, x, y, w, h):
        e = self.get_window(index_or_name)
        e["x"], e["y"], e["w"], e["h"] = x, y, w, h
        e["_never_moved"] = False
        struct.pack_into('<4i', self.raw, e["_rect_offset"], x, y, w, h)

    def save(self, path=None):
        path = path or self.path
        if os.path.exists(path):
            bak = path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(path, "rb") as fsrc, open(bak, "wb") as fdst:
                fdst.write(fsrc.read())
        with open(path, "wb") as f:
            f.write(self.raw)
        self.path = path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("uso: python darkeden_windowset.py caminho/pro/Nome-Dim-Mundo.set")
        sys.exit(1)
    us = UserSetFile()
    us.load(sys.argv[1])
    name, dim, world = decode_char_name(sys.argv[1])
    print(f"personagem: {name!r}  dimensao={dim}  mundo={world}")
    print(f"arquivo: {len(us.raw)} bytes (esperado {EXPECTED_FILE_SIZE})")
    for e in us.windows:
        moved = "" if e["_never_moved"] else "  <- ja' foi movida"
        print(f"  [{e['index']:2d}] {e['name']:24s} rect=({e['x']:5d},{e['y']:5d},"
              f"{e['w']:5d},{e['h']:5d}) alpha={e['alpha']} autohide={e['autohide']}{moved}")
