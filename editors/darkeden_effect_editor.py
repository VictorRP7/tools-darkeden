#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DarkEden Effect Editor - editor visual do sistema de EFEITOS real do
cliente (magias, golpes, auras) - substitui a ferramenta antiga
"EffectManager" (que precisava de .tga brutos que ninguem mais tem).

Este editor abre DIRETO os arquivos que o JOGO DE VERDADE le' (Data\\Info\\
EffectSpriteType.inf + Data\\Image\\Effect.aspk/.aspki/.ppk/.ppki/.efpk/
.efpki) - so' apontar a pasta Data do cliente e ele acha tudo sozinho. Ver
darkeden_effect.py pro formato binario completo (confirmado byte-a-byte
contra o codigo-fonte C++ e testado com round-trip identico nos 7 arquivos
reais, incluindo o Effect.aspk de 160MB).

Autor: VictorRP7

Como funciona por dentro (resumo - detalhes completos em darkeden_effect.py):
  - EffectSpriteType.inf: tabela de 2631 "tipos de efeito" - cada posicao
    na tabela E' o FrameID. So' os do tipo EFFECT (1957 deles) tem sprite/
    paleta/animacao de verdade (os outros tipos - NORMAL/SHADOW/SCREEN -
    usam OUTROS arquivos que este editor nao mexe, ver Limitacoes).
  - Effect.efpk: pra' cada FrameID, uma lista de direcoes (geralmente 8),
    cada direcao uma lista de frames de animacao (qual sprite, com que
    deslocamento, luz, se e' "fundo").
  - Effect.aspk: os pixels de cada sprite (alpha + indice de paleta).
  - Effect.ppk: uma paleta (ate' 255 cores) POR FrameID - compartilhada
    entre todos os sprites/direcoes/frames desse efeito.

Uso:
    python darkeden_effect_editor.py

Ajuste CLIENT_DIR abaixo pro caminho do cliente na sua maquina - o editor
acha sozinho Data\\Info\\EffectSpriteType.inf e Data\\Image\\Effect.*
a partir dai'.
"""
import os
import sys
import struct
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import darkeden_effect as effect

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

# ---------------------------------------------------------------------------
CLIENT_DIR = r"C:\Users\Victoria\OneDrive\Área de Trabalho\DARKEDEN"

CANVAS_BG = (32, 32, 44)


def nearest_palette_index(rgb, palette_colors):
    """Indice da cor mais proxima (distancia euclidiana simples) dentro de
    uma lista de (r,g,b) - usado ao importar uma imagem contra uma paleta
    JA' EXISTENTE (nao inventa cor nova, so' acha a mais parecida)."""
    r, g, b = rgb
    best_i, best_d = 0, None
    for i, (pr, pg, pb) in enumerate(palette_colors):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if best_d is None or d < best_d:
            best_d = d
            best_i = i
    return best_i


def image_to_pal_index_rows(img, palette_colors, alpha_threshold=8):
    """Converte um PIL.Image RGBA em linhas de (alpha_0_31, pal_index) ou
    None (transparente) - pronto pra' AlphaSpritePack.encode_sprite()."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < alpha_threshold:
                row.append(None)
            else:
                idx = nearest_palette_index((r, g, b), palette_colors)
                alpha31 = min(31, a * 31 // 255)
                row.append((alpha31, idx))
        rows.append(row)
    return rows


def build_palette_from_images(images, max_colors=255):
    """Monta uma paleta nova (ate' 255 cores) a partir de uma ou mais
    PIL.Image RGBA, usando a quantizacao adaptativa do Pillow (median-cut)
    sobre os pixels NAO-transparentes de todas juntas."""
    combo = Image.new("RGB", (sum(im.width for im in images), max(im.height for im in images)), (0, 0, 0))
    x = 0
    for im in images:
        rgb = im.convert("RGBA")
        bg = Image.new("RGB", rgb.size, (0, 0, 0))
        bg.paste(rgb, (0, 0), rgb)
        combo.paste(bg, (x, 0))
        x += im.width
    quantized = combo.quantize(colors=max_colors, method=Image.MEDIANCUT)
    pal_raw = quantized.getpalette()[:max_colors * 3]
    colors = [tuple(pal_raw[i:i + 3]) for i in range(0, len(pal_raw), 3)]
    return colors


class EffectEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("DarkEden Effect Editor")
        self.root.geometry("1500x920")

        self.system = None
        self.current_frame_id = None
        self.current_direction = 0
        self.current_frame_index = 0
        self.playing = False
        self._play_job = None
        self._photo = None

        self._build_ui()
        self._try_auto_open()

    # -------------------------------------------------------------- UI build
    def _build_ui(self):
        tb = ttk.Frame(self.root)
        tb.pack(fill=tk.X, padx=4, pady=4)

        ttk.Button(tb, text="Abrir pasta Data...", command=self._open_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Salvar", command=self._save).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y)
        ttk.Button(tb, text="Novo efeito...", command=self._new_effect).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Importar frame de imagem...", command=self._import_frame).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Exportar frame atual...", command=self._export_frame).pack(side=tk.LEFT, padx=2)

        ttk.Label(tb, text="Filtro:").pack(side=tk.LEFT, padx=(12, 2))
        self.filter_var = tk.StringVar(value="")
        filt = ttk.Entry(tb, textvariable=self.filter_var, width=16)
        filt.pack(side=tk.LEFT)
        filt.bind("<KeyRelease>", lambda e: self._populate_frame_list())

        self.only_with_data_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tb, text="So' com animacao", variable=self.only_with_data_var,
                        command=self._populate_frame_list).pack(side=tk.LEFT, padx=8)

        sb = ttk.Frame(self.root)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar(value="Pronto.")
        ttk.Label(sb, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN).pack(
            side=tk.LEFT, fill=tk.X, expand=True)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ------------------------------------------------ left: frame list
        left = ttk.Frame(main)
        ttk.Label(left, text="Efeitos (FrameID: BltType):").pack(anchor=tk.W)
        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.frame_listbox = tk.Listbox(list_frame, exportselection=False, width=20, font=("Consolas", 9))
        sb_left = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.frame_listbox.yview)
        self.frame_listbox.config(yscrollcommand=sb_left.set)
        self.frame_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_left.pack(side=tk.RIGHT, fill=tk.Y)
        self.frame_listbox.bind("<<ListboxSelect>>", lambda e: self._on_select_frame())
        main.add(left, weight=1)

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

        # ------------------------------------------------- right: properties
        right = ttk.Frame(main)
        ttk.Label(right, text="Direcoes / Frames:").pack(anchor=tk.W)
        self.dirtree = ttk.Treeview(right, columns=("info",), show="tree headings", height=14)
        self.dirtree.heading("#0", text="Direcao/Frame")
        self.dirtree.heading("info", text="sprite / cx,cy / luz")
        self.dirtree.pack(fill=tk.BOTH, expand=True)
        self.dirtree.bind("<<TreeviewSelect>>", lambda e: self._on_tree_select())

        prop = ttk.LabelFrame(right, text="Frame selecionado")
        prop.pack(fill=tk.X, pady=6)
        self.prop_vars = {}
        for i, label in enumerate(["Sprite ID", "CX", "CY", "Luz (0-127)"]):
            ttk.Label(prop, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=2, pady=2)
            var = tk.StringVar(value="0")
            ttk.Entry(prop, textvariable=var, width=10).grid(row=i, column=1, sticky=tk.W, padx=2, pady=2)
            self.prop_vars[label] = var
        self.bg_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(prop, text="Fundo (atras do personagem)", variable=self.bg_var).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)
        ttk.Button(prop, text="Aplicar", command=self._apply_frame_props).grid(
            row=5, column=0, columnspan=2, pady=4)

        btns = ttk.Frame(right)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="+ Direcao", command=self._add_direction).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="- Direcao", command=self._remove_direction).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="- Frame", command=self._remove_frame).pack(side=tk.LEFT, padx=2)

        main.add(right, weight=1)

    # -------------------------------------------------------------- File I/O
    def _try_auto_open(self):
        info_path = os.path.join(CLIENT_DIR, "Data", "Info", "EffectSpriteType.inf")
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
            self.system = effect.EffectSystem(data_dir)
        except Exception as e:
            messagebox.showerror("Erro ao abrir", str(e))
            return
        self._populate_frame_list()
        self._set_status(
            f"{len(self.system.sprite_types.records)} tipos de efeito, "
            f"{self.system.sprites.count} sprites, {self.system.palettes.count} paletas, "
            f"{len(self.system.frames.frames)} FrameIDs com animacao carregados de {data_dir}.")

    def _save(self):
        if not self.system:
            return
        try:
            self.system.save_all()
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return
        self._set_status("Salvo (Effect.aspk/.aspki, .ppk/.ppki, .efpk/.efpki) - backup automatico criado.")
        messagebox.showinfo("Salvo",
            "Effect.aspk/.aspki, Effect.ppk/.ppki e Effect.efpk/.efpki foram salvos, "
            "com backup automatico dos arquivos anteriores ao lado.\n\n"
            "EffectSpriteType.inf so' e' salvo se voce criou um efeito novo (isso ja' "
            "salva automaticamente na hora).")

    # -------------------------------------------------------------- Frame list
    def _populate_frame_list(self):
        """So' lista registros do tipo EFFECT (blt_type==1) - e' o unico
        tipo cujo campo frame_id indexa Effect.aspk/.ppk/.efpk, os arquivos
        que este editor le'/grava. NORMAL/SCREEN/SHADOW usam suas PROPRIAS
        familias de arquivo (NormalEffect.*, EffectScreen.*, ShadowEffect.*)
        com seus proprios contadores de frame_id comecando do zero -
        mostrar eles aqui misturado daria acesso ao Effect.aspk errado.
        Ver EffectSpriteTypeRecord e o comentario em darkeden_effect.py."""
        self.frame_listbox.delete(0, tk.END)
        if not self.system:
            return
        filt = self.filter_var.get().strip()
        only_data = self.only_with_data_var.get()
        self._listed_frame_ids = []
        for r in self.system.sprite_types.records:
            if r.blt_type != 1:  # so' EFFECT - ver docstring do metodo
                continue
            if filt and filt not in str(r.frame_id):
                continue
            if only_data:
                if r.frame_id >= len(self.system.frames.frames):
                    continue
                directions = self.system.frames.frames[r.frame_id]
                if not directions or not any(len(d) for d in directions):
                    continue
            self._listed_frame_ids.append(r.frame_id)
            self.frame_listbox.insert(tk.END, f"{r.frame_id:5d}  {r.blt_type_name}")

    def _on_select_frame(self):
        sel = self.frame_listbox.curselection()
        if not sel:
            return
        frame_id = self._listed_frame_ids[sel[0]]
        self._select_frame_id(frame_id)

    def _select_frame_id(self, frame_id):
        self.current_frame_id = frame_id
        self.current_direction = 0
        self.current_frame_index = 0
        self._stop_play()

        directions = []
        if frame_id < len(self.system.frames.frames):
            directions = self.system.frames.frames[frame_id]
        n_dirs = max(1, len(directions))
        self.direction_spin.config(to=max(0, n_dirs - 1))
        self.direction_var.set(0)

        self._populate_dirtree()
        self._update_frame_spin_range()
        self._redraw()

    # -------------------------------------------------------------- Tree
    def _populate_dirtree(self):
        for item in self.dirtree.get_children():
            self.dirtree.delete(item)
        if self.current_frame_id is None or self.current_frame_id >= len(self.system.frames.frames):
            return
        directions = self.system.frames.frames[self.current_frame_id]
        for di, frames in enumerate(directions):
            dnode = self.dirtree.insert("", tk.END, iid=f"d{di}", text=f"Direcao {di}",
                                         values=(f"{len(frames)} frame(s)",))
            for fi, fr in enumerate(frames):
                self.dirtree.insert(dnode, tk.END, iid=f"d{di}f{fi}", text=f"  frame {fi}",
                                     values=(f"spr={fr.sprite_id} cx={fr.cx} cy={fr.cy} luz={fr.light}",))

    def _on_tree_select(self):
        sel = self.dirtree.selection()
        if not sel:
            return
        iid = sel[0]
        if "f" in iid[1:]:
            di, fi = iid[1:].split("f")
            self.current_direction = int(di)
            self.current_frame_index = int(fi)
            self.direction_var.set(self.current_direction)
            self.frame_var.set(self.current_frame_index)
            self._load_frame_props()
            self._redraw()

    # -------------------------------------------------------------- Preview
    def _current_direction_frames(self):
        if self.current_frame_id is None or self.current_frame_id >= len(self.system.frames.frames):
            return []
        directions = self.system.frames.frames[self.current_frame_id]
        if not directions or self.current_direction >= len(directions):
            return []
        return directions[self.current_direction]

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
        self._load_frame_props()
        self._redraw()

    def _load_frame_props(self):
        frames = self._current_direction_frames()
        if not frames or self.current_frame_index >= len(frames):
            return
        fr = frames[self.current_frame_index]
        self.prop_vars["Sprite ID"].set(str(fr.sprite_id))
        self.prop_vars["CX"].set(str(fr.cx))
        self.prop_vars["CY"].set(str(fr.cy))
        self.prop_vars["Luz (0-127)"].set(str(fr.light))
        self.bg_var.set(fr.background)

    def _apply_frame_props(self):
        frames = self._current_direction_frames()
        if not frames or self.current_frame_index >= len(frames):
            return
        fr = frames[self.current_frame_index]
        try:
            fr.sprite_id = int(self.prop_vars["Sprite ID"].get())
            fr.cx = int(self.prop_vars["CX"].get())
            fr.cy = int(self.prop_vars["CY"].get())
            fr.light = max(0, min(127, int(self.prop_vars["Luz (0-127)"].get())))
            fr.background = self.bg_var.get()
        except ValueError:
            messagebox.showerror("Valor invalido", "X/Y/Luz/Sprite ID precisam ser numeros inteiros.")
            return
        self._populate_dirtree()
        self._redraw()
        self._set_status("Frame atualizado (em memoria) - use Salvar pra' gravar em disco.")

    def _redraw(self):
        self.canvas.delete("all")
        if Image is None or self.system is None or self.current_frame_id is None:
            return
        frames = self._current_direction_frames()
        if not frames or self.current_frame_index >= len(frames):
            return
        fr = frames[self.current_frame_index]
        try:
            sprite = self.system.decode_sprite(fr.sprite_id, self.current_frame_id)
        except Exception as e:
            self._set_status(f"Erro decodificando sprite {fr.sprite_id}: {e}")
            return
        if sprite.width == 0 or sprite.height == 0:
            return

        cw = self.canvas.winfo_width() or 400
        ch = self.canvas.winfo_height() or 400
        # canvas grande, efeito pequeno e centralizado - o sprite ocupa so'
        # uma fracao do lado menor do canvas (nao mais metade dele).
        scale = max(1, min(6, min(cw, ch) // max(sprite.width, sprite.height, 1) // 4))

        img = Image.frombytes("RGBA", (sprite.width, sprite.height), sprite.rgba)
        if scale > 1:
            img = img.resize((sprite.width * scale, sprite.height * scale), Image.NEAREST)

        bg = Image.new("RGB", img.size, CANVAS_BG)
        bg.paste(img, (0, 0), img)
        self._photo = ImageTk.PhotoImage(bg)

        cx = cw / 2 + fr.cx * scale
        cy = ch / 2 + fr.cy * scale
        self.canvas.create_line(cw / 2 - 10, ch / 2, cw / 2 + 10, ch / 2, fill="#666")
        self.canvas.create_line(cw / 2, ch / 2 - 10, cw / 2, ch / 2 + 10, fill="#666")
        self.canvas.create_image(cx, cy, image=self._photo, anchor=tk.CENTER)
        self.canvas.create_text(
            8, 8, anchor=tk.NW, fill="#aaa", font=("Arial", 9),
            text=f"FrameID {self.current_frame_id}  dir {self.current_direction}  "
                 f"frame {self.current_frame_index}/{max(0, len(frames) - 1)}  "
                 f"sprite {fr.sprite_id} ({sprite.width}x{sprite.height})"
                 f"{'  [FUNDO]' if fr.background else ''}")

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

    # -------------------------------------------------------------- Structure edits
    def _add_direction(self):
        if self.current_frame_id is None:
            return
        self.system.frames.ensure_frame_id(self.current_frame_id)
        self.system.frames.frames[self.current_frame_id].append([])
        n_dirs = len(self.system.frames.frames[self.current_frame_id])
        self.direction_spin.config(to=max(0, n_dirs - 1))
        self._populate_dirtree()
        self._set_status(f"Direcao {n_dirs - 1} adicionada ao FrameID {self.current_frame_id}.")

    def _remove_direction(self):
        if self.current_frame_id is None:
            return
        directions = self.system.frames.frames[self.current_frame_id]
        if not directions or not (0 <= self.current_direction < len(directions)):
            return
        if not messagebox.askyesno("Confirmar", f"Remover a direcao {self.current_direction} inteira?"):
            return
        directions.pop(self.current_direction)
        self.current_direction = 0
        self.direction_var.set(0)
        n_dirs = len(directions)
        self.direction_spin.config(to=max(0, n_dirs - 1))
        self._populate_dirtree()
        self._update_frame_spin_range()
        self._redraw()

    def _remove_frame(self):
        frames = self._current_direction_frames()
        if not frames or self.current_frame_index >= len(frames):
            return
        if not messagebox.askyesno("Confirmar", "Remover esse frame da animacao?"):
            return
        frames.pop(self.current_frame_index)
        self.current_frame_index = max(0, self.current_frame_index - 1)
        self.frame_var.set(self.current_frame_index)
        self._update_frame_spin_range()
        self._populate_dirtree()
        self._redraw()

    # -------------------------------------------------------------- New effect
    def _new_effect(self):
        if not self.system:
            messagebox.showwarning("Abra a pasta Data primeiro", "Precisa abrir a pasta Data do cliente antes.")
            return
        # o novo registro entra no FIM CRU da tabela (table_position) - isso
        # NUNCA desloca nenhum registro existente, entao nada em NENHUM
        # outro arquivo do jogo que referencie um FrameID por numero quebra.
        # O frame_id de verdade (usado pra' indexar Effect.aspk/.ppk/.efpk)
        # e' um contador SEPARADO, proprio do BltType EFFECT - ver docstring
        # de EffectSpriteTypeRecord.
        table_position = len(self.system.sprite_types.records)
        new_id = sum(1 for r in self.system.sprite_types.records if r.blt_type == 1)
        rec = effect.EffectSpriteTypeRecord(
            table_position, new_id, blt_type=1, flag=0,
            action_effect_frame_id=effect.FRAMEID_NULL,
            female_effect_sprite_type=effect.FRAMEID_NULL,
            pair_frame_ids=[])
        self.system.sprite_types.records.append(rec)

        self.system.frames.ensure_frame_id(new_id)
        self.system.frames.frames[new_id] = [[] for _ in range(8)]

        # paleta vazia (256 cores pretas) - so' preenchida de verdade quando
        # o primeiro frame for importado de uma imagem (ver _import_frame)
        empty_colors = [(0, 0, 0)] * 2
        pal_bytes = effect.PalettePack.encode_palette(empty_colors)
        self.system.palettes.append_palette(pal_bytes)

        # salva a tabela de tipos AGORA (e' o unico arquivo que nao entra
        # no "Salvar" principal, ver _save())
        info_path = os.path.join(self.system.data_dir, "Info", "EffectSpriteType.inf")
        self.system.sprite_types.save(info_path)

        self._populate_frame_list()
        self._set_status(f"Efeito novo criado: FrameID {new_id} (tipo EFFECT, 8 direcoes vazias). "
                          "Importe uma imagem pra' cada direcao/frame e depois Salvar.")
        messagebox.showinfo("Efeito criado",
            f"FrameID {new_id} criado (EffectSpriteType.inf ja' foi salvo).\n\n"
            "Agora selecione ele na lista, escolha uma direcao, e use "
            "'Importar frame de imagem...' pra' adicionar os sprites.")

    # -------------------------------------------------------------- Import/export
    def _import_frame(self):
        if self.current_frame_id is None:
            messagebox.showwarning("Selecione um efeito", "Escolha (ou crie) um efeito na lista primeiro.")
            return
        if Image is None:
            messagebox.showerror("Falta Pillow", "Instale Pillow (pip install Pillow) pra' importar imagens.")
            return
        path = filedialog.askopenfilename(
            title="Escolha a imagem do frame (PNG com transparencia recomendado)",
            filetypes=[("Imagens", "*.png;*.tga;*.bmp"), ("Todos", "*.*")])
        if not path:
            return

        img = Image.open(path).convert("RGBA")
        pal = self.system.get_palette(self.current_frame_id)

        if len(pal.colors) <= 2:
            # paleta ainda vazia (efeito novo) - constroi uma paleta nova
            # a partir desta primeira imagem
            new_colors = build_palette_from_images([img])
            pal = effect.Palette(new_colors)
            self.system._palette_cache[self.current_frame_id] = pal
            # reescreve a entrada da paleta no pack (ainda so' em memoria)
            ppk = self.system.palettes
            ppk._offsets = None
            # troca so' funciona reconstruindo o pack inteiro de forma simples:
            # remonta o registro daquele FrameID concatenando antes/depois
            self._replace_palette_entry(self.current_frame_id, new_colors)

        rows = image_to_pal_index_rows(img, pal.colors)
        sprite_bytes = effect.AlphaSpritePack.encode_sprite(img.width, img.height, rows)
        new_sprite_id = self.system.sprites.append_sprite(sprite_bytes)

        self.system.frames.ensure_frame_id(self.current_frame_id)
        directions = self.system.frames.frames[self.current_frame_id]
        while len(directions) <= self.current_direction:
            directions.append([])
        directions[self.current_direction].append(
            effect.EffectFrame(new_sprite_id, 0, 0, 0, False))

        self._populate_dirtree()
        self._update_frame_spin_range()
        self.current_frame_index = len(directions[self.current_direction]) - 1
        self.frame_var.set(self.current_frame_index)
        self._redraw()
        self._set_status(f"Sprite {new_sprite_id} importado de {os.path.basename(path)} "
                          f"({img.width}x{img.height}) - adicionado como novo frame. Use Salvar pra' gravar.")

    def _replace_palette_entry(self, frame_id, new_colors):
        """Reconstroi Effect.ppk trocando so' a paleta do frame_id dado -
        usado quando um efeito novo (paleta vazia) recebe sua primeira
        imagem importada."""
        ppk = self.system.palettes
        entries = []
        for i in range(ppk.count):
            entries.append(ppk.decode(i).colors if i != frame_id else new_colors)
        if frame_id >= ppk.count:
            entries.append(new_colors)
        out = bytearray(struct.pack("<H", len(entries)))
        offsets = []
        pos = 2
        blobs = []
        for colors in entries:
            offsets.append(pos)
            b = effect.PalettePack.encode_palette(colors)
            blobs.append(b)
            pos += len(b)
        for b in blobs:
            out += b
        ppk.data = bytes(out)
        ppk.count = len(entries)
        ppk._offsets = offsets

    def _export_frame(self):
        if self.current_frame_id is None:
            return
        frames = self._current_direction_frames()
        if not frames or self.current_frame_index >= len(frames):
            messagebox.showwarning("Nada selecionado", "Selecione um frame com animacao primeiro.")
            return
        fr = frames[self.current_frame_index]
        sprite = self.system.decode_sprite(fr.sprite_id, self.current_frame_id)
        if sprite.width == 0 or sprite.height == 0:
            messagebox.showwarning("Sprite vazio", "Esse frame nao tem pixels (sprite vazio).")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=f"effect_{self.current_frame_id}_dir{self.current_direction}_f{self.current_frame_index}.png",
            filetypes=[("PNG", "*.png")])
        if not path:
            return
        img = Image.frombytes("RGBA", (sprite.width, sprite.height), sprite.rgba)
        img.save(path)
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
    EffectEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
