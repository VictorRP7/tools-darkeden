# 🛠️ DarkEden Tools (Python)

Editores e bibliotecas em Python para os arquivos binarios do cliente **DarkEden** — trabalhe com sprites, efeitos, skills, personagens, interface e muito mais sem precisar de hex editor.

> **Autor:** VictorRP7
> **Base:** ferramentas originais de TigerBlitz, reescritas/expandidas a partir do codigo-fonte C++ real do cliente (`client-master/`), nao por tentativa e erro. Todo formato binario foi validado com round-trip byte-a-byte contra os arquivos reais do jogo.

---

## 📋 Indice

- [Estrutura do repositorio](#-estrutura-do-repositorio)
- [Requisitos](#-requisitos)
- [Ferramentas incluídas](#-ferramentas-incluidas)
  - [Editor de Itens (Item.inf)](#editor-de-itens-iteminf)
  - [Editor de Interface (interface.inf)](#editor-de-interface-interfaceinf)
  - [Editor de Efeitos](#editor-de-efeitos)
  - [Editor de Skills](#editor-de-skills)
  - [Editor de Personagem](#editor-de-personagem)
  - [Editor de UI / Reskin](#editor-de-ui--reskin)
- [Como usar](#-como-usar)
- [Arquivos binarios decifrados](#-arquivos-binarios-decifrados)
- [Limitações conhecidas](#-limitacoes-conhecidas)
- [Licença / Creditos](#-licenca--creditos)

---

## 📁 Estrutura do repositorio

```
tools-darkeden/
├── lib/                    # Bibliotecas compartilhadas (leitura/escrita dos formatos)
│   ├── darkeden_sprite.py       # Sprites de item (CIndexSprite555)
│   ├── darkeden_truesprite.py   # Sprites truecolor (CSprite555/565) - fundos de tela
│   ├── darkeden_windowset.py    # Layout de janelas do jogo (formato .set)
│   ├── darkeden_effect.py       # Sistema de efeitos visuais (EffectSpriteType + .aspk/.ppk)
│   ├── darkeden_skill.py        # Action.inf - lado visual das skills
│   ├── darkeden_creature.py     # Creature.inf + CreatureSprite.inf + Creature.cfpk
│   └── darkeden_uiskin.py       # Sistema de reskin (arte das telas do jogo) + descoberta de .spk
│
├── editors/                 # Editores visuais (GUI com Tkinter)
│   ├── ItemINF_Editor.py         # Editor completo de Item.inf
│   ├── ItemOption.py             # Editor de encantamentos (ItemOption.inf)
│   ├── darkeden_interface_editor.py  # Editor visual do interface.inf + janelas do jogo
│   ├── darkeden_effect_editor.py     # Editor de efeitos visuais (preview animado)
│   ├── darkeden_skill_editor.py      # Editor de skills (icone + efeito visual)
│   ├── darkeden_creature_editor.py   # Editor de aparencia e animacao de personagens
│   ├── darkeden_uiskin_editor.py     # Editor de reskin (troca a arte das telas)
│   └── test_ui.py               # Teste automatizado do SkillEditor
│
├── data/                    # Dados de configuracao
│   └── skill_icons.json         # Mapeamento skill → indice de icone (340 entradas)
│
└── README.md                # Este arquivo
```

---

## ✅ Requisitos

- **Python 3.10+** (testado com Python 3.13)
- **Pillow:** necessario para os previews de imagem
  ```
  pip install pillow
  ```
- **tkinter** (ja vem com a instalacao padrao do Python no Windows)

Nenhuma outra dependencia externa. Nenhum dos arquivos `.inf`/`.ispk`/`.aspk`/`.ppk`/`.cfpk`/`.set` e' RAR ou formato generico — sao todos formatos binarios proprios do motor do jogo, lidos/escritos diretamente por `struct`, confirmados linha a linha no codigo-fonte C++ real.

> ⚠️ **Atencao:** antes de usar, edite a constante `CLIENT_DIR` no topo de cada editor para o caminho da sua instalacao do DarkEden (ex: `r"C:\DarkEden"`).

---

## 🧰 Ferramentas incluídas

### Editor de Itens (Item.inf)

**`python editors/ItemINF_Editor.py`**

Editor completo do `Data\Info\Item.inf` com abas:

| Aba | Funcionalidade |
|-----|---------------|
| **Basic Info** | Nome, descricao, preco, peso, grid, preview do icone real do jogo |
| **Frames & Sounds** | 6 IDs de sprite + 4 IDs de som |
| **Stats** | Value1-7 (rotulo muda conforme a classe do item), ataque, defesa, durabilidade |
| **Requirements** | STR/DEX/INT/SUM/Level/Raca, Male/Female Only |
| **Advanced** | Item Style (Normal/Unico), Elemento, Rareza |
| **Raw Data** | Hex dump para conferencia |

**ItemOption.py** — editor do pool de encantamentos (`ItemOption.inf`) com dicas de Plus Point e referencia cruzada entre opcoes.

---

### Editor de Interface (interface.inf)

**`python editors/darkeden_interface_editor.py`**

Editor visual do `Data\Info\interface.inf` — o arquivo que define a **posicao** de cada botao/campo nas telas do jogo.

| Tela | Status |
|------|--------|
| **TITLE** | 🟡 Dado morto (codigo usa literais fixos) |
| **GAME_MENU** | 🟢 Ao vivo — editar aqui muda o menu Esc no jogo |
| **OPTION** | 🟡 Parcial — so' funciona dentro do jogo |
| **NEW_CHAR** | 🟢 Ao vivo — muda a criacao de personagem |
| **INFO** | 🟢 Ao vivo — muda a janela de status |
| **LOGIN (popup)** | 🔵 So' referencia visual (posicoes fixas no C++) |
| **Janelas do jogo** | 🔵 Modelo por raca (arquivo .set separado) |

Recursos:
- **Fundo real** de cada tela decodificado dos `.spk` (nao so' retangulo cinza)
- **Sprites reais** de botoes/icones nos pontos (NEW_CHAR, OPTION, INFO)
- **Arrastar** pontos com o mouse e ver a posicao atualizar ao vivo
- **Ajuste automatico** de zoom para caber todos os pontos na tela
- LOGIN e JANELAS DO JOGO como pseudo-telas para organizacao

---

### Editor de Efeitos

**`python editors/darkeden_effect_editor.py`**

Editor visual completo dos 1957 efeitos do jogo (magias, golpes, auras):

- Navegue pelos efeitos com preview animado (Play)
- Edite deslocamento X/Y, luz e flag de fundo de cada frame
- **Importe PNG** como frame novo (quantizacao automatica contra a paleta do efeito)
- **Crie efeitos novos** do zero (aloca FrameID, 8 direcoes, paleta propria)
- Exporte qualquer frame para PNG

Abre direto os arquivos que o jogo usa: `EffectSpriteType.inf` + `Effect.aspk/.ppk/.efpk`.

---

### Editor de Skills

**`python editors/darkeden_skill_editor.py`**

Visualize e edite qual **efeito visual** cada skill dispara:

- **Lista com icone real** da skill ao lado do nome (647 icones, 36x36)
- **Pontos de efeito**: Cast (M/F), Nodes intermediarios, Resultado/Impacto
- **Preview animado** com Play para cada efeito
- **Importar/atribuir icone** novo para skills sem icone
- **Troque o efeito** que uma skill dispara (digite o EffectSpriteType)

> ⚠️ Dano, custo de MP, cooldown sao **server-side** (banco de dados) — edite pelo site local (`tools/client_editor`, localhost:8765).

---

### Editor de Personagem

**`python editors/darkeden_creature_editor.py`**

Editor visual de aparencia e animacao de personagens/criaturas:

- Navegue por **13361 personagens** com preview da animacao (Acao/Direcao/Frame)
- **Play** para ver o ciclo de animacao completo
- Slayer: **duas camadas** (calca + casaco) com offsets de alinhamento
- Editor de frame: adicionar/remover frames em qualquer direcao
- **Clonar personagem**: copia aparencia + corpo, so' troca o nome
- Suporte a Vampire, Slayer (com sistema de roupa addon), Ousters, NPCs

---

### Editor de UI / Reskin

**`python editors/darkeden_uiskin_editor.py`**

Troque a **arte de verdade** das telas e janelas do jogo:

- **46 telas/areas cobertas**: Titulo, Login, Selecao de Personagem, Opcoes, Menu ESC, Status, Inventario, Minimapa, HP/MP, Atalhos, Loja de NPC, Party, Gear, Quests, MailBox, WorldMap, e mais
- Importe PNG para substituir qualquer sprite
- Exporte qualquer sprite como PNG para editar em programas de desenho
- Preview da tela inteira com a parte selecionada em destaque
- **Descoberta automatica** (botao "Descobrir .spk..."): encontra arquivos .spk no seu cliente que ainda nao estao mapeados

> Complementar ao Interface Editor: aquele reposiciona pontos; este troca imagens.

---

## 🚀 Como usar

Cada editor e' standalone — basta rodar com Python:

```bash
# Acesse a pasta do repositorio
cd tools-darkeden

# Edite CLIENT_DIR no editor escolhido (constante no topo do arquivo)
# Exemplo: CLIENT_DIR = r"C:\MeuJogo\DarkEden"

# Rode o editor desejado
python editors/ItemINF_Editor.py
python editors/darkeden_interface_editor.py
python editors/darkeden_effect_editor.py
python editors/darkeden_skill_editor.py
python editors/darkeden_creature_editor.py
python editors/darkeden_uiskin_editor.py
```

Todos os editores abrem os arquivos automaticamente a partir da pasta `Data/` do cliente.

---

## 🔬 Arquivos binarios decifrados

Todo formato foi confirmado lendo o codigo-fonte C++ real e validado com round-trip byte-a-byte:

| Arquivo | Formato | Status |
|---------|---------|--------|
| `Item.inf` | Container de classes → registros ITEMTABLE_INFO | ✅ Leitura e escrita |
| `ItemOption.inf` | Pool de encantamentos | ✅ Leitura e escrita |
| `Item.ispk` / `.ispki` | CIndexSprite555 (indexado, tingivel) | ✅ Leitura, escrita, append |
| `interface.inf` | Blocos CHAVE/TIPO com pontos/retangulos | ✅ Leitura e escrita |
| `UserSet/*.set` | Layout de janelas por personagem (669 bytes) | ✅ Leitura e escrita |
| `EffectSpriteType.inf` | Tabela mestra de efeitos | ✅ Leitura e escrita |
| `Effect.aspk` / `.ppk` / `.efpk` | CAlphaSpritePal (alpha + indice de paleta) | ✅ Leitura e escrita |
| `Action.inf` | Tabela de acoes/skills (1191 registros) | ✅ Leitura e escrita |
| `SkillIcon.spk` | CSprite555/565 (icones 36x36) | ✅ Leitura e escrita |
| `Creature.inf` | Registros de personagem (tamanho variavel) | ✅ Leitura e escrita |
| `Creature.cfpk` | Animacao: Acao → Direcao → Frame | ✅ Leitura e escrita |
| `Creature.ispk` | CIndexSprite555 (341MB) | ✅ Leitura |
| `*.spk` (UI) | CSprite555/565 (telas, botoes, janelas) | ✅ Leitura e escrita |
| `Title.spk`, `Login.spk`, etc | Fundos de tela | ✅ Leitura e escrita |

---

## ⚠️ Limitacoes conhecidas

1. **Item.inf:** `TileFrameID`/`DropFrameID`/`GearFrameID` passam por tabela de indirecao (CImageFramePack) ainda nao mapeada — preview/adiciao de icone so' cobre o icone de **inventario**.
2. **interface.inf:** TITLE e OPTION (tela de titulo) sao **dados mortos** — o C++ usa literais fixos, nao le os pontos do arquivo. GAME_MENU e NEW_CHAR sao **ao vivo**.
3. **Slayer:** a previsao mostra so' a aparencia padrao (pele + roupa basica), nao os itens equipados de verdade.
4. **Ousters:** recolorimento aproximado (2 de 4 canais de cor reais).
5. **NEW_CHAR widescreen:** nao tem arte de fundo propria.
6. **Efeito do tipo "Sombra" (BltType):** formato ainda nao mapeado para previsa/edicao.
7. **Nomes de personagem** no seletor de `.set` podem aparecer como mojibake (charset cp949/euc-kr).

---

## 📜 Licenca / Creditos

- **Ferramentas originais** (ItemINF_Editor.py forma inicial, ItemOption.py): **TigerBlitz** / comunidade
- **Reverse engineering, reescrita e expansao** de todos os formatos binarios: **VictorRP7**, 2026
- Baseado no codigo-fonte do [opendarkeden](https://github.com/opendarkeden)
