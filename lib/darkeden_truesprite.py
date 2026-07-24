#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Decodificador do formato de sprite "cor verdadeira" (truecolor) do DarkEden -
CSprite555/CSprite565 (client-master/Client/SpriteLib/CSprite555.cpp,
CSprite565.cpp) - usado pelas telas de UI que tem uma imagem de fundo unica
(Title.spk, Title_1024.spk, TitleBack.spk, TitleMenuDefault.spk, Login.spk,
LoginMenu.spk, OptionTitle.spk etc).

Este e' um formato DIFERENTE do CIndexSprite555 (ver darkeden_sprite.py na
pasta "tool python", usado por Item.ispk e pelos sprites de personagem):
CIndexSprite555 tem pixels "recoloraveis" (indice numa paleta de 495 tons)
alem de pixels literais; CSprite555/565 so' tem pixels literais RGB565 - sem
sistema de tingimento, e' so' uma imagem RLE comum.

Formato real, confirmado byte-a-byte contra os arquivos de verdade
(Title.spk/.spki, TitleMenuDefault.spk/.spki) e o codigo-fonte
(CSprite565.cpp:72-158, CSprite555.cpp:102-213, CSprite.cpp SetPixel/Blt):

  Arquivo .spk (pack inteiro):
    WORD  sprite_count                     ; sem assinatura/magic antes disso
    <sprite_count sprites, um atras do outro, sem padding entre eles>

  Sprite:
    WORD width
    WORD height
    ; se width==0 ou height==0: sprite vazio valido, sem linhas, para por aqui
    <height scanlines, linha 0 primeiro (topo)>

  Scanline:
    WORD row_len_words     ; contagem de WORDS do bloco abaixo (INCLUI a
                            ; propria word "segment_count" abaixo)
    <row_len_words WORDs = o "RLE row" abaixo, row_len_words*2 bytes>

  RLE row (primeira word = segment_count):
    WORD segment_count
    <segment_count segmentos>

  Segmento:
    WORD transparent_run_count   ; quantos pixels pular (transparentes)
    WORD color_run_count         ; quantos pixels literais vem a seguir
    WORD pixel[color_run_count]  ; RGB565 (bit15..11=R, bit10..5=G, bit4..0=B),
                                  ; little-endian, 2 bytes cada

