"""
darkeden_uiskin.py - reskin visual das telas/janelas do cliente DarkEden:
TITULO, LOGIN, SELECAO DE PERSONAGEM, OPCOES, MENU ESC, INVENTARIO,
MINIMAPA, BARRA DE HP/MP, BARRA DE ATALHOS, MOLDURA DA TELA DE JOGO/CHAT,
LOJA DE NPC, PARTY, GEAR, EFFECT STATUS, QUESTS, MAILBOX, EXCHANGE,
TRANSMIT, WORLD MAP, SERVER SELECT, FRIEND LIST, PERSONAL SHOP,
BLOODBURST, TUTORIAL, POWERJJANG, BULLETIN, PORTAL, LOTTERY, CREDIT,
FACE/ROSTOS, MAIN BUTTONS, SKILL ETC, NAMING

EXPANDIDO 2026-07-23: de 12 para 36 telas/areas cobertas.
================================================================================
Author: VictorRP7
Written: 2026-07-21 (expandido no mesmo dia com OPTION/GAME_MENU/janelas
do jogo, a pedido: "ver se consegue melhorar" - tela de opcoes, inventario,
minimapa etc)

Diferente do `darkeden_interface_editor.py` (que reposiciona PONTOS do
`interface.inf` - onde cada botao/campo FICA), este modulo troca a ARTE de
verdade (o que cada botao/fundo MOSTRA) - fundo da tela de titulo, popup de
login, tela de selecao de personagem, e os sprites de cada botao (normal/
pressionado/hover). Formatos e telas confirmados lendo o codigo-fonte C++
real antes de escrever qualquer coisa:

    client-master/VS_UI/src/VS_UI_Title.cpp
        C_VS_UI_TITLE        (tela de titulo, ~4760-5120)
        C_VS_UI_LOGIN        (popup de login, ~4180-4460)
        C_VS_UI_CHAR_MANAGER (tela de SELECAO de personagem - NAO e' a
                               C_VS_UI_NEWCHAR, que e' so' a CRIACAO de um
                               personagem novo e ja' tem editor proprio,
                               ~2899-3421)
    client-master/VS_UI/src/header/VS_UI_title.h
        enums TITLE_SPK, CHAR_MANAGER_SPK_ID/COMMON_SPK_ID (posicao de
        cada sprite dentro do .spk correspondente)
    client-master/Client/SpriteLib/CSprite555.cpp / CSprite565.cpp
        SaveToFile - confirma que o formato de ESCRITA e' o espelho exato
        do formato de LEITURA ja' implementado em darkeden_truesprite.py
        (ver esse modulo pro formato binario completo do .spk/.spki e as
        funcoes de escrita adicionadas la': encode_sprite_from_image,
        TrueSpritePack.replace_sprite/append_sprite/save).

TODAS as posicoes abaixo sao LITERAIS FIXOS no C++ (nenhuma dessas 3 telas
consulta o interface.inf - confirmado: zero chamadas a' pSkin->GetPoint()
em qualquer uma das 3 classes) - por isso este editor NAO reposiciona nada,
so' troca a IMAGEM de cada pedaco. Posicoes mostradas aqui sao so' pra'
montar o preview (pra' voce ver ONDE cada coisa fica na tela enquanto
escolhe o que trocar), sempre no modo classico 800x600 (widescreen
1024x768 tem coordenadas diferentes pros botoes do TITLE - ver
TITLE_POSITIONS_WIDESCREEN - mas o restante desta ferramenta assume
classico, mesma limitacao ja' documentada pro NEW_CHAR no interface editor).

IMPORTANTE sobre a tela de SELECAO DE PERSONAGEM: o nome da classe C++ e'
"C_VS_UI_CHAR_MANAGER" (achado via C_VS_UI::SelectCharacter() ->
m_pC_char_manager->SelectSlot()) - so' documentando aqui pra' quem for
procurar no codigo-fonte depois, ja' que o nome sugere "gerenciador" e nao
"tela de selecao", mas e' exatamente essa a tela que aparece depois do
login, com os 3 slots de personagem.

IMPORTANTE sobre os botoes do TITLE (Connect/Option/Credit/Exit): a tela
real NUNCA desenha esses sprites em repouso (confirmado em
ShowButtonWidget, VS_UI_Title.cpp:5096-5101) - so' aparecem com o mouse em
cima (hover) ou pressionado. Este editor MOSTRA os 3 estados sempre (pra'
dar pra' editar/visualizar todos), mas isso e' uma conveniencia da
ferramenta, nao like o jogo realmente parece "parado".
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import darkeden_truesprite as truesprite


class Asset:
    """Um pedaco de arte trocavel: um sprite especifico dentro de um .spk,
    numa ou mais posicoes de tela (mais de uma so' pros 3 slots de
    personagem, que repetem a MESMA imagem 3 vezes)."""
    __slots__ = ('key', 'label', 'spk_filename', 'sprite_index', 'positions', 'is_background')

    def __init__(self, key, label, spk_filename, sprite_index, positions, is_background=False):
        self.key = key
        self.label = label
        self.spk_filename = spk_filename
        self.sprite_index = sprite_index
        self.positions = positions  # lista de (x,y)
        self.is_background = is_background


# ---------------------------------------------------------------------------
# TITLE (C_VS_UI_TITLE) - fundo Title.spk (800x600) + 4 botoes x 2 estados
# em TitleMenuDefault.spk (8 sprites, 84x21 cada) - posicoes classicas
# confirmadas em VS_UI_Title.cpp:4841-4844 (widescreen: 4834-4837, ver
# TITLE_POSITIONS_WIDESCREEN abaixo, nao usado pelo preview desta ferramenta)
# ---------------------------------------------------------------------------
TITLE_POSITIONS_WIDESCREEN = {
    "CONNECT": (888, 544), "OPTION": (888, 592), "CREDIT": (888, 640), "EXIT": (888, 688),
}

TITLE_ASSETS = [
    Asset("BG", "Fundo (Title.spk)", "Title.spk", 0, [(0, 0)], is_background=True),
    Asset("CONNECT_HILIGHT", "Botao Connect (normal/hover)", "TitleMenuDefault.spk", 0, [(673, 371)]),
    Asset("CONNECT_PUSH", "Botao Connect (pressionado)", "TitleMenuDefault.spk", 1, [(673, 371)]),
    Asset("OPTION_HILIGHT", "Botao Option (normal/hover)", "TitleMenuDefault.spk", 2, [(673, 419)]),
    Asset("OPTION_PUSH", "Botao Option (pressionado)", "TitleMenuDefault.spk", 3, [(673, 419)]),
    Asset("CREDIT_HILIGHT", "Botao Credit (normal/hover)", "TitleMenuDefault.spk", 4, [(673, 467)]),
    Asset("CREDIT_PUSH", "Botao Credit (pressionado)", "TitleMenuDefault.spk", 5, [(673, 467)]),
    Asset("EXIT_HILIGHT", "Botao Exit (normal/hover)", "TitleMenuDefault.spk", 6, [(673, 515)]),
    Asset("EXIT_PUSH", "Botao Exit (pressionado)", "TitleMenuDefault.spk", 7, [(673, 515)]),
]

# ---------------------------------------------------------------------------
# LOGIN (C_VS_UI_LOGIN) - popup Login.spk (222x179) + 3 botoes x 2 estados
# em LoginMenu.spk (enum NEW_ID=0,OK=1,CANCEL=2,PUSHED_NEW_ID=3,PUSHED_OK=4,
# PUSHED_CANCEL=5 - VS_UI_title.h:266-274) - posicoes VS_UI_Title.cpp~4435-4454
# ---------------------------------------------------------------------------
LOGIN_ASSETS = [
    Asset("BG", "Fundo do popup (Login.spk)", "Login.spk", 0, [(0, 0)], is_background=True),
    Asset("NEW_ID", "Botao Novo Cadastro (normal)", "LoginMenu.spk", 0, [(118, 123)]),
    Asset("NEW_ID_PUSH", "Botao Novo Cadastro (pressionado)", "LoginMenu.spk", 3, [(118, 123)]),
    Asset("OK", "Botao OK / Conectar (normal)", "LoginMenu.spk", 1, [(52, 123)]),
    Asset("OK_PUSH", "Botao OK / Conectar (pressionado)", "LoginMenu.spk", 4, [(52, 123)]),
    Asset("CANCEL", "Botao Cancelar (normal)", "LoginMenu.spk", 2, [(156, 28)]),
    Asset("CANCEL_PUSH", "Botao Cancelar (pressionado)", "LoginMenu.spk", 5, [(156, 28)]),
]

# ---------------------------------------------------------------------------
# SELECAO DE PERSONAGEM (C_VS_UI_CHAR_MANAGER) - 3 camadas de fundo +
# moldura de slot (repetida 3x) + 4 botoes x 3 estados (normal/pressionado/
# hover). heart_rect = {250,430,610} (VS_UI_Title.cpp:114), HEART_Y=180
# (:113) - os 3 slots de personagem usam a MESMA moldura/imagem, so' a
# POSICAO muda, por isso "SLOT_FRAME"/"SLOT_FRAME_HL" tem 3 posicoes.
# ---------------------------------------------------------------------------
_HEART_RECT = [250, 430, 610]
_HEART_Y = 180

CHAR_SELECT_ASSETS = [
    Asset("BG_FAR", "Fundo distante (TitleBack.spk, 1024x768)", "TitleBack.spk", 0, [(0, 0)], is_background=True),
    Asset("BG", "Fundo (Common.spk)", "Common.spk", 0, [(0, 0)], is_background=True),
    Asset("TITLE_LABEL", "Rotulo 'TITLE' (CharManager.spk)", "CharManager.spk", 2, [(265, 50)], is_background=True),
    Asset("SLOT_FRAME", "Moldura do slot de personagem (normal)", "CharManager.spk", 0,
          [(x, _HEART_Y) for x in _HEART_RECT], is_background=True),
    Asset("SLOT_FRAME_HL", "Moldura do slot de personagem (destacada/selecionada)", "CharManager.spk", 1,
          [(x, _HEART_Y) for x in _HEART_RECT]),
    Asset("BACK", "Botao Voltar (normal)", "Common.spk", 1, [(28, 522)]),
    Asset("BACK_PUSH", "Botao Voltar (pressionado)", "Common.spk", 2, [(28, 522)]),
    Asset("BACK_HOVER", "Botao Voltar (hover)", "Common.spk", 3, [(28, 522)]),
    Asset("ENTER", "Botao Entrar no Jogo (normal)", "Common.spk", 4, [(687, 522)]),
    Asset("ENTER_PUSH", "Botao Entrar no Jogo (pressionado)", "Common.spk", 5, [(687, 522)]),
    Asset("ENTER_HOVER", "Botao Entrar no Jogo (hover)", "Common.spk", 6, [(687, 522)]),
    Asset("CREATE", "Botao Criar Personagem (normal)", "CharManager.spk", 6, [(555, 542)]),
    Asset("CREATE_PUSH", "Botao Criar Personagem (pressionado)", "CharManager.spk", 7, [(555, 542)]),
    Asset("CREATE_HOVER", "Botao Criar Personagem (hover)", "CharManager.spk", 8, [(555, 542)]),
    Asset("DELETE", "Botao Excluir Personagem (normal)", "CharManager.spk", 3,
          [(x + 119, _HEART_Y + 36) for x in _HEART_RECT]),
    Asset("DELETE_PUSH", "Botao Excluir Personagem (pressionado)", "CharManager.spk", 4,
          [(x + 119, _HEART_Y + 36) for x in _HEART_RECT]),
    Asset("DELETE_HOVER", "Botao Excluir Personagem (hover)", "CharManager.spk", 5,
          [(x + 119, _HEART_Y + 36) for x in _HEART_RECT]),
]

# ---------------------------------------------------------------------------
# OPTION (C_VS_UI_OPTION) e GAME_MENU (C_VS_UI_GAMEMENU) - fundo DIFERENTE
# por raca (Slayer/Vampire/Ousters) - Option.spk/OptionRACE.spk/
# GameMenuRACE.spk. Diferente de TITLE/LOGIN/CHAR_SELECT, os BOTOES dessas
# duas telas tem posicao AO VIVO no interface.inf de verdade (confirmado em
# darkeden_interface_editor.py - "AO VIVO" pro GAME_MENU, "PARCIAL" (so' o
# caminho de dentro do jogo) pro OPTION) - por isso a posicao de preview
# aqui e' lida do interface.inf de verdade (via InterfaceDocument, o mesmo
# parser do Interface Editor) em vez de um literal fixo; se o arquivo nao
# for achado, cai num valor aproximado so' pra' nao quebrar o preview.
#
# GAME_MENU: so' o FUNDO por raca tem sprite mapeado - os botoes (Continue/
# Logout/Option) sao "dado morto em repouso" igual TITLE (ShowButtonWidget,
# VS_UI_Game.cpp:6220-6224 - so' aparecem com mouse em cima/pressionado) e
# esse mapeamento sprite-por-botao nunca foi levantado nesta pesquisa
# (diferente de TITLE, onde achamos TitleMenuDefault.spk) - por isso, ao
# contrario de OPTION, aqui so' entra o fundo por enquanto.
# ---------------------------------------------------------------------------
_OPTION_RACE_SPK = {"SLAYER": "OptionSlayer.spk", "VAMPIRE": "OptionVampire.spk", "OUSTERS": "OptionOusters.spk"}
_GAME_MENU_RACE_SPK = {"SLAYER": "GameMenuSlayer.spk", "VAMPIRE": "GameMenuVampire.spk", "OUSTERS": "GameMenuOusters.spk"}

# ---------------------------------------------------------------------------
# STATUS/INFO (C_VS_UI_INFO) - janela de status do personagem (STR/DEX/INT/
# HP/MP/Nome/Fama/Alinhamento). NAO tem um fundo unico de tela inteira (nao
# e' uma imagem so' como Title/Login) - e' montada de pecinhas pequenas de
# InfoSlayer/Vampire/Ousters.spk: CHAR_BOX (moldura do retrato, indice 15,
# posicao FIXA por raca) + DESC_BOX (caixa de nome/fama, indice 16) + um
# icone por STR/DEX/INT/HP/MP/etc - os DOIS ultimos grupos tem posicao AO
# VIVO (vem dos pontos Desc_Box/Field_x1 do proprio interface.inf) - MESMA
# formula ja usada por darkeden_interface_editor.InterfaceEditor.
# _background_layers, so' que aqui devolvendo Asset em vez de desenhar
# direto no canvas.
# ---------------------------------------------------------------------------
_INFO_RACE_SPK = {"SLAYER": "InfoSlayer.spk", "VAMPIRE": "InfoVampire.spk", "OUSTERS": "InfoOusters.spk"}

_INFO_NAME_ICON_LABELS = {29: "Icone Nome", 30: "Icone Alinhamento", 46: "Icone Fama"}
_INFO_STAT_ICON_LABELS = {
    32: "Icone STR", 33: "Icone DEX", 34: "Icone INT", 35: "Icone HP", 47: "Icone MP",
    36: "Icone Chance de Acerto", 37: "Icone Dano", 38: "Icone Defesa", 39: "Icone Protecao",
    76: "Icone EP (so Ousters)",
}


def _info_assets(doc, race="SLAYER"):
    fname = _INFO_RACE_SPK.get(race, _INFO_RACE_SPK["SLAYER"])
    char_box_x, char_box_y = truesprite.INFO_CHAR_BOX_POS.get(race, (20, 22))
    assets = [Asset("CHAR_BOX", "Moldura do retrato", fname, truesprite.INFO_CHAR_BOX_SPRITE_INDEX,
                     [(char_box_x, char_box_y)], is_background=True)]

    if doc is None:
        return assets  # sem interface.inf carregado, so' a moldura (posicao fixa) da' pra mostrar

    rects = doc.get("INFO", "RECT_LIST")
    if not rects:
        return assets
    l, t, r, _b = rects[0].values
    base = {"SLAYER": l, "VAMPIRE": t, "OUSTERS": r}.get(race)
    if base is None:
        return assets

    points = {e.order_index: e for e in doc.get("INFO", "POINT_LIST")}
    desc_entry = points.get(base)
    field1_entry = points.get(base + 1)

    if desc_entry is not None:
        assets.append(Asset("DESC_BOX", "Caixa de nome/fama/nivel", fname,
                             truesprite.INFO_DESC_BOX_SPRITE_INDEX,
                             [(desc_entry.values[0], desc_entry.values[1])], is_background=True))

    layout = truesprite.INFO_ICON_LAYOUT.get(race, {})
    if field1_entry is not None:
        for offset, sprite_idx, gap_idx in layout.get("name_group", []):
            pt = points.get(base + offset)
            if pt is None:
                continue
            x = field1_entry.values[0] + pt.values[0]
            y = char_box_y + pt.values[1] + truesprite.INFO_FIELD_GAP * gap_idx
            label = _INFO_NAME_ICON_LABELS.get(sprite_idx, f"Icone #{sprite_idx}")
            assets.append(Asset(f"NAME_{sprite_idx}", label, fname, sprite_idx, [(x, y)]))
    if desc_entry is not None:
        for offset, sprite_idx, gap_idx in layout.get("stat_group", []):
            pt = points.get(base + offset)
            if pt is None:
                continue
            x = char_box_x + pt.values[0]
            y = desc_entry.values[1] + pt.values[1] + truesprite.INFO_FIELD_GAP * gap_idx
            label = _INFO_STAT_ICON_LABELS.get(sprite_idx, f"Icone #{sprite_idx}")
            assets.append(Asset(f"STAT_{sprite_idx}", label, fname, sprite_idx, [(x, y)]))
    return assets

_OPTION_POINT_LABELS = {
    0: "Botao Fechar", 1: "Aba Atalho", 2: "Aba Tela", 3: "Aba Som", 4: "Aba Jogo",
    5: "Quadrado do Checkbox",
}


def _interface_points(doc, key):
    """{order_index: (x,y)} de uma CHAVE POINT_LIST do interface.inf ja'
    carregado (doc pode ser None se o arquivo nao foi achado)."""
    if doc is None:
        return {}
    return {e.order_index: tuple(e.values) for e in doc.get(key, "POINT_LIST")}


def _option_assets(doc, race="SLAYER"):
    fname = _OPTION_RACE_SPK.get(race, _OPTION_RACE_SPK["SLAYER"])
    assets = [Asset("BG", f"Fundo ({race.title()})", fname, 0, [(0, 0)], is_background=True)]
    pts = _interface_points(doc, "OPTION")
    for order_index, label in _OPTION_POINT_LABELS.items():
        sprite = truesprite.get_point_sprite("OPTION", order_index, race)
        if sprite is None:
            continue
        spk_filename, sprite_index = sprite
        pos = pts.get(order_index, (20 + order_index * 60, 20))
        assets.append(Asset(f"PT_{order_index}", label, spk_filename, sprite_index, [pos]))
    return assets


def _game_menu_assets(doc, race="SLAYER"):
    fname = _GAME_MENU_RACE_SPK.get(race, _GAME_MENU_RACE_SPK["SLAYER"])
    return [Asset("BG", f"Fundo ({race.title()})", fname, 0, [(0, 0)], is_background=True)]


# ---------------------------------------------------------------------------
# JANELAS DO JOGO (Inventario/Minimapa/Barra de HP-MP/Barra de Atalhos/
# Moldura da tela) - C_VS_UI_INVENTORY, C_VS_UI_MINIMAP, C_VS_UI_HPBAR,
# C_VS_UI_*_QUICKITEM, C_VS_UI_CHATTING (VS_UI/src/VS_UI_GameCommon.cpp) -
# confirmado que TODAS usam o mesmo CSpritePack (CTypePack2<CSprite,
# CSprite555,CSprite565> - VS_UI_util.h:56-70, CSpritePack.h:17), mesmo
# formato .spk/.spki de tudo mais neste modulo. Diferente de TITLE/LOGIN/
# CHAR_SELECT/OPTION/GAME_MENU (telas inteiras com fundo proprio), estas
# sao JANELAS que flutuam por cima do mundo jogavel - nao tem um "fundo de
# tela" atras delas, entao o preview aqui mostra so' a propria janela
# (pode sobrar espaco vazio ao redor, e' normal).
# ---------------------------------------------------------------------------
_INVENTORY_RACE_SPK = {"SLAYER": "InventorySlayer.spk", "VAMPIRE": "InventoryVampire.spk",
                        "OUSTERS": "InventoryOusters.spk"}
# grid_start_offset_x/y por raca + GRID_X=10,GRID_Y=6,GRID_UNIT_PIXEL=30
# (VS_UI_GameCommon.h:1009-1012, ctor ~6765-6814)
_INVENTORY_GRID_ORIGIN = {"SLAYER": (13, 25), "VAMPIRE": (17, 19), "OUSTERS": (25, 35)}
_INVENTORY_GRID_SIZE = (10, 6)
_INVENTORY_GRID_UNIT = 30


def _inventory_grid_positions(race):
    ox, oy = _INVENTORY_GRID_ORIGIN.get(race, _INVENTORY_GRID_ORIGIN["SLAYER"])
    cols, rows = _INVENTORY_GRID_SIZE
    return [(ox + c * _INVENTORY_GRID_UNIT, oy + r * _INVENTORY_GRID_UNIT)
            for r in range(rows) for c in range(cols)]


def _inventory_assets(doc, race="SLAYER"):
    fname = _INVENTORY_RACE_SPK.get(race, _INVENTORY_RACE_SPK["SLAYER"])
    grid_pos = _inventory_grid_positions(race)
    assets = [
        Asset("WINDOW", "Fundo da janela (normal)", fname, 0, [(0, 0)], is_background=True),
        Asset("WINDOW_ALPHA", "Fundo da janela (translucido)", fname, 1, [(0, 0)]),
        Asset("ITEMBACK", "Fundo de slot com item (normal) - grade 10x6 inteira", fname, 2, grid_pos,
              is_background=True),
        Asset("ITEMBACK_ALPHA", "Fundo de slot com item (translucido)", fname, 3, [grid_pos[0]]),
    ]
    if race == "VAMPIRE":
        assets.append(Asset("WINDOW_BOTTOM", "Tira extra debaixo (so Vampire)", fname, 4, [(0, 257)]))
    return assets


# NAO cobrimos os botoes (dinheiro/descricao/ajuda/fechar/alpha) desta
# janela - eles vem de um arquivo COMPARTILHADO (m_pC_assemble_box_button_spk,
# SPK_ASSEMBLE_BOX_BUTTON_SLAYER/VAMPIRE/OUSTERS) cujo NOME DE ARQUIVO real
# nao foi confirmado com certeza nesta pesquisa - ver "Limitacoes conhecidas".

_MINIMAP_RACE_SPK = {"SLAYER": "MinimapSlayer.spk", "VAMPIRE": "MinimapVampire.spk",
                      "OUSTERS": "MinimapOusters.spk"}


def _minimap_assets(doc, race="SLAYER"):
    fname = _MINIMAP_RACE_SPK.get(race, _MINIMAP_RACE_SPK["SLAYER"])
    # MAIN/MAIN_ALPHA sao a MESMA janela (2 estados) - RIGHT/BOARD/ICON_*
    # tem deslocamento exato NAO confirmado nesta pesquisa (so' a formula
    # geral "encostado na borda direita"), entao ficam enfileirados abaixo
    # so' pra' navegacao/edicao - nao e' a posicao exata em jogo.
    return [
        Asset("MAIN", "Moldura do minimapa (normal)", fname, 0, [(0, 0)], is_background=True),
        Asset("MAIN_ALPHA", "Moldura do minimapa (translucida)", fname, 1, [(0, 140)]),
        Asset("RIGHT", "Borda direita", fname, 2, [(220, 0)]),
        Asset("BOARD", "Placa deslizante (nome da zona)", fname, 3, [(220, 140)]),
        Asset("ICON_SELF", "Icone do jogador (voce)", fname, 4, [(280, 0)]),
        Asset("ICON_PARTY", "Icone de membro do grupo", fname, 5, [(280, 20)]),
    ]


_HPBAR_RACE_SPK = {"SLAYER": "HPBarSlayer.spk", "VAMPIRE": "HPBarVampire.spk", "OUSTERS": "HPBarOusters.spk"}


def _hpbar_assets(doc, race="SLAYER"):
    fname = _HPBAR_RACE_SPK.get(race, _HPBAR_RACE_SPK["SLAYER"])
    return [Asset("BG", f"Fundo da barra de HP/MP ({race.title()})", fname, 0, [(0, 0)], is_background=True)]


# Vampire NAO tem arquivo proprio - reusa QuickitemSlayer.spk (confirmado:
# nao existe SPK_VAMPIRE_QUICKITEM nenhum no codigo-fonte).
_QUICKSLOT_RACE_SPK = {"SLAYER": "QuickitemSlayer.spk", "VAMPIRE": "QuickitemSlayer.spk",
                        "OUSTERS": "QuickitemOusters.spk"}


def _quickslot_assets(doc, race="SLAYER"):
    fname = _QUICKSLOT_RACE_SPK.get(race, _QUICKSLOT_RACE_SPK["SLAYER"])
    note = " (mesmo arquivo do Slayer)" if race == "VAMPIRE" else ""
    return [Asset("SLOT", f"Moldura de 1 slot de atalho{note}", fname, 0, [(0, 0)], is_background=True)]


_CHATTING_RACE_SPK = {"SLAYER": "ChattingSlayer.spk", "VAMPIRE": "ChattingVampire.spk",
                       "OUSTERS": "ChattingOusters.spk"}

# ---------------------------------------------------------------------------
# LOJA DE NPC (C_VS_UI_SHOP, VS_UI/src/VS_UI_Shop.cpp) - fundo/abas em
# Shop&StorageRACE.spk (enum IMAGE_SPK_INDEX, VS_UI_Shop.h:40-61), grade de
# 5x4 prateleiras (SLOT_X_COUNT=5, SLOT_Y_COUNT=4, SLOT_WIDTH=60,
# SLOT_HEIGHT=90 - VS_UI_Shop.h:69-77), posicoes classicas confirmadas no
# construtor (VS_UI_Shop.cpp:105-137, Ousters soma +10 em tudo E aumenta a
# janela +20x+20). Zero chamadas a GetPoint()/SkinManager neste arquivo -
# 100% literal fixo, igual Titulo/Login/Selecao de Personagem.
#
# ACHADO: os 3 arquivos por raca sao ESTRUTURALMENTE identicos (28 sprites,
# mesmas dimensoes sprite a sprite - MAIN_WINDOW sempre 303x93, as abas
# sempre 95x27, batendo exato com TAB_WIDTH/TAB_HEIGHT) mas com MD5
# diferente - so' o estilo visual/cor muda por raca, nao a estrutura.
#
# MAIN_WINDOW (indice 0) NAO e' o fundo da janela inteira (apesar do nome) -
# e' o fundo de UMA FILEIRA da prateleira, desenhado 4x (uma por fileira),
# confirmado em Show() (VS_UI_Shop.cpp:638-641: BltLocked no inicio de
# CADA fileira, nao uma vez so'). A moldura da janela em si vem de
# gpC_global_resource->DrawDialogLocked() - um dialogo GENERICO compartilhado
# por varios popups do jogo, fora do escopo aqui (nao e' especifico da loja).
#
# STORAGE_TAB1/2/3 (indices 10-18) existem no mesmo arquivo mas pertencem a
# uma tela de DEPOSITO/BANCO separada (nao rastreada nesta pesquisa) - por
# isso ficam de fora, so' as abas Normal/Especial/Misterioso (as 3 da LOJA
# de verdade) entram.
# ---------------------------------------------------------------------------
_SHOP_RACE_SPK = {"SLAYER": "Shop&StorageSlayer.spk", "VAMPIRE": "Shop&StorageVampire.spk",
                  "OUSTERS": "Shop&StorageOusters.spk"}

_SHOP_SLOT_X_COUNT = 5
_SHOP_SLOT_Y_COUNT = 4
_SHOP_SLOT_WIDTH = 60
_SHOP_SLOT_HEIGHT = 90


def _shop_offsets(race):
    """(shelf_x, [shelf_y x4], tab_x[3], tab_y) - literais do construtor,
    com o ajuste +10 que so' o Ousters recebe (VS_UI_Shop.cpp:120-137)."""
    bump = 10 if race == "OUSTERS" else 0
    shelf_x = 15 + bump
    shelf_y = [23 + bump, 125 + bump, 227 + bump, 329 + bump]
    tab_x = [15 + bump, 119 + bump, 224 + bump]
    tab_y = 422 + bump
    return shelf_x, shelf_y, tab_x, tab_y


