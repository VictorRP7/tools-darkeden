#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leitor/gravador do sistema de EFEITOS REAL do cliente DarkEden (magias,
golpes, auras etc) - construido lendo o codigo-fonte C++ de verdade
(client-master/Client/SpriteLib, client-master/Client/framelib), NAO a
ferramenta antiga "EffectManager" (essa e' so' um pipeline de criacao de
conteudo que precisa de .tga brutos que nao existem mais em lugar nenhum -
este modulo aqui le/grava direto os arquivos que o JOGO de verdade usa).

Autor: VictorRP7

Visao geral do sistema (4 arquivos trabalham juntos, todos em Data\\Image
exceto o primeiro que fica em Data\\Info):

  EffectSpriteType.inf   - tabela mestra: pra' cada FrameID (0..N-1, o
                           indice NA PROPRIA TABELA e' o FrameID - nao tem
                           campo separado) diz o BltType (Normal/Effect/
                           Shadow/Screen) e metadados de pareamento.
                           Confirmado: MEffectSpriteTypeTable.cpp:71-143,
                           client-master/Client/MEffectSpriteTypeTable.h.

  Effect.efpk/.efpki     - "Effect Frame Pack": pra' cada FrameID, uma
                           lista de ATE' 255 direcoes, cada direcao uma
                           lista de frames de animacao (SpriteID + offset
                           x,y + luz + fundo). E' isso que liga um FrameID
                           a' sequencia de sprites que faz a animacao
                           tocar. Confirmado: client-master/Client/
                           framelib/CFrame.cpp, CFramePack.h, TArray.h.

  Effect.aspk/.aspki     - os pixels de verdade: um sprite por SpriteID,
                           formato "alpha + indice de paleta" (CADA pixel
                           tem um BYTE de alpha (0-31) e um BYTE de indice
                           de paleta - NAO e' RGB nem RGB565 puro). Fica
                           bonito porque combina exatamente com o formato
                           usado no jogo pra' efeitos translucidos/glow.
                           Confirmado: client-master/Client/SpriteLib/
                           CSpritePalBase.cpp (container por sprite),
                           CAlphaSpritePal.cpp (RLE por linha).

  Effect.ppk/.ppki       - as paletas: uma paleta (ate' 255 cores RGB565)
                           POR FrameID (nao por sprite!) - o mesmo FrameID
                           usa uma paleta so' pra' todos os seus sprites/
                           direcoes/frames. Confirmado: client-master/
                           Client/SpriteLib/MPalette.cpp, MPalettePack.h.

Cadeia de uso em jogo (MTopView.h:551-553, MRisingEffectGenerator.cpp,
MAttachEffect.cpp): uma magia/golpe escolhe um FrameID -> pega a paleta
desse FrameID no .ppk -> pra' cada direcao/frame do .efpk pega o SpriteID
-> desenha o sprite do .aspk usando aquela paleta.

===========================================================================
FORMATOS BINARIOS EXATOS (confirmados linha por linha, todos little-endian)
===========================================================================

EffectSpriteType.inf (CTypeTable<EFFECTSPRITETYPETABLE_INFO>):
    DWORD record_count
    record_count x:
        BYTE  blt_type              ; 0=NORMAL,1=EFFECT,2=SHADOW,3=SCREEN
        WORD  frame_id              ; SO' informativo - o indice na tabela
                                     ; (0-based) e' o FrameID de verdade,
                                     ; nao esse campo
        BYTE  flag                  ; bit0=bPairFrameBack, bit1=RepeatFrame
        WORD  action_effect_frame_id  ; 0xFFFF = nenhum (FRAMEID_NULL)
        WORD  female_effect_sprite_type  ; 0xFFFF = nenhum
        BYTE  num_pair
        num_pair x WORD pair_frame_id

Effect.aspki (indice - CTypePack<CAlphaSpritePal>):
    WORD  sprite_count
    sprite_count x DWORD offset     ; posicao de cada sprite dentro do .aspk

Effect.aspk (dados - mesmo container, sequencial, sem gap entre sprites):
    WORD  sprite_count
    sprite_count x CAlphaSpritePal (ver abaixo)

CAlphaSpritePal (um sprite - CSpritePalBase.cpp:49-86):
    DWORD size            ; tamanho em bytes do pixel_blob abaixo
    WORD  width
    WORD  height
    BYTE  pixel_blob[size]     ; todas as linhas RLE concatenadas
    WORD  row_len[height]      ; tamanho EM BYTES de cada linha dentro do
                                ; pixel_blob (linha i comeca no offset
                                ; soma(row_len[0..i-1]))

Linha RLE dentro do pixel_blob (CAlphaSpritePal.cpp SetPixel/Blt):
    BYTE  segment_count
    segment_count x:
        BYTE  trans_count          ; pixels transparentes/pulados (0-255)
        BYTE  color_count          ; pixels coloridos que vem a seguir
        color_count x:
            BYTE  alpha            ; 0-31 (5 bits uteis)
            BYTE  palette_index    ; indice dentro da paleta do FrameID

Effect.ppki (indice - CTypePack2<MPalette,MPalette555,MPalette565>):
    WORD  palette_count             ; == numero de FrameIDs com paleta
    palette_count x DWORD offset

Effect.ppk (dados, mesmo container):
    WORD  palette_count
    palette_count x MPalette (ver abaixo)

MPalette (uma paleta - MPalette.cpp:49-97 - SEMPRE 565 no disco):
    BYTE  size
    size x WORD color              ; RGB565, little-endian

Effect.efpki (indice - CFramePack<DIRECTION_EFFECTFRAME_ARRAY>::SaveToFile,
              CFramePack.h:74-118):
    WORD  frame_id_count            ; TYPE_FRAMEID = unsigned short
    frame_id_count x DWORD offset   ; (escrito como C++ `long`, 4 bytes)

Effect.efpk (dados - TArray<DIRECTION_EFFECTFRAME_ARRAY,TYPE_FRAMEID>):
    WORD  frame_id_count
    frame_id_count x DIRECTION_EFFECTFRAME_ARRAY (ver abaixo)

DIRECTION_EFFECTFRAME_ARRAY (TArray<EFFECTFRAME_ARRAY,BYTE>, TArray.h:193-229):
    BYTE  direction_count           ; 0 se esse FrameID nao tem nada
    direction_count x EFFECTFRAME_ARRAY

EFFECTFRAME_ARRAY (TArray<CEffectFrame,WORD>):
    WORD  frame_count
    frame_count x CEffectFrame

CEffectFrame (CFrame.cpp:16-107):
    WORD  sprite_id                 ; TYPE_SPRITEID = unsigned short
    short cx                        ; deslocamento X de desenho
    short cy                        ; deslocamento Y de desenho
    BYTE  light_and_bg              ; bit7 = fundo(background), bits0-6 = luz

Nenhum destes tem assinatura/magic - o contador WORD/DWORD do topo e' a
UNICA validacao possivel (por isso os round-trips desta ferramenta sempre
conferem byte-a-byte antes de qualquer coisa ser considerada "funcionando").
"""
import os
import struct
from datetime import datetime

# ---------------------------------------------------------------------------
# EffectSpriteType.inf
# ---------------------------------------------------------------------------

BLT_TYPE_NAMES = {0: "NORMAL", 1: "EFFECT", 2: "SHADOW", 3: "SCREEN"}
FRAMEID_NULL = 0xFFFF


class EffectSpriteTypeRecord:
    """IMPORTANTE (corrigido apos testar contra o jogo de verdade): o campo
    frame_id gravado no arquivo NAO e' a posicao na tabela - e' um contador
    PROPRIO DE CADA BltType, comecando do zero (confirmado lendo
    MRisingEffectGenerator.cpp:30-32: `bltType` escolhe QUAL familia de
    arquivo usar - Effect.* pro EFFECT, EffectScreen.* pro SCREEN, etc - e
    `frameID` [este campo] e' o indice DENTRO daquela familia). So' parece
    "ser a posicao" pros registros EFFECT porque eles ficam contiguos logo
    no comeco da tabela (posicoes 0..1956 nesta versao) - confirmado
    empiricamente: os primeiros 1957 registros sao EFFECT com frame_id
    igual a' posicao (0,1,2...), e os 606 registros SCREEN seguintes (a
    partir da posicao 1957) tem frame_id recomecando do 0 (0,1,2...605) -
    um contador TOTALMENTE separado, indexando Effect.aspk/.ppk/.efpk que
    este modulo trata."""
    __slots__ = ("table_position", "frame_id", "blt_type", "flag",
                 "action_effect_frame_id", "female_effect_sprite_type",
                 "pair_frame_ids")

    def __init__(self, table_position, frame_id, blt_type, flag,
                 action_effect_frame_id, female_effect_sprite_type,
                 pair_frame_ids):
        self.table_position = table_position  # posicao crua no arquivo -
                                   # so' pra' preservar ordem/round-trip,
                                   # NAO usar pra' indexar aspk/ppk/efpk
        self.frame_id = frame_id  # o campo de verdade gravado no disco -
                                   # ESTE e' o indice real dentro da familia
                                   # de arquivos do proprio BltType (so'
                                   # coincide com table_position pro EFFECT)
        self.blt_type = blt_type
        self.flag = flag
        self.action_effect_frame_id = action_effect_frame_id
        self.female_effect_sprite_type = female_effect_sprite_type
        self.pair_frame_ids = pair_frame_ids

    @property
    def blt_type_name(self):
        return BLT_TYPE_NAMES.get(self.blt_type, f"?{self.blt_type}")

    @property
    def repeat_frame(self):
        return bool(self.flag & 0x02)

    @property
    def pair_frame_back(self):
        return bool(self.flag & 0x01)


class EffectSpriteTypeTable:
    """Data\\Info\\EffectSpriteType.inf - lista de EffectSpriteTypeRecord,
    UMA POR LINHA DO ARQUIVO (table_position = posicao). O FrameID de
    verdade pra' achar sprite/paleta/animacao e' r.frame_id (o campo
    gravado), NAO table_position - ver docstring de EffectSpriteTypeRecord."""

    def __init__(self):
        self.records = []

    def load(self, path):
        with open(path, "rb") as f:
            data = f.read()
        count = struct.unpack_from("<I", data, 0)[0]
        pos = 4
        records = []
        for table_position in range(count):
            blt_type = data[pos]; pos += 1
            frame_id = struct.unpack_from("<H", data, pos)[0]; pos += 2
            flag = data[pos]; pos += 1
            action_effect_frame_id = struct.unpack_from("<H", data, pos)[0]; pos += 2
            female_effect_sprite_type = struct.unpack_from("<H", data, pos)[0]; pos += 2
            num_pair = data[pos]; pos += 1
            pair_frame_ids = []
            if num_pair:
                pair_frame_ids = list(struct.unpack_from(f"<{num_pair}H", data, pos))
                pos += num_pair * 2
            records.append(EffectSpriteTypeRecord(
                table_position, frame_id, blt_type, flag, action_effect_frame_id,
                female_effect_sprite_type, pair_frame_ids))
        self.records = records

    def save(self, path):
        out = bytearray()
        out += struct.pack("<I", len(self.records))
        for r in self.records:
            out += struct.pack("<BHBHHB", r.blt_type, r.frame_id, r.flag,
                                r.action_effect_frame_id,
                                r.female_effect_sprite_type,
                                len(r.pair_frame_ids))
            for p in r.pair_frame_ids:
                out += struct.pack("<H", p)
        with open(path, "wb") as f:
            f.write(bytes(out))


# ---------------------------------------------------------------------------
# Effect.aspk / .aspki - sprites (alpha + indice de paleta)
# ---------------------------------------------------------------------------

def _read_indexed_pack_container(data):
    """WORD count no topo - offsets calculados sequencialmente (todos os
    packs .spk-like deste jogo nao tem gap entre registros, confirmado
    repetidas vezes esta sessao) - devolve (count, offset_of_record_0)."""
    count = struct.unpack_from("<H", data, 0)[0]
    return count, 2


class AlphaEffectSprite:
    """Um sprite decodificado de Effect.aspk - width/height + uma matriz
    RGBA ja' resolvida contra a paleta do FrameID (ver AlphaSpritePack.decode)."""
    __slots__ = ("width", "height", "rgba")

    def __init__(self, width, height, rgba):
        self.width = width
        self.height = height
        self.rgba = rgba  # bytes, 4 por pixel (R,G,B,A 0-255)


class AlphaSpritePack:
    """Effect.aspk - um CAlphaSpritePal por SpriteID. So' guarda os dados
    CRUS (alpha+indice) no decode_raw - pra' virar cor de verdade precisa
    de uma paleta (ver decode() abaixo, que resolve contra uma MPalette)."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()
        self.count, _ = _read_indexed_pack_container(self.data)
        self._offsets = None

    def _build_offsets(self):
        data = self.data
        pos = 2
        offsets = []
        for _ in range(self.count):
            offsets.append(pos)
            size = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            width, height = struct.unpack_from("<HH", data, pos)
            pos += 4
            pos += size          # pixel_blob
            pos += height * 2    # row_len[]
        self._offsets = offsets

    def decode_raw(self, index):
        """(width, height, rows) - rows e' uma lista de listas de
        segmentos (trans_count, [(alpha,pal_index), ...]) por linha, SEM
        resolver contra paleta nenhuma ainda (uso interno/edicao)."""
        if self._offsets is None:
            self._build_offsets()
        if not (0 <= index < self.count):
            raise IndexError(f"sprite {index} fora do intervalo (0..{self.count - 1})")
        data = self.data
        pos = self._offsets[index]
        size, width, height = struct.unpack_from("<IHH", data, pos)
        pos += 8
        blob_start = pos
        pos += size
        row_lens = struct.unpack_from(f"<{height}H", data, pos)

        rows = []
        blob_pos = blob_start
        for row_len in row_lens:
            row_end = blob_pos + row_len
            if row_len == 0:
                rows.append([])
                blob_pos = row_end
                continue
            segment_count = data[blob_pos]
            p = blob_pos + 1
            segments = []
            for _ in range(segment_count):
                trans_count = data[p]; color_count = data[p + 1]
                p += 2
                pixels = []
                for _ in range(color_count):
                    alpha = data[p]; pal_idx = data[p + 1]
                    p += 2
                    pixels.append((alpha, pal_idx))
                segments.append((trans_count, pixels))
            rows.append(segments)
            blob_pos = row_end
        return width, height, rows

    def decode(self, index, palette):
        """Resolve o sprite `index` contra uma MPalette (ver PalettePack)
        e devolve um AlphaEffectSprite (RGBA pronto pra' desenhar/exportar).
        Alpha de disco e' 0-31 (5 bits) - escalado aqui pra' 0-255."""
        width, height, rows = self.decode_raw(index)
        rgba = bytearray(width * height * 4)
        for y, segments in enumerate(rows):
            x = 0
            row_base = y * width * 4
            for trans_count, pixels in segments:
                x += trans_count
                for alpha, pal_idx in pixels:
                    if 0 <= x < width:
                        r, g, b = palette.get_rgb(pal_idx)
                        a = min(255, alpha * 255 // 31)
                        off = row_base + x * 4
                        rgba[off:off + 4] = bytes((r, g, b, a))
                    x += 1
        return AlphaEffectSprite(width, height, bytes(rgba))

    @staticmethod
    def encode_sprite(width, height, pal_index_rows, colorkey_index=None):
        """Monta os bytes CRUS de um CAlphaSpritePal a partir de
        pal_index_rows: lista (por linha) de listas (por pixel) de
        (alpha_0_31, pal_index) ou None (pixel transparente/pulado).
        Devolve bytes prontos pra' AlphaSpritePack.append_sprite()."""
        row_blobs = []
        for row in pal_index_rows:
            segments = bytearray()
            segment_count = 0
            x = 0
            n = len(row)
            while x < n:
                trans_count = 0
                while x < n and row[x] is None and trans_count < 255:
                    trans_count += 1
                    x += 1
                color_pixels = []
                while x < n and row[x] is not None and len(color_pixels) < 255:
                    color_pixels.append(row[x])
                    x += 1
                if trans_count == 0 and not color_pixels and x < n:
                    # pixel isolado que nao avancou (nao deveria acontecer,
                    # guarda de seguranca contra loop infinito)
                    x += 1
                    continue
                segments += struct.pack("<BB", trans_count, len(color_pixels))
                for alpha, pal_idx in color_pixels:
                    segments += struct.pack("<BB", alpha, pal_idx)
                segment_count += 1
                if trans_count == 0 and not color_pixels:
                    break
            row_blob = struct.pack("<B", segment_count) + bytes(segments)
            row_blobs.append(row_blob)

        pixel_blob = b"".join(row_blobs)
        row_lens = [len(b) for b in row_blobs]
        out = struct.pack("<IHH", len(pixel_blob), width, height)
        out += pixel_blob
        out += struct.pack(f"<{height}H", *row_lens)
        return out

    def append_sprite(self, sprite_bytes):
        """Adiciona um sprite (bytes de um CAlphaSpritePal, ver
        encode_sprite) no final do pack em memoria. So' grava em disco
        quando save() for chamado. Devolve o novo indice (SpriteID)."""
        if self._offsets is None:
            self._build_offsets()
        new_index = self.count
        self.data = bytearray(self.data)
        self._offsets.append(len(self.data))
        self.data += sprite_bytes
        self.count += 1
        struct.pack_into("<H", self.data, 0, self.count)
        return new_index

    def save(self, path=None):
        path = path or self.path
        if os.path.exists(path):
            bak = path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(path, "rb") as fsrc, open(bak, "wb") as fdst:
                fdst.write(fsrc.read())
        with open(path, "wb") as f:
            f.write(bytes(self.data))
        self.path = path

    def save_index(self, aspki_path):
        """Reescreve o .aspki (indice) - precisa ser chamado junto com
        save() sempre que sprites forem adicionados/alterados."""
        if self._offsets is None:
            self._build_offsets()
        out = struct.pack("<H", self.count)
        out += struct.pack(f"<{self.count}I", *self._offsets)
        if os.path.exists(aspki_path):
            bak = aspki_path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(aspki_path, "rb") as fsrc, open(bak, "wb") as fdst:
                fdst.write(fsrc.read())
        with open(aspki_path, "wb") as f:
            f.write(out)


# ---------------------------------------------------------------------------
# Effect.ppk / .ppki - paletas (uma por FrameID)
# ---------------------------------------------------------------------------

def _rgb565_to_888(word):
    r5 = (word >> 11) & 0x1F
    g6 = (word >> 5) & 0x3F
    b5 = word & 0x1F
    return (r5 * 255) // 31, (g6 * 255) // 63, (b5 * 255) // 31


def _rgb888_to_565(r, g, b):
    return ((r * 31 // 255) << 11) | ((g * 63 // 255) << 5) | (b * 31 // 255)


class Palette:
    """Uma paleta MPalette565 decodificada (lista de tuplas RGB 0-255)."""
    __slots__ = ("colors",)

    def __init__(self, colors):
        self.colors = colors  # lista de (r,g,b), indice 0..size-1

    def get_rgb(self, index):
        if 0 <= index < len(self.colors):
            return self.colors[index]
        return (255, 0, 255)  # indice invalido - magenta bem visivel, nao deveria acontecer


class PalettePack:
    """Effect.ppk - uma Palette por FrameID (mesmo indice de FrameID usado
    em EffectSpriteType.inf e Effect.efpk)."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()
        self.count, _ = _read_indexed_pack_container(self.data)
        self._offsets = None

    def _build_offsets(self):
        data = self.data
        pos = 2
        offsets = []
        for _ in range(self.count):
            offsets.append(pos)
            size = data[pos]
            pos += 1 + size * 2
        self._offsets = offsets

    def decode(self, index):
        if self._offsets is None:
            self._build_offsets()
        if not (0 <= index < self.count):
            raise IndexError(f"paleta {index} fora do intervalo (0..{self.count - 1})")
        data = self.data
        pos = self._offsets[index]
        size = data[pos]
        pos += 1
        colors = []
        for i in range(size):
            word = struct.unpack_from("<H", data, pos)[0]
            pos += 2
            colors.append(_rgb565_to_888(word))
        return Palette(colors)

    @staticmethod
    def encode_palette(colors):
        """colors: lista de (r,g,b) 0-255, max 255 cores. Devolve os bytes
        crus de uma MPalette565 pronta pra' append_palette()."""
        if len(colors) > 255:
            raise ValueError("paleta so' suporta ate' 255 cores")
        out = struct.pack("<B", len(colors))
        for r, g, b in colors:
            out += struct.pack("<H", _rgb888_to_565(r, g, b))
        return out

    def append_palette(self, palette_bytes):
        if self._offsets is None:
            self._build_offsets()
        new_index = self.count
        self.data = bytearray(self.data)
        self._offsets.append(len(self.data))
        self.data += palette_bytes
        self.count += 1
        struct.pack_into("<H", self.data, 0, self.count)
        return new_index

    def save(self, path=None):
        path = path or self.path
        if os.path.exists(path):
            bak = path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(path, "rb") as fsrc, open(bak, "wb") as fdst:
                fdst.write(fsrc.read())
        with open(path, "wb") as f:
            f.write(bytes(self.data))
        self.path = path

    def save_index(self, ppki_path):
        if self._offsets is None:
            self._build_offsets()
        out = struct.pack("<H", self.count)
        out += struct.pack(f"<{self.count}I", *self._offsets)
        if os.path.exists(ppki_path):
            bak = ppki_path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(ppki_path, "rb") as fsrc, open(bak, "wb") as fdst:
                fdst.write(fsrc.read())
        with open(ppki_path, "wb") as f:
            f.write(out)


# ---------------------------------------------------------------------------
# Effect.efpk / .efpki - direcoes/frames de animacao (liga FrameID -> sprites)
# ---------------------------------------------------------------------------

class EffectFrame:
    """Um frame de animacao dentro de uma direcao - qual SpriteID desenhar,
    com que deslocamento, luz e se e' 'fundo' (atras do personagem)."""
    __slots__ = ("sprite_id", "cx", "cy", "light", "background")

    def __init__(self, sprite_id, cx, cy, light, background):
        self.sprite_id = sprite_id
        self.cx = cx
        self.cy = cy
        self.light = light
        self.background = background


class EffectFramePack:
    """Effect.efpk - pack[frame_id] = lista de direcoes, cada direcao uma
    lista de EffectFrame. Estrutura aninhada, ver docstring do modulo."""

    def __init__(self, path=None):
        self.path = path
        self.frames = []  # frames[frame_id] = [ [EffectFrame,...] por direcao ]
        if path:
            self.load(path)

    def load(self, path):
        with open(path, "rb") as f:
            data = f.read()
        pos = 0
        frame_id_count = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        all_frames = []
        for _ in range(frame_id_count):
            dir_count = data[pos]
            pos += 1
            directions = []
            for _ in range(dir_count):
                n_frames = struct.unpack_from("<H", data, pos)[0]
                pos += 2
                frames = []
                for _ in range(n_frames):
                    sprite_id, cx, cy, light_bg = struct.unpack_from("<HhhB", data, pos)
                    pos += 7
                    background = bool(light_bg & 0x80)
                    light = light_bg & 0x7F
                    frames.append(EffectFrame(sprite_id, cx, cy, light, background))
                directions.append(frames)
            all_frames.append(directions)
        self.path = path
        self.frames = all_frames

    def save(self, path=None):
        path = path or self.path
        out = bytearray()
        out += struct.pack("<H", len(self.frames))
        for directions in self.frames:
            out += struct.pack("<B", len(directions))
            for frames in directions:
                out += struct.pack("<H", len(frames))
                for fr in frames:
                    light_bg = (fr.light & 0x7F) | (0x80 if fr.background else 0)
                    out += struct.pack("<HhhB", fr.sprite_id, fr.cx, fr.cy, light_bg)
        if os.path.exists(path):
            bak = path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(path, "rb") as fsrc, open(bak, "wb") as fdst:
                fdst.write(fsrc.read())
        with open(path, "wb") as f:
            f.write(bytes(out))
        self.path = path

    def save_index(self, efpki_path):
        """Reescreve o .efpki - recalcula os offsets sequenciais varrendo
        o proprio self.frames (nao precisa reler o .efpk)."""
        offsets = []
        pos = 2  # depois do WORD frame_id_count
        for directions in self.frames:
            offsets.append(pos)
            pos += 1  # dir_count
            for frames in directions:
                pos += 2  # n_frames
                pos += len(frames) * 7  # cada CEffectFrame = 7 bytes
        out = struct.pack("<H", len(self.frames))
        out += struct.pack(f"<{len(self.frames)}I", *offsets)
        if os.path.exists(efpki_path):
            bak = efpki_path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(efpki_path, "rb") as fsrc, open(bak, "wb") as fdst:
                fdst.write(fsrc.read())
        with open(efpki_path, "wb") as f:
            f.write(out)

    def ensure_frame_id(self, frame_id):
        """Garante que self.frames tem pelo menos frame_id+1 entradas
        (preenchendo com listas vazias) - util ao criar um efeito novo."""
        while len(self.frames) <= frame_id:
            self.frames.append([])


# ---------------------------------------------------------------------------
# Fachada de conveniencia - abre os 4 arquivos de uma vez a partir da pasta
# Data do cliente.
# ---------------------------------------------------------------------------

class EffectSystem:
    """Abre EffectSpriteType.inf + Effect.aspk/.sppk + Effect.ppk/.ppki +
    Effect.efpk/.efpki de uma vez, a partir da pasta Data do cliente."""

    def __init__(self, data_dir):
        self.image_dir = os.path.join(data_dir, "Image")
        self.sprite_types = EffectSpriteTypeTable()
        self.sprite_types.load(os.path.join(data_dir, "Info", "EffectSpriteType.inf"))

        self.packs = {}
        self._load_packs()

        self._palette_cache = {}

    @staticmethod
    def _find_sprite_pack(base_path):
        """Tenta abrir o sprite pack com diferentes extensões possíveis
        (.aspk padrao, .sppk variante) - o formato binario e' o mesmo
        CAlphaSpritePal (WORD count + DWORD offsets), so' muda a extensao
        do arquivo (ex: Effect.aspk vs effectscreen.sppk)."""
        for ext in (".aspk", ".sppk"):
            path = base_path + ext
            if os.path.isfile(path):
                return AlphaSpritePack(path)
        return None

    def _load_packs(self):
        # Mapeamento: 1=EFFECT, 3=SCREEN (0=NORMAL/2=SHADOW sem arquivos)
        for blt_type, prefix in [(1, "Effect"), (3, "EffectScreen")]:
            base = os.path.join(self.image_dir, prefix)
            try:
                sprites = self._find_sprite_pack(base)
                if sprites is None:
                    continue
                self.packs[blt_type] = {
                    "sprites": sprites,
                    "palettes": PalettePack(base + ".ppk"),
                    "frames": EffectFramePack(base + ".efpk")
                }
            except Exception:
                continue

    def get_pack(self, blt_type):
        return self.packs.get(blt_type)

    def get_palette(self, frame_id, blt_type=1):
        pack = self.get_pack(blt_type)
        if not pack: return None
        key = (frame_id, blt_type)
        pal = self._palette_cache.get(key)
        if pal is None:
            pal = pack["palettes"].decode(frame_id)
            self._palette_cache[key] = pal
        return pal

    def decode_sprite(self, sprite_id, frame_id, blt_type=1):
        pack = self.get_pack(blt_type)
        if not pack: return None
        return pack["sprites"].decode(sprite_id, self.get_palette(frame_id, blt_type))

    def save_all(self):
        """Salva os 3 arquivos editaveis (aspk/aspki, ppk/ppki, efpk/efpki)
        - EffectSpriteType.inf nao e' reescrito automaticamente (chame
        self.sprite_types.save(...) explicitamente se editou a tabela)."""
        self.sprites.save(self.aspk_path)
        self.sprites.save_index(self.aspki_path)
        self.palettes.save(self.ppk_path)
        self.palettes.save_index(self.ppki_path)
        self.frames.save(self.efpk_path)
        self.frames.save_index(self.efpki_path)
        self._palette_cache = {}
