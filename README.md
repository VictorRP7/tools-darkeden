<div align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Status-Ativo-00C853?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Licença-Open%20Source-FF6F00?style=for-the-badge"/>
  <br/>
  <img src="https://img.shields.io/badge/Formatos-7%20decifrados-7B1FA2?style=flat-square"/>
  <img src="https://img.shields.io/badge/Ferramentas-8%20editores-0277BD?style=flat-square"/>
  <img src="https://img.shields.io/badge/Linhas%20de%20código-~12%20mil-FF6F00?style=flat-square"/>
</div>

<br/>

<h1 align="center">⚔️ DarkEden Tools</h1>

<p align="center">
  <b>Editores Python para os arquivos binários do cliente DarkEden</b><br/>
  Sprites • Efeitos • Skills • Personagens • Interface • Reskin
</p>

<p align="center">
  <i>Sem hex editor. Sem mistério. Código-fonte C++ real como referência.</i>
</p>

<br/>

---

## ✨ O que é isso?

Um conjunto de ferramentas em Python puro para **editar visualmente** os arquivos do jogo **DarkEden** — itens, efeitos de magia, skills, aparência de personagens, posição de botões na tela, e até a arte das telas.

Cada ferramenta foi construída **lendo o código-fonte C++ real do jogo** antes de escrever uma linha de Python — nenhum formato foi "adivinhado" por tentativa e erro.