def _shop_assets(doc, race="SLAYER"):
    fname = _SHOP_RACE_SPK.get(race, _SHOP_RACE_SPK["SLAYER"])
    shelf_x, shelf_y, tab_x, tab_y = _shop_offsets(race)

    row_positions = [(shelf_x, y) for y in shelf_y]
    assets = [Asset("MAIN_WINDOW", "Fundo de 1 fileira da prateleira (repetido 4x)", fname, 0,
                     row_positions, is_background=True)]

    tab_labels = ["Normal", "Especial", "Misterioso"]
    tab_states = [(1, "normal"), (4, "em cima do mouse"), (7, "pressionada")]
    for tab_i, label in enumerate(tab_labels):
        for sprite_offset, state_label in tab_states:
            sprite_idx = sprite_offset + tab_i
            assets.append(Asset(f"TAB_{tab_i}_{sprite_offset}", f"Aba {label} ({state_label})",
                                 fname, sprite_idx, [(tab_x[tab_i], tab_y)]))
    return assets


def _chatting_assets(doc, race="SLAYER"):
    fname = _CHATTING_RACE_SPK.get(race, _CHATTING_RACE_SPK["SLAYER"])
    # sprite 0 aqui e' 800x600 - achado surpreendente (nao e' so' uma
    # caixinha de chat pequena): parece ser a MOLDURA/decoracao da tela
    # de jogo inteira, que ja' inclui a area onde o chat fica recortado.
    return [Asset("BG", "Moldura da tela do jogo (inclui area do chat)", fname, 0, [(0, 0)], is_background=True)]


