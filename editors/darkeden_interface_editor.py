#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DarkEden Interface Editor - editor visual do interface.inf/ChinaInterface.inf
REAL deste jogo (nao e' um INI generico - e' o formato proprio lido por
SkinManager::LoadInformation, client-master/VS_UI/src/SkinManager.cpp).

Formato real (confirmado lendo o codigo-fonte):
  ; comentario
  *CHAVE TIPO                  <- CHAVE em {INFO,GAME_MENU,OPTION,TITLE,NEW_CHAR}
  X Y                          ; comentario opcional     <- se TIPO=POINT_LIST
  L T R B                      ; comentario opcional     <- se TIPO=RECT_LIST
  *END                         <- fecha o bloco

Cada entrada e' acessada por INDICE (0,1,2...) dentro da lista da sua
CHAVE+TIPO - nao tem nome, so' a posicao importa pro codigo do jogo. O
comentario ao lado (quando existe) e' a UNICA pista de pra' que serve
cada uma - por isso o editor mostra o comentario, nao so' o indice.

O arquivo de verdade fica dentro de Data\\Info\\infodata.rpk (RAR
antigo, senha "darkeden") - e o cliente so' consegue LER RAR antigo,
mas as ferramentas desta maquina so' criam RAR5 (incompativel). Por
isso este editor NAO mexe no .rpk: ele salva um arquivo solto em
Data\\Info\\infodata_EN\\interface.inf, que o CRarFile::Open()
modificado (ver client-master/VS_UI/RarFile.cpp) le' automaticamente
ANTES de tentar extrair do .rpk - nao precisa recompilar nem remontar
RAR nenhum.

Uso:
    python darkeden_interface_editor.py [caminho/pro/interface.inf]

Se nao passar caminho, tenta achar automaticamente extraindo do
infodata.rpk do cliente configurado em CLIENT_DIR abaixo (precisa de
7z.exe instalado e no PATH ou no caminho padrao do 7-Zip).

Fundo real da tela (2026-07-21, expandido pro jogo inteiro)
-------------------------------------------------------------
Quando o modo "Ajuste automatico" esta' DESLIGADO, o canvas mostra a
imagem de fundo REAL da tela (nao so' um retangulo cinza) pra' toda tela
mapeada em darkeden_truesprite.get_background_layers() - cada uma
confirmada lendo o construtor/Show() da classe C++ correspondente:

  - TITLE: Title.spk (800x600) / Title_1024.spk (1024x768, combobox
    "Canvas"). DADO MORTO (ver abaixo).
  - LOGIN (popup - so' referencia): Login.spk - popup que abre em cima da
    tela de titulo ao clicar CONNECT. Sem pontos no interface.inf.
  - GAME_MENU: fundo DIFERENTE por raca (combobox "Raca") -
    GameMenuSlayer/Vampire/Ousters.spk. AO VIVO (ver abaixo). So' os 2
    pontos da raca escolhida aparecem (os outros 4 sao de outra raca).
  - OPTION: fundo DIFERENTE por raca - OptionSlayer/Vampire/Ousters.spk.
    PARCIALMENTE AO VIVO (ver abaixo) - so' o caminho de dentro do jogo.
  - NEW_CHAR: DUAS camadas compostas - Common.spk (fundo cheio 800x600) +
    CharCreate.spk (painel, parcialmente transparente) em (250,150) por
    cima. AO VIVO. So' modo classico (widescreen nao suportado - ver
    darkeden_truesprite.get_background_layers docstring).
  - INFO: janela de status do personagem (STR/DEX/INT/HP/MP/Nome/Fama).
    AO VIVO (CORRECAO - ver abaixo, uma pesquisa anterior errou isso).
    Fundo por raca: CHAR_BOX (moldura do retrato, indice 15, posicao
    fixa) + DESC_BOX (indice 16, posicao AO VIVO - segue o ponto
    'Desc_Box' se voce editar). So' os 2 pontos mais relevantes tem
    peca visual - o resto (STR/DEX/etc) sao so' pontos, sem sprite
    proprio pra' mostrar.

Precisa de Pillow (pip install Pillow) - sem isso, ou se nao achar algum
arquivo, o editor cai de volta no retangulo cinza de sempre pra' aquela
camada, sem quebrar. Ver darkeden_truesprite.py pro decodificador do
formato (CSprite555/565 - formato DIFERENTE do CIndexSprite555 usado por
Item.ispk/personagens) e pra' get_background_layers() com as citacoes
completas de cada tela.

Status ao vivo/morto de cada CHAVE (resumo - texto completo em
KEY_STATUS_NOTES abaixo, tambem mostrado na barra de status do editor):
  - TITLE: MORTO - C_VS_UI_TITLE busca SkinManager::TITLE mas nunca chama
    GetPoint() pras' 4 pontos; usa literais fixos (673,371 etc classico,
    888,544 etc widescreen). interface.inf foi corrigido pra' bater com o
    valor classico so' por consistencia - continua sem efeito ate' alguem
    mudar VS_UI_Title.cpp pra' ler GetPoint() de verdade e recompilar.
  - GAME_MENU: AO VIVO - C_VS_UI_GAMEMENU (VS_UI_Game.cpp) chama
    GetPoint() de verdade pros 6 pontos (2 por raca). Editar aqui MUDA os
    botoes do menu Esc no jogo de verdade.
  - OPTION: PARCIAL - C_VS_UI_OPTION so' chama GetPoint()/GetRect() no
    caminho m_IsTitle==false (dialogo aberto de dentro do jogo via Esc);
    o dialogo de opcoes da tela de titulo usa literais fixos, igual TITLE.
  - NEW_CHAR: AO VIVO - C_VS_UI_NEWCHAR chama GetPoint() em sequencia pra'
    cada botao. Editar aqui MUDA a tela de criacao de personagem.
  - INFO: AO VIVO (CORRECAO 2026-07-21 - uma pesquisa anterior, mais
    rasa, tinha concluido "morto"; uma pesquisa mais profunda achou 3
    chamadas reais em VS_UI_GameCommon.cpp: C_VS_UI_INFO::_Show1/_Show2/
    _Show5). _Show2 (janela de status, aba "Char") chama GetPoint() de
    verdade pro Desc_Box, Field_x1/x2, Name/Fame/Align e os 9 offsets
    STR..PROTECTION. Editar/salvar aqui MUDA essas posicoes no jogo. So'
    os deslocamentos finais de cada numero impresso (+4/+5px, gap fixo
    por linha) sao literais por cima dessas ancoras - isso NAO torna a
    secao "morta", so' significa que o pixel exato do texto tem um
    ajuste fino adicional.

LOGIN (popup - so' referencia): os campos de usuario/senha NAO estao em
NENHUM arquivo de dados - sao #define fixos no C++ (LOGIN_ID_X/Y=59,49 e
LOGIN_PASSWORD_X/Y=59,89, ambos 130x23, relativos ao topo-esquerdo do
popup Login.spk de 222x179). Por isso esse "ecra" foi adicionado so' como
referencia visual (fundo real + retangulos tracejados dos campos) - nao
tem entradas editaveis/arrastáveis porque nao existe onde salvar isso.

Sprites REAIS de botao/icone nos pontos (2026-07-21)
-------------------------------------------------------
Alem do fundo, alguns pontos agora mostram o SPRITE REAL do botao/icone
que fica ali - nao um marcador abstrato -, seguindo a posicao ao vivo (se
arrastar, o sprite anda junto). Ver darkeden_truesprite.get_point_sprite()
e INFO_ICON_LAYOUT pras' citacoes completas:
  - NEW_CHAR: os 19 botoes (Voltar/Proximo, troca de rosto, Slayer/
    Vampire/Ousters, Masculino/Feminino, Salvar/Carregar/Rolar, Check,
    +/- de STR/DEX/INT) - confirmado nos enums COMMON_SPK_ID/CREATE_SPK_ID
    (VS_UI_title.h:572,583).
  - OPTION: botao fechar + as 4 abas (atalho/tela/som/jogo) + o quadrado
    do checkbox - confirmado nos enums MAIN_SPK/ETC_SPK (VS_UI_title.h:
    1176,1187). Muda de imagem conforme a raca escolhida.
  - INFO: os icones de Nome/Fama/Alinhamento e os 8-9 icones de STR/DEX/
    INT/HP/MP(ou EP p/ Ousters)/TOHIT/DAMAGE/DEFENSE/PROTECTION -
    confirmado no enum C_GLOBAL_RESOURCE::INFO_SPK (VS_UI_GlobalResource.h)
    E na contagem exata de sprites de cada InfoRACE.spk (112/105/114 -
    bateu certinho, forte confirmacao). A posicao de CADA icone e'
    CALCULADA AO VIVO a partir dos pontos Desc_Box/Field_x1 e do proprio
    offset STR/DEX/etc - arraste qualquer um desses pontos e os icones
    relacionados se movem junto, exatamente como o C++ faz.
  - TITLE e GAME_MENU FICAM DE FORA de proposito: confirmado no codigo
    (ShowButtonWidget de cada um) que o sprite de botao so' aparece com
    mouse em cima (hover) ou pressionado - em repouso nada e' desenhado
    (a aparencia "parada" ja' esta' no proprio fundo). Mostrar sempre
    enganaria sobre como a tela normalmente se parece.

