#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DarkEden UI Skin Editor - troca a ARTE de verdade das telas de TITULO,
LOGIN e SELECAO DE PERSONAGEM (fundo + botoes) - mesmo padrao dos outros
editores desta pasta, mas complementar ao `darkeden_interface_editor.py`:
aquele reposiciona PONTOS (onde cada coisa fica); este troca IMAGENS (o
que cada coisa mostra). Ver `darkeden_uiskin.py` pro formato completo e as
citacoes do codigo-fonte C++ de cada tela/botao.

Uso:
    python darkeden_uiskin_editor.py
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import darkeden_uiskin as uiskin

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

# ---------------------------------------------------------------------------
CLIENT_DIR = r"C:\Users\Victoria\OneDrive\Área de Trabalho\DARKEDEN"

CANVAS_BG = (32, 32, 44)
HIGHLIGHT_COLOR = "#ff4040"


def _rgb_mask_to_rgba(width, height, rgb, mask):
    rgba = bytearray(width * height * 4)
    for i in range(width * height):
        rgba[i * 4:i * 4 + 3] = rgb[i * 3:i * 3 + 3]
        rgba[i * 4 + 3] = mask[i]
    return bytes(rgba)


class UiSkinEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("DarkEden UI Skin Editor")
        self.root.geometry("1500x900")

        self.system = None
        self.screen_key = "TITLE"
        self.current_asset = None
        self._scene_photo = None
        self._asset_photo = None

        self._build_ui()
        self._try_auto_open()

    # -------------------------------------------------------------- UI build
    def _build_ui(self):
        tb = ttk.Frame(self.root)
        tb.pack(fill=tk.X, padx=4, pady=4)

        ttk.Button(tb, text="Abrir pasta Data...", command=self._open_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Salvar tudo modificado", command=self._save).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Descobrir .spk...", command=self._discover_spk).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y)

        ttk.Label(tb, text="Tela:").pack(side=tk.LEFT, padx=(4, 2))
        self.screen_var = tk.StringVar(value=uiskin.SCREENS["TITLE"]["label"])
        screen_labels = [s["label"] for s in uiskin.SCREENS.values()]
        screen_combo = ttk.Combobox(tb, textvariable=self.screen_var, values=screen_labels,
                                     state="readonly", width=36)
        screen_combo.pack(side=tk.LEFT, padx=2)
        screen_combo.bind("<<ComboboxSelected>>", lambda e: self._on_screen_change())

        ttk.Label(tb, text="Raca:").pack(side=tk.LEFT, padx=(8, 2))
        self.race_var = tk.StringVar(value="SLAYER")
        self.race_combo = ttk.Combobox(tb, textvariable=self.race_var, values=["SLAYER", "VAMPIRE", "OUSTERS"],
                                        state="readonly", width=10)
        self.race_combo.pack(side=tk.LEFT, padx=2)
        self.race_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_asset_list())
        self.race_combo.config(state="disabled")

        sb = ttk.Frame(self.root)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar(value="Pronto.")
        ttk.Label(sb, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN).pack(
            side=tk.LEFT, fill=tk.X, expand=True)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ------------------------------------------------ left: asset list
        left = ttk.Frame(main)
        ttk.Label(left, text="Partes trocaveis:").pack(anchor=tk.W)
        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.asset_listbox = tk.Listbox(list_frame, exportselection=False, width=34, font=("Consolas", 9))
        sb_left = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.asset_listbox.yview)
        self.asset_listbox.config(yscrollcommand=sb_left.set)
        self.asset_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_left.pack(side=tk.RIGHT, fill=tk.Y)
        self.asset_listbox.bind("<<ListboxSelect>>", lambda e: self._on_select_asset())
        main.add(left, weight=2)

        # ------------------------------------------------- center: scene preview
        center = ttk.Frame(main)
        ttk.Label(center, text="Preview da tela inteira (o quadrado vermelho marca a parte selecionada):").pack(anchor=tk.W)
        self.scene_canvas = tk.Canvas(center, bg="#202028", highlightthickness=1, highlightbackground="#666")
        self.scene_canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        main.add(center, weight=6)

        # ------------------------------------------------- right: asset editor
        right = ttk.Frame(main)
        ttk.Label(right, text="Parte selecionada:").pack(anchor=tk.W)
        self.asset_label_var = tk.StringVar(value="-")
        ttk.Label(right, textvariable=self.asset_label_var, wraplength=260, font=("Arial", 10, "bold")).pack(
            anchor=tk.W, pady=(0, 6))

        self.asset_canvas = tk.Canvas(right, bg="#202028", height=220, highlightthickness=1,
                                       highlightbackground="#666")
        self.asset_canvas.pack(fill=tk.X, pady=(0, 6))

        self.asset_info_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.asset_info_var).pack(anchor=tk.W)

        self.resize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right, text="Redimensionar a imagem nova pro tamanho original",
                        variable=self.resize_var).pack(anchor=tk.W, pady=(8, 2))

        ttk.Button(right, text="Importar imagem...", command=self._import_image).pack(fill=tk.X, pady=2)
        ttk.Button(right, text="Exportar imagem atual...", command=self._export_image).pack(fill=tk.X, pady=2)

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(right, text="Arquivos modificados (nao salvos):").pack(anchor=tk.W)
        self.modified_var = tk.StringVar(value="(nenhum)")
        ttk.Label(right, textvariable=self.modified_var, wraplength=260, foreground="#c04040").pack(anchor=tk.W)

        main.add(right, weight=3)

    # -------------------------------------------------------------- File I/O
    def _try_auto_open(self):
        data_dir = os.path.join(CLIENT_DIR, "Data")
        if os.path.isdir(os.path.join(data_dir, "Ui", "spk")):
            self._open(data_dir)
        else:
            self._set_status("Abra a pasta Data do cliente (botao 'Abrir pasta Data...').")

    def _open_dialog(self):
        p = filedialog.askdirectory(title="Escolha a pasta Data do cliente DarkEden",
                                     initialdir=CLIENT_DIR)
        if p:
            self._open(p)

    def _open(self, data_dir):
        self.system = uiskin.UiSkinSystem(data_dir)
        self._populate_asset_list()
        self._set_status(f"Carregado de {data_dir}. Escolha uma tela e uma parte pra editar.")

    def _save(self):
        if not self.system:
            return
        try:
            saved = self.system.save_all_modified()
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return
        if not saved:
            messagebox.showinfo("Nada pra salvar", "Nenhum arquivo foi modificado ainda nesta sessao.")
            return
        self._update_modified_label()
        self._set_status(f"Salvos: {', '.join(saved)} (.spk + .spki, com backup automatico).")
        messagebox.showinfo("Salvo", f"Arquivos gravados (com backup automatico):\n\n" + "\n".join(saved))

    # -------------------------------------------------------------- Screen/asset list
    def _current_screen(self):
        for key, screen in uiskin.SCREENS.items():
            if screen["label"] == self.screen_var.get():
                return key, screen
        return "TITLE", uiskin.SCREENS["TITLE"]

    def _on_screen_change(self):
        self.screen_key, screen = self._current_screen()
        self.race_combo.config(state="readonly" if screen["needs_race"] else "disabled")
        self._populate_asset_list()

    def _populate_asset_list(self):
        self.asset_listbox.delete(0, tk.END)
        self.screen_key, screen = self._current_screen()
        if not self.system:
            self._listed_assets = []
            return
        self._listed_assets = self.system.list_assets(self.screen_key, self.race_var.get())
        for asset in self._listed_assets:
            tag = "[fundo] " if asset.is_background else ""
            self.asset_listbox.insert(tk.END, f"{tag}{asset.label}")
        self.current_asset = None
        self._redraw_scene()
        self._redraw_asset()

    def _on_select_asset(self):
        sel = self.asset_listbox.curselection()
        if not sel:
            return
        self.current_asset = self._listed_assets[sel[0]]
        self.asset_label_var.set(self.current_asset.label)
        self._redraw_scene()
        self._redraw_asset()

    # -------------------------------------------------------------- Rendering
    def _redraw_scene(self):
        self.scene_canvas.delete("all")
        if Image is None or self.system is None:
            return
        _key, screen = self._current_screen()
        assets = self._listed_assets

        # tamanho da tela = bbox de todas as camadas de FUNDO (mais robusto
        # que um "size" fixo por tela - OPTION/GAME_MENU nao tem um tamanho
        # unico documentado aqui, e o fundo real ja' diz o tamanho certo)
        sw = sh = 0
        decoded = {}
        for asset in assets:
            try:
                w, h, rgb, mask = self.system.decode_asset(asset)
            except Exception:
                continue
            decoded[asset.key] = (w, h, rgb, mask)
            if not w or not h:
                continue
            for (x, y) in asset.positions:
                sw = max(sw, x + w)
                sh = max(sh, y + h)
        sw = sw or 800
        sh = sh or 600

        composite = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        for asset in assets:
            w, h, rgb, mask = decoded.get(asset.key, (0, 0, b'', b''))
            if not w or not h:
                continue
            rgba = _rgb_mask_to_rgba(w, h, rgb, mask)
            img = Image.frombytes("RGBA", (w, h), rgba)
            for (x, y) in asset.positions:
                composite.paste(img, (x, y), img)

        cw = self.scene_canvas.winfo_width() or 800
        ch = self.scene_canvas.winfo_height() or 600
        scale = min(1.0, (cw - 20) / sw, (ch - 20) / sh)
        if scale <= 0:
            scale = 1.0
        disp_w, disp_h = max(1, int(sw * scale)), max(1, int(sh * scale))
        disp_img = composite.resize((disp_w, disp_h), Image.LANCZOS) if scale != 1.0 else composite

        bg = Image.new("RGB", disp_img.size, CANVAS_BG)
        bg.paste(disp_img, (0, 0), disp_img)
        self._scene_photo = ImageTk.PhotoImage(bg)

        ox = (cw - disp_w) / 2
        oy = (ch - disp_h) / 2
        self.scene_canvas.create_image(ox, oy, image=self._scene_photo, anchor=tk.NW)

        if self.current_asset is not None:
            w, h, _rgb, _mask = self.system.decode_asset(self.current_asset)
            for (x, y) in self.current_asset.positions:
                x0 = ox + x * scale
                y0 = oy + y * scale
                x1 = ox + (x + w) * scale
                y1 = oy + (y + h) * scale
                self.scene_canvas.create_rectangle(x0, y0, x1, y1, outline=HIGHLIGHT_COLOR, width=2)

        self.scene_canvas.create_text(
            8, 8, anchor=tk.NW, fill="#aaa", font=("Arial", 9),
            text=f"{screen['label']} ({sw}x{sh}, modo classico)")

    def _redraw_asset(self):
        self.asset_canvas.delete("all")
        self.asset_info_var.set("")
        if Image is None or self.system is None or self.current_asset is None:
            return
        asset = self.current_asset
        try:
            w, h, rgb, mask = self.system.decode_asset(asset)
        except Exception as e:
            self.asset_info_var.set(f"Erro: {e}")
            return
        if not w or not h:
            self.asset_info_var.set(f"{asset.spk_filename} #{asset.sprite_index} - sprite vazio (0x0)")
            return

        rgba = _rgb_mask_to_rgba(w, h, rgb, mask)
        img = Image.frombytes("RGBA", (w, h), rgba)
        cw = self.asset_canvas.winfo_width() or 260
        ch = self.asset_canvas.winfo_height() or 220
        scale = max(1, min(6, int(min(cw, ch) * 0.8) // max(w, h, 1)))
        if scale > 1:
            img = img.resize((w * scale, h * scale), Image.NEAREST)
        bg = Image.new("RGB", img.size, CANVAS_BG)
        bg.paste(img, (0, 0), img)
        self._asset_photo = ImageTk.PhotoImage(bg)
        self.asset_canvas.create_image(cw / 2, ch / 2, image=self._asset_photo, anchor=tk.CENTER)

        n_pos = len(asset.positions)
        rep = f" (repetida {n_pos}x na tela)" if n_pos > 1 else ""
        self.asset_info_var.set(f"{asset.spk_filename} #{asset.sprite_index} - {w}x{h}{rep}")

    def _update_modified_label(self):
        if not self.system:
            return
        mods = self.system.modified_packs()
        self.modified_var.set(", ".join(mods) if mods else "(nenhum)")

    # -------------------------------------------------------------- Import/export
    def _import_image(self):
        if self.current_asset is None:
            messagebox.showwarning("Nada selecionado", "Escolha uma parte na lista primeiro.")
            return
        if Image is None:
            messagebox.showerror("Falta Pillow", "Instale Pillow (pip install Pillow) pra importar imagens.")
            return
        path = filedialog.askopenfilename(
            title="Escolha a imagem nova (PNG com transparencia recomendado)",
            filetypes=[("Imagens", "*.png;*.tga;*.bmp"), ("Todos", "*.*")])
        if not path:
            return
        try:
            w, h = self.system.replace_asset_image(self.current_asset, path, resize_to_original=self.resize_var.get())
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e))
            return
        self._update_modified_label()
        self._redraw_scene()
        self._redraw_asset()
        self._set_status(f"'{self.current_asset.label}' trocado por {os.path.basename(path)} ({w}x{h}) - "
                          f"em memoria, use 'Salvar tudo modificado' pra gravar em disco.")

    def _export_image(self):
        if self.current_asset is None:
            messagebox.showwarning("Nada selecionado", "Escolha uma parte na lista primeiro.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=f"{self.screen_key}_{self.current_asset.key}.png",
            filetypes=[("PNG", "*.png")])
        if not path:
            return
        try:
            self.system.export_asset_image(self.current_asset, path)
        except Exception as e:
            messagebox.showerror("Erro ao exportar", str(e))
            return
        self._set_status(f"Exportado para {path}")

    # -------------------------------------------------------------- Helpers
    def _set_status(self, msg):
        self.status_var.set(msg)

    # -------------------------------------------------------------- Discover .spk
    def _discover_spk(self):
        if not self.system:
            messagebox.showinfo("Abrir pasta primeiro",
                "Abra a pasta Data do cliente primeiro (botao 'Abrir pasta Data...').")
            return
        import darkeden_truesprite as truesprite
        data_dir = os.path.join(self.system.client_dir, "Data")
        uncovered = uiskin.discover_uncovered_spk(data_dir)
        if not uncovered:
            messagebox.showinfo("Nada novo",
                "Todos os arquivos .spk encontrados ja' estao cobertos pelas 46 telas mapeadas.\n"
                "(ou a pasta Data/Ui/spk/ nao foi encontrada)")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Arquivos .spk NAO mapeados ({len(uncovered)} encontrados)")
        dialog.geometry("640x480")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog,
            text=f"Ha' {len(uncovered)} arquivo(s) .spk na pasta do cliente que nao estao\n"
                 "em nenhuma das 46 telas mapeadas. Selecione um pra' navegar nos sprites:",
            justify=tk.LEFT).pack(padx=8, pady=(8, 2), anchor=tk.W)

        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        cols = ("#0", "Sprites", "Tamanho")
        tree = ttk.Treeview(frame, columns=cols[1:], show="tree headings", selectmode="browse")
        tree.heading("#0", text="Arquivo .spk")
        tree.heading("Sprites", text="Sprites")
        tree.heading("Tamanho", text="KB")
        tree.column("#0", width=320)
        tree.column("Sprites", width=80, anchor=tk.CENTER)
        tree.column("Tamanho", width=80, anchor=tk.CENTER)
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        for fname, n_sprites, size_kb in uncovered:
            tree.insert("", tk.END, text=fname,
                        values=(str(n_sprites) if n_sprites else "?", str(size_kb)))

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)

        # preview area
        preview_frame = ttk.LabelFrame(dialog, text="Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        preview_canvas = tk.Canvas(preview_frame, bg="#202028", highlightthickness=0)
        preview_canvas.pack(fill=tk.BOTH, expand=True)

        preview_info = tk.StringVar(value="Selecione um arquivo acima para ver os sprites.")
        ttk.Label(preview_frame, textvariable=preview_info,
                  foreground="#aaa", wraplength=600).pack(anchor=tk.W, padx=4)

        sprite_listbox = tk.Listbox(preview_frame, height=6, font=("Consolas", 9))
        sprite_listbox.pack(fill=tk.X, padx=4, pady=(0, 4))

        current_data = {}  # guarda (pack, preview_photos) pra nao perder ref

        def on_select_file():
            sel = tree.selection()
            if not sel:
                return
            fname = tree.item(sel[0], "text")
            fpath = os.path.join(data_dir, "Ui", "spk", fname)
            if not os.path.isfile(fpath):
                preview_info.set(f"Arquivo nao encontrado: {fpath}")
                return
            try:
                pack = truesprite.TrueSpritePack(fpath)
            except Exception as e:
                preview_info.set(f"Erro ao abrir: {e}")
                return
            current_data["pack"] = pack
            sprite_listbox.delete(0, tk.END)
            n = getattr(pack, "count", 0)
            if n == 0:
                # tenta descobrir por tentativa
                n = 0
                while True:
                    try:
                        w, h, _r, _m = pack.decode(n)
                        if w == 0 and h == 0:
                            break
                        n += 1
                    except Exception:
                        break
            for i in range(n):
                try:
                    w, h, _r, _m = pack.decode(i)
                    sprite_listbox.insert(tk.END, f"  #{i}  ({w}x{h})")
                except Exception:
                    sprite_listbox.insert(tk.END, f"  #{i}  (erro)")
            sprite_listbox.selection_set(0) if n > 0 else None
            preview_info.set(f"{fname}: {n} sprite(s) (somente visualizacao/exportacao)")
            on_select_sprite()

        def on_select_sprite():
            preview_canvas.delete("all")
            pack = current_data.get("pack")
            if not pack:
                return
            sel = sprite_listbox.curselection()
            if not sel:
                return
            idx_text = sprite_listbox.get(sel[0])
            try:
                idx = int(idx_text.strip().split(" ")[0].lstrip("#"))
            except (ValueError, IndexError):
                return
            try:
                w, h, rgb, mask = pack.decode(idx)
            except Exception as e:
                preview_info.set(f"Erro no sprite #{idx}: {e}")
                return
            if not w or not h:
                preview_info.set(f"#{idx}: sprite vazio (0x0)")
                return
            from PIL import Image, ImageTk
            rgba = bytearray(w * h * 4)
            for i in range(w * h):
                rgba[i * 4:i * 4 + 3] = rgb[i * 3:i * 3 + 3]
                rgba[i * 4 + 3] = mask[i]
            img = Image.frombytes("RGBA", (w, h), bytes(rgba))
            cw = preview_canvas.winfo_width() or 400
            ch = preview_canvas.winfo_height() or 200
            scale = min(6, max(1, int(min(cw, ch) * 0.85) // max(w, h, 1)))
            if scale > 1:
                img = img.resize((w * scale, h * scale), Image.NEAREST)
            bg = Image.new("RGB", img.size, (32, 32, 44))
            bg.paste(img, (0, 0), img)
            photo = ImageTk.PhotoImage(bg)
            current_data["photos"] = current_data.get("photos", []) + [photo]
            preview_canvas.create_image(cw / 2, ch / 2, image=photo, anchor=tk.CENTER)
            preview_info.set(f"#{idx} ({w}x{h}) - {fname}  |  Clique 'Exportar PNG' pra salvar")

        tree.bind("<<TreeviewSelect>>", lambda e: on_select_file())
        sprite_listbox.bind("<<ListboxSelect>>", lambda e: on_select_sprite())

        def do_export():
            pack = current_data.get("pack")
            if not pack:
                return
            sel = sprite_listbox.curselection()
            if not sel:
                return
            idx_text = sprite_listbox.get(sel[0])
            try:
                idx = int(idx_text.strip().split(" ")[0].lstrip("#"))
            except (ValueError, IndexError):
                return
            out = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=f"sprite_{idx}.png",
                filetypes=[("PNG", "*.png")])
            if not out:
                return
            try:
                w, h, rgb, mask = pack.decode(idx)
                if not w or not h:
                    raise ValueError("sprite vazio")
                from PIL import Image
                rgba = bytearray(w * h * 4)
                for i in range(w * h):
                    rgba[i * 4:i * 4 + 3] = rgb[i * 3:i * 3 + 3]
                    rgba[i * 4 + 3] = mask[i]
                Image.frombytes("RGBA", (w, h), bytes(rgba)).save(out)
                preview_info.set(f"Exportado #{idx} -> {out}")
            except Exception as ex:
                messagebox.showerror("Erro", str(ex))

        ttk.Button(btn_frame, text="Exportar PNG", command=do_export).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Fechar", command=dialog.destroy).pack(side=tk.RIGHT, padx=2)
        self.status_var.set(msg)


def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    UiSkinEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