# =============================================================================
# NOVAS TELAS ADICIONADAS (2026-07-23) - expandindo a cobertura do editor
# pra' janelas que faltavam: Party, Gear, Quest, Mail, Trade, Transmit,
# WorldMap, ServerSelect, Friend, PersonalShop, BloodBurst, Tutorial,
# Powerjjang, Bulletin, Portal, Lottery, Credit, Face, Main, SkillEtc, Naming
# =============================================================================

# ---------------------------------------------------------------------------
# PARTY (C_VS_UI_PARTY) - janela de grupo. PartyRACE.spk tem 21 sprites:
# sprite 0 = fundo da janela, sprite 1 = fundo alternativo,
# sprite 2 = faixa de cabecalho, 3-10 = slots de membros (23x23),
# sprite 11+ = botoes/icones. Posicoes NAO confirmadas no C++ nesta pesquisa
# (VS_UI_Party.h nao escaneado), entao os botoes extras ficam enfileirados.
# ---------------------------------------------------------------------------
_PARTY_RACE_SPK = {"SLAYER": "PartySlayer.spk", "VAMPIRE": "PartyVampire.spk",
                    "OUSTERS": "PartyOusters.spk"}


def _party_assets(doc, race="SLAYER"):
    fname = _PARTY_RACE_SPK.get(race, _PARTY_RACE_SPK["SLAYER"])
    assets = [Asset("WINDOW", "Fundo da janela", fname, 0, [(0, 0)], is_background=True)]
    assets.append(Asset("WINDOW_ALT", "Fundo alternativo", fname, 1, [(120, 0)]))
    assets.append(Asset("HEADER", "Faixa do cabecalho", fname, 2, [(0, 0)]))
    for i in range(3, 11):
        assets.append(Asset(f"MEMBER_{i-3}", f"Slot de membro #{i-3}", fname, i, [(4, 30 + (i-3)*26)]))
    return assets