JANELAS DO JOGO - modelo por raca (2026-07-21)
-------------------------------------------------
Nova opcao na combo "Tela (chave)": "JANELAS DO JOGO (modelo por raca)".
ISSO NAO E' O interface.inf - e' um mecanismo TOTALMENTE diferente: as 24
janelas de UI do jogo (Inventario, Info/status, HP bar, minimapa,
quickslot, missoes etc) ja' sao arrastaveis com o mouse dentro do jogo, e
a posicao final e' salva sozinha (ao sair do mundo) POR PERSONAGEM, num
arquivo binario "UserSet\\<Nome>-<Dim>-<Mundo>.set" - ver
darkeden_windowset.py pro formato exato (confirmado byte-a-byte contra
todos os .set reais deste projeto, sempre 669 bytes).

Por que "modelo por raca" e nao "por personagem": o tamanho de varias
janelas (ex: Inventario) muda de raca pra' raca (arte .spk diferente por
raca - InventorySlayer/Vampire/Ousters.spk). Editar aqui NAO mexe direto
num personagem - trabalha num MODELO proprio desta ferramenta (arquivo
window_layout_templates.json, ao lado deste script), um conjunto de
posicoes por raca. Fluxo:
  1. Escolha "JANELAS DO JOGO" na combo Tela + a raca no combo "Raca".
  2. Arraste os retangulos das 24 janelas na tela de referencia 800x600
     (ou edite X/Y/W/H no painel de propriedades) - janela "nunca
     definida" comeca sem retangulo, edite pra' dar uma posicao inicial.
  3. "Salvar modelo de janelas" grava o JSON com as 3 racas.
  4. "Aplicar a um personagem..." escolhe um UserSet\\*.set real (lista
     automaticamente os personagens encontrados em CLIENT_DIR\\UserSet) e
     GRAVA so' os Rects das janelas definidas no modelo dentro dele - o
     resto do arquivo (hotkeys, filtros de chat etc) fica intacto, sempre
     com backup automatico antes de sobrescrever.
"""
import os
import re
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
try:
    import darkeden_truesprite as truesprite
except ImportError:
    truesprite = None

try:
    import darkeden_windowset as windowset
except ImportError:
    windowset = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

import json

# ---------------------------------------------------------------------------
# Ajuste pro seu ambiente
# ---------------------------------------------------------------------------
CLIENT_DIR = r"C:\Users\Victoria\OneDrive\Área de Trabalho\DARKEDEN"
RPK_PASSWORD = "darkeden"
SEVENZIP_CANDIDATES = [
    r"C:\Program Files\7-Zip\7z.exe",
    "7z",
]

KEYS = ["INFO", "GAME_MENU", "OPTION", "TITLE", "NEW_CHAR"]
LIST_TYPES = ["POINT_LIST", "RECT_LIST"]

# "LOGIN_REF" nao e' uma CHAVE real do interface.inf (nao existe *LOGIN
# la' dentro) - e' um popup a parte (C_VS_UI_LOGIN, Data\Ui\spk\Login.spk)
# que abre por cima da tela de titulo quando clica CONNECT, com os campos
# de usuario/senha em posicoes fixas no C++ (LOGIN_ID_X/Y, LOGIN_PASSWORD_X/Y
# em VS_UI_Title.cpp) - sem representacao em NENHUM arquivo de dados. Foi
# adicionado aqui so' pra' visualizacao de referencia (fundo real + onde
# ficam os campos), nao e' editavel porque nao ha' entrada de interface.inf
# nenhuma pra' salvar.
LOGIN_REF_KEY = "LOGIN_REF"
LOGIN_REF_LABEL = "LOGIN (popup - so' referencia)"

# campos fixos do popup de login (classico 800x600) - ver VS_UI_Title.cpp
# C_VS_UI_LOGIN::C_VS_UI_LOGIN(), Rect id_rt/pass_rt (130x23 cada)
LOGIN_REF_FIELDS = [
    ("ID", 59, 49, 130, 23),
    ("SENHA", 59, 89, 130, 23),
]

# "JANELAS DO JOGO" - MODELO POR RACA das 24 janelas de UI que o jogador
# arrasta em jogo (inventario, status/info, quickslot etc - ver
# darkeden_windowset.py pro formato real do arquivo UserSet\*.set onde
# isso e' salvo DE VERDADE, POR PERSONAGEM). Diferente de tudo mais nesta
# ferramenta, isso NAO vem/vai pro interface.inf - e' um MODELO proprio
# desta ferramenta (guardado em window_layout_templates.json, ao lado
# deste script), um conjunto por raca (nao por personagem), porque o
# tamanho de varias janelas (ex: Inventario) muda de raca pra' raca (arte
# .spk diferente por raca). Editar aqui NAO afeta nenhum personagem
# sozinho - use "Aplicar a um personagem..." pra' gravar o modelo da raca
# escolhida dentro de um UserSet\*.set especifico (so' reescreve os Rects,
# o resto do arquivo fica intacto).
WINDOWSET_KEY = "WINDOWSET_REF"
WINDOWSET_LABEL = "JANELAS DO JOGO (modelo por raca)"
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "window_layout_templates.json")

DISPLAY_KEYS = KEYS + [LOGIN_REF_LABEL, WINDOWSET_LABEL]


def load_window_templates():
    """{raca: {nome_da_janela: [x,y,w,h] ou None}} - None = "nunca
    definida nesse modelo" (mesma semantica do -1,-1,-1,-1 real do
    cliente). Comeca vazio (tudo None) se o JSON ainda nao existe - de
    proposito, pra' nao inventar posicao que ninguem confirmou."""
    races = list(truesprite.RACES) if truesprite else ["SLAYER", "VAMPIRE", "OUSTERS"]
    names = list(windowset.WINDOW_NAMES) if windowset else []
    templates = {race: {name: None for name in names} for race in races}
    if os.path.isfile(TEMPLATE_PATH):
        try:
            with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for race in races:
                for name in names:
                    v = saved.get(race, {}).get(name)
                    if v is not None:
                        templates[race][name] = list(v)
        except Exception:
            pass
    return templates


def save_window_templates(templates):
    with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)

# Status ao vivo/morto de cada CHAVE - explicado na barra de status quando
# escolhida, pra' quem for editar saber de antemao se vai ter efeito no
# jogo. Ver docstring do modulo pros detalhes/citacoes completas.
KEY_STATUS_NOTES = {
    "INFO": (
        "INFO: AO VIVO (CORRIGIDO - pesquisa anterior estava ERRADA) - e' a "
        "janela de status do personagem (STR/DEX/INT/HP/MP/Nome/Fama/Nivel), "
        "C_VS_UI_INFO::_Show2 (VS_UI_GameCommon.cpp) LE' pSkin->GetPoint() de "
        "verdade pro Desc_Box, Field_x1/x2, Name/Fame/Align e os 9 offsets de "
        "icone STR..PROTECTION. Editar e salvar aqui MUDA essas posicoes no "
        "jogo. So' os deslocamentos finais de cada NUMERO impresso (+4/+5px, "
        "gap*20/linha) sao literais fixos por cima. Mostra CHAR_BOX (moldura "
        "do retrato, posicao fixa) + DESC_BOX (posicao AO VIVO, segue o ponto "
        "'Desc_Box' se voce arrastar)."),
    "GAME_MENU": (
        "GAME_MENU: AO VIVO - o menu ESC do jogo (Option/Logout/Continue) le' "
        "pSkin->GetPoint() de verdade (VS_UI_Game.cpp, C_VS_UI_GAMEMENU). Editar "
        "e salvar aqui MUDA a posicao dos botoes no jogo de verdade. So' os 2 "
        "pontos da raca escolhida no combo 'Raca' aparecem agora (Slayer=0,1 / "
        "Vampire=2,3 / Ousters=4,5), pra' bater com o fundo mostrado."),
    "OPTION": (
        "OPTION: PARCIALMENTE AO VIVO - so' o dialogo de opcoes ABERTO DE DENTRO "
        "DO JOGO (Esc -> Option) le' esses pontos de verdade (C_VS_UI_OPTION, "
        "m_IsTitle==false). O dialogo de opcoes da TELA DE TITULO usa literais "
        "fixos e ignora esse mesmo interface.inf (igual TITLE). Editar aqui afeta "
        "so' o caminho dentro do jogo. O fundo muda conforme a raca escolhida."),
    "NEW_CHAR": (
        "NEW_CHAR: AO VIVO - C_VS_UI_NEWCHAR le' pSkin->GetPoint() pra' cada "
        "botao, em sequencia (VS_UI_Title.cpp). Editar e salvar aqui MUDA a "
        "posicao dos botoes na tela de criacao de personagem de verdade."),
    "TITLE": (
        "TITLE: DADO MORTO - C_VS_UI_TITLE busca o SkinManager::TITLE mas nunca "
        "chama GetPoint() pra' CONNECT/OPTION/CREDIT/EXIT; usa literais fixos "
        "(673,371 etc). Editar aqui NAO muda os botoes no jogo (ver nota no "
        "proprio interface.inf salvo)."),
}

