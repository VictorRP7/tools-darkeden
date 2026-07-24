#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DarkEden Skill Editor - editor visual das SKILLS reais do cliente,
mostrando o ICONE da skill, a skill E o(s) efeito(s) visuais que ela
dispara - mesmo estilo do darkeden_effect_editor.py (fundo/preview real,
animacao com Play), so' que navegando a partir da SKILL em vez do efeito
direto.

Le'/grava `Data\\Info\\Action.inf` (ver darkeden_skill.py pro formato
binario completo, confirmado byte-a-byte contra o arquivo real de 1191
skills), `Data\\Ui\\spk\\SkillIcon.spk` (icone de cada skill - mesmo
formato `CSprite555/565` de `darkeden_truesprite.py`, ja' com leitura E
ESCRITA) e usa darkeden_effect.py (ja' existente) pra' resolver e mostrar
a animacao de qualquer "ponto de efeito" da skill selecionada:
  - Cast (Masculino) / Cast (Feminino) - o efeito no PROPRIO personagem
    ao lancar a skill.
  - Node 0, 1, 2... - passos extras (ex: um projetil que sai da mao e
    viaja ate' o alvo, separado do efeito de cast).
  - Resultado: Cast / Node 0... - o efeito de IMPACTO no alvo, guardado
    num registro SEPARADO da mesma tabela (indice = SkillID +
    MinResultActionInfo, ver MActionResult.cpp:162).

2026-07-22: dado "um talento" a mais - a lista de skills e a lista de
pontos de efeito agora mostram uma MINIATURA de verdade em cada linha
(icone da skill / primeiro frame do efeito), igual a tabela do site local
(tools\\client_editor, aba Skills) mostra - so' que aqui integrado ao
preview animado que o site nao tem.

Autor: VictorRP7

IMPORTANTE: dano/custo de MP/cooldown/nivel NAO estao aqui - isso e'
server-side (banco de dados, editavel pelo site local em
tools\\client_editor, aba "Skills"). Este editor mexe no lado CLIENTE:
nome interno, tempos de casting, o ICONE da skill, e o mais importante -
QUAL efeito visual (EffectSpriteType/FrameID) cada skill dispara. Editar
aqui deixa dar "roupa nova" visual pra' uma skill sem mexer no
balanceamento dela.

Uso:
    python darkeden_skill_editor.py

Ajuste CLIENT_DIR abaixo pro caminho do cliente.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import darkeden_skill as skill
import darkeden_effect as effect

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

CLIENT_DIR = r"C:\Users\Victoria\OneDrive\Área de Trabalho\DARKEDEN"
CANVAS_BG = (32, 32, 44)
ICON_SCALE = 2  # 36x36 nativo -> 72x72 na lista/preview, pixel-art nitido (NEAREST)
ROW_ICON_PX = 24  # tamanho do icone dentro de cada linha das listas (Treeview)


def _rgb_mask_to_rgba(width, height, rgb, mask):
    """darkeden_truesprite.TrueSpritePack.decode() devolve rgb (3 bytes/pixel)
    + mask (1 byte/pixel) separados - junta num RGBA pronto pro Pillow."""
    rgba = bytearray(width * height * 4)
    for i in range(width * height):
        rgba[i * 4:i * 4 + 3] = rgb[i * 3:i * 3 + 3]
        rgba[i * 4 + 3] = mask[i]
    return bytes(rgba)


def get_effect_slots(tbl, skill_id):
    """Lista de (label, obj, attr) - cada "ponto de efeito" desta skill.
    obj/attr e' onde o EffectSpriteType de verdade mora (pra' ler/editar
    genericamente via getattr/setattr, sem precisar de um caso especial
    por tipo de slot)."""
    rec = tbl.records[skill_id]
    slots = [("Cast (Masculino)", rec, "action_effect_sprite_type")]
    if rec.action_effect_sprite_type_female != rec.action_effect_sprite_type:
        slots.append(("Cast (Feminino)", rec, "action_effect_sprite_type_female"))
    for i, node in enumerate(rec.nodes):
        slots.append((f"Node {i} (proprio)", node, "effect_sprite_type"))
    ridx = tbl.result_index_for(skill_id)
    if ridx is not None and ridx != skill_id:
        rrec = tbl.records[ridx]
        slots.append((f"Resultado #{ridx}: Cast", rrec, "action_effect_sprite_type"))
        for i, node in enumerate(rrec.nodes):
            slots.append((f"Resultado #{ridx}: Node {i}", node, "effect_sprite_type"))
    return slots


class SkillEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("DarkEden Skill Editor")
        self.root.geometry("1600x940")

        self.tbl = None
        self.effect_system = None
        self.icon_system = None
        self.current_skill_id = None
        self.current_slots = []
        self.current_slot_index = None
        self.current_direction = 0
        self.current_frame_index = 0
        self.playing = False
        self._play_job = None
        self._photo = None
        self._icon_photo = None
        self._row_icon_cache = {}   # icon_index -> PhotoImage (linhas da lista de skills)
        self._slot_thumb_cache = {}  # (frame_id, sprite_id) -> PhotoImage (linhas da lista de pontos de efeito)
        self._photo_cache = {}      # Garante que as imagens nao sejam coletadas pelo GC
        self._blank_row_photo = None

        self._build_ui()
        self._try_auto_open()

    # -------------------------------------------------------------- Thumbnails
    def _make_blank_row_photo(self):
        if Image is None:
            return None
        img = Image.new("RGBA", (ROW_ICON_PX, ROW_ICON_PX), (0, 0, 0, 0))
        return ImageTk.PhotoImage(img)

    def _row_photo_from_rgba(self, w, h, rgba, cache, cache_key):
        """Constroi (com cache) uma PhotoImage pequena (ROW_ICON_PX) pronta
        pra' usar como `image=` de uma linha de Treeview - usado tanto pro
        icone da skill quanto pra' miniatura do primeiro frame de um efeito."""
        if cache_key in cache:
            return cache[cache_key]
        if Image is None or not w or not h:
            cache[cache_key] = self._blank_row_photo
            return self._blank_row_photo
        img = Image.frombytes("RGBA", (w, h), rgba)
        img.thumbnail((ROW_ICON_PX, ROW_ICON_PX), Image.NEAREST)
        canvas_img = Image.new("RGBA", (ROW_ICON_PX, ROW_ICON_PX), (0, 0, 0, 0))
        ox = (ROW_ICON_PX - img.width) // 2
        oy = (ROW_ICON_PX - img.height) // 2
        canvas_img.paste(img, (ox, oy), img)
        photo = ImageTk.PhotoImage(canvas_img)
        cache[cache_key] = photo
        return photo

    def _skill_row_icon(self, skill_id):
        if self.icon_system is None:
            return self._blank_row_photo
        idx = self.icon_system.get_icon_index(skill_id)
        if idx is None:
            return self._blank_row_photo
        if idx in self._row_icon_cache:
            return self._row_icon_cache[idx]
        try:
            w, h, rgb, mask = self.icon_system.decode_icon(skill_id)
        except Exception:
            self._row_icon_cache[idx] = self._blank_row_photo
            return self._blank_row_photo
        rgba = _rgb_mask_to_rgba(w, h, rgb, mask)
        return self._row_photo_from_rgba(w, h, rgba, self._row_icon_cache, idx)

    def _slot_row_thumb(self, obj, attr):
        est = getattr(obj, attr)
        if est == skill.EFFECTSPRITETYPE_NULL or self.effect_system is None:
            return self._blank_row_photo
        if est >= len(self.effect_system.sprite_types.records):
            return self._blank_row_photo
        type_rec = self.effect_system.sprite_types.records[est]
        if type_rec.blt_type != 1:
            return self._blank_row_photo
        frame_id = type_rec.frame_id
        if frame_id >= len(self.effect_system.frames.frames):
            return self._blank_row_photo
        directions = self.effect_system.frames.frames[frame_id]
        first_frame = next((fr for d in directions for fr in d), None)
        if first_frame is None:
            return self._blank_row_photo
        cache_key = (frame_id, first_frame.sprite_id)
        if cache_key in self._slot_thumb_cache:
            return self._slot_thumb_cache[cache_key]
        try:
            sprite = self.effect_system.decode_sprite(first_frame.sprite_id, frame_id)
        except Exception:
            self._slot_thumb_cache[cache_key] = self._blank_row_photo
            return self._blank_row_photo
        return self._row_photo_from_rgba(sprite.width, sprite.height, sprite.rgba,
                                          self._slot_thumb_cache, cache_key)

    # -------------------------------------------------------------- UI build
    def _build_ui(self):
        self._blank_row_photo = self._make_blank_row_photo()

        style = ttk.Style()
        style.configure("Skill.Treeview", rowheight=ROW_ICON_PX + 8)

        tb = ttk.Frame(self.root)
        tb.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(tb, text="Abrir pasta Data...", command=self._open_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Salvar Action.inf", command=self._save).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y)
        ttk.Label(tb, text="Filtro (nome ou SkillID):").pack(side=tk.LEFT, padx=(4, 2))
        self.filter_var = tk.StringVar(value="")
        filt = ttk.Entry(tb, textvariable=self.filter_var, width=24)
        filt.pack(side=tk.LEFT)
        filt.bind("<KeyRelease>", lambda e: self._populate_skill_list())
        self.only_with_effect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tb, text="So' com efeito visual", variable=self.only_with_effect_var,
                        command=self._populate_skill_list).pack(side=tk.LEFT, padx=8)

        sb = ttk.Frame(self.root)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar(value="Pronto.")
        ttk.Label(sb, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN).pack(
            side=tk.LEFT, fill=tk.X, expand=True)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ------------------------------------------------ left: skill list
        left = ttk.Frame(main)
        ttk.Label(left, text="Skills (icone + SkillID: nome):").pack(anchor=tk.W)
        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.skill_tree = ttk.Treeview(list_frame, show="tree", style="Skill.Treeview", selectmode="browse")
        sb_left = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.skill_tree.yview)
        self.skill_tree.config(yscrollcommand=sb_left.set)
        self.skill_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_left.pack(side=tk.RIGHT, fill=tk.Y)
        self.skill_tree.bind("<<TreeviewSelect>>", lambda e: self._on_select_skill())
        main.add(left, weight=3)

        # -------------------------------------------------- center-left: notebook (Effects Grid + Animation)
        slots_frame = ttk.Frame(main)
        self.slots_notebook = ttk.Notebook(slots_frame)
        self.slots_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Effects Grid
        effects_grid_tab = ttk.Frame(self.slots_notebook)
        self.slots_notebook.add(effects_grid_tab, text="Effects Grid")
        ttk.Label(effects_grid_tab, text="Todos os efeitos desta skill:").pack(anchor=tk.W, padx=4, pady=4)

        grid_scroll = ttk.Frame(effects_grid_tab)
        grid_scroll.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.effects_grid_tree = ttk.Treeview(
            grid_scroll, show="tree", style="Skill.Treeview",
            selectmode="browse", height=8, columns=("type", "est", "blttype", "frameid")
        )
        self.effects_grid_tree.column("#0", width=250)
        self.effects_grid_tree.column("type", width=80)
        self.effects_grid_tree.column("est", width=70)
        self.effects_grid_tree.column("blttype", width=70)
        self.effects_grid_tree.column("frameid", width=70)

        self.effects_grid_tree.heading("#0", text="Efeito")
        self.effects_grid_tree.heading("type", text="Tipo")
        self.effects_grid_tree.heading("est", text="EffectSpriteType")
        self.effects_grid_tree.heading("blttype", text="BltType")
        self.effects_grid_tree.heading("frameid", text="FrameID")

        sb_grid = ttk.Scrollbar(grid_scroll, orient=tk.VERTICAL, command=self.effects_grid_tree.yview)
        self.effects_grid_tree.config(yscrollcommand=sb_grid.set)
        self.effects_grid_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_grid.pack(side=tk.RIGHT, fill=tk.Y)
        self.effects_grid_tree.bind("<<TreeviewSelect>>", lambda e: self._on_select_effect_grid())

        # Tab 2: Animation Preview
        anim_tab = ttk.Frame(self.slots_notebook)
        self.slots_notebook.add(anim_tab, text="Anim Preview")
        self.anim_preview_frame = anim_tab

        main.add(slots_frame, weight=2)


        # ------------------------------------------------- center: preview
        center = ttk.Frame(main)
        preview_tb = ttk.Frame(center)
        preview_tb.pack(fill=tk.X)
        ttk.Label(preview_tb, text="Direcao:").pack(side=tk.LEFT)
        self.direction_var = tk.IntVar(value=0)
        self.direction_spin = ttk.Spinbox(preview_tb, from_=0, to=0, width=4,
                                           textvariable=self.direction_var,
                                           command=self._on_direction_change)
        self.direction_spin.pack(side=tk.LEFT, padx=2)
        ttk.Label(preview_tb, text="Frame:").pack(side=tk.LEFT, padx=(12, 0))
        self.frame_var = tk.IntVar(value=0)
        self.frame_spin = ttk.Spinbox(preview_tb, from_=0, to=0, width=4,
                                       textvariable=self.frame_var,
                                       command=self._on_frame_spin_change)
        self.frame_spin.pack(side=tk.LEFT, padx=2)
        self.play_btn = ttk.Button(preview_tb, text="Play", command=self._toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=12)

        self.canvas = tk.Canvas(center, bg="#202028", highlightthickness=1, highlightbackground="#666")
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        main.add(center, weight=7)

        # ------------------------------------------------- right: skill info
        right = ttk.Frame(main)
        ttk.Label(right, text="Info da skill:").pack(anchor=tk.W)

        # Botão para impacto
        self.impact_btn = ttk.Button(right, text="Ver Efeito de Impacto", command=self._go_to_impact)
        self.impact_btn.pack(fill=tk.X, pady=5)

        icon_box = ttk.LabelFrame(right, text="Icone (SkillIcon.spk)")
        icon_box.pack(fill=tk.X, pady=(4, 6))
        icon_row = ttk.Frame(icon_box)
        icon_row.pack(fill=tk.X, padx=4, pady=4)
        icon_size = 36 * ICON_SCALE
        self.icon_canvas = tk.Canvas(icon_row, width=icon_size, height=icon_size,
                                      bg="#202028", highlightthickness=1, highlightbackground="#666")
        self.icon_canvas.pack(side=tk.LEFT, padx=(0, 8))
        icon_btns = ttk.Frame(icon_row)
        icon_btns.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Button(icon_btns, text="Importar icone...", command=self._import_icon).pack(fill=tk.X, pady=1)
        ttk.Button(icon_btns, text="Exportar icone...", command=self._export_icon).pack(fill=tk.X, pady=1)
        ttk.Button(icon_btns, text="Atribuir icone novo", command=self._assign_icon).pack(fill=tk.X, pady=1)
        self.icon_info_var = tk.StringVar(value="-")
        ttk.Label(icon_box, textvariable=self.icon_info_var, foreground="#666").pack(anchor=tk.W, padx=4, pady=(0, 4))

        info = ttk.LabelFrame(right, text="Dados de Action.inf (so' o lado visual)")
        info.pack(fill=tk.X, pady=4)
        self.info_vars = {}
        fields = ["SkillID", "Nome", "Delay", "Range", "CastingActionInfo", "Parent",
                  "MinResultActionInfo p/ esta"]
        for i, label in enumerate(fields):
            ttk.Label(info, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=2, pady=1)
            var = tk.StringVar(value="-")
            if label in ["Delay", "Range", "CastingActionInfo", "Parent"]:
                ent = ttk.Entry(info, textvariable=var, width=10)
                ent.grid(row=i, column=1, sticky=tk.W, padx=2, pady=1)
                self.info_vars[label] = var
            else:
                ttk.Label(info, textvariable=var).grid(row=i, column=1, sticky=tk.W, padx=2, pady=1)
                self.info_vars[label] = var

        ttk.Button(right, text="Aplicar Info da Skill", command=self._apply_skill_info).pack(pady=5)

        ttk.Label(right,
                  text="Lembrete: dano/MP/cooldown/nivel sao server-side\n"
                       "(banco de dados) - edite isso no site local\n"
                       "(tools\\client_editor, aba Skills). Aqui da'\n"
                       "pra' trocar o ICONE e QUAL EFEITO VISUAL a skill\n"
                       "dispara.",
                  foreground="#888", wraplength=220, justify=tk.LEFT).pack(anchor=tk.W, pady=10)

        main.add(right, weight=2)

    # -------------------------------------------------------------- File I/O
    def _try_auto_open(self):
        action_path = os.path.join(CLIENT_DIR, "Data", "Info", "Action.inf")
        if os.path.isfile(action_path):
            self._open(os.path.join(CLIENT_DIR, "Data"))
        else:
            self._set_status("Abra a pasta Data do cliente (botao 'Abrir pasta Data...').")

    def _open_dialog(self):
        p = filedialog.askdirectory(title="Escolha a pasta Data do cliente DarkEden", initialdir=CLIENT_DIR)
        if p:
            self._open(p)

    def _open(self, data_dir):
        try:
            self.tbl = skill.ActionInfoTable()
            self.tbl.load(os.path.join(data_dir, "Info", "Action.inf"))
            self.effect_system = effect.EffectSystem(data_dir)
            self.icon_system = skill.SkillIconSystem(data_dir)
        except Exception as e:
            messagebox.showerror("Erro ao abrir", str(e))
            return
        self._row_icon_cache.clear()
        self._slot_thumb_cache.clear()
        self._populate_skill_list()
        self._set_status(f"{len(self.tbl.records)} registros de Action.inf carregados "
                          f"({self.tbl.min_result_action_info} e' o 1o indice de 'resultado'). "
                          f"{len(self.effect_system.sprite_types.records)} tipos de efeito disponiveis. "
                          f"{len(self.icon_system.icon_map)} skills com icone mapeado.")

    def _save(self):
        if not self.tbl:
            return
        try:
            self.tbl.save()
            saved_icon = False
            if self.icon_system is not None and self.icon_system.is_dirty():
                self.icon_system.save()
                saved_icon = True
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return
        msg = "Action.inf salvo (backup automatico do arquivo anterior criado ao lado)."
        if saved_icon:
            msg += " SkillIcon.spk/.spki (e skill_icons.json, se algum icone novo foi atribuido) tambem salvos."
        self._set_status(msg)
        messagebox.showinfo("Salvo", msg)

    # -------------------------------------------------------------- Skill list
    def _populate_skill_list(self):
        for iid in self.skill_tree.get_children():
            self.skill_tree.delete(iid)
        if not self.tbl:
            return
        filt = self.filter_var.get().strip().upper()
        only_effect = self.only_with_effect_var.get()
        self._listed_skill_ids = []
        # so' mostra skills "de verdade" (antes do bloco de resultados/impacto)
        limit = self.tbl.min_result_action_info if self.tbl.min_result_action_info > 0 else len(self.tbl.records)
        for skill_id in range(min(limit, len(self.tbl.records))):
            rec = self.tbl.records[skill_id]
            name = rec.name.decode("cp949", errors="replace")
            if filt and filt not in name.upper() and filt != str(skill_id):
                continue
            if only_effect and rec.action_effect_sprite_type == skill.EFFECTSPRITETYPE_NULL and not rec.nodes:
                continue
            pos = len(self._listed_skill_ids)
            self._listed_skill_ids.append(skill_id)
            photo = self._skill_row_icon(skill_id)
            self.skill_tree.insert("", tk.END, iid=str(pos), text=f"  {skill_id:4d}  {name}", image=photo)

    def _on_select_skill(self):
        sel = self.skill_tree.selection()
        if not sel:
            return
        skill_id = self._listed_skill_ids[int(sel[0])]
        self._select_skill(skill_id)

    def _go_to_impact(self):
        if self.current_skill_id is None or self.tbl is None:
            return
        ridx = self.tbl.result_index_for(self.current_skill_id)
        if ridx is not None and ridx != self.current_skill_id:
            self._select_skill(ridx)
        else:
            self._set_status("Esta skill não possui um registro de impacto separado.")

    def _select_skill(self, skill_id):
        self.current_skill_id = skill_id
        rec = self.tbl.records[skill_id]

        self.info_vars["SkillID"].set(str(skill_id))
        self.info_vars["Nome"].set(rec.name.decode("cp949", errors="replace"))
        self.info_vars["Delay"].set(str(rec.delay))
        self.info_vars["Range"].set(str(rec.range))
        self.info_vars["CastingActionInfo"].set(str(rec.casting_action_info))
        self.info_vars["Parent"].set(str(rec.parent))
        ridx = self.tbl.result_index_for(skill_id)
        self.info_vars["MinResultActionInfo p/ esta"].set(str(ridx) if ridx is not None else "-")

        # Atualiza o botão de impacto
        if ridx is not None and ridx != skill_id:
            self.impact_btn.config(state=tk.NORMAL)
        else:
            self.impact_btn.config(state=tk.DISABLED)

        self._redraw_icon()

        self.current_slots = get_effect_slots(self.tbl, skill_id)
        self._populate_effects_grid()

    def _populate_effects_grid(self):
        """Preenche a grid de efeitos com todos os pontos de efeito desta skill."""
        for iid in self.effects_grid_tree.get_children():
            self.effects_grid_tree.delete(iid)

        if not self.current_slots:
            return

        for i, (label, obj, attr) in enumerate(self.current_slots):
            val = getattr(obj, attr)
            blt_type_name = "-"
            frame_id_str = "-"

            if val != skill.EFFECTSPRITETYPE_NULL and val < len(self.effect_system.sprite_types.records):
                type_rec = self.effect_system.sprite_types.records[val]
                blt_type_name = effect.BLT_TYPE_NAMES.get(type_rec.blt_type, f"?{type_rec.blt_type}")
                frame_id_str = str(type_rec.frame_id)

            val_str = "Sem" if val == skill.EFFECTSPRITETYPE_NULL else str(val)
            self.effects_grid_tree.insert(
                "", tk.END,
                iid=str(i),
                text=f"  {label}",
                values=(label.split("(")[0].strip(), val_str, blt_type_name, frame_id_str)
            )

    def _on_select_effect_grid(self):
        """Quando seleciona um efeito na grid, mostra preview da animação."""
        sel = self.effects_grid_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.current_slots):
            self._show_animation_preview(idx)

    def _on_select_effect_grid(self):
        """Quando seleciona um efeito na grid, mostra preview da animação."""
        sel = self.effects_grid_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.current_slots):
            self._show_animation_preview(idx)

    def _show_animation_preview(self, slot_index):
        """Preenche o tab de Anim Preview com todos os frames em um grid."""
        self.current_slot_index = slot_index
        for widget in self.anim_preview_frame.winfo_children():
            widget.destroy()

        # Header com direção
        header = ttk.Frame(self.anim_preview_frame)
        header.pack(fill=tk.X, pady=4)
        ttk.Label(header, text="Direção:").pack(side=tk.LEFT, padx=4)
        self.direction_var = tk.IntVar(value=0)
        self.direction_spin = ttk.Spinbox(header, from_=0, to=0, width=4,
                                           textvariable=self.direction_var,
                                           command=self._render_anim_strip)
        self.direction_spin.pack(side=tk.LEFT, padx=4)

        # Container do grid (com scroll)
        grid_container = ttk.Frame(self.anim_preview_frame)
        grid_container.pack(fill=tk.BOTH, expand=True)

        self.anim_canvas = tk.Canvas(grid_container, bg="#202028")
        sb = ttk.Scrollbar(grid_container, orient=tk.VERTICAL, command=self.anim_canvas.yview)
        self.anim_canvas.config(yscrollcommand=sb.set)
        self.anim_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.anim_frame = ttk.Frame(self.anim_canvas)
        self.anim_canvas.create_window((0, 0), window=self.anim_frame, anchor=tk.NW)
        self.anim_frame.bind("<Configure>", lambda e: self.anim_canvas.configure(scrollregion=self.anim_canvas.bbox("all")))

        self._render_anim_strip()

    def _render_anim_strip(self):
        """Desenha o grid de todos os frames da direção selecionada."""
        for widget in self.anim_frame.winfo_children():
            widget.destroy()

        if self.current_slot_index is None or not self.current_slots:
            ttk.Label(self.anim_frame, text="Nenhum efeito selecionado").pack(padx=10, pady=10)
            return

        label, obj, attr = self.current_slots[self.current_slot_index]
        effect_sprite_type = getattr(obj, attr)

        if effect_sprite_type == skill.EFFECTSPRITETYPE_NULL or effect_sprite_type >= len(self.effect_system.sprite_types.records):
            ttk.Label(self.anim_frame, text="Efeito não mapeado").pack(padx=10, pady=10)
            return

        # Busca FrameID do EffectSpriteType
        type_rec = self.effect_system.sprite_types.records[effect_sprite_type]
        frame_id = type_rec.frame_id
        blt_type = type_rec.blt_type
        pack = self.effect_system.get_pack(blt_type)

        # Lê todos os frames desta direção
        try:
            if not pack or frame_id >= len(pack["frames"].frames):
                ttk.Label(self.anim_frame, text=f"FrameID {frame_id} fora do range do pack (BLT {blt_type})").pack(padx=10, pady=10)
                return

            direction_frames = pack["frames"].frames[frame_id]
            dir_idx = self.direction_var.get()
            if not direction_frames:
                ttk.Label(self.anim_frame, text="Esse efeito nao tem direcoes definidas.").pack(padx=10, pady=10)
                return

            if dir_idx >= len(direction_frames):
                dir_idx = 0
                self.direction_var.set(0)

            frames = direction_frames[dir_idx]
            if not frames:
                ttk.Label(self.anim_frame, text="Essa direcao nao tem frames.").pack(padx=10, pady=10)
                return

        except Exception as e:
            ttk.Label(self.anim_frame, text=f"Erro ao ler frames: {e}").pack(padx=10, pady=10)
            return

        # Desenha cada frame
        for i, frame in enumerate(frames):
            # Destaca background
            bg_color = "#2d2d3a"
            fg_color = "#ccc"
            if getattr(frame, "background", False):
                bg_color = "#3d2d2d" # Vermelho escuro para BG
                fg_color = "#ffaaaa"

            cell = tk.Frame(self.anim_frame, borderwidth=1, relief=tk.RAISED, bg=bg_color)
            cell.pack(side=tk.LEFT, padx=3, pady=3)

            try:
                sprite_data = self.effect_system.decode_sprite(frame.sprite_id, frame_id, blt_type)
                img = Image.frombytes("RGBA", (sprite_data.width, sprite_data.height), sprite_data.rgba)
                img.thumbnail((64, 64), Image.NEAREST)
                photo = ImageTk.PhotoImage(img)
                self._photo_cache[f"strip_{i}"] = photo

                lbl = tk.Label(cell, image=photo, bg=bg_color)
                lbl.pack(padx=2, pady=2)

                lbl.bind("<Button-1>", lambda e, idx=i: self._jump_to_frame(idx))

                tag = " [BG]" if getattr(frame, "background", False) else ""
                tk.Label(cell, text=f"#{i}{tag}", font=("Consolas", 8), bg=bg_color, fg=fg_color).pack()
            except Exception as e:
                tk.Label(cell, text=f"F{i}\nErro", font=("Arial", 6), bg="#500", fg="white").pack(padx=4, pady=4)

    def _jump_to_frame(self, frame_index):
        self.frame_var.set(frame_index)
        self._on_frame_spin_change()

    def _export_frame_direct(self, frame, i, frame_id, blt_type=1):
        if Image is None: return
        try:
            sprite = self.effect_system.decode_sprite(frame.sprite_id, frame_id, blt_type)
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=f"effect_{frame_id}_dir{self.current_direction}_f{i}.png",
                filetypes=[("PNG", "*.png")])
            if path:
                Image.frombytes("RGBA", (sprite.width, sprite.height), sprite.rgba).save(path)
                self._set_status(f"Frame exportado para {path}")
        except Exception as e:
            messagebox.showerror("Erro", str(e))


    # -------------------------------------------------------------- Icon
    def _redraw_icon(self):
        self.icon_canvas.delete("all")
        self._icon_photo = None
        size = 36 * ICON_SCALE
        if self.icon_system is None or self.current_skill_id is None:
            self.icon_info_var.set("-")
            return
        idx = self.icon_system.get_icon_index(self.current_skill_id)
        if idx is None:
            self.icon_info_var.set("Esta skill nao tem icone atribuido.")
            self.icon_canvas.create_text(size / 2, size / 2, fill="#666", font=("Arial", 9),
                                          text="(sem icone)", width=size - 10)
            return
        try:
            w, h, rgb, mask = self.icon_system.decode_icon(self.current_skill_id)
        except Exception as e:
            self.icon_info_var.set(f"Erro decodificando icone: {e}")
            return
        if Image is None or not w or not h:
            self.icon_info_var.set(f"indice {idx} - {w}x{h}")
            return
        rgba = _rgb_mask_to_rgba(w, h, rgb, mask)
        img = Image.frombytes("RGBA", (w, h), rgba)
        img = img.resize((w * ICON_SCALE, h * ICON_SCALE), Image.NEAREST)
        bg = Image.new("RGB", img.size, CANVAS_BG)
        bg.paste(img, (0, 0), img)
        self._icon_photo = ImageTk.PhotoImage(bg)
        self.icon_canvas.create_image(size / 2, size / 2, image=self._icon_photo, anchor=tk.CENTER)
        self.icon_info_var.set(f"SkillIcon.spk #{idx} - {w}x{h}")

    def _import_icon(self):
        if self.current_skill_id is None or self.icon_system is None:
            messagebox.showwarning("Nenhuma skill selecionada", "Escolha uma skill na lista primeiro.")
            return
        if self.icon_system.get_icon_index(self.current_skill_id) is None:
            messagebox.showwarning("Sem icone atribuido",
                                    "Essa skill ainda nao tem indice de icone - use 'Atribuir icone novo' primeiro.")
            return
        if Image is None:
            messagebox.showerror("Falta Pillow", "Instale Pillow (pip install Pillow) pra' importar imagens.")
            return
        path = filedialog.askopenfilename(
            title="Escolha a imagem do icone novo (PNG 36x36 recomendado)",
            filetypes=[("Imagens", "*.png;*.tga;*.bmp"), ("Todos", "*.*")])
        if not path:
            return
        try:
            w, h = self.icon_system.replace_icon_image(self.current_skill_id, path, resize_to_original=True)
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e))
            return
        self._row_icon_cache.pop(self.icon_system.get_icon_index(self.current_skill_id), None)
        self._redraw_icon()
        # atualiza so' a linha desta skill na lista, sem reconstruir tudo
        for pos, sid in enumerate(self._listed_skill_ids):
            if sid == self.current_skill_id:
                self.skill_tree.item(str(pos), image=self._skill_row_icon(sid))
                break
        self._set_status(f"Icone da skill {self.current_skill_id} trocado por {os.path.basename(path)} "
                          f"({w}x{h}) - em memoria, use 'Salvar Action.inf' pra' gravar em disco.")

    def _export_icon(self):
        if self.current_skill_id is None or self.icon_system is None:
            return
        idx = self.icon_system.get_icon_index(self.current_skill_id)
        if idx is None:
            messagebox.showwarning("Sem icone", "Essa skill nao tem icone atribuido pra' exportar.")
            return
        if Image is None:
            return
        w, h, rgb, mask = self.icon_system.decode_icon(self.current_skill_id)
        if not w or not h:
            messagebox.showwarning("Icone vazio", "Esse icone nao tem pixels (sprite vazio).")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=f"skill_{self.current_skill_id}_icon.png",
            filetypes=[("PNG", "*.png")])
        if not path:
            return
        rgba = _rgb_mask_to_rgba(w, h, rgb, mask)
        Image.frombytes("RGBA", (w, h), rgba).save(path)
        self._set_status(f"Icone exportado para {path}")

    def _assign_icon(self):
        if self.current_skill_id is None or self.icon_system is None:
            messagebox.showwarning("Nenhuma skill selecionada", "Escolha uma skill na lista primeiro.")
            return
        if self.icon_system.get_icon_index(self.current_skill_id) is not None:
            messagebox.showinfo("Ja' tem icone", "Essa skill ja' tem um icone atribuido - use 'Importar icone...' "
                                                  "pra' trocar a imagem dele.")
            return
        if not messagebox.askyesno("Atribuir icone novo",
                                    "Isso reaproveita uma sobra de indice livre dentro de SkillIcon.spk "
                                    "(nunca aumenta o arquivo) e guarda essa atribuicao em skill_icons.json. "
                                    "Continuar?"):
            return
        try:
            idx = self.icon_system.assign_new_icon_slot(self.current_skill_id)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return
        self._redraw_icon()
        for pos, sid in enumerate(self._listed_skill_ids):
            if sid == self.current_skill_id:
                self.skill_tree.item(str(pos), image=self._skill_row_icon(sid))
                break
        self._set_status(f"Indice de icone {idx} atribuido a skill {self.current_skill_id} (em memoria) - "
                          "importe uma imagem e use 'Salvar Action.inf' pra' gravar em disco.")

    # -------------------------------------------------------------- Slots
    def _on_select_slot(self):
        sel = self.slot_tree.selection()
        if not sel:
            return
        self.current_slot_index = int(sel[0])
        self._stop_play()
        self.current_direction = 0
        self.current_frame_index = 0
        self.direction_var.set(0)
        self.frame_var.set(0)
        self._load_slot_info()
        self._update_direction_range()
        self._update_frame_spin_range()
        self._redraw()

    def _current_slot(self):
        if self.current_slot_index is None or self.current_slot_index >= len(self.current_slots):
            return None
        return self.current_slots[self.current_slot_index]

    def _load_slot_info(self):
        slot = self._current_slot()
        if not slot:
            return
        label, obj, attr = slot
        est = getattr(obj, attr)
        self.slot_effect_var.set(str(est))
        if est == skill.EFFECTSPRITETYPE_NULL:
            self.slot_info_var.set("Sem efeito (0xFFFF = nenhum).")
            return
        if est >= len(self.effect_system.sprite_types.records):
            self.slot_info_var.set(f"EffectSpriteType {est} fora do intervalo da tabela.")
            return
        type_rec = self.effect_system.sprite_types.records[est]
        if type_rec.blt_type != 1:
            self.slot_info_var.set(
                f"BltType={type_rec.blt_type_name} (frame_id {type_rec.frame_id}) - "
                "so' o tipo EFFECT tem preview de animacao aqui.")
        else:
            self.slot_info_var.set(f"BltType=EFFECT, frame_id={type_rec.frame_id} - animacao abaixo.")

    def _resolve_slot_frame_id(self):
        """(frame_id, blt_type) do slot de efeito atual, ou (None, None) se
        sem efeito valido. Agora aceita QUALQUER BltType (1=EFFECT, 3=SCREEN,
        0=NORMAL etc) - o pack correspondente precisa existir, senao o frame
        nao vai aparecer."""
        slot = self._current_slot()
        if not slot:
            return None, None
        _label, obj, attr = slot
        est = getattr(obj, attr)
        if est == skill.EFFECTSPRITETYPE_NULL or est >= len(self.effect_system.sprite_types.records):
            return None, None
        type_rec = self.effect_system.sprite_types.records[est]
        return type_rec.frame_id, type_rec.blt_type

    # -------------------------------------------------------------- Preview
    def _current_direction_frames(self):
        resolved = self._resolve_slot_frame_id()
        if resolved[0] is None:
            return []
        frame_id, blt_type = resolved
        pack = self.effect_system.get_pack(blt_type)
        if pack is None or frame_id >= len(pack["frames"].frames):
            return []
        directions = pack["frames"].frames[frame_id]
        if not directions or self.current_direction >= len(directions):
            return []
        return directions[self.current_direction]

    def _update_direction_range(self):
        resolved = self._resolve_slot_frame_id()
        if resolved[0] is None:
            self.direction_spin.config(to=0)
            return
        frame_id, blt_type = resolved
        pack = self.effect_system.get_pack(blt_type)
        n_dirs = 1
        if pack and frame_id < len(pack["frames"].frames):
            n_dirs = max(1, len(pack["frames"].frames[frame_id]))
        self.direction_spin.config(to=max(0, n_dirs - 1))

    def _update_frame_spin_range(self):
        frames = self._current_direction_frames()
        self.frame_spin.config(to=max(0, len(frames) - 1))

    def _on_direction_change(self):
        self.current_direction = self.direction_var.get()
        self.current_frame_index = 0
        self.frame_var.set(0)
        self._update_frame_spin_range()
        self._redraw()

    def _on_frame_spin_change(self):
        self.current_frame_index = self.frame_var.get()
        self._redraw()

    def _apply_slot_effect(self):
        slot = self._current_slot()
        if not slot:
            return
        label, obj, attr = slot
        try:
            new_val = int(self.slot_effect_var.get())
        except ValueError:
            messagebox.showerror("Valor invalido", "EffectSpriteType precisa ser um numero inteiro "
                                                     "(65535 = nenhum).")
            return
        setattr(obj, attr, new_val)
        idx = self.current_slot_index
        tag = "sem efeito" if new_val == skill.EFFECTSPRITETYPE_NULL else str(new_val)
        photo = self._slot_row_thumb(obj, attr)
        self.slot_tree.item(str(idx), text=f"  {label}  [{tag}]", image=photo)
        self.slot_tree.selection_set(str(idx))
        self.current_direction = 0
        self.current_frame_index = 0
        self.direction_var.set(0)
        self.frame_var.set(0)
        self._load_slot_info()
        self._update_direction_range()
        self._update_frame_spin_range()
        self._redraw()
        self._set_status(f"'{label}' atualizado (em memoria) - use 'Salvar Action.inf' pra' gravar em disco.")

    def _apply_skill_info(self):
        if self.current_skill_id is None:
            return
        rec = self.tbl.records[self.current_skill_id]
        try:
            rec.delay = int(self.info_vars["Delay"].get())
            rec.range = int(self.info_vars["Range"].get())
            val = int(self.info_vars["CastingActionInfo"].get())
            rec.casting_action_info_raw = (rec.casting_action_info_raw & ~0xFFFF) | (val & 0xFFFF)
            rec.parent = int(self.info_vars["Parent"].get())
        except ValueError:
            messagebox.showerror("Erro", "Valores numéricos inválidos.")
            return
        self._set_status("Info da skill aplicada (em memória).")

    def _redraw(self):
        self.canvas.delete("all")
        if Image is None or self.effect_system is None:
            return

        # Desenha centro do personagem
        cw = self.canvas.winfo_width() or 400
        ch = self.canvas.winfo_height() or 400
        self.canvas.create_line(cw / 2 - 30, ch / 2, cw / 2 + 30, ch / 2, fill="#555")
        self.canvas.create_line(cw / 2, ch / 2 - 30, cw / 2, ch / 2 + 30, fill="#555")

        frames = self._current_direction_frames()
        if not frames or self.current_frame_index >= len(frames):
            self.canvas.create_text(cw / 2, ch / 2, fill="#666", font=("Arial", 11),
                                     text="(sem frame nesta direcao/indice)")
            return

        fr = frames[self.current_frame_index]
        resolved = self._resolve_slot_frame_id()
        frame_id = resolved[0]
        blt_type = resolved[1] if resolved[0] is not None else 1
        try:
            sprite = self.effect_system.decode_sprite(fr.sprite_id, frame_id, blt_type)
        except Exception as e:
            self._set_status(f"Erro decodificando sprite {fr.sprite_id}: {e}")
            return

        if sprite.width == 0 or sprite.height == 0:
            return

        scale = max(1, min(10, min(cw, ch) // max(sprite.width, sprite.height, 1) // 3))

        img = Image.frombytes("RGBA", (sprite.width, sprite.height), sprite.rgba)
        if scale > 1:
            img = img.resize((sprite.width * scale, sprite.height * scale), Image.NEAREST)

        # Background = atrás do personagem (escurecido)
        if getattr(fr, 'background', False):
            overlay = Image.new("RGBA", img.size, (50, 0, 0, 100)) # Vermelho escuro
            img = Image.alpha_composite(img, overlay)

        self._photo_cache['preview'] = ImageTk.PhotoImage(img)

        cx = cw / 2 + fr.cx * scale
        cy = ch / 2 + fr.cy * scale
        self.canvas.create_image(cx, cy, image=self._photo_cache['preview'], anchor=tk.CENTER)

        # Info de debug
        slot = self._current_slot()
        label = slot[0] if slot else "?"
        bg_tag = "[BACK]" if getattr(fr, 'background', False) else "[FRONT]"
        blt_names = {0: "NORMAL", 1: "EFFECT", 2: "SHADOW", 3: "SCREEN"}
        blt_label = blt_names.get(blt_type, f"?{blt_type}")
        self.canvas.create_text(
            8, 8, anchor=tk.NW, fill="#0f0", font=("Consolas", 10, "bold"),
            text=f"{label} {bg_tag} [{blt_label}]")
        self.canvas.create_text(
            8, 24, anchor=tk.NW, fill="#aaa", font=("Consolas", 9),
            text=f"Frame: {self.current_frame_index}/{len(frames)-1} | Sprite: {fr.sprite_id} | Size: {sprite.width}x{sprite.height} | Offset: {fr.cx},{fr.cy}")

    # -------------------------------------------------------------- Play
    def _toggle_play(self):
        if self.playing:
            self._stop_play()
        else:
            self.playing = True
            self.play_btn.config(text="Stop")
            self._play_tick()

    def _stop_play(self):
        self.playing = False
        self.play_btn.config(text="Play")
        if self._play_job:
            self.root.after_cancel(self._play_job)
            self._play_job = None

    def _play_tick(self):
        if not self.playing:
            return
        frames = self._current_direction_frames()
        if frames:
            self.current_frame_index = (self.current_frame_index + 1) % len(frames)
            self.frame_var.set(self.current_frame_index)
            self._redraw()
        self._play_job = self.root.after(120, self._play_tick)

    # -------------------------------------------------------------- Helpers
    def _set_status(self, msg):
        self.status_var.set(msg)


def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    SkillEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