# ---------------------------------------------------------------------------
# GEAR (C_VS_UI_GEAR) - janela de equipamento (paperdoll). GearRACE.spk
# tem o fundo do corpo + slot rings/amuleto. GearSlotRACE.spk tem os slots
# individuais (arma, armadura, capacete, luvas, bota, escudo, capa, brinco).
# Confirmado: VS_UI_GameCommon.h:300-450 (enums GEAR_SPK), VS_UI_Game.cpp.
# ---------------------------------------------------------------------------
_GEAR_RACE_SPK = {"SLAYER": "GearSlayer.spk", "VAMPIRE": "GearVampire.spk",
                   "OUSTERS": "GearOusters.spk"}
_GEAR_SLOT_RACE_SPK = {"SLAYER": "GearSlotSlayer.spk", "VAMPIRE": "GearSlotVampire.spk",
                         "OUSTERS": "GearSlotOusters.spk"}

# Posicoes aproximadas dos slots no paperdoll (valores classicos, SEM
# confirmacao exata no C++ - sao calculadas vs gear window rect)
_GEAR_SLOT_POS = {
    "SLAYER": {"HELMET": (100, 21), "ARMOR": (100, 66), "GLOVE": (19, 130),
               "BOOT": (100, 166), "WEAPON": (15, 43), "SHIELD": (164, 43),
               "CAPE": (164, 97), "AMULET": (97, 200), "RING1": (55, 218),
               "RING2": (140, 218), "EARRING": (97, 240)},
    "VAMPIRE": {"HELMET": (100, 21), "ARMOR": (100, 66), "GLOVE": (19, 130),
                "BOOT": (100, 166), "WEAPON": (15, 43), "SHIELD": (164, 43),
                "CAPE": (164, 97), "AMULET": (97, 200), "RING1": (55, 218),
                "RING2": (140, 218), "EARRING": (97, 240)},
    "OUSTERS": {"HELMET": (100, 21), "ARMOR": (100, 66), "GLOVE": (19, 130),
                "BOOT": (100, 166), "WEAPON": (15, 43), "SHIELD": (164, 43),
                "CAPE": (164, 97), "AMULET": (97, 210), "RING1": (55, 228),
                "RING2": (140, 228), "EARRING": (97, 250)},
}

# Indices de sprite dentro do GearSlotRACE.spk pra cada slot
_GEAR_SLOT_SPRITES = {
    "HELMET": 0, "ARMOR": 1, "GLOVE": 2, "BOOT": 3, "WEAPON": 5,
    "SHIELD": 4, "CAPE": 6, "AMULET": 7, "RING1": 8, "RING2": 8,
    "EARRING": 9,
}

_GEAR_SLOT_LABELS = {
    "HELMET": "Capacete", "ARMOR": "Armadura", "GLOVE": "Luvas",
    "BOOT": "Botas", "WEAPON": "Arma", "SHIELD": "Escudo",
    "CAPE": "Capa", "AMULET": "Amuleto", "RING1": "Anel 1",
    "RING2": "Anel 2", "EARRING": "Brinco",
}


def _gear_assets(doc, race="SLAYER"):
    fname = _GEAR_RACE_SPK.get(race, _GEAR_RACE_SPK["SLAYER"])
    sfname = _GEAR_SLOT_RACE_SPK.get(race, _GEAR_SLOT_RACE_SPK["SLAYER"])
    assets = [Asset("BODY", f"Fundo do personagem ({race})", fname, 0, [(0, 0)], is_background=True)]
    if race == "SLAYER":
        assets.append(Asset("BODY_ADV", "Fundo (Advancement)", fname, 1, [(0, 0)]))
    for slot_key, sprite_idx in _GEAR_SLOT_SPRITES.items():
        pos = _GEAR_SLOT_POS.get(race, _GEAR_SLOT_POS["SLAYER"]).get(slot_key, (50, 50))
        label = _GEAR_SLOT_LABELS.get(slot_key, slot_key)
        assets.append(Asset(f"SLOT_{slot_key}", f"Slot: {label}", sfname, sprite_idx, [pos],
                            is_background=True))
    return assets


# ---------------------------------------------------------------------------
# EFFECT_STATUS - janela de efeitos ativos no personagem (buffs/debuffs).
# EffectStatusRACE.spk: 19 sprites - sprite 0 = moldura exterior,
# 1-3 = bordas, 4+ = icones de efeito (18x18).
# ---------------------------------------------------------------------------
_EFFECT_STATUS_RACE_SPK = {"SLAYER": "EffectStatusSlayer.spk", "VAMPIRE": "EffectStatusVampire.spk",
                            "OUSTERS": "EffectStatusOusters.spk"}


def _effect_status_assets(doc, race="SLAYER"):
    fname = _EFFECT_STATUS_RACE_SPK.get(race, _EFFECT_STATUS_RACE_SPK["SLAYER"])
    assets = [Asset("FRAME", "Moldura exterior", fname, 0, [(0, 0)], is_background=True)]
    assets.append(Asset("BORDER_T", "Borda superior", fname, 1, [(0, 0)]))
    assets.append(Asset("BORDER_L", "Borda esquerda", fname, 2, [(0, 0)]))
    assets.append(Asset("BORDER_R", "Borda direita", fname, 3, [(0, 0)]))
    for i in range(4, min(19, 4 + 8)):
        assets.append(Asset(f"ICON_{i}", f"Icone de efeito #{i-3}", fname, i, [(6 + (i-4)*24, 30)]))
    return assets


# ---------------------------------------------------------------------------
# QUEST (C_VS_UI_QUEST) - janela de missoes/quests. QuestManager_RACE.spk:
# 18 sprites - sprite 0 = fundo da janela, 1-2 = abas (Recebidas/Completas),
# 3-8 = botoes de categoria, 9-11 = linhas de quest (267x20), etc.
# VS_UI_QuestManager.h, VS_UI_QuestManager.cpp.
# ---------------------------------------------------------------------------
_QUEST_RACE_SPK = {"SLAYER": "QuestManager_Slayer.spk", "VAMPIRE": "QuestManager_Vampire.spk",
                    "OUSTERS": "QuestManager_Ousters.spk"}

_QUEST_TAB_LABELS = {1: "Aba Recebidas", 2: "Aba Completas"}
_QUEST_CAT_LABELS = {3: "Categoria 1", 4: "Categoria 2", 5: "Categoria 3",
                      6: "Categoria 4", 7: "Categoria 5", 8: "Categoria 6"}


def _quest_assets(doc, race="SLAYER"):
    fname = _QUEST_RACE_SPK.get(race, _QUEST_RACE_SPK["SLAYER"])
    assets = [Asset("WINDOW", "Fundo da janela", fname, 0, [(0, 0)], is_background=True)]
    for idx, label in _QUEST_TAB_LABELS.items():
        assets.append(Asset(f"TAB_{idx}", label, fname, idx, [(10 + (idx-1) * 120, 5)]))
    for idx, label in _QUEST_CAT_LABELS.items():
        assets.append(Asset(f"CAT_{idx}", label, fname, idx, [(10, 30 + (idx-3) * 20)]))
    for i in range(9, 12):
        assets.append(Asset(f"LINE_{i}", f"Linha de quest #{i-8}", fname, i, [(10, 160 + (i-9) * 22)]))
    return assets


# ---------------------------------------------------------------------------
# MAILBOX - janela de correio. MailBox.spk: 26 sprites - icones de carta
# (14x11 a 40x27), botoes, linhas de lista. Nao e' por raca.
# ---------------------------------------------------------------------------
def _mailbox_assets(doc, race="SLAYER"):
    fname = "MailBox.spk"
    assets = [Asset("ICON_NEW", "Icone carta nova", fname, 0, [(0, 0)]),
              Asset("ICON_READ", "Icone carta lida", fname, 1, [(20, 0)]),
              Asset("BTN_WRITE_N", "Botao Escrever (normal)", fname, 2, [(40, 0)]),
              Asset("BTN_WRITE_P", "Botao Escrever (pressionado)", fname, 3, [(80, 0)]),
              Asset("BTN_DEL_N", "Botao Excluir (normal)", fname, 4, [(120, 0)]),
              Asset("BTN_DEL_P", "Botao Excluir (pressionado)", fname, 5, [(160, 0)]),
              Asset("BTN_REPLY_N", "Botao Responder (normal)", fname, 6, [(200, 0)]),
              Asset("BTN_REPLY_P", "Botao Responder (pressionado)", fname, 7, [(240, 0)])]
    for i in range(8, 12):
        assets.append(Asset(f"ROW_{i}", f"Linha de carta #{i-7}", fname, i, [(10, 40 + (i-8) * 22)]))
    return assets


# ---------------------------------------------------------------------------
# EXCHANGE / TRADE - janela de troca entre jogadores. ExchangeRACE.spk:
# 2 sprites: sprite 0 = fundo da janela, sprite 1 = slot de item (30x30).
# So' Slayer e Ousters tem arquivo (Vampire reusa de outra forma).
# VS_UI_Exchange.cpp.
# ---------------------------------------------------------------------------
_EXCHANGE_RACE_SPK = {"SLAYER": "ExchangeSlayer.spk", "OUSTERS": "ExchangeOusters.spk",
                       "VAMPIRE": "ExchangeSlayer.spk"}