> 🛡️ **Baseado no** [opendarkeden](https://github.com/opendarkeden)

---

## 📥 Como usar

```bash
# Clone o repositório
git clone https://github.com/VictorRP7/tools-darkeden.git
cd tools-darkeden

# Instale a única dependência
pip install pillow

# Edite o CLIENT_DIR no editor desejado (caminho do seu DarkEden)
# E rode:
python editors/ItemINF_Editor.py
```

> ⚡ Cada editor é **standalone** — abre sozinho, acha os arquivos do jogo automaticamente.

---

## 🧰 Ferramentas

<div align="center">

| Comando | O que faz | ⭐ |
|---------|-----------|:---:|
| `python editors/ItemINF_Editor.py` | Edita todos os itens do jogo | ⭐⭐⭐ |
| `python editors/ItemOption.py` | Encantamentos dos equipamentos | ⭐⭐ |
| `python editors/darkeden_interface_editor.py` | Posição dos botões na tela | ⭐⭐⭐ |
| `python editors/darkeden_effect_editor.py` | Efeitos visuais (criar/importar) | ⭐⭐⭐ |
| `python editors/darkeden_skill_editor.py` | Qual efeito cada skill dispara | ⭐⭐⭐ |
| `python editors/darkeden_creature_editor.py` | Aparência e animação de personagens | ⭐⭐⭐ |
| `python editors/darkeden_uiskin_editor.py` | Troca a arte das telas (reskin) | ⭐⭐⭐ |

</div>

---

## 📂 Estrutura do projeto

```
tools-darkeden/
│
├── 📁 lib/              # Biblioteca principal (7 módulos)
│   ├── darkeden_sprite.py      # Ícones de item (CIndexSprite555)
│   ├── darkeden_truesprite.py  # Sprites truecolor (CSprite555/565)
│   ├── darkeden_windowset.py   # Layout de janelas (.set)
│   ├── darkeden_effect.py      # Efeitos visuais (.aspk/.ppk/.efpk)
│   ├── darkeden_skill.py       # Action.inf (lado visual das skills)
│   ├── darkeden_creature.py    # Creature.inf + animação (.cfpk)
│   └── darkeden_uiskin.py      # Reskin + descoberta de .spk
│
├── 📁 editors/           # Editores visuais (GUI Tkinter)
│   ├── ItemINF_Editor.py
│   ├── ItemOption.py
│   ├── darkeden_interface_editor.py
│   ├── darkeden_effect_editor.py
│   ├── darkeden_skill_editor.py
│   ├── darkeden_creature_editor.py
│   ├── darkeden_uiskin_editor.py
│   └── test_ui.py
│
├── 📁 data/              # Dados de configuração
│   └── skill_icons.json        # 340 mapeamentos skill → ícone
│
└── 📄 README.md
```

---

## 🔬 O que já foi decifrado

| Arquivo | Formato | Lê | Escreve |
|---------|--------|:--:|:-------:|
| `Item.inf` | Container de classes de item | ✅ | ✅ |
| `ItemOption.inf` | Pool de encantamentos | ✅ | ✅ |
| `Item.ispk` | CIndexSprite555 (indexado + tingível) | ✅ | ✅ |
| `interface.inf` | Blocos CHAVE/TIPO | ✅ | ✅ |
| `UserSet/*.set` | Layout de janelas (669 bytes) | ✅ | ✅ |
| `EffectSpriteType.inf` | Tabela mestra de 2631 efeitos | ✅ | ✅ |
| `Effect.aspk` / `.ppk` / `.efpk` | CAlphaSpritePal (160 MB) | ✅ | ✅ |
| `Action.inf` | 1191 registros de skill | ✅ | ✅ |
| `SkillIcon.spk` | 647 ícones de skill | ✅ | ✅ |
| `Creature.inf` | 13361 registros de personagem | ✅ | ✅ |
| `Creature.cfpk` | Animação (Ação → Direção → Frame) | ✅ | ✅ |
| `Creature.ispk` | 341 MB de sprites de personagem | ✅ | ❌ |
| `*.spk` (interface) | CSprite555/565 | ✅ | ✅ |

---

## 🌟 Destaques

<details>
<summary><b>🎨 Editor de Reskin — 46 telas cobertas</b></summary>

Troque a **arte de verdade** das telas do jogo com `darkeden_uiskin_editor.py`:

- Título, Login, Seleção de Personagem
- Menu ESC, Opções, Status
- Inventário, Minimapa, HP/MP, Atalhos
- Loja de NPC, Party, Gear, Quests
- MailBox, WorldMap, e **muitos mais**

🇧​​​​​ Botão **"Descobrir .spk..."** encontra automaticamente arquivos de arte não mapeados no seu cliente.

</details>

<details>
<summary><b>🎬 Editor de Efeitos — Preview animado</b></summary>

`darkeden_effect_editor.py` — Navegue pelos 1957 efeitos com **Play**, edite frames, importe PNG, crie efeitos novos do zero com 8 direções e paleta própria.

</details>

<details>
<summary><b>🧙 Editor de Personagem — 13 mil criaturas</b></summary>

`darkeden_creature_editor.py` — Animação completa (Ação/Direção/Frame) para Vampire, Slayer (2 camadas de roupa!), Ousters, NPCs. Clone personagens, adicione/remova frames.

</details>

<details>
<summary><b>📍 Interface — Posição ao vivo</b></summary>

`darkeden_interface_editor.py` — Arraste os pontos com o mouse. O que é "ao vivo" (GAME_MENU, NEW_CHAR, INFO) realmente muda no jogo. O que é "morto" (TITLE) vem com aviso explícito.

</details>

---

## ⚠️ Limitações conhecidas

- **TileFrameID/DropFrameID/GearFrameID** — passam por tabela de indireção não mapeada (só InventoryFrameID tem preview)
- **TITLE** no `interface.inf` — o C++ usa literais fixos, editar não tem efeito
- **Slayer** — preview mostra apenas a aparência padrão (sem itens equipados)
- **Ousters** — 2 de 4 canais de cor implementados
- **NEW_CHAR widescreen** — sem arte de fundo própria
- **BltType=Sombra** — formato ainda não mapeado

---

## 📜 Créditos

<table>
  <tr>
    <td><b>Ferramentas originais</b></td>
    <td>TigerBlitz / comunidade</td>
  </tr>
  <tr>
    <td><b>Reverse engineering e expansão</b></td>
    <td><b>VictorRP7</b>, 2026</td>
  </tr>
  <tr>
    <td><b>Projeto base</b></td>
    <td><a href="https://github.com/opendarkeden">opendarkeden</a></td>
  </tr>
</table>

---

<div align="center">
  <sub>Feito com ☕ e muito <code>struct.unpack</code></sub>
</div>
