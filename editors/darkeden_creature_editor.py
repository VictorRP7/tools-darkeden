#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DarkEden Creature Editor - editor visual de APARENCIA e ANIMACAO de
personagens/criaturas do cliente (o mesmo dado por tras da aba "Personagem"
do site local) - mesmo padrao dos editores de Efeito e Skill deste projeto.

Abre DIRETO os arquivos que o JOGO DE VERDADE le' (Data\\Info\\Creature.inf +
CreatureSprite.inf, Data\\Image\\Creature.ispk/.cfpk + Ousters.*/addonman.*/
addonwoman.* conforme a tribo) - so' apontar a pasta Data do cliente. Ver
darkeden_creature.py pro formato binario completo e a logica de composicao
de camadas (Slayer usa calca+casaco separados sobre o mesmo personagem).

Autor: VictorRP7

Uso:
    python darkeden_creature_editor.py
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import darkeden_creature as dc

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

# ---------------------------------------------------------------------------
CLIENT_DIR = r"C:\Users\Victoria\OneDrive\Área de Trabalho\DARKEDEN"

CANVAS_BG = (32, 32, 44)

TRIBE_FILTER_OPTIONS = ["Todos"] + [dc.TRIBE_NAMES[k] for k in sorted(dc.TRIBE_NAMES)]


def _rgb_mask_to_rgba(width, height, rgb, mask):
    """darkeden_sprite.SpritePack.decode() devolve rgb (3 bytes/pixel) + mask
    (1 byte/pixel, 0 ou 255) separados - junta num RGBA pronto pro Pillow."""
    rgba = bytearray(width * height * 4)
    for i in range(width * height):
        rgba[i * 4:i * 4 + 3] = rgb[i * 3:i * 3 + 3]
        rgba[i * 4 + 3] = mask[i]
    return bytes(rgba)


class CreatureEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("DarkEden Creature Editor")
        self.root.geometry("1550x920")

        self.system = None
        self.current_index = None
        self.current_action = 0
        self.current_direction = 0
        self.current_frame_index = 0
        self.playing = False
        self._play_job = None
        self._photo = None
        self._listed_indices = []

        self._build_ui()
        self._try_auto_open()

    # -------------------------------------------------------------- UI build
    def _build_ui(self):
        tb = ttk.Frame(self.root)
        tb.pack(fill=tk.X, padx=4, pady=4)

        ttk.Button(tb, text="Abrir pasta Data...", command=self._open_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Salvar", command=self._save).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y)
        ttk.Button(tb, text="Novo personagem (clonar)...", command=self._clone_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Exportar frame atual...", command=self._export_frame).pack(side=tk.LEFT, padx=2)

        ttk.Label(tb, text="Filtro:").pack(side=tk.LEFT, padx=(12, 2))
        self.filter_var = tk.StringVar(value="")
        filt = ttk.Entry(tb, textvariable=self.filter_var, width=18)
        filt.pack(side=tk.LEFT)
        filt.bind("<KeyRelease>", lambda e: self._populate_creature_list())

        ttk.Label(tb, text="Tribo:").pack(side=tk.LEFT, padx=(12, 2))
        self.tribe_filter_var = tk.StringVar(value="Todos")
        tribe_combo = ttk.Combobox(tb, textvariable=self.tribe_filter_var, values=TRIBE_FILTER_OPTIONS,
                                    state="readonly", width=12)
        tribe_combo.pack(side=tk.LEFT)
        tribe_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_creature_list())

        sb = ttk.Frame(self.root)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar(value="Pronto.")
        ttk.Label(sb, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN).pack(
            side=tk.LEFT, fill=tk.X, expand=True)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ------------------------------------------------ left: creature list
        left = ttk.Frame(main)
        ttk.Label(left, text="Personagens (CreatureType: Nome):").pack(anchor=tk.W)
        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.creature_listbox = tk.Listbox(list_frame, exportselection=False, width=26, font=("Consolas", 9))
        sb_left = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.creature_listbox.yview)
        self.creature_listbox.config(yscrollcommand=sb_left.set)
        self.creature_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_left.pack(side=tk.RIGHT, fill=tk.Y)
        self.creature_listbox.bind("<<ListboxSelect>>", lambda e: self._on_select_creature())
        main.add(left, weight=2)

        # ------------------------------------------------- center: preview
        center = ttk.Frame(main)
        preview_tb = ttk.Frame(center)
        preview_tb.pack(fill=tk.X)

        ttk.Label(preview_tb, text="Acao:").pack(side=tk.LEFT)
        self.action_var = tk.StringVar(value="")
        self.action_combo = ttk.Combobox(preview_tb, textvariable=self.action_var, state="readonly", width=16)
        self.action_combo.pack(side=tk.LEFT, padx=2)
        self.action_combo.bind("<<ComboboxSelected>>", lambda e: self._on_action_change())

        ttk.Label(preview_tb, text="Direcao:").pack(side=tk.LEFT, padx=(12, 0))
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

        # ------------------------------------------------- right: properties
        right = ttk.Frame(main)

        info = ttk.LabelFrame(right, text="Personagem")
        info.pack(fill=tk.X, pady=(0, 6))
        self.info_vars = {}
        for i, label in enumerate(["Nome", "ColorSet (pele)"]):
            ttk.Label(info, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=2, pady=2)
            var = tk.StringVar(value="")
            ttk.Entry(info, textvariable=var, width=16).grid(row=i, column=1, sticky=tk.W, padx=2, pady=2)
            self.info_vars[label] = var

        self.gender_var = tk.StringVar(value="Masculino")
        ttk.Label(info, text="Genero:").grid(row=2, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Combobox(info, textvariable=self.gender_var, state="readonly", width=13,
                     values=["Masculino", "Feminino"]).grid(row=2, column=1, sticky=tk.W, padx=2, pady=2)

        self.tribe_label_var = tk.StringVar(value="-")
        ttk.Label(info, text="Tribo:").grid(row=3, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Label(info, textvariable=self.tribe_label_var).grid(row=3, column=1, sticky=tk.W, padx=2, pady=2)

        self.sprite_types_label_var = tk.StringVar(value="-")
        ttk.Label(info, text="SpriteTypes:").grid(row=4, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Label(info, textvariable=self.sprite_types_label_var, wraplength=180).grid(
            row=4, column=1, sticky=tk.W, padx=2, pady=2)

        ttk.Button(info, text="Aplicar", command=self._apply_character_props).grid(
            row=5, column=0, columnspan=2, pady=4)

        prop = ttk.LabelFrame(right, text="Frame selecionado")
        prop.pack(fill=tk.X, pady=6)
        self.layer_prop_frame = prop
        self.layer_widgets = []  # populated dynamically per creature (1 or 2 layers)

        btns = ttk.Frame(right)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="+ Frame (copiar ultimo)", command=self._add_frame).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="- Frame", command=self._remove_frame).pack(side=tk.LEFT, padx=2)

        main.add(right, weight=2)

    # -------------------------------------------------------------- File I/O
    def _try_auto_open(self):
        info_path = os.path.join(CLIENT_DIR, "Data", "Info", "Creature.inf")
        if os.path.isfile(info_path):
            self._open(os.path.join(CLIENT_DIR, "Data"))
        else:
            self._set_status("Abra a pasta Data do cliente (botao 'Abrir pasta Data...').")

    def _open_dialog(self):
        p = filedialog.askdirectory(title="Escolha a pasta Data do cliente DarkEden",
                                     initialdir=CLIENT_DIR)
        if p:
            self._open(p)

    def _open(self, data_dir):
        try:
            self.system = dc.CreatureSystem(data_dir)
        except Exception as e:
            messagebox.showerror("Erro ao abrir", str(e))
            return
        self._populate_creature_list()
        self._set_status(
            f"{len(self.system.creatures.records)} personagens, "
            f"{len(self.system.creature_sprites.entries)} entradas de CreatureSprite.inf "
            f"carregados de {data_dir}.")

    def _save(self):
        if not self.system:
            return
        try:
            self.system.creatures.save()
            for pack in self.system._body_packs.values():
                if pack._cfpk is not None:
                    pack._cfpk.save()
            if self.system._addon_pack is not None and self.system._addon_pack._cfpk is not None:
                self.system._addon_pack.cfpk.save()
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return
        self._set_status("Salvo (Creature.inf + os .cfpk que foram tocados) - backup automatico criado.")
        messagebox.showinfo("Salvo",
            "Creature.inf e qualquer .cfpk (Creature/Ousters/addonman/addonwoman) que voce "
            "editou nesta sessao foram salvos, com backup automatico ao lado.\n\n"
            "Os .ispk (pixels) nunca sao modificados por este editor - so' leitura.")

    # -------------------------------------------------------------- Creature list
    def _populate_creature_list(self):
        self.creature_listbox.delete(0, tk.END)
        if not self.system:
            return
        filt = self.filter_var.get().strip().lower()
        tribe_filter = self.tribe_filter_var.get()
        self._listed_indices = []
        for idx, c in enumerate(self.system.creatures.records):
            name = c.name.decode('cp949', errors='replace')
            if filt and filt not in name.lower() and filt not in str(idx):
                continue
            if tribe_filter != "Todos" and c.tribe_name != tribe_filter:
                continue
            self._listed_indices.append(idx)
            self.creature_listbox.insert(tk.END, f"{idx:5d}  {name}")
            if len(self._listed_indices) >= 5000:
                self.creature_listbox.insert(tk.END, "... (mais de 5000 - refine o filtro)")
                break

    def _on_select_creature(self):
        sel = self.creature_listbox.curselection()
        if not sel or sel[0] >= len(self._listed_indices):
            return
        self._select_creature(self._listed_indices[sel[0]])

    def _select_creature(self, index):
        self.current_index = index
        self.current_action = 0
        self.current_direction = 0
        self.current_frame_index = 0
        self._stop_play()

        c = self.system.creatures.records[index]
        self.info_vars["Nome"].set(c.name.decode('cp949', errors='replace'))
        self.info_vars["ColorSet (pele)"].set(str(c.color_set))
        self.gender_var.set("Masculino" if c.b_male else "Feminino")
        self.tribe_label_var.set(c.tribe_name)
        self.sprite_types_label_var.set(", ".join(str(s) for s in c.sprite_types))

        n_actions = self.system.action_count(c)
        names = [f"{i}: {dc.ACTION_NAMES.get(i, '?')}" for i in range(n_actions)]
        self.action_combo.config(values=names)
        if names:
            self.action_combo.current(0)
        else:
            self.action_var.set("")

        self._update_direction_range()
        self._update_frame_spin_range()
        self._build_layer_props()
        self._redraw()

    # -------------------------------------------------------------- Preview nav
    def _current_creature(self):
        if self.current_index is None:
            return None
        return self.system.creatures.records[self.current_index]

    def _update_direction_range(self):
        c = self._current_creature()
        if c is None:
            self.direction_spin.config(to=0)
            return
        n_dirs = self.system.direction_count(c, self.current_action)
        self.direction_spin.config(to=max(0, n_dirs - 1))

    def _current_layers(self):
        c = self._current_creature()
        if c is None:
            return []
        return self.system.render_frame(c, self.current_action, self.current_direction, self.current_frame_index)

    def _frame_count(self):
        """Quantidade de frames na Acao/Direcao atual - usa a camada 'coat'
        (ou a unica camada, pra tribos sem addon) como referencia, ja que
        coat/trouser sempre tem a mesma contagem de frames (confirmado
        empiricamente - ver darkeden_creature.py)."""
        c = self._current_creature()
        if c is None:
            return 0
        pack_key = self.system.body_pack_key_for(c)
        if pack_key is not None:
            fid = self.system.frame_id_for(c)
            if fid is None or fid == dc.FRAMEID_NULL:
                return 0
            fr = self.system.get_body_pack(pack_key).cfpk.get(fid, self.current_action, self.current_direction)
            return len(fr) if fr else 0
        if dc.is_slayer_tribe(c.tribe):
            coat_id, _trouser_id = dc.addon_ids_for(c.b_male)
            addon = self.system.get_addon_pack().cfpk
            fr = addon.get(coat_id, self.current_action, self.current_direction)
            return len(fr) if fr else 0
        return 0

    def _update_frame_spin_range(self):
        self.frame_spin.config(to=max(0, self._frame_count() - 1))

    def _on_action_change(self):
        sel = self.action_combo.get()
        if not sel:
            return
        self.current_action = int(sel.split(":")[0])
        self.current_direction = 0
        self.current_frame_index = 0
        self.direction_var.set(0)
        self.frame_var.set(0)
        self._update_direction_range()
        self._update_frame_spin_range()
        self._load_layer_props()
        self._redraw()

    def _on_direction_change(self):
        self.current_direction = self.direction_var.get()
        self.current_frame_index = 0
        self.frame_var.set(0)
        self._update_frame_spin_range()
        self._load_layer_props()
        self._redraw()

    def _on_frame_spin_change(self):
        self.current_frame_index = self.frame_var.get()
        self._load_layer_props()
        self._redraw()

    # -------------------------------------------------------------- Layer property panel
    def _layer_specs(self):
        """(label, frame_pack, frame_id) pra cada camada da criatura atual -
        1 item pra corpo direto, 2 (calca, casaco) pra Slayer/Slayer NPC."""
        c = self._current_creature()
        if c is None:
            return []
        pack_key = self.system.body_pack_key_for(c)
        if pack_key is not None:
            fid = self.system.frame_id_for(c)
            if fid is None or fid == dc.FRAMEID_NULL:
                return []
            return [("Corpo", self.system.get_body_pack(pack_key).cfpk, fid)]
        if dc.is_slayer_tribe(c.tribe):
            coat_id, trouser_id = dc.addon_ids_for(c.b_male)
            addon = self.system.get_addon_pack().cfpk
            return [("Calca", addon, trouser_id), ("Casaco", addon, coat_id)]
        return []

    def _build_layer_props(self):
        for w in self.layer_widgets:
            w.destroy()
        self.layer_widgets = []
        self.layer_prop_vars = []
        specs = self._layer_specs()
        for row, (label, _pack, _fid) in enumerate(specs):
            lbl = ttk.Label(self.layer_prop_frame, text=f"{label} - Sprite/CX/CY:")
            lbl.grid(row=row * 2, column=0, columnspan=3, sticky=tk.W, padx=2, pady=(6, 0))
            self.layer_widgets.append(lbl)
            row_vars = {}
            for col, field in enumerate(["Sprite", "CX", "CY"]):
                var = tk.StringVar(value="0")
                e = ttk.Entry(self.layer_prop_frame, textvariable=var, width=7)
                e.grid(row=row * 2 + 1, column=col, sticky=tk.W, padx=2, pady=(0, 4))
                self.layer_widgets.append(e)
                row_vars[field] = var
            self.layer_prop_vars.append(row_vars)
        if specs:
            btn = ttk.Button(self.layer_prop_frame, text="Aplicar", command=self._apply_layer_props)
            btn.grid(row=len(specs) * 2, column=0, columnspan=3, pady=4)
            self.layer_widgets.append(btn)
        self._load_layer_props()

    def _load_layer_props(self):
        if not hasattr(self, 'layer_prop_vars'):
            return
        specs = self._layer_specs()
        for (label, pack, fid), row_vars in zip(specs, self.layer_prop_vars):
            frames = pack.get(fid, self.current_action, self.current_direction)
            if frames and 0 <= self.current_frame_index < len(frames):
                sid, cx, cy = frames[self.current_frame_index]
                row_vars["Sprite"].set(str(sid))
                row_vars["CX"].set(str(cx))
                row_vars["CY"].set(str(cy))

    def _apply_layer_props(self):
        specs = self._layer_specs()
        for (label, pack, fid), row_vars in zip(specs, self.layer_prop_vars):
            frames = pack.get(fid, self.current_action, self.current_direction)
            if not frames or not (0 <= self.current_frame_index < len(frames)):
                continue
            try:
                sid = int(row_vars["Sprite"].get())
                cx = int(row_vars["CX"].get())
                cy = int(row_vars["CY"].get())
            except ValueError:
                messagebox.showerror("Valor invalido", f"Sprite/CX/CY de '{label}' precisam ser inteiros.")
                return
            frames[self.current_frame_index][0] = sid
            frames[self.current_frame_index][1] = cx
            frames[self.current_frame_index][2] = cy
        self._redraw()
        self._set_status("Frame atualizado (em memoria) - use Salvar pra gravar em disco.")

    # -------------------------------------------------------------- Character props
    def _apply_character_props(self):
        c = self._current_creature()
        if c is None:
            return
        c.name = self.info_vars["Nome"].get().encode('cp949', errors='replace')
        try:
            c.color_set = int(self.info_vars["ColorSet (pele)"].get())
        except ValueError:
            messagebox.showerror("Valor invalido", "ColorSet precisa ser um numero inteiro.")
            return
        c.b_male = (self.gender_var.get() == "Masculino")
        self._populate_creature_list()
        self._redraw()
        self._set_status("Personagem atualizado (em memoria) - use Salvar pra gravar em disco.")

    def _clone_dialog(self):
        c = self._current_creature()
        if c is None:
            messagebox.showwarning("Nenhum personagem selecionado", "Selecione um personagem pra clonar primeiro.")
            return
        top = tk.Toplevel(self.root)
        top.title("Novo personagem (clonar)")
        ttk.Label(top, text=f"Clonando a aparencia de: {c.name.decode('cp949', errors='replace')}").grid(
            row=0, column=0, columnspan=2, padx=8, pady=8)
        ttk.Label(top, text="Nome novo:").grid(row=1, column=0, sticky=tk.W, padx=8)
        name_var = tk.StringVar(value="NovoPersonagem")
        ttk.Entry(top, textvariable=name_var, width=24).grid(row=1, column=1, padx=8, pady=4)

        def do_clone():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Nome vazio", "Digite um nome.")
                return
            new_idx = self.system.creatures.clone_record(self.current_index, name)
            top.destroy()
            self._populate_creature_list()
            self._set_status(f"Personagem {new_idx} ('{name}') criado clonando a aparencia de "
                              f"'{c.name.decode('cp949', errors='replace')}' - use Salvar pra gravar.")
            messagebox.showinfo("Personagem criado",
                f"CreatureType {new_idx} criado (em memoria) - use Salvar pra gravar em Creature.inf.")

        ttk.Button(top, text="Criar", command=do_clone).grid(row=2, column=0, columnspan=2, pady=8)

    # -------------------------------------------------------------- Add/remove frame
    def _add_frame(self):
        specs = self._layer_specs()
        if not specs:
            messagebox.showwarning("Sem animacao", "Esse personagem nao tem dados de animacao pra editar.")
            return
        for label, pack, fid in specs:
            frames = pack.get(fid, self.current_action, self.current_direction)
            if not frames:
                messagebox.showwarning("Direcao vazia", f"A camada '{label}' nao tem frame nenhum nessa direcao pra copiar.")
                return
            last = frames[-1]
            pack.append_frame(fid, self.current_action, self.current_direction, last[0], last[1], last[2])
        self._update_frame_spin_range()
        self.current_frame_index = self._frame_count() - 1
        self.frame_var.set(self.current_frame_index)
        self._load_layer_props()
        self._redraw()
        self._set_status("Frame novo adicionado (copia do ultimo) - use Salvar pra gravar.")

    def _remove_frame(self):
        specs = self._layer_specs()
        if not specs:
            return
        if self._frame_count() <= 0:
            return
        if not messagebox.askyesno("Confirmar", "Remover o ULTIMO frame dessa Acao/Direcao (em todas as camadas)?"):
            return
        for label, pack, fid in specs:
            try:
                pack.remove_last_frame(fid, self.current_action, self.current_direction)
            except ValueError:
                pass
        self._update_frame_spin_range()
        self.current_frame_index = max(0, self._frame_count() - 1)
        self.frame_var.set(self.current_frame_index)
        self._load_layer_props()
        self._redraw()

    # -------------------------------------------------------------- Rendering
    def _redraw(self):
        self.canvas.delete("all")
        if Image is None or self.system is None or self.current_index is None:
            return
        layers = self._current_layers()
        if not layers:
            self.canvas.create_text(8, 8, anchor=tk.NW, fill="#aaa", font=("Arial", 9),
                                     text="(sem frame nessa Acao/Direcao)")
            return

        cw = self.canvas.winfo_width() or 400
        ch = self.canvas.winfo_height() or 400

        # bbox de TODAS as camadas juntas, em coordenadas originais (nao
        # escaladas) - cada camada e' um retangulo width x height centrado
        # em (cx,cy). Escalar so' pelo tamanho da MAIOR camada sozinha (como
        # a 1a versao fazia) subestima o espaco vertical de verdade quando
        # cy desloca muito (ex: Slayer com calca+casaco em pontos bem
        # diferentes) - o casaco podia acabar escalado pra fora do canvas.
        left = min(l.cx - l.width / 2 for l in layers)
        right = max(l.cx + l.width / 2 for l in layers)
        top = min(l.cy - l.height / 2 for l in layers)
        bottom = max(l.cy + l.height / 2 for l in layers)
        bbox_w = max(1.0, right - left)
        bbox_h = max(1.0, bottom - top)

        scale = max(1, min(8, int(min(cw, ch) * 0.55 / max(bbox_w, bbox_h))))

        pad = 40 * scale
        comp_w = int(bbox_w * scale) + pad * 2
        comp_h = int(bbox_h * scale) + pad * 2
        composite = Image.new("RGBA", (comp_w, comp_h), (0, 0, 0, 0))
        # ponto onde (cx=0,cy=0) cai dentro do composite
        anchor_x = int(-left * scale) + pad
        anchor_y = int(-top * scale) + pad

        for layer in layers:
            rgba = _rgb_mask_to_rgba(layer.width, layer.height, layer.rgb, layer.mask)
            img = Image.frombytes("RGBA", (layer.width, layer.height), rgba)
            if scale > 1:
                img = img.resize((layer.width * scale, layer.height * scale), Image.NEAREST)
            px = anchor_x + layer.cx * scale - img.width // 2
            py = anchor_y + layer.cy * scale - img.height // 2
            composite.paste(img, (px, py), img)

        bg = Image.new("RGB", composite.size, CANVAS_BG)
        bg.paste(composite, (0, 0), composite)
        self._photo = ImageTk.PhotoImage(bg)

        cx, cy = cw / 2, ch / 2
        self.canvas.create_line(cx - 10, cy, cx + 10, cy, fill="#666")
        self.canvas.create_line(cx, cy - 10, cx, cy + 10, fill="#666")
        self.canvas.create_image(cx, cy, image=self._photo, anchor=tk.CENTER)

        c = self._current_creature()
        n_frames = self._frame_count()
        self.canvas.create_text(
            8, 8, anchor=tk.NW, fill="#aaa", font=("Arial", 9),
            text=f"{c.name.decode('cp949', errors='replace')}  acao {self.current_action} "
                 f"dir {self.current_direction}  frame {self.current_frame_index}/{max(0, n_frames - 1)}  "
                 f"({len(layers)} camada{'s' if len(layers) != 1 else ''})")

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
        n_frames = self._frame_count()
        if n_frames:
            self.current_frame_index = (self.current_frame_index + 1) % n_frames
            self.frame_var.set(self.current_frame_index)
            self._redraw()
        self._play_job = self.root.after(150, self._play_tick)

    # -------------------------------------------------------------- Export
    def _export_frame(self):
        layers = self._current_layers()
        if not layers or Image is None:
            messagebox.showwarning("Nada pra exportar", "Selecione um personagem com animacao primeiro.")
            return
        c = self._current_creature()
        max_dim = max(max(l.width, l.height, 1) for l in layers)
        pad = 40
        size = max_dim + pad * 2
        composite = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ax = ay = size // 2
        for layer in layers:
            rgba = _rgb_mask_to_rgba(layer.width, layer.height, layer.rgb, layer.mask)
            img = Image.frombytes("RGBA", (layer.width, layer.height), rgba)
            px = ax + layer.cx - img.width // 2
            py = ay + layer.cy - img.height // 2
            composite.paste(img, (px, py), img)
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=f"creature_{self.current_index}_a{self.current_action}_d{self.current_direction}_f{self.current_frame_index}.png",
            filetypes=[("PNG", "*.png")])
        if not path:
            return
        composite.save(path)
        self._set_status(f"Exportado para {path}")

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
    CreatureEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