def _exchange_assets(doc, race="SLAYER"):
    fname = _EXCHANGE_RACE_SPK.get(race, _EXCHANGE_RACE_SPK["SLAYER"])
    return [Asset("WINDOW", "Fundo da janela", fname, 0, [(0, 0)], is_background=True),
            Asset("SLOT", "Slot de item", fname, 1, [(20, 40)])]


# ---------------------------------------------------------------------------
# TRANSMIT - janela de transmissoes/skills passivas. transmitRACE.spk:
# 12 sprites - fundo + botoes de slot (58x20) + icones de transmisao.
# ---------------------------------------------------------------------------
_TRANSMIT_RACE_SPK = {"SLAYER": "transmitSlayer.spk", "VAMPIRE": "transmitVampire.spk",
                       "OUSTERS": "transmitOusters.spk"}


def _transmit_assets(doc, race="SLAYER"):
    fname = _TRANSMIT_RACE_SPK.get(race, _TRANSMIT_RACE_SPK["SLAYER"])
    assets = [Asset("WINDOW", "Fundo da janela", fname, 0, [(0, 0)], is_background=True)]
    for i in range(1, 10):
        assets.append(Asset(f"SLOT_{i}", f"Slot de transmisao #{i}", fname, i, [(10, 30 + (i-1) * 24)]))
    if race == "OUSTERS":
        assets.append(Asset("SLOT_SPECIAL", "Slot especial (Ousters)", fname, 1, [(10, 260)]))
    return assets


# ---------------------------------------------------------------------------
# WORLD MAP - mapa mundial. WorldMap.spk: 33 sprites - sprite 0 = mapa
# (746x571), 1-3 = icones de localizacao (14x14), 4-11 = legendas/placas
# (102x52), 12+ = detalhes. WorldMapIcon.spk: 4 icones de 7x11.
# ---------------------------------------------------------------------------
def _worldmap_assets(doc, race="SLAYER"):
    fname = "WorldMap.spk"
    assets = [Asset("MAP", "Mapa mundial", fname, 0, [(0, 0)], is_background=True),
              Asset("ICON_DOT", "Ponto de localizacao", fname, 1, [(373, 285)]),
              Asset("ICON_ARROW", "Seta de direcao", fname, 2, [(400, 300)]),
              Asset("ICON_TARGET", "Alvo de quest", fname, 3, [(420, 310)])]
    for i in range(4, 8):
        assets.append(Asset(f"LEGEND_{i}", f"Legenda #{i-3}", fname, i, [(10, 400 + (i-4) * 55)]))
    return assets


# ---------------------------------------------------------------------------
# SERVER SELECT - tela de selecao de servidor. ServerSelect.spk:
# 11 sprites - sprite 0 = fundo (426x348), 1-2 = botoes de canal, 3+ = setas.
# ---------------------------------------------------------------------------
def _server_select_assets(doc, race="SLAYER"):
    fname = "ServerSelect.spk"
    assets = [Asset("BG", "Fundo da janela", fname, 0, [(0, 0)], is_background=True),
              Asset("CHANNEL_N", "Canal (normal)", fname, 1, [(30, 40)]),
              Asset("CHANNEL_P", "Canal (pressionado)", fname, 2, [(30, 80)]),
              Asset("ARROW_UP", "Seta para cima", fname, 3, [(200, 20)]),
              Asset("ARROW_DOWN", "Seta para baixo", fname, 4, [(200, 200)])]
    return assets


# ---------------------------------------------------------------------------
# FRIEND - lista de amigos/messenger. RACEFriend.spk: 21 sprites -
# sprite 0 = fundo da janela, 1-6 = botoes de estado, 7 = scrollbar,
# 8+ = icones de status (online/offline/ausente).
# ---------------------------------------------------------------------------
_FRIEND_RACE_SPK = {"SLAYER": "SlayerFriend.spk", "VAMPIRE": "VampireFriend.spk",
                     "OUSTERS": "OustersFriend.spk"}


def _friend_assets(doc, race="SLAYER"):
    fname = _FRIEND_RACE_SPK.get(race, _FRIEND_RACE_SPK["SLAYER"])
    assets = [Asset("WINDOW", "Fundo da janela", fname, 0, [(0, 0)], is_background=True)]
    btn_labels = ["Adicionar", "Remover", "Messenger"]
    for i, label in enumerate(btn_labels):
        assets.append(Asset(f"BTN_N_{i}", f"Botao {label} (normal)", fname, 1 + i*3, [(10, 150 + i*24)]))
        assets.append(Asset(f"BTN_P_{i}", f"Botao {label} (pressionado)", fname, 2 + i*3, [(10, 151 + i*24)]))
    assets.append(Asset("SCROLL", "Barra de scroll", fname, 7, [(95, 155)]))
    for i in range(8, 13):
        assets.append(Asset(f"STATUS_{i}", f"Icone de status #{i-7}", fname, i, [(8, 10 + (i-8)*16)]))
    return assets


# ---------------------------------------------------------------------------
# PERSONAL SHOP - loja pessoal (NPC mercantil). RACEPersnalShop.spk:
# 10 sprites - sprite 0 = placa "loja", 1-3 = abas, 4-9 = botoes de item.
# ---------------------------------------------------------------------------
_PERSONAL_SHOP_RACE_SPK = {"SLAYER": "SlayerPersnalShop.spk", "VAMPIRE": "VampirePersnalShop.spk",
                            "OUSTERS": "OustersPersnalShop.spk"}


def _personal_shop_assets(doc, race="SLAYER"):
    fname = _PERSONAL_SHOP_RACE_SPK.get(race, _PERSONAL_SHOP_RACE_SPK["SLAYER"])
    assets = [Asset("SIGN", "Placa da loja", fname, 0, [(0, 0)], is_background=True)]
    tab_labels = ["Vender", "Comprar", "Gerenciar"]
    for i, label in enumerate(tab_labels):
        assets.append(Asset(f"TAB_{i}", f"Aba {label}", fname, 1 + i, [(10 + i*100, 45)]))
    for i in range(4, 10):
        assets.append(Asset(f"SLOT_{i}", f"Slot #{i-3}", fname, i, [(10 + (i-4)*46, 80)]))
    return assets


# ---------------------------------------------------------------------------
# BLOODBURST - efeito/animacao de Blood Burst. BloodBurstRACE.spk:
# 44 sprites - bordas e cantos para efeito de transicao de tela.
# Efeito visual, nao uma janela de UI interativa.
# ---------------------------------------------------------------------------
_BLOODBURST_RACE_SPK = {"SLAYER": "BloodBurstSlayer.spk", "VAMPIRE": "BloodBurstVampire.spk",
                         "OUSTERS": "BloodBurstOusters.spk"}


def _bloodburst_assets(doc, race="SLAYER"):
    fname = _BLOODBURST_RACE_SPK.get(race, _BLOODBURST_RACE_SPK["SLAYER"])
    assets = [Asset("BAR_TOP", "Barra superior", fname, 0, [(0, 0)], is_background=True),
              Asset("BAR_LEFT", "Barra esquerda", fname, 1, [(0, 0)]),
              Asset("BAR_BOTTOM", "Barra inferior", fname, 2, [(0, 580)]),
              Asset("BAR_RIGHT", "Barra direita", fname, 3, [(780, 0)])]
    for i in range(4, 8):
        assets.append(Asset(f"CORNER_{i}", f"Canto #{i-3}", fname, i, [(0, 0)]))
    return assets


# ---------------------------------------------------------------------------
# TUTORIAL BOOK / BOOKCASE / COMPUTER - sistema de tutorial do jogo.
# TutorialBook.spk: livro (643x468) + botoes. TutorialBookcase.spk:
# estante com 259 sprites. TutorialComputer.spk: computador (465x437).
# ---------------------------------------------------------------------------
def _tutorial_book_assets(doc, race="SLAYER"):
    fname = "TutorialBook.spk"
    return [Asset("BOOK", "Livro de tutorial", fname, 0, [(0, 0)], is_background=True),
            Asset("BTN_NEXT", "Botao Proxima pagina", fname, 1, [(580, 420)]),
            Asset("ICON_DOT", "Ponto marcador", fname, 2, [(300, 300)]),
            Asset("ICON_DOT_2", "Ponto marcador 2", fname, 3, [(320, 300)])]


def _tutorial_computer_assets(doc, race="SLAYER"):
    fname = "TutorialComputer.spk"
    return [Asset("COMPUTER", "Computador do tutorial", fname, 0, [(0, 0)], is_background=True),
            Asset("LIGHT", "Luz indicadora", fname, 1, [(220, 60)]),
            Asset("TAB_1", "Aba 1", fname, 2, [(50, 30)]),
            Asset("TAB_2", "Aba 2", fname, 3, [(180, 30)])]


# ---------------------------------------------------------------------------
# POWERJJANG - janela de itens especiais/power-up. Powerjjang_RACE.spk:
# 4 sprites: sprite 0 = placa/fundo (175x40), 1-3 = slots de item (56-63x27-34).
# ---------------------------------------------------------------------------
_POWERJJANG_RACE_SPK = {"SLAYER": "Powerjjang_Slayer.spk", "VAMPIRE": "Powerjjang_Vampire.spk",
                         "OUSTERS": "Powerjjang_Ousters.spk"}


def _powerjjang_assets(doc, race="SLAYER"):
    fname = _POWERJJANG_RACE_SPK.get(race, _POWERJJANG_RACE_SPK["SLAYER"])
    return [Asset("PLATE", "Placa Powerjjang", fname, 0, [(0, 0)], is_background=True),
            Asset("SLOT_1", "Slot de item 1", fname, 1, [(10, 42)]),
            Asset("SLOT_2", "Slot de item 2", fname, 2, [(70, 42)]),
            Asset("SLOT_3", "Slot de item 3", fname, 3, [(130, 42)])]