Os pixels no disco sao SEMPRE RGB565 (CSprite.h:20-32: "on disk it is always
5:6:5"), independente do sprite ser CSprite555 ou CSprite565 em memoria - a
diferenca entre as duas so' importa pro renderer DirectDraw original, nao pra'
leitura do arquivo. Por isso este decodificador nao precisa se preocupar com
qual das duas classes seria usada em tempo real - so' ha' um formato de
arquivo.

O arquivo .spki (indice) so' serve pra' acesso aleatorio rapido no cliente
real (WORD count + DWORD offset[count]); como aqui a leitura e' sempre
sequencial e o pack inteiro cabe tranquilamente na memoria, o .spki e'
ignorado - os offsets nele batem exatamente com a posicao sequencial (nao ha'
gap/padding entre sprites), entao nao faz falta.
"""
import struct
import os
import shutil


def _rgb565_to_888(pixel):
    """Desempacota um WORD RGB565 (R:5 G:6 B:5, R nos bits mais altos) pra'
    uma tupla (r, g, b) de 8 bits por canal."""
    r5 = (pixel >> 11) & 0x1F
    g6 = (pixel >> 5) & 0x3F
    b5 = pixel & 0x1F
    r8 = (r5 * 255) // 31
    g8 = (g6 * 255) // 63
    b8 = (b5 * 255) // 31
    return r8, g8, b8


class TrueSpritePack:
    """Leitor sequencial de um .spk (formato CSprite555/565 - ver docstring
    do modulo). Le' o arquivo inteiro uma vez e monta um indice de offsets
    (equivalente ao .spki que o cliente real usa), assim como SpritePack faz
    em darkeden_sprite.py pro formato CIndexSprite555."""

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.data = f.read()
        self.count = struct.unpack_from('<H', self.data, 0)[0]
        self._offsets = None

    def _build_offsets(self):
        offsets = []
        pos = 2
        data = self.data
        for _ in range(self.count):
            offsets.append(pos)
            w, h = struct.unpack_from('<HH', data, pos)
            pos += 4
            if w and h:
                for _ in range(h):
                    row_len_words = struct.unpack_from('<H', data, pos)[0]
                    pos += 2 + row_len_words * 2
        self._offsets = offsets

    def decode(self, index):
        """Decodifica o sprite `index` pra' (width, height, rgb_bytes,
        mask_bytes) - rgb_bytes e' 3 bytes por pixel (RGB 8-bit), mask_bytes
        e' 1 byte por pixel (0=transparente, 255=opaco), mesma convencao de
        darkeden_sprite.SpritePack.decode() pra' poder reusar to_ppm()."""
        if self._offsets is None:
            self._build_offsets()
        if not (0 <= index < self.count):
            raise IndexError(f"sprite index {index} fora do intervalo (0..{self.count - 1})")

        data = self.data
        pos = self._offsets[index]
        width, height = struct.unpack_from('<HH', data, pos)
        pos += 4

        rgb = bytearray(width * height * 3)
        mask = bytearray(width * height)

        if not width or not height:
            return width, height, bytes(rgb), bytes(mask)

        for y in range(height):
            row_len_words = struct.unpack_from('<H', data, pos)[0]
            pos += 2
            row_end = pos + row_len_words * 2
            segment_count = struct.unpack_from('<H', data, pos)[0]
            rpos = pos + 2

            x = 0
            row_base = (y * width) * 3
            for _ in range(segment_count):
                trans_count, color_count = struct.unpack_from('<HH', data, rpos)
                rpos += 4
                x += trans_count
                if color_count:
                    pixels = struct.unpack_from(f'<{color_count}H', data, rpos)
                    rpos += color_count * 2
                    for p in pixels:
                        if 0 <= x < width:
                            r, g, b = _rgb565_to_888(p)
                            off = row_base + x * 3
                            rgb[off:off + 3] = bytes((r, g, b))
                            mask[y * width + x] = 255
                        x += 1

            pos = row_end

        return width, height, bytes(rgb), bytes(mask)

    # ---------------------------------------------------------------- write
    # ESCRITA (2026-07-21) - confirmado espelhando exatamente o formato de
    # leitura acima contra CSprite555::SaveToFile/CSprite565::SaveToFile
    # (client-master/Client/SpriteLib/CSprite555.cpp:22-97,
    # CSprite565.cpp:21-70): mesmo layout linha-a-linha (row_len,
    # segment_count, segments de trans_count/color_count/pixels RGB565),
    # sem limite de tamanho de "run" (contagens sao WORD) e transparencia
    # sempre binaria (sem alpha parcial no arquivo). CSprite555 guarda em
    # RAM como RGB555 mas converte pra' 565 ao salvar (555.cpp:60-64) - no
    # DISCO e' sempre RGB565, exatamente o que o decode() acima ja' le'.
    #
    # IMPORTANTE (confirmado lendo CTypePack::LoadFromFileRunning,
    # CTypePack.h:203-234, usado por C_SPRITE_PACK::Open,
    # VS_UI_util.cpp:641-662): o .spki NAO e' opcional/so'-otimizacao pra'
    # esses arquivos de UI - o cliente le' os offsets de LA' pra' saber
    # onde cada sprite comeca (nao escaneia sequencial). Por isso toda
    # gravacao aqui SEMPRE regrava o .spki tambem, nunca so' o .spk.

    def _sprite_byte_range(self, index):
        if self._offsets is None:
            self._build_offsets()
        if not (0 <= index < self.count):
            raise IndexError(f"sprite index {index} fora do intervalo (0..{self.count - 1})")
        start = self._offsets[index]
        end = self._offsets[index + 1] if index + 1 < self.count else len(self.data)
        return start, end

    def raw_sprite_bytes(self, index):
        """Bytes crus (ja' no formato de disco) do sprite `index` - usado
        pra' copiar sprites intactos ao remontar o arquivo, sem precisar
        decodificar/reconstruir cada um a partir dos pixels."""
        start, end = self._sprite_byte_range(index)
        return self.data[start:end]

    def replace_sprite(self, index, new_sprite_bytes):
        """Troca o sprite `index` (em memoria - chame save() pra' gravar em
        disco). new_sprite_bytes e' o formato cru retornado por
        encode_sprite_from_image()."""
        start, end = self._sprite_byte_range(index)
        self.data = self.data[:start] + bytes(new_sprite_bytes) + self.data[end:]
        self._offsets = None

    def append_sprite(self, new_sprite_bytes):
        """Acrescenta um sprite novo no final (em memoria). Devolve o
        indice novo (= contagem antiga)."""
        new_index = self.count
        self.count += 1
        self.data = struct.pack('<H', self.count) + self.data[2:] + bytes(new_sprite_bytes)
        self._offsets = None
        return new_index

    def save(self, spk_path=None, spki_path=None):
        """Grava o .spk (dados) E o .spki (indice de offsets, OBRIGATORIO -
        ver nota acima) - sempre com backup automatico (uma vez so', na
        primeira gravacao real) dos dois arquivos."""
        spk_path = spk_path or self.path
        if spki_path is None:
            spki_path = _spki_path_for(spk_path)

        backup_spk = spk_path + ".bak_before_save"
        if os.path.exists(spk_path) and not os.path.exists(backup_spk):
            shutil.copyfile(spk_path, backup_spk)
        with open(spk_path, 'wb') as f:
            f.write(self.data)

        if self._offsets is None:
            self._build_offsets()
        if os.path.exists(spki_path):
            backup_spki = spki_path + ".bak_before_save"
            if not os.path.exists(backup_spki):
                shutil.copyfile(spki_path, backup_spki)
        with open(spki_path, 'wb') as f:
            f.write(struct.pack('<H', self.count))
            for off in self._offsets:
                f.write(struct.pack('<I', off))

        self.path = spk_path


