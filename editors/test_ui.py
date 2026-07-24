# -*- coding: utf-8 -*-
"""Teste intensivo do SkillEditor: instancia + carrega dados + seleciona skill + troca aba."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))

import tkinter as tk
from darkeden_skill_editor import SkillEditor, CLIENT_DIR

root = tk.Tk()
root.withdraw()
data_dir = os.path.join(CLIENT_DIR, "Data")

try:
    editor = SkillEditor(root)
    print("✓ Instanciado")
except Exception as e:
    print(f"✗ Instanciacao: {e}")
    import traceback; traceback.print_exc()
    root.destroy(); sys.exit(1)

if not os.path.isdir(data_dir):
    print(f"⚠ Data dir não encontrado em {data_dir}, pulando testes interativos.")
    root.after(100, root.destroy)
    root.mainloop()
    print("✓ Teste basico concluido")
    sys.exit(0)

# Forca a abertura com o caminho real
def run_tests():
    try:
        editor._open(data_dir)
        print(f"✓ Action.inf aberto: {len(editor.tbl.records)} skills")

        # Seleciona a primeira skill na lista
        children = editor.skill_tree.get_children()
        if children:
            editor.skill_tree.selection_set(children[0])
            editor._on_select_skill()
            print("✓ Skill 0 selecionada")

        # Seleciona um efeito na grid
        grid_children = editor.effects_grid_tree.get_children()
        if grid_children:
            editor.effects_grid_tree.selection_set(grid_children[0])
            editor._on_select_effect_grid()
            print("✓ Efeito 0 na grid selecionado")

            # Troca para a aba Anim Preview
            editor.slots_notebook.select(1)
            editor._redraw()
            print("✓ Anim Preview ativado e redrawn")

        # Forca um redraw da preview central
        editor._redraw()
        print("✓ Redraw da preview central concluido")

        print("✓ Todos os testes passaram sem TclError!")
    except Exception as e:
        print(f"✗ ERRO durante testes: {e}")
        import traceback; traceback.print_exc()
    finally:
        root.destroy()

root.after(500, run_tests)
root.mainloop()