# ---------------------------------------------------------------------------
# BULLETIN BOARD - quadro de avisos. BulletinBoard.spk: 7 sprites -
# sprite 0 = fundo (208x143), 1-6 = botoes de pagina (9x9, 10x10).
# ---------------------------------------------------------------------------
def _bulletin_board_assets(doc, race="SLAYER"):
    fname = "BulletinBoard.spk"
    return [Asset("BOARD", "Quadro de avisos", fname, 0, [(0, 0)], is_background=True),
            Asset("PAGE_UP", "Pagina anterior", fname, 1, [(95, 130)]),
            Asset("PAGE_DOWN", "Proxima pagina", fname, 2, [(105, 130)]),
            Asset("CLOSE_N", "Fechar (normal)", fname, 3, [(195, 5)]),
            Asset("CLOSE_P", "Fechar (pressionado)", fname, 4, [(205, 5)])]


# ---------------------------------------------------------------------------
# PORTAL / TELEPORT - janela de teletransporte. PortalMapRACE.spk:
# 6-12 sprites de mapas (200x100 cada). PortalEtcRACE.spk: botoes/icones.
# ---------------------------------------------------------------------------
_PORTAL_MAP_RACE_SPK = {"SLAYER": "PortalMapSlayer.spk", "OUSTERS": "PortalMapOusters.spk",
                         "VAMPIRE": "PortalMapSlayer.spk"}
_PORTAL_ETC_RACE_SPK = {"SLAYER": "PortalEtcSlayer.spk", "OUSTERS": "PortalEtcOusters.spk",
                         "VAMPIRE": "PortalEtcSlayer.spk"}


def _portal_assets(doc, race="SLAYER"):
    mfname = _PORTAL_MAP_RACE_SPK.get(race, _PORTAL_MAP_RACE_SPK["SLAYER"])
    efname = _PORTAL_ETC_RACE_SPK.get(race, _PORTAL_ETC_RACE_SPK["SLAYER"])
    assets = []
    for i in range(6):
        assets.append(Asset(f"MAP_{i}", f"Mapa de portal #{i}", mfname, i, [(0, i * 105)], is_background=True))
    assets.append(Asset("BTN_OK", "Botao OK", efname, 0, [(300, 250)]))
    assets.append(Asset("BTN_CANCEL", "Botao Cancelar", efname, 1, [(365, 250)]))
    return assets


# ---------------------------------------------------------------------------
# LOTTERY - bilhete de loteria/raspadinha. LotteryCard.spk: 32 sprites -
# sprite 0 = fundo do bilhete (235x220), 1 = faixa, 2 = area do premio,
# 3-8 = botoes numericos, 9+ = simbolos de premio.
# ---------------------------------------------------------------------------
def _lottery_assets(doc, race="SLAYER"):
    fname = "LotteryCard.spk"
    return [Asset("CARD", "Bilhete de loteria", fname, 0, [(0, 0)], is_background=True),
            Asset("BANNER", "Faixa do bilhete", fname, 1, [(0, 0)]),
            Asset("PRIZE_AREA", "Area do premio", fname, 2, [(5, 18)])]


# ---------------------------------------------------------------------------
# CREDIT - tela de creditos. Credit.spk: 3 sprites -
# sprite 0 = fundo (800x600), 1 = lista de creditos (368x2175),
# 2 = moldura (374x46).
# ---------------------------------------------------------------------------
def _credit_assets(doc, race="SLAYER"):
    fname = "Credit.spk"
    return [Asset("BG", "Fundo dos creditos", fname, 0, [(0, 0)], is_background=True),
            Asset("TEXT", "Texto dos creditos", fname, 1, [(216, 0)]),
            Asset("FRAME", "Moldura", fname, 2, [(213, 0)])]


# ---------------------------------------------------------------------------
# FACE - selecao de rostos (criacao de personagem). Face.spk: 9 sprites
# (55x70 cada) - os 9 rostos disponiveis. FaceMake.spk: 9 sprites (110x139)
# - versao ampliada dos rostos. FaceParty.spk: 9 icones de face (30x38)
# para a janela de grupo. Nao sao por raca.
# ---------------------------------------------------------------------------
def _face_make_assets(doc, race="SLAYER"):
    return [Asset("FACE_MAKE", "Rosto ampliado (FaceMake.spk)", "FaceMake.spk", 0, [(0, 0)], is_background=True)]


def _face_party_assets(doc, race="SLAYER"):
    return [Asset("FACE_PARTY", "Icone de face (FaceParty.spk)", "FaceParty.spk", 0, [(0, 0)], is_background=True)]


# ---------------------------------------------------------------------------
# MAIN BUTTON - botoes principais do jogo (MainRACE.spk). 7-10 sprites:
# sprite 0 = painel de botoes (178x164), 1-2 = setas, 3-4 = botoes de menu,
# 5+ = detalhes. VS_UI_Main.h, VS_UI_Game.cpp.
# ---------------------------------------------------------------------------
_MAIN_BUTTON_RACE_SPK = {"SLAYER": "MainSlayer.spk", "VAMPIRE": "MainVampire.spk",
                          "OUSTERS": "MainOusters.spk"}


def _main_button_assets(doc, race="SLAYER"):
    fname = _MAIN_BUTTON_RACE_SPK.get(race, _MAIN_BUTTON_RACE_SPK["SLAYER"])
    return [Asset("PANEL", "Painel de botoes", fname, 0, [(0, 0)], is_background=True),
            Asset("ARROW_DOWN", "Seta para baixo", fname, 1, [(80, 140)]),
            Asset("ARROW_UP", "Seta para cima", fname, 2, [(80, 155)])]


# ---------------------------------------------------------------------------
# SKILL ETC - icones diversos de skill. SkillEtcRACE.spk: 3 sprites -
# sprite 0 = moldura (42x42), 1-2 = icones de bloqueio/cancelamento.
# ---------------------------------------------------------------------------
_SKILL_ETC_RACE_SPK = {"SLAYER": "SkillEtcSlayer.spk", "VAMPIRE": "SkillEtcVampire.spk",
                        "OUSTERS": "SkillEtcOusters.spk"}


def _skill_etc_assets(doc, race="SLAYER"):
    fname = _SKILL_ETC_RACE_SPK.get(race, _SKILL_ETC_RACE_SPK["SLAYER"])
    return [Asset("FRAME", "Moldura de skill (42x42)", fname, 0, [(0, 0)], is_background=True),
            Asset("LOCK", "Icone de bloqueio", fname, 1, [(4, 4)]),
            Asset("CANCEL", "Icone de cancelamento", fname, 2, [(4, 26)])]


# ---------------------------------------------------------------------------
# NAMING - sistema de nomenclatura (nomes de itens/personagens).
# NamingRACE.spk: 4 sprites de 56-81x11-12 - prefixos/sufixos de nome.
# ---------------------------------------------------------------------------
_NAMING_RACE_SPK = {"SLAYER": "NamingSlayer.spk", "VAMPIRE": "NamingVampire.spk",
                     "OUSTERS": "NamingOusters.spk"}


def _naming_assets(doc, race="SLAYER"):
    fname = _NAMING_RACE_SPK.get(race, _NAMING_RACE_SPK["SLAYER"])
    return [Asset("PREFIX_1", "Prefixo de nome 1", fname, 0, [(0, 0)]),
            Asset("PREFIX_2", "Prefixo de nome 2", fname, 1, [(60, 0)]),
            Asset("SUFFIX_1", "Sufixo de nome 1", fname, 2, [(0, 15)]),
            Asset("SUFFIX_2", "Sufixo de nome 2", fname, 3, [(60, 15)])]


# =============================================================================
# RODADA 2 DE EXPANSAO (continuacao 2026-07-23)
# AssembleMessageBox, OptionTitle, Progress, Elevator, Symbol, XMasCard,
# WebBrowser, NpcFace, ScrollBar, ArrowTile, UseGrade, Question, FileDialog
# =============================================================================

# ---------------------------------------------------------------------------
# ASSEMBLE_MESSAGE_BOX - janela de dialogo/mensagem generica do jogo.
# AssembleMessageBox.spk: 8 sprites de moldura (bordas 9-patch 382x286).
# AssembleMessageBoxRACE.spk: 10-12 sprites de fundo (799x600) por raca.
# AssembleMessageBoxButtonRACE.spk: 55 sprites de botoes (60x29) por raca.
# Usado em: loja, quest, popups de confirmacao - dialogo generico.
# VS_UI_AssembleMessageBox.h/.cpp.
# ---------------------------------------------------------------------------
_ASSEMBLE_BOX_BTN_RACE = {"SLAYER": "AssembleMessageBoxButtonSlayer.spk",
                           "VAMPIRE": "AssembleMessageBoxButtonVampire.spk",
                           "OUSTERS": "AssembleMessageBoxButtonOusters.spk"}
_ASSEMBLE_BOX_RACE = {"SLAYER": "AssembleMessageBoxSlayer.spk",
                       "VAMPIRE": "AssembleMessageBoxVampire.spk",
                       "OUSTERS": "AssembleMessageBoxOusters.spk"}


def _assemble_msgbox_assets(doc, race="SLAYER"):
    frame_fname = "AssembleMessageBox.spk"
    bg_fname = _ASSEMBLE_BOX_RACE.get(race, _ASSEMBLE_BOX_RACE["SLAYER"])
    btn_fname = _ASSEMBLE_BOX_BTN_RACE.get(race, _ASSEMBLE_BOX_BTN_RACE["SLAYER"])
    assets = [
        Asset("FRAME_TL", "Moldura top-left", frame_fname, 0, [(0, 0)], is_background=True),
        Asset("FRAME_TR", "Moldura top-right", frame_fname, 1, [(379, 0)], is_background=True),
        Asset("FRAME_BL", "Moldura bottom-left", frame_fname, 2, [(0, 283)], is_background=True),
        Asset("FRAME_BR", "Moldura bottom-right", frame_fname, 3, [(379, 283)], is_background=True),
    ]
    for i in range(2):  # First 2 backgrounds
        assets.append(Asset(f"BG_{i}", f"Fundo #{i} ({race})", bg_fname, i, [(0, 0)], is_background=True))
    for i in range(3):
        assets.append(Asset(f"BTN_{i}", f"Botao #{i+1} (normal)", btn_fname, i, [(50 + i*90, 250)]))
        assets.append(Asset(f"BTN_{i}_P", f"Botao #{i+1} (pressionado)", btn_fname, i+10, [(50 + i*90, 251)]))
    return assets