def _spki_path_for(spk_path):
    """<algo>.spk -> <algo>.spki (preserva maiuscula/minuscula do resto)."""
    root, ext = os.path.splitext(spk_path)
    return root + ext + "i"


def _rgb888_to_565(r, g, b):
    """Empacota RGB de 8 bits por canal no WORD 565 do formato em disco
    (inverso de _rgb565_to_888)."""
    return ((r * 31 // 255) << 11) | ((g * 63 // 255) << 5) | (b * 31 // 255)


def encode_sprite_from_image(image_path, target_size=None, alpha_threshold=128):
    """Constroi um sprite CSprite555/565 (bytes crus: WORD width,height +
    por linha [WORD row_len_words, WORD segment_count, segmentos de
    (trans_count,color_count,color_count x WORD RGB565)]) a partir de uma
    imagem qualquer, via Pillow. Transparencia e' binaria (so' "desenhado"
    ou "pulado" - o formato nao tem alpha parcial, ver docstring do
    modulo), igual darkeden_sprite.encode_sprite_from_image() mas SEM o
    campo indexCount (esse formato nao tem pixel "recoloravel").

    target_size=(w,h): se informado, redimensiona a imagem pra' esse
    tamanho ANTES de codificar (Pillow LANCZOS) - use o tamanho do sprite
    original que voce esta' substituindo pra' garantir que o layout da
    tela nao quebre (botoes/fundos tem posicao fixa esperando aquele
    tamanho). Deixe None pra' manter o tamanho nativo da imagem importada."""
    from PIL import Image

    img = Image.open(image_path).convert("RGBA")
    if target_size and img.size != tuple(target_size):
        img = img.resize(tuple(target_size), Image.LANCZOS)
    width, height = img.size
    pixels = img.load()

    out = bytearray()
    out += struct.pack('<HH', width, height)

    for y in range(height):
        segments = []
        x = 0
        while x < width:
            trans_start = x
            while x < width and pixels[x, y][3] < alpha_threshold:
                x += 1
            trans_count = x - trans_start
            if x >= width:
                break
            run = []
            while x < width and pixels[x, y][3] >= alpha_threshold:
                r, g, b, a = pixels[x, y]
                run.append(_rgb888_to_565(r, g, b))
                x += 1
            segments.append((trans_count, run))

        row_words = [len(segments)]
        for trans_count, run in segments:
            row_words.append(trans_count)
            row_words.append(len(run))
            row_words.extend(run)

        out += struct.pack('<H', len(row_words))
        out += struct.pack(f'<{len(row_words)}H', *row_words)

    return bytes(out), width, height


def to_ppm(width, height, rgb, mask, bg=(48, 48, 64)):
    """Composita rgb/mask sobre um fundo solido e retorna um blob PPM (P6)
    binario - Tkinter's PhotoImage(data=...) le' isso direto, sem precisar
    de Pillow. Identica a' funcao homonima em darkeden_sprite.py."""
    out = bytearray(width * height * 3)
    for i in range(width * height):
        if mask[i]:
            out[i * 3:i * 3 + 3] = rgb[i * 3:i * 3 + 3]
        else:
            out[i * 3:i * 3 + 3] = bytes(bg)
    header = f"P6\n{width} {height}\n255\n".encode('ascii')
    return header + bytes(out)


def find_ui_spk(client_dir, spk_filename):
    """Acha Data\\Ui\\spk\\<spk_filename> dentro da pasta do cliente
    (CLIENT_DIR do darkeden_interface_editor.py), com fallback
    case-insensitive. Retorna None se nao encontrar (o fundo visual e'
    so' um complemento - o editor continua funcionando sem ele)."""
    import os
    candidate = os.path.join(client_dir, "Data", "Ui", "spk", spk_filename)
    if os.path.isfile(candidate):
        return candidate
    ui_dir = os.path.join(client_dir, "Data", "Ui", "spk")
    if os.path.isdir(ui_dir):
        for fname in os.listdir(ui_dir):
            if fname.lower() == spk_filename.lower():
                return os.path.join(ui_dir, fname)
    return None


# Fundo real de cada CHAVE do interface.inf - confirmado lendo o
# codigo-fonte de cada janela (VS_UI_Title.cpp / VS_UI_Game.cpp), uma
# camada por vez (a primeira da lista fica embaixo). x,y sao o deslocamento
# de cada camada dentro da janela real (0,0 = topo-esquerda da janela, que
# e' a mesma origem que os pontos do interface.inf usam).
#
# TITLE (C_VS_UI_TITLE::C_VS_UI_TITLE, VS_UI_Title.cpp~4800): fundo unico
#   Title.spk (800x600) / Title_1024.spk (1024x768, so' no modo widescreen
#   g_MyFull) - janela centralizada, tamanho exato do sprite.
# LOGIN_REF (C_VS_UI_LOGIN::C_VS_UI_LOGIN, ~4180): popup de ID/senha,
#   Login.spk (222x179) / Login_1024.spk - so' referencia visual (ver
#   LOGIN_REF_KEY no editor - nao ha' pontos de interface.inf pra' isso).
# GAME_MENU (C_VS_UI_GAMEMENU, VS_UI_Game.cpp~6136): menu ESC do jogo
#   (Option/Logout/Continue) - fundo DIFERENTE por raca, sem variante
#   widescreen (g_GameRect e' sempre 800x600 fixo mesmo em tela larga -
#   WinMain.cpp:62). Pontos sao AO VIVO (pSkin->GetPoint() de verdade).
# OPTION (C_VS_UI_OPTION::C_VS_UI_OPTION, VS_UI_Title.cpp~5450, caminho
#   m_IsTitle==false = dialogo de opcoes ABERTO DE DENTRO DO JOGO): fundo
#   DIFERENTE por raca, sem variante widescreen. Pontos sao AO VIVO so'
#   nesse caminho (m_IsTitle==false) - o dialogo de opcoes acessado pela
#   tela de titulo usa literais fixos, ignora interface.inf (igual TITLE).
# NEW_CHAR (C_VS_UI_NEWCHAR::C_VS_UI_NEWCHAR/Show, ~1075/2393): fundo em
#   DUAS camadas - Common.spk sprite 0 (800x600, backdrop cheio) +
#   CharCreate.spk sprite 0 (510x354, painel decorado, parcialmente
#   transparente) colado em (250,150) por cima. So' modo classico -
#   Common_1024.spk sprite 0 NAO e' uma imagem solida (so' 239436/480000
#   pixels opacos - sobra letterbox que exigiria mais camadas nao
#   confirmadas), entao o widescreen fica de fora por ora.
# INFO (C_VS_UI_INFO::_Show2, VS_UI_GameCommon.cpp~17030): CORRECAO - essa
#   CHAVE NAO e' morta (diferente do que se pensava antes) - e' a janela de
#   status do personagem (Esc/tecla de info -> aba "Char"), com STR/DEX/
#   INT/HP/MP/Nome/Fama/Alinhamento etc. E' um HIBRIDO: os pontos-ancora
#   (Desc_Box, Field_x1/x2, Name/Fame/Align Fix Position, e os 9 offsets de
#   icone STR..PROTECTION) VEM do interface.inf via pSkin->GetPoint() de
#   verdade; so' os PEQUENOS deslocamentos finais de cada numero impresso
#   (+4/+5 px, gap*20 por linha) sao literais fixos por cima dessas ancoras.
#   Nao ha' UM fundo unico pra' essa tela (nao e' uma imagem de tela
#   inteira como Title/Login) - e' montada por varias pecas pequenas do
#   InfoSlayer/Vampire/Ousters.spk (112-114 sprites cada). Mostramos as
#   DUAS pecas mais relevantes pra' orientacao visual:
#     - CHAR_BOX (indice 15 no enum C_GLOBAL_RESOURCE::INFO_SPK, ver
#       VS_UI_GlobalResource.h:228) - moldura do retrato, POSICAO FIXA no
#       C++ (m_rt_char_box.Set: Slayer 20,22 / Vampire+Ousters 20,15 -
#       VS_UI_GameCommon.cpp:11941,11952,11963).
#     - DESC_BOX (indice 16) - caixa de nome/fama/nivel, posicao AO VIVO
#       (e' literalmente o ponto "Desc_Box" do interface.inf) - por isso
#       essa camada e' calculada dinamicamente no editor (ver
#       InterfaceEditor._background_layers), nao aqui nessa funcao estatica.
#   Tamanho da janela (pra' nao cortar o canvas antes da hora): Slayer
#   321x330, Vampire/Ousters 336x335 (Set() na construtora, mesmos arquivo
#   e linhas do m_rt_char_box acima).
RACES = ("SLAYER", "VAMPIRE", "OUSTERS")

INFO_CHAR_BOX_SPRITE_INDEX = 15   # C_GLOBAL_RESOURCE::CHAR_BOX
INFO_DESC_BOX_SPRITE_INDEX = 16   # C_GLOBAL_RESOURCE::DESC_BOX
INFO_CHAR_BOX_POS = {
    "SLAYER": (20, 22),
    "VAMPIRE": (20, 15),
    "OUSTERS": (20, 15),
}
INFO_WINDOW_SIZE = {
    "SLAYER": (321, 330),
    "VAMPIRE": (336, 335),
    "OUSTERS": (336, 335),
}

# Icones REAIS de nome/status - confirmado lendo C_VS_UI_INFO::_Show2
# (VS_UI_GameCommon.cpp, blocos Slayer~17138-17220, Vampire~17542-17627,
# Ousters~17918-18014) e o enum C_GLOBAL_RESOURCE::INFO_SPK
# (VS_UI_GlobalResource.h) - indices confirmados por contagem sequencial
# (com as 2 unicas reatribuicoes "=" do enum inteiro) E por bater EXATO
# com a contagem real de sprites de cada InfoRACE.spk (112/105/114).
#
# Cada entrada de "name_group"/"stat_group" e' (offset_do_ponto, indice_do_
# sprite_INFO_SPK, indice_da_linha/gap). offset_do_ponto e' somado ao
# indice-base da raca (tirado AO VIVO do *INFO RECT_LIST, ver
# InterfaceEditor._info_race_starts) pra' achar o ponto de verdade.
#
# Formula de posicao (x_window,y_window omitidos - sao 0 no nosso sistema
# de referencia, a origem e' sempre o topo-esquerda da janela):
#   name_group: x = point[base+1].x (Field_x1) + point[base+offset].x
#               y = CHAR_BOX_Y (fixo por raca) + point[base+offset].y + 20*gap
#   stat_group: x = CHAR_BOX_X (fixo, =20 sempre) + point[base+offset].x
#               y = point[base].y (Desc_Box.y) + point[base+offset].y + 20*gap
# TITLE_STR=32,TITLE_DEX=33,TITLE_INT=34,TITLE_HP=35,TITLE_TOHIT=36,
# TITLE_DAMAGE=37,TITLE_DEFENCE=38,TITLE_PROTECTION=39,TITLE_FAME=46,
# TITLE_MP=47(mesmo indice de TITLE_BONUS - racas diferentes, nunca ao
# mesmo tempo),TITLE_NAME=29,TITLE_ALIGN=30,OUSTERS_EP=76.
INFO_FIELD_GAP = 20

INFO_ICON_LAYOUT = {
    "SLAYER": {
        "name_group": [
            (2, 29, 0),   # TITLE_NAME
            (2, 46, 1),   # TITLE_FAME
            (2, 30, 2),   # TITLE_ALIGN
        ],
        "stat_group": [
            (3, 32, 0), (4, 33, 1), (5, 34, 2), (6, 35, 3),   # STR DEX INT HP
            (7, 47, 4),                                        # MP (TITLE_MP)
            (8, 36, 5), (9, 37, 6), (10, 38, 7), (11, 39, 8),  # TOHIT DAMAGE DEFENCE PROTECTION
        ],
    },
    "VAMPIRE": {
        "name_group": [
            (3, 29, 0),   # TITLE_NAME
            (3, 30, 1),   # TITLE_ALIGN
        ],
        "stat_group": [
            (4, 32, 0), (5, 33, 1), (6, 34, 2), (7, 35, 3),
            (8, 36, 4), (9, 37, 5), (10, 38, 6), (11, 39, 7),
        ],
    },
    "OUSTERS": {
        "name_group": [
            (3, 29, 0),   # TITLE_NAME
            (3, 30, 1),   # TITLE_ALIGN
        ],
        "stat_group": [
            (10, 32, 0), (11, 33, 1), (12, 34, 2), (13, 35, 3),   # STR DEX INT HP
            (14, 76, 4),                                          # EP (OUSTERS_EP)
            (15, 36, 5), (16, 37, 6), (17, 38, 7), (18, 39, 8),   # TOHIT DAMAGE DEFENCE PROTECTION
        ],
    },
}

_INFO_SPK_BY_RACE = {
    "SLAYER": "InfoSlayer.spk",
    "VAMPIRE": "InfoVampire.spk",
    "OUSTERS": "InfoOusters.spk",
}


def get_window_min_size(key, race="SLAYER"):
    """Tamanho minimo (w,h) da janela real dessa CHAVE/raca, pra' evitar
    cortar o canvas quando as camadas de fundo nao cobrem a janela inteira
    (ex: INFO so' tem 2 pecas pequenas, bem menores que a janela toda) - ou
    None se nao ha' um tamanho fixo confirmado pra' essa combinacao."""
    if key == "INFO":
        return INFO_WINDOW_SIZE.get(race)
    return None


# Sprite REAL de cada ponto de NEW_CHAR/OPTION - confirmado lendo os
# enums COMMON_SPK_ID/CREATE_SPK_ID (VS_UI/src/header/VS_UI_title.h:572,
# 583, classe C_VS_UI_NEWCHAR) e MAIN_SPK/ETC_SPK (VS_UI_title.h:1176,
# 1187, classe C_VS_UI_OPTION), com as dimensoes de cada sprite conferidas
# empiricamente (todas de tamanho de botao/aba/checkbox, nada absurdo) e
# duas renderizadas visualmente pra' confirmar (mostram "Slayer"/"Check").
#
# TITLE e GAME_MENU FICAM DE FORA DE PROPOSITO: confirmado lendo
# C_VS_UI_TITLE::ShowButtonWidget (VS_UI_Title.cpp:5096-5101) e
# C_VS_UI_GAMEMENU::ShowButtonWidget (VS_UI_Game.cpp:6220-6224) que os
# sprites de botao (CONNECT_HILIGHT etc) SO' sao desenhados com o mouse
# em cima (hover) ou pressionado - em repouso NADA e' desenhado, porque o
# visual "parado" ja' esta' embutido na propria imagem de fundo. Mostrar
# esses sprites sempre enganaria sobre a aparencia normal da tela.
NEW_CHAR_POINT_SPRITES = {
    0: ("Common.spk", 1),        # BACK_BUTTON
    1: ("Common.spk", 4),        # NEXT_BUTTON
    2: ("CharCreate.spk", 10),   # FACE_BACK_BUTTON
    3: ("CharCreate.spk", 13),   # FACE_NEXT_BUTTON
    4: ("CharCreate.spk", 5),    # SLAYER_BUTTON
    5: ("CharCreate.spk", 6),    # VAMPIRE_BUTTON
    6: ("CharCreate.spk", 7),    # OUSTERS_BUTTON
    7: ("CharCreate.spk", 8),    # MALE_BUTTON
    8: ("CharCreate.spk", 9),    # FEMALE_BUTTON
    9: ("CharCreate.spk", 19),   # SAVE_BUTTON
    10: ("CharCreate.spk", 22),  # LOAD_BUTTON
    11: ("CharCreate.spk", 25),  # REROLL_BUTTON
    12: ("CharCreate.spk", 16),  # CHECK_BUTTON
    13: ("CharCreate.spk", 29),  # PLUS_BUTTON (STR)
    14: ("CharCreate.spk", 32),  # MINUS_BUTTON (STR)
    15: ("CharCreate.spk", 29),  # PLUS_BUTTON (DEX)
    16: ("CharCreate.spk", 32),  # MINUS_BUTTON (DEX)
    17: ("CharCreate.spk", 29),  # PLUS_BUTTON (INT)
    18: ("CharCreate.spk", 32),  # MINUS_BUTTON (INT)
}

OPTION_POINT_SPRITES_STATIC = {
    0: ("Option.spk", 15),   # BUTTON_CLOSE
    5: ("Option.spk", 11),   # CHECK_BACK_DISABLE
}
OPTION_MAIN_SPK_TAB_SPRITE = {1: 2, 2: 3, 3: 4, 4: 5}  # TAB_CONTROL/GRAPHIC/SOUND/GAME
_OPTION_RACE_SPK = {
    "SLAYER": "OptionSlayer.spk", "VAMPIRE": "OptionVampire.spk", "OUSTERS": "OptionOusters.spk",
}


def get_point_sprite(key, order_index, race="SLAYER"):
    """Retorna (spk_filename, sprite_index) do sprite REAL do botao/campo
    nesse ponto especifico - ou None se nao ha' sprite mapeado pra' essa
    CHAVE/indice (a maioria dos pontos deste editor nao tem, so' NEW_CHAR
    e OPTION - ver comentario acima sobre por que TITLE/GAME_MENU ficam de
    fora)."""
    if key == "NEW_CHAR":
        return NEW_CHAR_POINT_SPRITES.get(order_index)
    if key == "OPTION":
        if order_index in OPTION_POINT_SPRITES_STATIC:
            return OPTION_POINT_SPRITES_STATIC[order_index]
        if order_index in OPTION_MAIN_SPK_TAB_SPRITE:
            fname = _OPTION_RACE_SPK.get(race)
            if fname:
                return (fname, OPTION_MAIN_SPK_TAB_SPRITE[order_index])
    return None


def get_background_layers(key, widescreen=False, race="SLAYER"):
    """Retorna lista de (spk_filename, sprite_index, x, y) - as camadas do
    fundo real dessa CHAVE, primeira embaixo - ou [] se essa combinacao nao
    tem fundo confirmado (a tela pode ainda existir no interface.inf, so'
    nao ha' uma imagem de fundo pronta pra' mostrar atras dela).

    Nota sobre INFO: essa funcao so' devolve a camada ESTATICA (CHAR_BOX,
    posicao fixa no C++) - a camada DINAMICA do DESC_BOX (posicao vem do
    proprio interface.inf, editavel) e' adicionada pelo chamador
    (InterfaceEditor._background_layers), que tem acesso ao documento
    carregado; esta funcao aqui nao tem."""
    if key == "TITLE":
        return [("Title_1024.spk" if widescreen else "Title.spk", 0, 0, 0)]
    if key == "LOGIN_REF":
        return [("Login_1024.spk" if widescreen else "Login.spk", 0, 0, 0)]
    if key == "NEW_CHAR":
        if widescreen:
            return []
        return [("Common.spk", 0, 0, 0), ("CharCreate.spk", 0, 250, 150)]
    if key == "GAME_MENU":
        fname = {"SLAYER": "GameMenuSlayer.spk", "VAMPIRE": "GameMenuVampire.spk",
                 "OUSTERS": "GameMenuOusters.spk"}.get(race)
        return [(fname, 0, 0, 0)] if fname else []
    if key == "OPTION":
        fname = {"SLAYER": "OptionSlayer.spk", "VAMPIRE": "OptionVampire.spk",
                 "OUSTERS": "OptionOusters.spk"}.get(race)
        return [(fname, 0, 0, 0)] if fname else []
    if key == "INFO":
        fname = _INFO_SPK_BY_RACE.get(race)
        if not fname:
            return []
        cx, cy = INFO_CHAR_BOX_POS.get(race, (20, 22))
        return [(fname, INFO_CHAR_BOX_SPRITE_INDEX, cx, cy)]
    return []


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("uso: python darkeden_truesprite.py caminho/pro/Arquivo.spk [indice]")
        sys.exit(1)
    pack = TrueSpritePack(sys.argv[1])
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    w, h, rgb, mask = pack.decode(idx)
    opaque = sum(1 for b in mask if b) if w and h else 0
    print(f"{sys.argv[1]}: {pack.count} sprite(s); sprite #{idx} = {w}x{h}, "
          f"{opaque}/{w * h if w and h else 0} pixels opacos")