HEADER_RE = re.compile(r'^\*([A-Z_]+)\s+(POINT_LIST|RECT_LIST)\s*$')
END_RE = re.compile(r'^\*END\s*$')
POINT_LINE_RE = re.compile(r'^(-?\d+)\s+(-?\d+)(\s*;.*)?$')
RECT_LINE_RE = re.compile(r'^(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)(\s*;.*)?$')


def find_7z():
    for cand in SEVENZIP_CANDIDATES:
        if os.path.isabs(cand) and os.path.exists(cand):
            return cand
        found = shutil.which(cand)
        if found:
            return found
    return None


def auto_find_interface_inf():
    """Acha automaticamente o interface.inf mais relevante em CLIENT_DIR,
    na ordem que faz mais sentido pro fluxo de trabalho desta ferramenta:
    1) a pasta de override que o proprio editor grava (Save) - se ela
       existe, e' o arquivo com as edicoes mais recentes, o "de trabalho";
    2) o interface.inf solto que ja' foi extraido do .rpk anteriormente;
    3) a pasta de extracao temporaria que o botao "Extrair do .rpk" cria.
    Retorna None se nao achar nenhum (o editor continua funcionando, so'
    abre vazio e pede pra' apertar Open)."""
    candidates = [
        os.path.join(CLIENT_DIR, "Data", "Info", "infodata_EN", "interface.inf"),
        os.path.join(CLIENT_DIR, "Data", "Info", "interface.inf"),
        os.path.join(CLIENT_DIR, "Data", "Info", "_interface_editor_extract", "interface.inf"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def strip_redundant_index(order_index, comment):
    """O .inf original as vezes ja' embute o proprio indice no comentario
    (ex: '0:SkillInfo... posicao'). Sem isso a UI mostrava duas vezes
    ('0: 0:SkillInfo...') - aqui tira o prefixo quando ele repete order_index."""
    c = (comment or "").strip()
    m = re.match(rf'^{order_index}\s*[:.\-]?\s*', c)
    if m:
        c = c[m.end():].strip()
    return c


class Entry:
    """Uma linha de dado (ponto ou retangulo) dentro de um bloco CHAVE/TIPO."""
    def __init__(self, line_idx, key, list_type, order_index, values, comment):
        self.line_idx = line_idx      # indice na lista bruta de linhas do arquivo
        self.key = key
        self.list_type = list_type    # 'POINT_LIST' ou 'RECT_LIST'
        self.order_index = order_index  # posicao (0,1,2..) dentro de CHAVE+TIPO
        self.values = values          # [x,y] ou [l,t,r,b]
        self.comment = comment        # texto apos ';' (sem o ';'), ou ''

    @property
    def label(self):
        c = strip_redundant_index(self.order_index, self.comment)
        return f"{self.order_index}: {c}" if c else f"{self.order_index}"


class InterfaceDocument:
    """
    Documento do interface.inf real deste jogo. Preserva o arquivo
    linha a linha - salvar so' reescreve os NUMEROS das linhas que
    mudaram, mantendo comentario/espacamento/resto do arquivo intactos.
    """
    def __init__(self):
        self.lines = []          # linhas cruas (sem \r\n), na ordem do arquivo
        self.entries = []        # lista de Entry, na ordem em que aparecem
        self.by_key_type = {}    # (key, list_type) -> [Entry, ...]

    def load(self, path):
        with open(path, 'rb') as f:
            raw = f.read()
        text = raw.decode('euc_kr', errors='replace')
        # normaliza quebras de linha, guarda sem terminador
        self.lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        self._parse()

    def _parse(self):
        self.entries = []
        self.by_key_type = {}
        current = None  # (key, list_type)
        counters = {}

        for i, raw_line in enumerate(self.lines):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(';'):
                continue

            if line.startswith('*'):
                m = HEADER_RE.match(line)
                if m:
                    current = (m.group(1), m.group(2))
                    counters.setdefault(current, 0)
                    continue
                if END_RE.match(line):
                    current = None
                    continue
                # "*algumacoisa" desconhecido - ignora (nao deveria acontecer)
                continue

            if current is None:
                continue

            key, list_type = current
            if list_type == 'POINT_LIST':
                m = POINT_LINE_RE.match(line)
                if not m:
                    continue
                x, y = int(m.group(1)), int(m.group(2))
                comment = (m.group(3) or '').lstrip()
                if comment.startswith(';'):
                    comment = comment[1:].strip()
                idx = counters[current]
                counters[current] += 1
                entry = Entry(i, key, list_type, idx, [x, y], comment)
            else:
                m = RECT_LINE_RE.match(line)
                if not m:
                    continue
                l, t, r, b = (int(m.group(1)), int(m.group(2)),
                              int(m.group(3)), int(m.group(4)))
                comment = (m.group(5) or '').lstrip()
                if comment.startswith(';'):
                    comment = comment[1:].strip()
                idx = counters[current]
                counters[current] += 1
                entry = Entry(i, key, list_type, idx, [l, t, r, b], comment)

            self.entries.append(entry)
            self.by_key_type.setdefault(current, []).append(entry)

    def get(self, key, list_type):
        return self.by_key_type.get((key, list_type), [])

    def apply_entry(self, entry):
        """Reescreve so' a linha desse Entry, preservando comentario/espacamento."""
        raw_line = self.lines[entry.line_idx]
        # separa em "dados" + "; comentario" (se tiver), preservando o texto
        # do comentario exatamente como estava
        semi = raw_line.find(';')
        comment_part = raw_line[semi:] if semi >= 0 else ''
        if entry.list_type == 'POINT_LIST':
            new_data = f"{entry.values[0]} {entry.values[1]}"
        else:
            new_data = f"{entry.values[0]} {entry.values[1]} {entry.values[2]} {entry.values[3]}"
        if comment_part:
            self.lines[entry.line_idx] = f"{new_data}\t\t\t{comment_part}"
        else:
            self.lines[entry.line_idx] = new_data

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = '\r\n'.join(self.lines)
        with open(path, 'wb') as f:
            f.write(text.encode('euc_kr', errors='replace'))


# ---------------------------------------------------------------------------
class InterfaceEditor:
    CANVAS_SIZES = ["800x600", "1024x768"]

    def __init__(self, root, ini_path=None, save_path=None):
        self.root = root
        self.root.title("DarkEden Interface Editor")
        self.root.geometry("1300x850")

        self.doc = InterfaceDocument()
        self.ini_path = ini_path
        self.save_path = save_path
        self.canvas_w, self.canvas_h = 800, 600
        self.canvas_scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.current_key = KEYS[0]
        self.current_list_type = 'POINT_LIST'
        self.selected = None      # Entry
        self.hovered = None       # Entry (mouse em cima, sem clicar)
        self.dragging = None      # (entry, mouse_x0, mouse_y0, orig_values)
        self._suppress_trace = False
        self._view_bounds = None  # (minx,miny,maxx,maxy) do ajuste automatico

        self._bg_sprite_cache = {}   # caminho .spk -> (w, h, rgb, mask) ja' decodificado
        self._bg_photo = None        # referencia viva do PhotoImage atual (Tk descarta sem isso)
        self._point_sprite_photos = []  # referencias vivas dos sprites reais de botao (NEW_CHAR/OPTION)
        self.race_var = tk.StringVar(value=truesprite.RACES[0] if truesprite else "SLAYER")

        # estado do modo WINDOWSET_KEY ("JANELAS DO JOGO (modelo por raca)")
        # - completamente separado do self.doc/interface.inf, ver bloco de
        # comentario de WINDOWSET_KEY mais acima no arquivo.
        self.templates = load_window_templates() if windowset else {}
        self.template_selected = None    # nome da janela selecionada (str)
        self.template_hovered = None
        self.template_dragging = None    # (nome, mouse_x0, mouse_y0, orig_x, orig_y)

        self._build_ui()

        if self.ini_path and os.path.exists(self.ini_path):
            self._load(self.ini_path)
        else:
            self._set_status("Abra um interface.inf (Open) ou rode com o caminho como argumento.")

    # -------------------------------------------------------------- UI build
    def _build_ui(self):
        tb = ttk.Frame(self.root)
        tb.pack(fill=tk.X, padx=4, pady=4)

        ttk.Button(tb, text="Open...", command=self._open_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Extrair do .rpk...", command=self._extract_from_rpk).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Reload", command=self._reload).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Save (override _EN)", command=self._save).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Save As...", command=self._save_as).pack(side=tk.LEFT, padx=2)

        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y)

        ttk.Label(tb, text="Tela (chave):").pack(side=tk.LEFT)
        self.key_var = tk.StringVar(value=KEYS[0])
        key_combo = ttk.Combobox(tb, textvariable=self.key_var, values=DISPLAY_KEYS,
                                  width=26, state="readonly")
        key_combo.pack(side=tk.LEFT, padx=2)
        key_combo.bind("<<ComboboxSelected>>", lambda e: self._on_key_change())

        ttk.Label(tb, text="Lista:").pack(side=tk.LEFT, padx=(8, 0))
        self.type_var = tk.StringVar(value='POINT_LIST')
        type_combo = ttk.Combobox(tb, textvariable=self.type_var, values=LIST_TYPES,
                                   width=12, state="readonly")
        type_combo.pack(side=tk.LEFT, padx=2)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self._on_key_change())

        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y)

        ttk.Label(tb, text="Canvas:").pack(side=tk.LEFT)
        self.canvas_size_var = tk.StringVar(value="800x600")
        cb = ttk.Combobox(tb, textvariable=self.canvas_size_var, values=self.CANVAS_SIZES,
                          width=10, state="readonly")
        cb.pack(side=tk.LEFT, padx=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self._on_canvas_size_change())

        ttk.Label(tb, text="Raca (GAME_MENU/OPTION):").pack(side=tk.LEFT, padx=(8, 0))
        race_combo = ttk.Combobox(tb, textvariable=self.race_var,
                                   values=list(truesprite.RACES) if truesprite else ["SLAYER"],
                                   width=10, state="readonly")
        race_combo.pack(side=tk.LEFT, padx=2)
        race_combo.bind("<<ComboboxSelected>>", lambda e: self._on_race_change())

        self.autofit_var = tk.BooleanVar(value=True)
        autofit_chk = ttk.Checkbutton(tb, text="Ajuste automatico aos dados",
                                       variable=self.autofit_var,
                                       command=self._redraw)
        autofit_chk.pack(side=tk.LEFT, padx=8)

        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y)
        ttk.Button(tb, text="Salvar modelo de janelas",
                   command=self._save_window_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Aplicar a um personagem...",
                   command=self._apply_template_to_character).pack(side=tk.LEFT, padx=2)

        sb = ttk.Frame(self.root)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar(value="Pronto.")
        ttk.Label(sb, textvariable=self.status_var, anchor=tk.W,
                  relief=tk.SUNKEN).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.coord_var = tk.StringVar(value="X=0 Y=0")
        ttk.Label(sb, textvariable=self.coord_var, anchor=tk.E,
                  relief=tk.SUNKEN, width=20).pack(side=tk.RIGHT)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = ttk.Frame(main)
        ttk.Label(left, text="Entradas (indice: comentario):").pack(anchor=tk.W, pady=(0, 2))
        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.entry_listbox = tk.Listbox(list_frame, exportselection=False, width=36)
        sb_left = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.entry_listbox.yview)
        self.entry_listbox.config(yscrollcommand=sb_left.set)
        self.entry_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_left.pack(side=tk.RIGHT, fill=tk.Y)
        self.entry_listbox.bind("<<ListboxSelect>>", lambda e: self._on_listbox_select())
        main.add(left, weight=1)

        center = ttk.Frame(main)
        self.canvas = tk.Canvas(center, bg="#202028", highlightthickness=1,
                                highlightbackground="#666")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Configure>", lambda e: self._redraw())
        main.add(center, weight=4)

        right = ttk.Frame(main)
        ttk.Label(right, text="Propriedades:").pack(anchor=tk.W)
        prop = ttk.LabelFrame(right, text="Entrada selecionada")
        prop.pack(fill=tk.X, padx=2, pady=2)

        self.prop_name_var = tk.StringVar(value="-")
        ttk.Label(prop, textvariable=self.prop_name_var,
                  font=("Arial", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)

        ttk.Label(prop, text="Comentario:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.prop_comment_var = tk.StringVar(value="-")
        ttk.Label(prop, textvariable=self.prop_comment_var, wraplength=180).grid(
            row=1, column=1, sticky=tk.W, padx=2, pady=2)

        self.value_labels = ["X", "Y", "R", "B"]
        self.value_vars = [tk.StringVar(value="0") for _ in range(4)]
        self.value_spins = []
        for i in range(4):
            lbl = ttk.Label(prop, text=f"{self.value_labels[i]}:")
            lbl.grid(row=2 + i, column=0, sticky=tk.W, padx=2, pady=2)
            sp = ttk.Spinbox(prop, from_=-4096, to=4096, textvariable=self.value_vars[i], width=10)
            sp.grid(row=2 + i, column=1, sticky=tk.W, padx=2, pady=2)
            self.value_vars[i].trace_add("write", lambda *a, ix=i: self._on_prop_change())
            self.value_spins.append((lbl, sp))

        self.prop_extra_var = tk.StringVar(value="")
        ttk.Label(prop, textvariable=self.prop_extra_var, foreground="#666",
                  wraplength=200, justify=tk.LEFT).grid(
            row=6, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)

        ttk.Label(prop, text="(POINT_LIST so' usa X/Y;\nRECT_LIST usa os 4)",
                  foreground="#666").grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)

        main.add(right, weight=1)

    # -------------------------------------------------------------- File I/O
    def _open_dialog(self):
        p = filedialog.askopenfilename(
            title="Abrir interface.inf",
            filetypes=[("interface.inf", "interface.inf;ChinaInterface.inf"), ("Todos", "*.*")])
        if p:
            self.ini_path = p
            self._load(p)

    def _extract_from_rpk(self):
        sevenzip = find_7z()
        if not sevenzip:
            messagebox.showerror("7z nao encontrado",
                "Nao achei o 7z.exe (procurado em C:\\Program Files\\7-Zip\\7z.exe e no PATH).\n"
                "Instale o 7-Zip ou use 'Open...' com um interface.inf ja' extraido.")
            return

        rpk = filedialog.askopenfilename(
            title="Selecione o infodata.rpk",
            initialdir=os.path.join(CLIENT_DIR, "Data", "Info"),
            filetypes=[("infodata.rpk", "infodata.rpk"), ("Todos", "*.*")])
        if not rpk:
            return

        out_dir = os.path.join(os.path.dirname(rpk), "_interface_editor_extract")
        os.makedirs(out_dir, exist_ok=True)
        try:
            subprocess.run(
                [sevenzip, "e", f"-p{RPK_PASSWORD}", f"-o{out_dir}", rpk, "-y"],
                check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Erro extraindo", e.stderr.decode(errors='replace'))
            return

        candidate = os.path.join(out_dir, "interface.inf")
        if not os.path.exists(candidate):
            messagebox.showerror("Nao achei", f"interface.inf nao apareceu em {out_dir}")
            return

        self.ini_path = candidate
        self._load(candidate)
        self._set_status(f"Extraido de {rpk} -> {candidate}")

    def _load(self, path):
        try:
            self.doc.load(path)
        except Exception as e:
            messagebox.showerror("Erro ao carregar", str(e))
            return
        self.root.title(f"DarkEden Interface Editor - {os.path.basename(path)}")
        # abre direto na tela TITLE (com o fundo real) - e' a tela que
        # estamos trabalhando nesta sessao, poupa ter que trocar no combo
        # toda vez que abre o editor.
        self.key_var.set("TITLE")
        self._on_key_change()

    def _reload(self):
        if self.ini_path and os.path.exists(self.ini_path):
            self._load(self.ini_path)
            self._set_status("Recarregado.")

    def _default_save_path(self):
        # Salva na pasta de override que o CRarFile::Open() modificado ja'
        # sabe procurar (ver client-master/VS_UI/RarFile.cpp): mesmo nome
        # do .rpk original, sem extensao, + "_EN".
        return os.path.join(CLIENT_DIR, "Data", "Info", "infodata_EN", "interface.inf")

    def _save(self):
        path = self.save_path or self._default_save_path()
        self._do_save(path)

    def _save_as(self):
        p = filedialog.asksaveasfilename(
            defaultextension=".inf", initialfile="interface.inf",
            filetypes=[("interface.inf", "*.inf")])
        if p:
            self.save_path = p
            self._do_save(p)

    def _do_save(self, path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if os.path.exists(path):
                bak = path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                shutil.copy(path, bak)
            self.doc.save(path)
            self._set_status(f"Salvo em {path}")
            messagebox.showinfo("Salvo",
                f"Salvo em:\n{path}\n\n"
                "Isso vai pra' pasta de override que o cliente ja' checa antes "
                "do .rpk (nao precisa recompilar nem remontar RAR) - so' fechar "
                "e abrir o jogo de novo pra' ver o efeito.")
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))

    # ------------------------------------------------------ Section / parse
    def _on_canvas_size_change(self):
        w, h = self.canvas_size_var.get().split('x')
        self.canvas_w, self.canvas_h = int(w), int(h)
        self._redraw()

    def _on_race_change(self):
        # importa pra' GAME_MENU (filtra quais pontos aparecem), GAME_MENU/
        # OPTION/INFO (troca qual .spk de fundo por raca e' mostrado) e
        # WINDOWSET_KEY (troca qual modelo de raca esta' sendo editado) -
        # inofensivo pras' outras chaves, so' redesenha igual.
        self.selected = None
        self.template_selected = None
        self._populate_listbox()
        self._redraw()
        self._update_property_panel(None)

    def _on_key_change(self):
        raw = self.key_var.get()
        if raw == LOGIN_REF_LABEL:
            self.current_key = LOGIN_REF_KEY
        elif raw == WINDOWSET_LABEL:
            self.current_key = WINDOWSET_KEY
        else:
            self.current_key = raw
        self.current_list_type = self.type_var.get()
        self.selected = None
        self.template_selected = None

        if self.current_key == WINDOWSET_KEY:
            self.autofit_var.set(False)  # sempre tela de referencia 800x600 fixa
            self._populate_listbox()
            self._redraw()
            self._update_property_panel(None)
            n = len(windowset.WINDOW_NAMES) if windowset else 0
            self._set_status(
                f"JANELAS DO JOGO - modelo da raca {self.race_var.get()} ({n} janelas). "
                "Isso NAO e' o interface.inf - e' um modelo proprio desta ferramenta "
                "(window_layout_templates.json), guardado POR RACA. Use 'Aplicar a um "
                "personagem...' pra' gravar num UserSet\\*.set de verdade.")
            return

        if self._background_layers():
            # o fundo real so' faz sentido na visao "tela cheia de
            # referencia" (dimensoes exatas do sprite) - o modo "ajuste
            # automatico" redimensiona o quadro pra' caber so' os pontos,
            # o que distorceria a imagem de fundo.
            self.autofit_var.set(False)
        self._populate_listbox()
        self._redraw()
        self._update_property_panel(None)
        if self.current_key == LOGIN_REF_KEY:
            self._set_status(
                "LOGIN (popup de Connect): so' visualizacao - os campos ID/Senha sao "
                "posicoes fixas no C++ (VS_UI_Title.cpp), nao existem no interface.inf, "
                "entao nao da' pra' editar/salvar eles aqui.")
        elif self.current_key in KEY_STATUS_NOTES:
            entries = self._visible_entries()
            self._set_status(
                f"{len(entries)} entrada(s) mostrada(s). " + KEY_STATUS_NOTES[self.current_key])
        else:
            entries = self._visible_entries()
            self._set_status(f"{self.current_key} {self.current_list_type}: {len(entries)} entrada(s).")

    # -------------------------------------------------------- Fundo visual
    def _info_race_starts(self):
        """{"SLAYER":1,"VAMPIRE":13,"OUSTERS":29} - os indices onde cada
        bloco de raca comeca na *INFO POINT_LIST, tirados AO VIVO do
        proprio *INFO RECT_LIST (linha '1 13 29 0' do interface.inf) em vez
        de fixos aqui, pra' continuar certo mesmo se o arquivo mudar.
        None se o documento carregado nao tem esse RECT_LIST (arquivo
        incompleto/diferente)."""
        rects = self.doc.get("INFO", "RECT_LIST")
        if not rects:
            return None
        l, t, r, _b = rects[0].values
        return {"SLAYER": l, "VAMPIRE": t, "OUSTERS": r}

    def _info_race_range(self, race):
        """(start, end_inclusive_ou_None) - intervalo de order_index da
        *INFO POINT_LIST que pertence a' raca dada (end None = vai ate' o
        ultimo ponto da lista, pra' raca do fim). None se nao da' pra'
        calcular (sem RECT_LIST)."""
        starts = self._info_race_starts()
        if not starts:
            return None
        ordered = sorted(starts.values())
        start = starts[race]
        idx = ordered.index(start)
        end = ordered[idx + 1] - 1 if idx + 1 < len(ordered) else None
        return start, end

    def _background_layers(self):
        """Lista de (filename, sprite_index, x, y) - as camadas do fundo
        real da tela atual (ver darkeden_truesprite.get_background_layers
        pra' a fonte de cada uma), ou [] se nao ha' fundo confirmado pra'
        essa combinacao de CHAVE/widescreen/raca."""
        if truesprite is None or Image is None:
            return []
        widescreen = (self.canvas_size_var.get() == "1024x768")
        race = self.race_var.get()
        layers = list(truesprite.get_background_layers(self.current_key, widescreen, race))
        if self.current_key == "INFO":
            # DESC_BOX e os icones de nome/status sao AO VIVO (vem dos
            # proprios pontos do interface.inf: Desc_Box, Field_x1, e os
            # offsets STR..PROTECTION/Name/Fame/Align) - por isso essas
            # camadas sao montadas aqui, com acesso ao self.doc, em vez de
            # estaticas em darkeden_truesprite (ver INFO_ICON_LAYOUT la'
            # pra' a formula/citacoes completas).
            start = self._info_race_starts()
            fname = {"SLAYER": "InfoSlayer.spk", "VAMPIRE": "InfoVampire.spk",
                      "OUSTERS": "InfoOusters.spk"}.get(race)
            if start and fname:
                base = start[race]
                points = {e.order_index: e for e in self.doc.get("INFO", "POINT_LIST")}
                desc_entry = points.get(base)
                field1_entry = points.get(base + 1)
                if desc_entry is not None:
                    layers.append((fname, truesprite.INFO_DESC_BOX_SPRITE_INDEX,
                                    desc_entry.values[0], desc_entry.values[1]))
                char_box_x, char_box_y = truesprite.INFO_CHAR_BOX_POS.get(race, (20, 22))
                layout = truesprite.INFO_ICON_LAYOUT.get(race, {})
                if field1_entry is not None:
                    for offset, sprite_idx, gap_idx in layout.get("name_group", []):
                        pt = points.get(base + offset)
                        if pt is None:
                            continue
                        x = field1_entry.values[0] + pt.values[0]
                        y = char_box_y + pt.values[1] + truesprite.INFO_FIELD_GAP * gap_idx
                        layers.append((fname, sprite_idx, x, y))
                if desc_entry is not None:
                    for offset, sprite_idx, gap_idx in layout.get("stat_group", []):
                        pt = points.get(base + offset)
                        if pt is None:
                            continue
                        x = char_box_x + pt.values[0]
                        y = desc_entry.values[1] + pt.values[1] + truesprite.INFO_FIELD_GAP * gap_idx
                        layers.append((fname, sprite_idx, x, y))
        return layers

    def _background_description(self):
        """Texto curto pro titulo do canvas com os nomes dos arquivos de
        fundo em uso (ou '' se nenhum)."""
        layers = self._background_layers()
        if not layers:
            return ""
        return " + ".join(os.path.basename(fname) for fname, *_ in layers)

    def _decode_layer_cached(self, fname, sprite_index=0):
        """Decodifica (com cache) um sprite de um .spk de fundo. Nunca
        levanta excecao - um fundo faltando so' significa que essa camada
        fica de fora, o resto do editor continua funcionando normalmente."""
        path = truesprite.find_ui_spk(CLIENT_DIR, fname)
        if path is None:
            return None
        cache_key = (path, sprite_index)
        cached = self._bg_sprite_cache.get(cache_key)
        if cached is None:
            try:
                pack = truesprite.TrueSpritePack(path)
                cached = pack.decode(sprite_index)
            except Exception:
                return None
            self._bg_sprite_cache[cache_key] = cached
        w, h, rgb, mask = cached
        if not w or not h:
            return None
        try:
            rgb_img = Image.frombytes("RGB", (w, h), rgb)
            alpha_img = Image.frombytes("L", (w, h), mask)
            rgba_img = rgb_img.convert("RGBA")
            rgba_img.putalpha(alpha_img)
            return rgba_img
        except Exception:
            return None

    def _load_background_image(self):
        """Compoe todas as camadas de fundo da tela atual (ver
        _background_layers) num unico PIL.Image RGBA, primeira camada
        embaixo - ou None se nao houver nenhuma camada disponivel."""
        layers = self._background_layers()
        if not layers:
            return None
        images = []
        max_w = max_h = 0
        for fname, sprite_index, x, y in layers:
            img = self._decode_layer_cached(fname, sprite_index)
            if img is None:
                continue
            images.append((img, x, y))
            max_w = max(max_w, x + img.width)
            max_h = max(max_h, y + img.height)
        if not images:
            return None
        min_size = truesprite.get_window_min_size(self.current_key, self.race_var.get())
        if min_size:
            max_w = max(max_w, min_size[0])
            max_h = max(max_h, min_size[1])
        canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
        for img, x, y in images:
            canvas.alpha_composite(img, (x, y))
        return canvas

    def _populate_listbox(self):
        self.entry_listbox.delete(0, tk.END)
        if self.current_key == WINDOWSET_KEY:
            race_templates = self.templates.get(self.race_var.get(), {})
            for name in windowset.WINDOW_NAMES:
                v = race_templates.get(name)
                label = f"{name} ({v[0]},{v[1]},{v[2]}x{v[3]})" if v else f"{name} (nunca definida)"
                self.entry_listbox.insert(tk.END, label)
            return
        if self.current_key == LOGIN_REF_KEY:
            for name, fx, fy, fw, fh in LOGIN_REF_FIELDS:
                self.entry_listbox.insert(
                    tk.END, f"{name} (fixo no C++: {fx},{fy} {fw}x{fh}) - so' referencia")
            return
        for e in self._visible_entries():
            self.entry_listbox.insert(tk.END, e.label)

    def _visible_entries(self):
        """Entradas da CHAVE+TIPO atual que fazem sentido mostrar AGORA.
        Pra' GAME_MENU especificamente: o interface.inf guarda os 6 pontos
        (2 por raca: Slayer/Vampire/Ousters) juntos na mesma lista, mas so'
        os 2 da raca escolhida no combo "Raca" tem a ver com o fundo que
        esta' sendo mostrado - confirmado em VS_UI_Game.cpp (C_VS_UI_GAMEMENU):
        cada raca so' le' o par de pontos dela (GetPoint(0)/(1) Slayer,
        (2)/(3) Vampire, (4)/(5) Ousters). Mostrar os 6 juntos so' confundiria
        (pontos de OUTRA raca ficariam desalinhados em cima do fundo errado).
        Pra' INFO: ponto 0 e' compartilhado entre racas (SkillInfo DomainBar);
        o resto e' um bloco por raca de tamanho VARIAVEL (12 pontos Slayer,
        16 Vampire, 19 Ousters) - o intervalo de cada raca vem do proprio
        *INFO RECT_LIST (ver _info_race_range), nao esta' fixo aqui.
        Pras' outras CHAVEs, devolve a lista inteira sem filtrar."""
        entries = self.doc.get(self.current_key, self.current_list_type)
        if self.current_key == "GAME_MENU" and self.current_list_type == "POINT_LIST":
            race_offset = {"SLAYER": 0, "VAMPIRE": 2, "OUSTERS": 4}.get(self.race_var.get(), 0)
            entries = [e for e in entries if e.order_index in (race_offset, race_offset + 1)]
        elif self.current_key == "INFO" and self.current_list_type == "POINT_LIST":
            # ponto 0 (SkillInfo DomainBar) e' compartilhado entre as 3
            # racas; o resto do bloco de cada raca vem do intervalo
            # calculado a partir do *INFO RECT_LIST (ver _info_race_range).
            rng = self._info_race_range(self.race_var.get())
            if rng:
                start, end = rng
                entries = [e for e in entries
                           if e.order_index == 0
                           or (e.order_index >= start and (end is None or e.order_index <= end))]
        return entries

    # ------------------------------------------------------ Canvas drawing
    @staticmethod
    def _clean_comment(e):
        return strip_redundant_index(e.order_index, e.comment)

    def _compute_bounds(self):
        """Bounding box (minx,miny,maxx,maxy) de todas as entradas da
        tela/lista atual, com margem - usado no modo 'ajuste automatico'."""
        entries = self._visible_entries()
        if not entries:
            return (0, 0, self.canvas_w, self.canvas_h)
        xs, ys = [], []
        for e in entries:
            if e.list_type == 'POINT_LIST':
                xs.append(e.values[0])
                ys.append(e.values[1])
            else:
                xs.append(e.values[0]); xs.append(e.values[2])
                ys.append(e.values[1]); ys.append(e.values[3])
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        # margem: 15% do intervalo, com minimo de 40px (pra' nao colapsar
        # quando todos os pontos tem X ou Y identico)
        mx = max(40, (maxx - minx) * 0.15)
        my = max(40, (maxy - miny) * 0.15)
        return (minx - mx, miny - my, maxx + mx, maxy + my)

    def _redraw(self):
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        if self.current_key == WINDOWSET_KEY:
            self._redraw_windowset(cw, ch)
            return

        self._point_sprite_photos = []
        bg_img = None
        if self.autofit_var.get():
            bx0, by0, bx1, by1 = self._compute_bounds()
            rw, rh = bx1 - bx0, by1 - by0
            self._view_bounds = (bx0, by0)
            scale = min(cw / rw, ch / rh) * 0.95
            self.canvas_scale = scale
            sw, sh = rw * scale, rh * scale
            self.offset_x = (cw - sw) / 2 - bx0 * scale
            self.offset_y = (ch - sh) / 2 - by0 * scale
            frame_x0, frame_y0 = self.offset_x + bx0 * scale, self.offset_y + by0 * scale
            title = f"ajuste automatico ({int(rw)}x{int(rh)})  -  {self.current_key} {self.current_list_type}"
        else:
            bg_img = self._load_background_image()
            if bg_img is not None:
                # usa as dimensoes REAIS do sprite de fundo (podem nao bater
                # com o combobox de canvas - ex: o popup de LOGIN e' 222x179,
                # bem menor que 800x600) em vez do canvas_w/canvas_h.
                rw, rh = bg_img.size
            else:
                rw, rh = self.canvas_w, self.canvas_h
            scale = min(cw / rw, ch / rh) * 0.95
            self.canvas_scale = scale
            sw, sh = rw * scale, rh * scale
            self.offset_x = (cw - sw) / 2
            self.offset_y = (ch - sh) / 2
            frame_x0, frame_y0 = self.offset_x, self.offset_y
            title = f"{rw}x{rh} (tela cheia de referencia)  -  {self.current_key} {self.current_list_type}"

        if bg_img is not None:
            resized = bg_img.resize((max(1, int(sw)), max(1, int(sh))), Image.LANCZOS)
            self._bg_photo = ImageTk.PhotoImage(resized)
            self.canvas.create_image(frame_x0, frame_y0, image=self._bg_photo, anchor=tk.NW)
            self.canvas.create_rectangle(
                frame_x0, frame_y0, frame_x0 + sw, frame_y0 + sh,
                fill="", outline="#888", width=1)
            title += "  -  fundo real: " + self._background_description()
        else:
            self._bg_photo = None
            self.canvas.create_rectangle(
                frame_x0, frame_y0, frame_x0 + sw, frame_y0 + sh,
                fill="#303048", outline="#888", width=1)

        self.canvas.create_text(
            frame_x0 + sw / 2, frame_y0 - 8,
            text=title, fill="#aaa", anchor=tk.S, font=("Arial", 9))

        if bg_img is None:
            # a grade so' ajuda a ler coordenadas sobre fundo liso - sobre
            # o screenshot real ela so' atrapalharia a leitura da imagem.
            grid_x0 = int(self._view_bounds[0] if self.autofit_var.get() else 0)
            grid_y0 = int(self._view_bounds[1] if self.autofit_var.get() else 0)
            step = 50 if self.autofit_var.get() else 100
            gx = grid_x0 - (grid_x0 % step)
            while gx <= grid_x0 + rw:
                sx = self.offset_x + gx * scale
                self.canvas.create_line(sx, frame_y0, sx, frame_y0 + sh, fill="#383858")
                gx += step
            gy = grid_y0 - (grid_y0 % step)
            while gy <= grid_y0 + rh:
                sy = self.offset_y + gy * scale
                self.canvas.create_line(frame_x0, sy, frame_x0 + sw, sy, fill="#383858")
                gy += step

        # desenha os NAO-selecionados/NAO-hover primeiro (pra' ficarem
        # atras), o selecionado/hover por ultimo (fica por cima, visivel)
        entries = self._visible_entries()
        for e in entries:
            if e is not self.selected and e is not self.hovered:
                self._draw_entry(e)
        for e in entries:
            if e is self.hovered and e is not self.selected:
                self._draw_entry(e)
        if self.selected in entries:
            self._draw_entry(self.selected)

        if self.current_key == LOGIN_REF_KEY:
            self._draw_login_ref_fields(frame_x0, frame_y0, scale)

    def _draw_login_ref_fields(self, frame_x0, frame_y0, scale):
        """Desenha (so' leitura, sem drag/selecao) os retangulos dos campos
        ID/Senha do popup de login, em cima do fundo real - ver comentario
        de LOGIN_REF_KEY sobre por que isso nao vem do interface.inf."""
        for name, fx, fy, fw, fh in LOGIN_REF_FIELDS:
            sx0 = frame_x0 + fx * scale
            sy0 = frame_y0 + fy * scale
            sx1 = frame_x0 + (fx + fw) * scale
            sy1 = frame_y0 + (fy + fh) * scale
            self.canvas.create_rectangle(sx0, sy0, sx1, sy1, outline="#ffd060",
                                          width=2, dash=(4, 2))
            self.canvas.create_text(sx0, sy0 - 8, text=f"{name} (fixo, so' ref.)",
                                     fill="#ffd060", anchor=tk.W, font=("Arial", 8, "bold"))

    # -------------------------------------------------- Modo WINDOWSET_KEY
    # ("JANELAS DO JOGO (modelo por raca)") - completamente separado do
    # self.doc/interface.inf. Ver comentario de WINDOWSET_KEY mais acima.
    REFERENCE_W, REFERENCE_H = 800, 600  # g_GameRect - fixo neste cliente

    def _redraw_windowset(self, cw, ch):
        race = self.race_var.get()
        race_templates = self.templates.get(race, {})
        entries = [(name, v) for name, v in race_templates.items() if v is not None]

        xs = [0, self.REFERENCE_W]
        ys = [0, self.REFERENCE_H]
        for _name, v in entries:
            xs.append(v[0]); xs.append(v[0] + v[2])
            ys.append(v[1]); ys.append(v[1] + v[3])
        margin = 40
        bx0, by0 = min(xs) - margin, min(ys) - margin
        bx1, by1 = max(xs) + margin, max(ys) + margin
        rw, rh = bx1 - bx0, by1 - by0
        scale = min(cw / rw, ch / rh) * 0.95
        self.canvas_scale = scale
        sw, sh = rw * scale, rh * scale
        self.offset_x = (cw - sw) / 2 - bx0 * scale
        self.offset_y = (ch - sh) / 2 - by0 * scale

        ref_x0 = self.offset_x
        ref_y0 = self.offset_y
        self.canvas.create_rectangle(
            ref_x0, ref_y0, ref_x0 + self.REFERENCE_W * scale, ref_y0 + self.REFERENCE_H * scale,
            fill="#303048", outline="#888", width=1)
        self.canvas.create_text(
            ref_x0 + self.REFERENCE_W * scale / 2, ref_y0 - 8,
            text=f"tela de referencia {self.REFERENCE_W}x{self.REFERENCE_H} - modelo raca {race}",
            fill="#aaa", anchor=tk.S, font=("Arial", 9))

        for name, v in entries:
            if name != self.template_selected and name != self.template_hovered:
                self._draw_template_entry(name, v)
        for name, v in entries:
            if name == self.template_hovered and name != self.template_selected:
                self._draw_template_entry(name, v)
        if self.template_selected and race_templates.get(self.template_selected):
            self._draw_template_entry(self.template_selected, race_templates[self.template_selected])

    def _draw_template_entry(self, name, v):
        scale = self.canvas_scale
        is_sel = (name == self.template_selected)
        is_hover = (name == self.template_hovered)
        if is_sel:
            color, width = "#ffd060", 2.5
        elif is_hover:
            color, width = "#a0e080", 2
        else:
            color, width = "#5c8c50", 1
        x, y, w, h = v
        sx0 = self.offset_x + x * scale
        sy0 = self.offset_y + y * scale
        sx1 = self.offset_x + (x + w) * scale
        sy1 = self.offset_y + (y + h) * scale
        self.canvas.create_rectangle(sx0, sy0, sx1, sy1, fill="", outline=color,
                                      width=width, tags=f"w{name}")
        if is_sel or is_hover:
            self.canvas.create_text(sx0, sy0 - 8, text=name, fill="#fff",
                                     anchor=tk.W, font=("Arial", 8, "bold"), tags=f"w{name}")

    def _find_template_at(self, x, y, radius=6):
        items = self.canvas.find_overlapping(x - radius, y - radius, x + radius, y + radius)
        for item in reversed(items):
            for tag in self.canvas.gettags(item):
                if tag.startswith("w") and tag[1:] in windowset.WINDOW_NAMES:
                    return tag[1:]
        return None

    def _select_template(self, name):
        self.template_selected = name
        v = self.templates.get(self.race_var.get(), {}).get(name)
        self._update_property_panel_windowset(name, v)
        self._redraw()
        try:
            idx = windowset.WINDOW_NAMES.index(name)
            self.entry_listbox.selection_clear(0, tk.END)
            self.entry_listbox.selection_set(idx)
            self.entry_listbox.see(idx)
        except ValueError:
            pass

    def _update_property_panel_windowset(self, name, v):
        self._suppress_trace = True
        self.prop_name_var.set(name)
        if v is None:
            v = [0, 0, 100, 100]
            self.prop_extra_var.set("(nunca definida neste modelo - editar da' uma posicao inicial)")
        else:
            self.prop_extra_var.set("")
        self.value_vars[0].set(str(v[0]))
        self.value_vars[1].set(str(v[1]))
        self.value_vars[2].set(str(v[2]))
        self.value_vars[3].set(str(v[3]))
        self.value_spins[0][0].config(text="X:")
        self.value_spins[1][0].config(text="Y:")
        self.value_spins[2][0].config(text="W:")
        self.value_spins[3][0].config(text="H:")
        for lbl, sp in self.value_spins:
            sp.state(["!disabled"])
        self.root.after_idle(lambda: setattr(self, '_suppress_trace', False))

    def _on_prop_change_windowset(self):
        if self._suppress_trace or self.template_selected is None:
            return
        try:
            x = int(self.value_vars[0].get())
            y = int(self.value_vars[1].get())
            w = int(self.value_vars[2].get())
            h = int(self.value_vars[3].get())
        except ValueError:
            return
        self.templates[self.race_var.get()][self.template_selected] = [x, y, w, h]
        self._populate_listbox()
        self._redraw()

    def _save_window_template(self):
        if windowset is None:
            messagebox.showerror("Erro", "darkeden_windowset.py nao encontrado.")
            return
        save_window_templates(self.templates)
        self._set_status(f"Modelos de janela salvos em {TEMPLATE_PATH}")
        messagebox.showinfo("Salvo", f"Modelos de todas as racas salvos em:\n{TEMPLATE_PATH}\n\n"
                             "Isso e' so' o modelo desta ferramenta - use 'Aplicar a um "
                             "personagem...' pra' realmente gravar num UserSet\\*.set do jogo.")

    def _apply_template_to_character(self):
        if windowset is None:
            messagebox.showerror("Erro", "darkeden_windowset.py nao encontrado.")
            return
        race = self.race_var.get()
        race_templates = {k: v for k, v in self.templates.get(race, {}).items() if v is not None}
        if not race_templates:
            messagebox.showwarning("Nada pra' aplicar",
                f"O modelo da raca {race} nao tem nenhuma janela definida ainda - "
                "arraste alguma no modo 'JANELAS DO JOGO' antes de aplicar.")
            return
        files = windowset.find_userset_files(CLIENT_DIR)
        if not files:
            messagebox.showerror("Nenhum personagem encontrado",
                f"Nao achei nenhum UserSet\\*.set em {CLIENT_DIR}.")
            return
        labels = []
        label_to_path = {}
        for path in files:
            name, dim, world = windowset.decode_char_name(path)
            label = f"{name}  (dim={dim} mundo={world})"
            labels.append(label)
            label_to_path[label] = path

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Aplicar modelo '{race}' a um personagem")
        dialog.geometry("420x120")
        ttk.Label(dialog, text="Personagem (UserSet\\*.set):").pack(anchor=tk.W, padx=8, pady=(8, 2))
        chosen = tk.StringVar(value=labels[0])
        combo = ttk.Combobox(dialog, textvariable=chosen, values=labels, state="readonly", width=50)
        combo.pack(fill=tk.X, padx=8)

        def do_apply():
            path = label_to_path[chosen.get()]
            try:
                us = windowset.UserSetFile()
                us.load(path)
                for name, v in race_templates.items():
                    us.set_rect(name, v[0], v[1], v[2], v[3])
                us.save(path)
            except Exception as ex:
                messagebox.showerror("Erro ao aplicar", str(ex))
                return
            dialog.destroy()
            self._set_status(f"Modelo '{race}' ({len(race_templates)} janela(s)) aplicado em {path} "
                              "(backup do arquivo anterior criado ao lado).")
            messagebox.showinfo("Aplicado",
                f"Gravado em:\n{path}\n\n{len(race_templates)} janela(s) do modelo '{race}' "
                "escritas - o resto do arquivo (hotkeys, filtros etc) ficou intacto. Efeito: "
                "proximo login desse personagem/mundo, as janelas abrem nessa posicao.")

        btns = ttk.Frame(dialog)
        btns.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(btns, text="Aplicar", command=do_apply).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btns, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=2)

    def _draw_point_sprite(self, order_index, sx, sy, scale):
        """Desenha o sprite REAL do botao/campo nesse ponto (NEW_CHAR/
        OPTION - ver darkeden_truesprite.get_point_sprite), na posicao AO
        VIVO do ponto (acompanha se voce arrastar). Nao faz nada se essa
        CHAVE/indice nao tem sprite mapeado, ou se faltar Pillow/arquivo."""
        if truesprite is None or Image is None:
            return
        mapping = truesprite.get_point_sprite(self.current_key, order_index, self.race_var.get())
        if mapping is None:
            return
        fname, sprite_index = mapping
        img = self._decode_layer_cached(fname, sprite_index)
        if img is None:
            return
        w = max(1, round(img.width * scale))
        h = max(1, round(img.height * scale))
        try:
            resized = img.resize((w, h), Image.LANCZOS)
        except Exception:
            return
        photo = ImageTk.PhotoImage(resized)
        self._point_sprite_photos.append(photo)  # segura a referencia (Tk descarta sem isso)
        self.canvas.create_image(sx, sy, image=photo, anchor=tk.NW, tags=f"e{order_index}")

    def _draw_entry(self, e):
        scale = self.canvas_scale
        is_sel = (e is self.selected)
        is_hover = (e is self.hovered)
        show_label = is_sel or is_hover
        if is_sel:
            color, outline, size_mult = "#ffd060", "#fff", 1.3
        elif is_hover:
            color, outline, size_mult = "#a0e080", "#fff", 1.15
        else:
            color, outline, size_mult = "#5c8c50", "#8ab080", 1.0

        label = self._clean_comment(e) or str(e.order_index)

        if e.list_type == 'POINT_LIST':
            x, y = e.values
            size = 10 * size_mult
            sx = self.offset_x + x * scale
            sy = self.offset_y + y * scale
            self._draw_point_sprite(e.order_index, sx, sy, scale)
            self.canvas.create_oval(sx - size/2, sy - size/2, sx + size/2, sy + size/2,
                                    fill=color, outline=outline, width=1.5, tags=f"e{e.order_index}")
            if show_label:
                self.canvas.create_text(sx, sy - size - 6, text=f"#{e.order_index} {label}",
                                        fill="#fff", font=("Arial", 8, "bold"), tags=f"e{e.order_index}")
        else:
            l, t, r, b = e.values
            sx0 = self.offset_x + l * scale
            sy0 = self.offset_y + t * scale
            sx1 = self.offset_x + r * scale
            sy1 = self.offset_y + b * scale
            width = 2.5 if (is_sel or is_hover) else 1
            self.canvas.create_rectangle(sx0, sy0, sx1, sy1, fill="", outline=color,
                                         width=width, dash=(4, 2), tags=f"e{e.order_index}")
            if show_label:
                self.canvas.create_text((sx0+sx1)/2, sy0 - 8, text=f"#{e.order_index} {label}",
                                        fill="#fff", font=("Arial", 8, "bold"), tags=f"e{e.order_index}")

    # ------------------------------------------------------ Mouse handlers
    def _entry_at_index(self, idx):
        entries = self._visible_entries()
        for e in entries:
            if e.order_index == idx:
                return e
        return None

    def _find_entry_at(self, x, y, radius=6):
        items = self.canvas.find_overlapping(x - radius, y - radius, x + radius, y + radius)
        for item in reversed(items):  # topo primeiro (desenhado por ultimo)
            for tag in self.canvas.gettags(item):
                if tag.startswith("e") and tag[1:].isdigit():
                    e = self._entry_at_index(int(tag[1:]))
                    if e:
                        return e
        return None

    def _on_canvas_motion(self, ev):
        if self.canvas_scale > 0:
            wx = (ev.x - self.offset_x) / self.canvas_scale
            wy = (ev.y - self.offset_y) / self.canvas_scale
            self.coord_var.set(f"X={int(wx)} Y={int(wy)}")

        if self.dragging or self.template_dragging:
            return

        if self.current_key == WINDOWSET_KEY:
            name = self._find_template_at(ev.x, ev.y)
            if name != self.template_hovered:
                self.template_hovered = name
                self._redraw()
            return

        e = self._find_entry_at(ev.x, ev.y)
        if e is not self.hovered:
            self.hovered = e
            self._redraw()

    def _on_canvas_press(self, ev):
        if self.current_key == WINDOWSET_KEY:
            name = self._find_template_at(ev.x, ev.y)
            if name:
                v = self.templates[self.race_var.get()].get(name) or [0, 0, 100, 100]
                self.template_dragging = (name, ev.x, ev.y, v[0], v[1])
                self._select_template(name)
                return
            self.template_selected = None
            self._redraw()
            self._update_property_panel(None)
            return

        items = self.canvas.find_overlapping(ev.x - 3, ev.y - 3, ev.x + 3, ev.y + 3)
        for item in items:
            for tag in self.canvas.gettags(item):
                if tag.startswith("e") and tag[1:].isdigit():
                    idx = int(tag[1:])
                    e = self._entry_at_index(idx)
                    if e:
                        self.dragging = (e, ev.x, ev.y, list(e.values))
                        self._select_entry(e)
                        return
        self.selected = None
        self._redraw()
        self._update_property_panel(None)

    def _on_canvas_drag(self, ev):
        if self.current_key == WINDOWSET_KEY:
            if not self.template_dragging or self.canvas_scale <= 0:
                return
            name, sx, sy, orig_x, orig_y = self.template_dragging
            dx = (ev.x - sx) / self.canvas_scale
            dy = (ev.y - sy) / self.canvas_scale
            new_x = int(round(orig_x + dx))
            new_y = int(round(orig_y + dy))
            race = self.race_var.get()
            v = self.templates[race].get(name) or [0, 0, 100, 100]
            self.templates[race][name] = [new_x, new_y, v[2], v[3]]
            self._redraw()
            self._update_property_panel_windowset(name, self.templates[race][name])
            return

        if not self.dragging or self.canvas_scale <= 0:
            return
        e, sx, sy, orig = self.dragging
        dx = (ev.x - sx) / self.canvas_scale
        dy = (ev.y - sy) / self.canvas_scale
        if e.list_type == 'POINT_LIST':
            e.values[0] = int(round(orig[0] + dx))
            e.values[1] = int(round(orig[1] + dy))
        else:
            e.values[0] = int(round(orig[0] + dx))
            e.values[1] = int(round(orig[1] + dy))
            e.values[2] = int(round(orig[2] + dx))
            e.values[3] = int(round(orig[3] + dy))
        self._redraw()
        self._update_property_panel(e, suppress_trace=True)

    def _on_canvas_release(self, ev):
        if self.current_key == WINDOWSET_KEY:
            if self.template_dragging:
                name = self.template_dragging[0]
                self.template_dragging = None
                self._populate_listbox()
                v = self.templates[self.race_var.get()][name]
                self._set_status(f"[{name}] atualizado no modelo '{self.race_var.get()}': "
                                  f"{v}. 'Salvar modelo de janelas' grava em disco.")
            return

        if self.dragging:
            e = self.dragging[0]
            self.doc.apply_entry(e)
            self.dragging = None
            self._set_status(f"{self.current_key} {self.current_list_type} #{e.order_index} "
                              f"atualizado: {e.values}. Save grava em disco.")

    # ------------------------------------------------------ Selection
    def _on_listbox_select(self):
        sel = self.entry_listbox.curselection()
        if not sel:
            return
        if self.current_key == WINDOWSET_KEY:
            if sel[0] >= len(windowset.WINDOW_NAMES):
                return
            self._select_template(windowset.WINDOW_NAMES[sel[0]])
            return
        entries = self._visible_entries()
        if sel[0] >= len(entries):
            return
        self._select_entry(entries[sel[0]])

    def _select_entry(self, e):
        self.selected = e
        self._update_property_panel(e, suppress_trace=True)
        self._redraw()
        self.entry_listbox.selection_clear(0, tk.END)
        # a linha na listbox e' a POSICAO dentro da lista filtrada (pode
        # nao bater com order_index - ex: GAME_MENU filtra por raca, entao
        # Vampire (order_index 2,3) aparece nas linhas 0,1 da listbox).
        visible = self._visible_entries()
        if e in visible:
            row = visible.index(e)
            self.entry_listbox.selection_set(row)
            self.entry_listbox.see(row)

    def _update_property_panel(self, e, suppress_trace=True):
        if self.current_key == WINDOWSET_KEY:
            if e is None:
                self._suppress_trace = True
                self.prop_name_var.set("-")
                self.prop_extra_var.set("")
                for v in self.value_vars:
                    v.set("0")
                for lbl, sp in self.value_spins:
                    sp.state(["disabled"])
                self.root.after_idle(lambda: setattr(self, '_suppress_trace', False))
            return
        self._suppress_trace = True
        self.prop_name_var.set("-")
        self.prop_extra_var.set("")
        if e is None:
            self.prop_comment_var.set("-")
            for v in self.value_vars:
                v.set("0")
            for lbl, sp in self.value_spins:
                sp.state(["disabled"])
        else:
            self.prop_name_var.set(f"{self.current_key} #{e.order_index}")
            self.prop_comment_var.set(e.comment or f"(sem comentario, indice {e.order_index})")
            if e.list_type == 'POINT_LIST':
                self.value_vars[0].set(str(e.values[0]))
                self.value_vars[1].set(str(e.values[1]))
                self.value_vars[2].set("0")
                self.value_vars[3].set("0")
                self.value_spins[0][0].config(text="X:")
                self.value_spins[1][0].config(text="Y:")
                self.value_spins[0][1].state(["!disabled"])
                self.value_spins[1][1].state(["!disabled"])
                self.value_spins[2][1].state(["disabled"])
                self.value_spins[3][1].state(["disabled"])
            else:
                self.value_vars[0].set(str(e.values[0]))
                self.value_vars[1].set(str(e.values[1]))
                self.value_vars[2].set(str(e.values[2]))
                self.value_vars[3].set(str(e.values[3]))
                self.value_spins[0][0].config(text="Left:")
                self.value_spins[1][0].config(text="Top:")
                self.value_spins[2][0].config(text="Right:")
                self.value_spins[3][0].config(text="Bottom:")
                for lbl, sp in self.value_spins:
                    sp.state(["!disabled"])
        self.root.after_idle(lambda: setattr(self, '_suppress_trace', False))

    def _on_prop_change(self):
        if self.current_key == WINDOWSET_KEY:
            self._on_prop_change_windowset()
            return
        if self._suppress_trace or self.selected is None:
            return
        e = self.selected
        try:
            if e.list_type == 'POINT_LIST':
                e.values[0] = int(self.value_vars[0].get())
                e.values[1] = int(self.value_vars[1].get())
            else:
                e.values[0] = int(self.value_vars[0].get())
                e.values[1] = int(self.value_vars[1].get())
                e.values[2] = int(self.value_vars[2].get())
                e.values[3] = int(self.value_vars[3].get())
            self.doc.apply_entry(e)
            self._redraw()
        except ValueError:
            pass

    # ------------------------------------------------------ Helpers
    def _set_status(self, msg):
        self.status_var.set(msg)


def main():
    ini = sys.argv[1] if len(sys.argv) > 1 else auto_find_interface_inf()
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    InterfaceEditor(root, ini)
    root.mainloop()


if __name__ == "__main__":
    main()