# ---------------------------------------------------------------------------
# OPTION_TITLE - dialogo de opcoes da TELA DE TITULO (antes do login).
# Diferente do OPTION (dentro do jogo, por raca) - este e' o dialogo que
# abre quando clica "Option" no menu principal. OptionTitle.spk: 21 sprites
# com fundo (366x309) + abas/botoes (66x21). OptionTitleScroll.spk: scroll.
# VS_UI_Title.cpp: C_VS_UI_OPTION, caminho m_IsTitle==true.
# ---------------------------------------------------------------------------
def _option_title_assets(doc, race="SLAYER"):
    fname = "OptionTitle.spk"
    sfname = "OptionTitleScroll.spk"
    assets = [Asset("BG", "Fundo do dialogo", fname, 0, [(0, 0)], is_background=True),
              Asset("TITLE", "Faixa de titulo", fname, 1, [(56, 8)])]
    tab_labels = ["Atalho", "Tela", "Som", "Jogo"]
    for i, label in enumerate(tab_labels):
        assets.append(Asset(f"TAB_{i}_N", f"Aba {label} (normal)", fname, 2+i, [(12 + i*66, 48)]))
        assets.append(Asset(f"TAB_{i}_P", f"Aba {label} (pressionada)", fname, 6+i, [(12 + i*66, 49)]))
    assets.append(Asset("SCROLL", "Barra de scroll", sfname, 0, [(320, 80)], is_background=True))
    for i in range(1, 8):
        assets.append(Asset(f"SCROLL_DOT_{i}", f"Ponto scroll #{i}", sfname, i, [(340, 80 + i*16)]))
    return assets


# ---------------------------------------------------------------------------
# PROGRESS / LOADING - tela de progresso/carregamento. Progress.spk:
# 5 sprites: sprite 0 = fundo (796x596), 1 = texto "Now Loading",
# 2 = Preview de cena, 3 = barra de progresso, 4 = luz da barra.
# ---------------------------------------------------------------------------
def _progress_assets(doc, race="SLAYER"):
    fname = "Progress.spk"
    fname_w = "Progress_1024.spk"
    return [Asset("BG", 'Fundo "Now Loading"', fname, 0, [(0, 0)], is_background=True),
            Asset("TITLE", 'Texto "Now Loading"', fname, 1, [(225, 520)]),
            Asset("PREVIEW", "Preview da cena", fname, 2, [(190, 180)]),
            Asset("BAR", "Barra de progresso", fname, 3, [(200, 560)]),
            Asset("GLOW", "Brilho da barra", fname, 4, [(200, 560)]),
            Asset("BG_WIDE", "Fundo 1024x768", fname_w, 0, [(0, 0)], is_background=True)]


# ---------------------------------------------------------------------------
# ELEVATOR - UI de elevador/transporte. Elevator.spk: 7 sprites -
# sprite 0 = fundo (173x347), 1-2 = botoes de andar (55x54),
# 3-6 = indicadores de andar (88x46). VS_UI_Elevator.cpp.
# ---------------------------------------------------------------------------
def _elevator_assets(doc, race="SLAYER"):
    fname = "Elevator.spk"
    return [Asset("BG", "Fundo do elevador", fname, 0, [(0, 0)], is_background=True),
            Asset("FLOOR_UP", "Botao subir", fname, 1, [(58, 50)]),
            Asset("FLOOR_DOWN", "Botao descer", fname, 2, [(58, 110)]),
            Asset("INDICATOR_1", "Indicador andar 1", fname, 3, [(43, 180)]),
            Asset("INDICATOR_2", "Indicador andar 2", fname, 4, [(43, 230)]),
            Asset("INDICATOR_3", "Indicador andar 3", fname, 5, [(43, 280)]),
            Asset("INDICATOR_4", "Indicador andar 4", fname, 6, [(43, 330)])]


# ---------------------------------------------------------------------------
# SYMBOL - simbolos/selos de UI. Symbol.spk: 8 sprites de 152x364 cada -
# cada um e' um conjunto de simbolos diferentes (runas/selos/emblemas).
# ---------------------------------------------------------------------------
def _symbol_assets(doc, race="SLAYER"):
    fname = "Symbol.spk"
    assets = []
    for i in range(8):
        assets.append(Asset(f"SYMBOL_{i}", f"Simbolo #{i+1}", fname, i, [(0, i * 366)]))
    return assets


# ---------------------------------------------------------------------------
# XMAS_CARD - cartao especial de natal/evento. XMasCard.spk: 7 sprites -
# sprite 0 = fundo do cartao (218x156), 1-6 = adesivos/decoracoes (29x37).
# ---------------------------------------------------------------------------
def _xmas_card_assets(doc, race="SLAYER"):
    fname = "XMasCard.spk"
    return [Asset("CARD", "Cartao de natal", fname, 0, [(0, 0)], is_background=True),
            Asset("STICKER_1", "Adesivo 1", fname, 1, [(10, 10)]),
            Asset("STICKER_2", "Adesivo 2", fname, 2, [(50, 10)]),
            Asset("STICKER_3", "Adesivo 3", fname, 3, [(90, 10)]),
            Asset("STICKER_4", "Adesivo 4", fname, 4, [(130, 10)]),
            Asset("STICKER_5", "Adesivo 5", fname, 5, [(170, 10)]),
            Asset("STICKER_6", "Adesivo 6", fname, 6, [(10, 55)])]


# ---------------------------------------------------------------------------
# WEBBROWSER - navegador web interno (para paginas de evento/noticia).
# Webbrowser.spk: 4 sprites - sprite 0 = fundo (800x600),
# 1-3 = botoes de navegacao (35x19). VS_UI_WebBrowser.cpp.
# ---------------------------------------------------------------------------
def _webbrowser_assets(doc, race="SLAYER"):
    fname = "webbrowser.spk"
    return [Asset("BG", "Fundo do navegador", fname, 0, [(0, 0)], is_background=True),
            Asset("BTN_BACK", "Botao Voltar", fname, 1, [(10, 8)]),
            Asset("BTN_FWD", "Botao Avancar", fname, 2, [(50, 8)]),
            Asset("BTN_REFRESH", "Botao Atualizar", fname, 3, [(90, 8)])]


# ---------------------------------------------------------------------------
# NPC_FACE - retratos de NPC (usados em dialogos/lojas/quests).
# NpcFace.spk: 101 sprites - sprite 0 = moldura (144x177),
# 1-100 = rostos de NPC (109x140 cada, 10x10 grid).
# Confirmado: VS_UI_NpcEvent.cpp, NpcFace.h.
# ---------------------------------------------------------------------------
def _npc_face_assets(doc, race="SLAYER"):
    fname = "NpcFace.spk"
    return [Asset("FRAME", "Moldura do retrato", fname, 0, [(0, 0)], is_background=True),
            Asset("FACE_1", "Retrato NPC #1", fname, 1, [(17, 18)]),
            Asset("FACE_2", "Retrato NPC #2", fname, 2, [(17, 18)]),
            Asset("FACE_3", "Retrato NPC #3", fname, 3, [(17, 18)])]


# ---------------------------------------------------------------------------
# UI COMPONENTS (elementos pequenos compartilhados) - agrupa varios SPKs
# de componentes que sao muito pequenos pra' ser uma "tela" propria:
# ScrollBar, UseGrade, Question, ArrowTile, FileDialog, ComboCnt.
# ---------------------------------------------------------------------------
def _ui_components_assets(doc, race="SLAYER"):
    return [
        Asset("SCROLL_VBAR", "Barra de scroll vertical", "ScrollBar.spk", 0, [(0, 0)], is_background=True),
        Asset("SCROLL_THUMB", "Thumb do scroll", "ScrollBar.spk", 1, [(0, 550)]),
        Asset("SCROLL_UP", "Seta p/ cima", "ScrollBar.spk", 2, [(0, 570)]),
        Asset("SCROLL_DOWN", "Seta p/ baixo", "ScrollBar.spk", 3, [(0, 590)]),
        Asset("USEGRADE_N", "Grade de item (normal)", "UseGrade.spk", 0, [(50, 0)]),
        Asset("USEGRADE_HL", "Grade de item (destaque)", "UseGrade.spk", 1, [(100, 0)]),
        Asset("QUESTION", "Ponto de interrogacao", "Question.spk", 0, [(150, 0)]),
        Asset("FILEDIALOG_FOLDER", "Icone pasta", "FileDialog.spk", 0, [(200, 0)]),
        Asset("FILEDIALOG_FILE", "Icone arquivo", "FileDialog.spk", 1, [(220, 0)]),
    ]


# ---------------------------------------------------------------------------
# POWERJJANG_ITEM - botoes/efeitos de item Powerjjang (item especial que
# aparece na tela ao usar). Powerjjang_Item.spk: 7 sprites de 176x32
# cada - diferentes estilos de faixa "POWERJJANG!!".
# ---------------------------------------------------------------------------
def _powerjjang_item_assets(doc, race="SLAYER"):
    fname = "Powerjjang_Item.spk"
    return [Asset(f"BANNER_{i}", f"Faixa Powerjjang #{i+1}", fname, i, [(0, i * 34)]) for i in range(7)]


# ---------------------------------------------------------------------------
# DESCOBERTA: arquivos .spk no cliente que NAO estao em nenhuma tela mapeada
# ---------------------------------------------------------------------------
def _collect_referenced_spk():
    """Retorna set com todos os nomes de arquivo .spk referenciados em
    TODAS as 46 telas/areas do SCREENS. Usado pra descobrir quais .spk
    existem no cliente mas ainda nao tem mapeamento."""
    refs = set()
    for _key, screen in SCREENS.items():
        assets = screen["assets_fn"](None, "SLAYER")
        for a in assets:
            if a.spk_filename:
                refs.add(a.spk_filename)
    return refs


def discover_uncovered_spk(data_dir):
    """Varre Data\\Ui\\spk\\ em busca de arquivos .spk que existem no
    cliente mas NAO estao em nenhuma das 46 telas mapeadas. Retorna
    lista de (nome_arquivo, num_sprites, tamanho_kb) ordenada por nome.
    Retorna [] se o diretorio nao existir ou nao tiver .spk alem dos
    ja' mapeados."""
    spk_dir = os.path.join(data_dir, "Ui", "spk")
    if not os.path.isdir(spk_dir):
        return []
    refs = _collect_referenced_spk()
    uncovered = []
    for fname in sorted(os.listdir(spk_dir)):
        if not fname.lower().endswith(".spk"):
            continue
        # so' o .spk (nao .spki), e ignora se ja' esta' no SCREENS
        if fname in refs:
            continue
        fpath = os.path.join(spk_dir, fname)
        try:
            size_kb = os.path.getsize(fpath) // 1024
            pack = truesprite.TrueSpritePack(fpath)
            num_sprites = getattr(pack, 'count', 0)
        except Exception:
            num_sprites = 0
        uncovered.append((fname, num_sprites, size_kb))
    return sorted(uncovered, key=lambda x: x[0].lower())


# ---------------------------------------------------------------------------
# SCREENS
# ---------------------------------------------------------------------------
SCREENS = {
    "TITLE": {"label": "Tela de Titulo", "needs_race": False, "assets_fn": lambda doc, race: TITLE_ASSETS},
    "LOGIN": {"label": "Popup de Login", "needs_race": False, "assets_fn": lambda doc, race: LOGIN_ASSETS},
    "CHAR_SELECT": {"label": "Selecao de Personagem", "needs_race": False,
                    "assets_fn": lambda doc, race: CHAR_SELECT_ASSETS},
    "OPTION": {"label": "Dialogo de Opcoes", "needs_race": True, "assets_fn": _option_assets},
    "GAME_MENU": {"label": "Menu ESC (dentro do jogo)", "needs_race": True, "assets_fn": _game_menu_assets},
    "STATUS": {"label": "Status do Personagem", "needs_race": True, "assets_fn": _info_assets},
    "INVENTORY": {"label": "Inventario", "needs_race": True, "assets_fn": _inventory_assets},
    "MINIMAP": {"label": "Minimapa", "needs_race": True, "assets_fn": _minimap_assets},
    "HPBAR": {"label": "Barra de HP/MP", "needs_race": True, "assets_fn": _hpbar_assets},
    "QUICKSLOT": {"label": "Barra de Atalhos (Quickslot)", "needs_race": True, "assets_fn": _quickslot_assets},
    "CHATTING": {"label": "Moldura da tela / Chat", "needs_race": True, "assets_fn": _chatting_assets},
    "SHOP": {"label": "Loja de NPC", "needs_race": True, "assets_fn": _shop_assets},
    # === NOVAS TELAS (2026-07-23) ===
    "PARTY": {"label": "Janela de Grupo (Party)", "needs_race": True, "assets_fn": _party_assets},
    "GEAR": {"label": "Equipamento (Paperdoll)", "needs_race": True, "assets_fn": _gear_assets},
    "EFFECT_STATUS": {"label": "Efeitos Ativos (Buffs)", "needs_race": True, "assets_fn": _effect_status_assets},
    "QUEST": {"label": "Missoes/Quests", "needs_race": True, "assets_fn": _quest_assets},
    "MAILBOX": {"label": "Correio (MailBox)", "needs_race": False, "assets_fn": _mailbox_assets},
    "EXCHANGE": {"label": "Troca (Exchange/Trade)", "needs_race": True, "assets_fn": _exchange_assets},
    "TRANSMIT": {"label": "Transmissoes (Passivas)", "needs_race": True, "assets_fn": _transmit_assets},
    "WORLDMAP": {"label": "Mapa Mundial", "needs_race": False, "assets_fn": _worldmap_assets},
    "SERVER_SELECT": {"label": "Selecao de Servidor", "needs_race": False, "assets_fn": _server_select_assets},
    "FRIEND": {"label": "Lista de Amigos", "needs_race": True, "assets_fn": _friend_assets},
    "PERSONAL_SHOP": {"label": "Loja Pessoal (NPC)", "needs_race": True, "assets_fn": _personal_shop_assets},
    "BLOODBURST": {"label": "Blood Burst (efeito)", "needs_race": True, "assets_fn": _bloodburst_assets},
    "TUTORIAL_BOOK": {"label": "Livro de Tutorial", "needs_race": False, "assets_fn": _tutorial_book_assets},
    "TUTORIAL_COMPUTER": {"label": "Computador Tutorial", "needs_race": False, "assets_fn": _tutorial_computer_assets},
    "POWERJJANG": {"label": "Powerjjang (Itens Especiais)", "needs_race": True, "assets_fn": _powerjjang_assets},
    "BULLETIN": {"label": "Quadro de Avisos", "needs_race": False, "assets_fn": _bulletin_board_assets},
    "PORTAL": {"label": "Portal / Teletransporte", "needs_race": True, "assets_fn": _portal_assets},
    "LOTTERY": {"label": "Loteria / Raspadinha", "needs_race": False, "assets_fn": _lottery_assets},
    "CREDIT": {"label": "Tela de Creditos", "needs_race": False, "assets_fn": _credit_assets},
    "FACE_MAKE": {"label": "Rostos (Criacao de Personagem)", "needs_race": False, "assets_fn": _face_make_assets},
    "FACE_PARTY": {"label": "Icones de Rosto (Grupo)", "needs_race": False, "assets_fn": _face_party_assets},
    "MAIN_BUTTON": {"label": "Botoes Principais (Main)", "needs_race": True, "assets_fn": _main_button_assets},
    "SKILL_ETC": {"label": "Icones de Skill (Moldura)", "needs_race": True, "assets_fn": _skill_etc_assets},
    "NAMING": {"label": "Nomenclatura (Prefixos)", "needs_race": True, "assets_fn": _naming_assets},
    # === RODADA 2 (continuacao 2026-07-23) ===
    "ASSEMBLE_MSGBOX": {"label": "Dialogo/Mensagem (MessageBox)", "needs_race": True, "assets_fn": _assemble_msgbox_assets},
    "OPTION_TITLE": {"label": "Opcoes da Tela de Titulo", "needs_race": False, "assets_fn": _option_title_assets},
    "PROGRESS": {"label": "Tela de Progresso/Loading", "needs_race": False, "assets_fn": _progress_assets},
    "ELEVATOR": {"label": "Elevador / Transporte", "needs_race": False, "assets_fn": _elevator_assets},
    "SYMBOL": {"label": "Simbolos / Selos", "needs_race": False, "assets_fn": _symbol_assets},
    "XMAS_CARD": {"label": "Cartao de Natal (Evento)", "needs_race": False, "assets_fn": _xmas_card_assets},
    "WEBBROWSER": {"label": "Navegador Web (Evento)", "needs_race": False, "assets_fn": _webbrowser_assets},
    "NPC_FACE": {"label": "Retratos de NPC", "needs_race": False, "assets_fn": _npc_face_assets},
    "UI_COMPONENTS": {"label": "Componentes de UI (ScrollBar etc)", "needs_race": False, "assets_fn": _ui_components_assets},
    "POWERJJANG_ITEM": {"label": "Powerjjang Item (efeito)", "needs_race": False, "assets_fn": _powerjjang_item_assets},
}


class UiSkinSystem:
    """Fachada: abre .spk sob demanda (Data\\Ui\\spk\\<arquivo>, achado a
    partir da pasta Data do cliente) e da' decode/replace/save por Asset."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        # find_ui_spk() quer a pasta do CLIENTE (pai de "Data"), igual
        # CLIENT_DIR no interface_editor - data_dir e' sempre ".../Data"
        # (mesma convencao de EffectSystem/CreatureSystem neste projeto).
        self.client_dir = os.path.dirname(data_dir)
        self._packs = {}
        self._interface_doc = "not_loaded"  # sentinela - None = tentou e nao achou

    def get_interface_doc(self):
        """Carrega interface.inf (mesmo parser do Interface Editor, so'
        leitura aqui) pra' resolver a posicao AO VIVO dos botoes de OPTION/
        GAME_MENU - None se nao achar nenhuma copia (o preview cai pra'
        posicoes aproximadas nesse caso, ver _option_assets)."""
        if self._interface_doc == "not_loaded":
            self._interface_doc = None
            try:
                from darkeden_interface_editor import InterfaceDocument
            except ImportError:
                return None
            candidates = [
                os.path.join(self.data_dir, "Info", "infodata_EN", "interface.inf"),
                os.path.join(self.data_dir, "Info", "interface.inf"),
                os.path.join(self.data_dir, "Info", "_interface_editor_extract", "interface.inf"),
            ]
            for c in candidates:
                if os.path.isfile(c):
                    doc = InterfaceDocument()
                    doc.load(c)
                    self._interface_doc = doc
                    break
        return self._interface_doc

    def list_assets(self, screen_key, race="SLAYER"):
        screen = SCREENS[screen_key]
        doc = self.get_interface_doc() if screen["needs_race"] else None
        return screen["assets_fn"](doc, race)

    def get_pack(self, spk_filename):
        pack = self._packs.get(spk_filename)
        if pack is None:
            path = truesprite.find_ui_spk(self.client_dir, spk_filename)
            if path is None:
                raise FileNotFoundError(f"{spk_filename} nao encontrado em Data\\Ui\\spk")
            pack = truesprite.TrueSpritePack(path)
            pack.dirty = False
            self._packs[spk_filename] = pack
        return pack

    def try_get_pack(self, spk_filename):
        try:
            return self.get_pack(spk_filename)
        except FileNotFoundError:
            return None

    def decode_asset(self, asset):
        pack = self.try_get_pack(asset.spk_filename)
        if pack is None:
            return 0, 0, b'', b''
        return pack.decode(asset.sprite_index)

    def replace_asset_image(self, asset, image_path, resize_to_original=True):
        pack = self.get_pack(asset.spk_filename)
        target_size = None
        if resize_to_original:
            w, h, _rgb, _mask = pack.decode(asset.sprite_index)
            if w and h:
                target_size = (w, h)
        sprite_bytes, w, h = truesprite.encode_sprite_from_image(image_path, target_size=target_size)
        pack.replace_sprite(asset.sprite_index, sprite_bytes)
        pack.dirty = True
        return w, h

    def export_asset_image(self, asset, out_path):
        from PIL import Image
        w, h, rgb, mask = self.decode_asset(asset)
        if not w or not h:
            raise ValueError("sprite vazio (0x0) - nada pra exportar")
        rgba = bytearray(w * h * 4)
        for i in range(w * h):
            rgba[i * 4:i * 4 + 3] = rgb[i * 3:i * 3 + 3]
            rgba[i * 4 + 3] = mask[i]
        img = Image.frombytes("RGBA", (w, h), bytes(rgba))
        img.save(out_path)

    def modified_packs(self):
        return [fname for fname, pack in self._packs.items() if getattr(pack, "dirty", False)]

    def save_all_modified(self):
        saved = []
        for fname in self.modified_packs():
            pack = self._packs[fname]
            pack.save()
            pack.dirty = False
            saved.append(fname)
        return saved
