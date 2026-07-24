"""
ItemOption.py - DarkEden ItemOption.inf editor (enchant/prefix option pool)
=============================================================================
Original tool by TigerBlitz.

Fixed/precision-verified by VictorRP7 (2026-07-21).

BUG FIX: loading correctly read the 38 part-category headers (STR/DEX/INT/
HP/MP/etc. and their tier names), but they were never stored anywhere -
save_to_file() wrote them back out as 38 BLANK strings, silently wiping the
category names from the real file on every save. Now the headers read at
load time are kept (see ItemOptionTable.part_headers) and written back
unchanged. Verified with a load -> save -> byte-compare round trip against
the real itemOption.inf (identical output).

BINARY LAYOUT: confirmed correct as-is against client-master\\Client\\
MItemOptionTable.h/.cpp (class ITEMOPTION_INFO / ITEMOPTION_TABLE) - no
offset bugs here, unlike the older Item.inf editor this project also fixes.

FIELD SEMANTICS: every numeric field below was cross-checked against the
real getter/consumer code in the client (MItem.cpp, MPriceManager.cpp) and
the server (OptionInfo.h/.cpp, InitAllStat.cpp, MonsterManager.cpp) so the
UI labels/hints reflect what the game actually does with each value, not
just a guess from the field name:
  - color_set: an index (0-494) into the SAME generated 495x30 sprite tint
    palette used by Item.inf/darkeden_sprite.py (CIndexSprite::ColorSet) -
    NOT a raw color or a small enum. Sentinels 0xfffe/0xffff force the
    special "quest item"/"unique item" glow color regardless of this field.
  - upgrade_option_type / previous_option_type: indices into THIS SAME
    item list (not the Part table) - "becomes option #X on successful
    upgrade" / "reverts to option #Y on failure". 0 = no upgrade/downgrade
    path (index 0 is itself the reserved "NONE" option in the real data).
  - price_multiplier: a percentage, 100 = no change. The game SUMS this
    across every option currently on an item, then applies
    finalPrice = finalPrice * sum / 100 - so two +50% options together
    make an item worth 2x, not 1.5x twice.
  - plus_point: flat additive for most parts, EXCEPT the six STR/DEX/INT
    "transfer" parts (24-29, e.g. "STR to DEX") where it's a percentage OF
    THE BASE STAT moved from one to the other, and PART_DURABILITY (13)
    where - like price_multiplier - it's a 100-baseline percentage applied
    to max durability, not a flat point add.
  - require_str / require_dex / require_int: loaded and have live getters,
    but every call site that would apply them is commented out in both the
    client and server source - they are VESTIGIAL/DEAD in the running game.
    Kept editable for completeness, but flagged in the UI.
  - require_sum: very much alive, but applied doubled to the item's
    effective STR/DEX/INT requirement and singly to its total-stat
    requirement (mirrors Item.inf's own RequireSUM, just from a different
    field on a different struct).
  - require_level: alive, flat additive to the base item's RequireLevel.
  - PART_TRANS (31, "translate race language") is vestigial - no live code
    applies it either. PART_POTION_PRICE (35)'s C++ header comment is
    mislabeled "decrease gamble price" (copy/paste typo in the client's own
    source) but its actual behavior (confirmed via OPTION_POTION_PRICE /
    m_PotionPriceRatio) matches its name, "Decrease Potion Price" - cosmetic
    source bug only, not reflected here.

ItemOption.inf is NOT the same data as Item.inf - it's the separate pool of
random enchant bonuses (e.g. "+8 INT", "+12 HP") that can be rolled onto a
piece of equipment, referenced by index from Item.inf's DefaultOptionList
(see ItemINF_Editor.py / darkeden_sprite.py in this same folder).
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import struct
import os
import sys
import webbrowser

NONE_OPTION_INDEX = 0  # item list index 0 is the reserved "no option" placeholder in the real data
PERCENT_BASED_PARTS = {13, 24, 25, 26, 27, 28, 29}  # Durability + the 6 STR/DEX/INT transfer parts

# A live icon preview (cross-referencing Item.inf to find & render the real
# item that uses a given option, tinted with its Color Set) was attempted
# and thoroughly unit-tested here on 2026-07-21 - an exhaustive scripted
# click-through of all 198 options via the real event handler only ever
# produced correct equipment matches (rings/weapons/armor, never a pet or
# potion). Despite that, it never displayed correctly in actual live use
# (reported: showed pet/consumable names instead of equipment) and the
# mismatch could not be reproduced or isolated after several passes, so the
# feature was removed rather than ship something unverified. See README.md
# ("Tentativas descartadas") for the full writeup - color_set stays a plain
# editable number instead.

class ItemOptionInfo:
    """ITEMOPTION_INFO sınıfı - Basitleştirilmiş"""
    def __init__(self):
        self.ename = ""                 # İngilizce isim
        self.name = ""                  # Yerel isim
        self.part = 0                   # Özellik tipi
        self.plus_point = 0             # Artış değeri
        self.price_multiplier = 0       # Fiyat çarpanı (%)
        self.require_str = 0            # Gerekli güç
        self.require_dex = 0            # Gerekli çeviklik
        self.require_int = 0            # Gerekli zeka
        self.require_sum = 0            # Gerekli toplam özellik
        self.require_level = 0          # Gerekli seviye
        self.color_set = 0              # Renk seti
        self.upgrade_option_type = 0    # Yükseltme sonrası tip
        self.previous_option_type = 0   # Başarısızlık sonrası tip

class ItemOptionTable:
    """ITEMOPTION_TABLE sınıfı - Basitleştirilmiş"""
    
    # Verified 2026-07-21 name-for-name and order-for-order against the real
    # ITEMOPTION_TABLE::ITEMOPTION_PART enum (client-master\Client\
    # MItemOptionTable.h:63-112) and the server's independent OptionClass
    # enum - both match this list exactly, no corrections needed.
    PART_NAMES = {
        0: "STR (Strength)", 1: "DEX (Dexterity)", 2: "INT (Intelligence)", 3: "HP (Hit Points)",
        4: "MP (Mana Points)", 5: "HP Steal", 6: "MP Steal", 7: "HP Regeneration",
        8: "MP Regeneration", 9: "To Hit", 10: "Defense", 11: "Damage",
        12: "Protection", 13: "Durability", 14: "Poison Resistance", 15: "Acid Resistance",
        16: "Curse Resistance", 17: "Blood Resistance", 18: "Vision Range",
        19: "Attack Speed", 20: "Critical Hit", 21: "Luck", 22: "All Resistances",
        23: "All Attributes", 24: "STR to DEX", 25: "STR to INT", 26: "DEX to STR",
        27: "DEX to INT", 28: "INT to STR", 29: "INT to DEX", 30: "Decrease MP Consumption",
        31: "Translation", 32: "Magic Damage", 33: "Physical Damage", 34: "Decrease Gamble Price",
        35: "Decrease Potion Price", 36: "Magic Protection", 37: "Physical Protection"
    }

    # What Plus Point actually means for each part - shown live in the UI so
    # you don't have to remember which parts are flat adds vs. percentages.
    PLUS_POINT_HINT = {
        13: "Percentage, 100 = no change (applied to max durability)",
        24: "Percentage of base STR moved into DEX",
        25: "Percentage of base STR moved into INT",
        26: "Percentage of base DEX moved into STR",
        27: "Percentage of base DEX moved into INT",
        28: "Percentage of base INT moved into STR",
        29: "Percentage of base INT moved into DEX",
        34: "Flat amount, NEGATIVE to lower gamble price",
        35: "Flat amount, NEGATIVE to lower potion price",
    }
    PLUS_POINT_HINT_DEFAULT = "Flat additive amount (e.g. +8 means +8 to this stat)"

    def __init__(self):
        self.items = []
        self.encoding = 'utf-8'  # Default encoding
        self.part_headers = []  # (ename, name) per part, read from the file so save doesn't blank them out
    
    def set_encoding(self, encoding):
        """Encoding ayarla"""
        encoding_map = {
            'Korean(euc-kr)': 'euc-kr',
            'Korean(cp949)': 'cp949',
            'Chinese(gb2312)': 'gb2312',
            'Chinese(big5)': 'big5',
            'Chinese(gbk)': 'gbk',
            'Latin-1': 'latin-1',
            'UTF-8': 'utf-8'
        }
        self.encoding = encoding_map.get(encoding, 'utf-8')
        print(f"Encoding set to: {self.encoding}")
    
    def read_string_with_encoding(self, file):
        """Seçilen encoding ile string oku"""
        try:
            length_data = file.read(4)
            if len(length_data) < 4:
                return ""
            
            length = struct.unpack('i', length_data)[0]
            
            if length < 0 or length > 1000:
                # Geçersiz uzunluk, pozisyonu geri al
                file.seek(file.tell() - 4)
                return None
            
            if length > 0:
                string_data = file.read(length)
                if len(string_data) < length:
                    file.seek(file.tell() - 4 - len(string_data))
                    return None
                
                # Seçilen encoding ile dene
                try:
                    result = string_data.decode(self.encoding, errors='ignore')
                except:
                    # Fallback olarak diğer encoding'leri dene
                    fallback_encodings = ['utf-8', 'latin-1', 'cp949', 'gbk', 'cp1254', 'ascii', 'euc-kr', 'gb2312', 'big5']
                    result = ""
                    for enc in fallback_encodings:
                        try:
                            result = string_data.decode(enc, errors='ignore')
                            if len(result.strip()) > 0 and not result.startswith('\x00'):
                                break
                        except:
                            continue
            else:
                result = ""
            
            return result
            
        except Exception as e:
            print(f"String okuma hatası: {e}")
            return None

    def write_string_with_encoding(self, file, text):
        """String yaz (seçilen encoding ile)"""
        try:
            try:
                encoded = text.encode(self.encoding, errors='ignore')
            except:
                # Fallback olarak UTF-8 kullan
                encoded = text.encode('utf-8', errors='ignore')
            
            file.write(struct.pack('i', len(encoded)))
            file.write(encoded)
            return True
        except Exception as e:
            print(f"String yazma hatası: {e}")
            return False

    def load_from_file(self, filename):
        try:
            with open(filename, 'rb') as file:
                print("=== DOSYA YÜKLENİYOR ===")
                
                # Part sayısı (38 sabit)
                file.read(4)  # 38'i atla

                # Part name'leri oku ve sakla (save_to_file bunlari geri yazacak)
                self.part_headers = []
                for i in range(38):
                    # Her part için 2 string (EN ve TR)
                    ename = self.read_string_with_encoding(file)
                    name = self.read_string_with_encoding(file)
                    self.part_headers.append((ename or "", name or ""))
                    print(f"Part {i}: EN='{ename}', TR='{name}'")
                
                # Item sayısı (bu sefer doğru okumayı dene)
                size_data = file.read(4)
                if len(size_data) < 4:
                    print("Item sayısı okunamadı")
                    return False
                
                item_count = struct.unpack('i', size_data)[0]
                print(f"Ham item sayısı: {item_count}")
                
                # Eğer item_count mantıksızsa (negatif veya çok büyük), sabit 38 olarak al
                if item_count < 0 or item_count > 1000:
                    print("Geçersiz item sayısı, 38 olarak varsayılıyor")
                    item_count = 38
                
                print(f"İşlenecek item sayısı: {item_count}")
                
                # Item'ları oku
                self.items = []
                for i in range(item_count):
                    item = ItemOptionInfo()
                    
                    # Stringleri oku
                    item.ename = self.read_string_with_encoding(file) or ""
                    item.name = self.read_string_with_encoding(file) or ""
                    
                    # Sayısal alanları oku
                    data = file.read(44)  # 11 * 4 byte
                    if len(data) < 44:
                        print(f"Item {i} için yetersiz sayısal veri")
                        continue
                    
                    try:
                        values = struct.unpack('11i', data)
                        item.part = values[0]
                        item.plus_point = values[1]
                        item.price_multiplier = values[2]
                        item.require_str = values[3]
                        item.require_dex = values[4]
                        item.require_int = values[5]
                        item.require_sum = values[6]
                        item.require_level = values[7]
                        item.color_set = values[8]
                        item.upgrade_option_type = values[9]
                        item.previous_option_type = values[10]
                        
                        self.items.append(item)
                        print(f"Item {i}: EN='{item.ename}', TR='{item.name}', Part={item.part}")
                    except Exception as e:
                        print(f"Item {i} sayısal veri hatası: {e}")
                        continue
                
                print(f"Başarıyla {len(self.items)} item yüklendi")
                return len(self.items) > 0
                
        except Exception as e:
            print(f"Dosya okuma hatası: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_to_file(self, filename):
        try:
            with open(filename, 'wb') as file:
                print("=== DOSYA KAYDEDİLİYOR ===")
                
                # Part sayısı (38)
                file.write(struct.pack('i', 38))

                # Part name'leri (dosyadan okunanlar - bos degil!)
                headers = self.part_headers if self.part_headers else [("", "")] * 38
                for i in range(38):
                    ename, name = headers[i] if i < len(headers) else ("", "")
                    self.write_string_with_encoding(file, ename)
                    self.write_string_with_encoding(file, name)
                
                # Item sayısı
                file.write(struct.pack('i', len(self.items)))
                
                # Item'ları yaz
                for item in self.items:
                    self.write_string_with_encoding(file, item.ename)
                    self.write_string_with_encoding(file, item.name)
                    file.write(struct.pack('11i',
                        item.part, item.plus_point, item.price_multiplier,
                        item.require_str, item.require_dex, item.require_int,
                        item.require_sum, item.require_level,
                        item.color_set, item.upgrade_option_type, item.previous_option_type))
                    print(f"Item kaydedildi: EN='{item.ename}', TR='{item.name}'")
                
                print(f"Başarıyla {len(self.items)} item kaydedildi")
                return True
                
        except Exception as e:
            print(f"Dosya yazma hatası: {e}")
            import traceback
            traceback.print_exc()
            return False

# GUI kodu (Update butonu ile)
class ItemOptionEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Item Option Editor")
        self.root.geometry("1150x750")
        
        # İKON EKLEME
        try:
            # Önce aynı dizindeki ikonu dene
            icon_path = "app_icon.ico"
            
            # Eğer bulunamazsa, uygulama dizinini dene
            if not os.path.exists(icon_path):
                if getattr(sys, 'frozen', False):
                    # PyInstaller ile derlenmişse
                    application_path = sys._MEIPASS
                else:
                    # Normal Python çalıştırması
                    application_path = os.path.dirname(os.path.abspath(__file__))
                
                icon_path = os.path.join(application_path, "app_icon.ico")
            
            # İkonu yükle
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                print(f"İkon başarıyla yüklendi: {icon_path}")
            else:
                print(f"İkon bulunamadı: {icon_path}")
        except Exception as e:
            print(f"İkon yüklenirken hata oluştu: {e}")
        
        self.table = ItemOptionTable()
        self.current_file = None
        self.current_selection = None

        self.setup_ui()
    
    def show_about(self):
        """About diyalog penceresini göster"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About Item Option Editor")
        about_window.geometry("400x350")
        about_window.resizable(False, False)
        
        # Pencereyi ana pencerenin ortasına yerleştir
        about_window.transient(self.root)
        about_window.grab_set()
        
        # İkon ayarla (isteğe bağlı)
        try:
            if hasattr(self, 'root') and self.root.iconbitmap:
                about_window.iconbitmap(self.root.iconbitmap())
        except:
            pass
        
        # İçerik çerçevesi
        content_frame = ttk.Frame(about_window, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo/Başlık (isteğe bağlı)
        title_label = ttk.Label(content_frame, text="Item Option Editor", font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Versiyon bilgisi
        version_label = ttk.Label(content_frame, text="Version 1.0", font=('Arial', 10))
        version_label.pack(pady=(0, 20))
        
        # Program hakkında bilgi
        about_text = """This application allows you to edit ItemOption.inf files for your game.
    You can add, remove, and modify item options with ease.
    All changes are automatically saved to the file when you update an item."""
        
        about_label = ttk.Label(content_frame, text=about_text, wraplength=350, justify=tk.CENTER)
        about_label.pack(pady=(0, 20))
        
        # Website linki
        website_frame = ttk.Frame(content_frame)
        website_frame.pack(pady=(0, 20))
        
        website_label = ttk.Label(website_frame, text="Visit our website:", font=('Arial', 10, 'bold'))
        website_label.pack()
        
         # Website linki (tıklandığında tarayıcıda açılır)
        website_link = ttk.Label(website_frame, text="Discord Server", 
                               foreground="blue", cursor="hand2", font=('Arial', 10, 'underline'))
        website_link.pack()
        
        def open_website(event):
            webbrowser.open_new("https://discord.gg/EA9jxmy")
        
        website_link.bind("<Button-1>", open_website)
        
        # Geliştirici bilgisi (isteğe bağlı)
        developer_label = ttk.Label(content_frame, text="Developed by: TigerBlitz", font=('Arial', 9, 'underline'))
        developer_label.pack(pady=(0, 10))
        
        # Kapat butonu
        close_button = ttk.Button(content_frame, text="Close", command=about_window.destroy)
        close_button.pack(pady=(10, 0))
        
        # Enter tuşuyla kapatma
        about_window.bind('<Return>', lambda e: about_window.destroy())
        about_window.bind('<Escape>', lambda e: about_window.destroy())
        
        # Pencereyi ortala
        about_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (about_window.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (about_window.winfo_height() // 2)
        about_window.geometry(f"+{x}+{y}")
        
        
    def setup_ui(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Help menüsü (Yeni eklenen kısım)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        ttk.Label(left_frame, text="Item Option List", font=('Arial', 12, 'bold')).pack(pady=(0, 5))
        
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        self.listbox.bind('<<ListboxSelect>>', self.on_item_select)
        
        # Item işlemleri butonları (listeden sonra)
        item_buttons_frame = ttk.Frame(left_frame)
        item_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(item_buttons_frame, text="Add Item", command=self.add_item).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(item_buttons_frame, text="Remove Item", command=self.remove_item).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(item_buttons_frame, text="Reload", command=self.refresh_list).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(item_buttons_frame, text="Update Item", command=self.update_item).pack(side=tk.LEFT)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        ttk.Label(right_frame, text="Item Option Details", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        detail_frame = ttk.Frame(right_frame)
        detail_frame.pack(fill=tk.BOTH, expand=True)
        
        self.create_form_fields(detail_frame)
        
        # Alt kısımdaki butonlar (sadece encoding seçimi kaldı)
        bottom_frame = ttk.Frame(right_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Encoding seçimi
        encoding_frame = ttk.Frame(bottom_frame)
        encoding_frame.pack(side=tk.LEFT)
        
        ttk.Label(encoding_frame, text="Encoding:").pack(side=tk.LEFT, padx=(0, 5))
        
        encoding_options = [
            "UTF-8", 
            "Latin-1", 
            "Korean(euc-kr)", 
            "Korean(cp949)", 
            "Chinese(gb2312)", 
            "Chinese(big5)", 
            "Chinese(gbk)"
        ]
        
        self.encoding_var = tk.StringVar(value="UTF-8")
        encoding_combo = ttk.Combobox(encoding_frame, textvariable=self.encoding_var, 
                                    values=encoding_options, width=15, state="readonly")
        encoding_combo.pack(side=tk.LEFT, padx=(0, 5))
        encoding_combo.bind('<<ComboboxSelected>>', self.change_encoding)
    
    def change_encoding(self, event=None):
        """Encoding değişikliğini uygula ve mevcut dosyayı yeniden yükle"""
        selected_encoding = self.encoding_var.get()
        old_encoding = self.table.encoding
        
        # Encoding'i güncelle
        self.table.set_encoding(selected_encoding)
        
        # Eğer bir dosya yüklüyse, otomatik olarak yeniden yükle
        if self.current_file and os.path.exists(self.current_file):
            try:
                # Geçerli seçimi kaydet
                current_selection = None
                if self.listbox.curselection():
                    current_selection = self.listbox.curselection()[0]
                
                # Dosyayı yeniden yükle
                if self.table.load_from_file(self.current_file):
                    self.refresh_list()
                    messagebox.showinfo("Success", f"Encoding changed to: {selected_encoding}\nFile reloaded successfully!")
                    
                    # Önceki seçimi koru (mümkünse)
                    if current_selection is not None and current_selection < len(self.table.items):
                        self.listbox.selection_set(current_selection)
                        self.listbox.see(current_selection)
                        self.display_item_details(self.table.items[current_selection])
                else:
                    # Hata durumunda eski encoding'e dön
                    self.table.set_encoding(old_encoding)
                    self.encoding_var.set([k for k, v in {
                        'Korean(euc-kr)': 'euc-kr',
                        'Korean(cp949)': 'cp949',
                        'Chinese(gb2312)': 'gb2312',
                        'Chinese(big5)': 'big5',
                        'Chinese(gbk)': 'gbk',
                        'Latin-1': 'latin-1',
                        'UTF-8': 'utf-8'
                    }.items() if v == old_encoding][0])
                    messagebox.showerror("Error", "Failed to reload file with new encoding!")
            except Exception as e:
                # Hata durumunda eski encoding'e dön
                self.table.set_encoding(old_encoding)
                self.encoding_var.set([k for k, v in {
                    'Korean(euc-kr)': 'euc-kr',
                    'Korean(cp949)': 'cp949',
                    'Chinese(gb2312)': 'gb2312',
                    'Chinese(big5)': 'big5',
                    'Chinese(gbk)': 'gbk',
                    'Latin-1': 'latin-1',
                    'UTF-8': 'utf-8'
                }.items() if v == old_encoding][0])
                messagebox.showerror("Error", f"Failed to change encoding: {str(e)}")
        else:
            messagebox.showinfo("Encoding Changed", f"Encoding set to: {selected_encoding}")
    
    def create_form_fields(self, parent):
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        fields_frame = ttk.Frame(scrollable_frame)
        fields_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.fields = {}
        
        row = 0
        # İngilizce isim
        self.add_field(fields_frame, "EName", "ename", row)
        row += 1
        
        # Yerel isim
        self.add_field(fields_frame, "HName", "name", row)
        row += 1
        
        # Özellik tipi (dropdown)
        ttk.Label(fields_frame, text="Option Type:").grid(row=row, column=0, sticky=tk.W, pady=2)
        part_var = tk.StringVar()
        part_combo = ttk.Combobox(fields_frame, textvariable=part_var, width=30, state="readonly")
        part_combo['values'] = [self.table.PART_NAMES.get(i, f"Unknown ({i})") for i in range(38)]
        part_combo.grid(row=row, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        self.fields['part'] = part_var
        # Update the Plus Point hint live as soon as a category is picked,
        # even before "Update Item" is clicked - most useful while adding a
        # brand new option, when you're still deciding the part.
        part_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_plus_point_hint())
        row += 1

        # Hints/previews go on their OWN row right below each field, spanning
        # the full width - a 3rd side-by-side column was tried first but on
        # a normal-sized window it landed past the visible edge of this
        # panel (which only scrolls vertically), making it invisible.
        self.add_numeric_field(fields_frame, "Plus Point", "plus_point", row)
        row += 1
        self.plus_point_hint_var = tk.StringVar(value=self.table.PLUS_POINT_HINT_DEFAULT)
        ttk.Label(fields_frame, textvariable=self.plus_point_hint_var, foreground="#2a7ae2",
                  font=('Arial', 9, 'italic'), wraplength=420, justify=tk.LEFT).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(0, 6))
        row += 1

        self.add_numeric_field(fields_frame, "Price Multiplier (%, 100=no change)", "price_multiplier", row)
        row += 1

        for label, key in [("Required STR (not enforced - vestigial)", "require_str"),
                            ("Required DEX (not enforced - vestigial)", "require_dex"),
                            ("Required INT (not enforced - vestigial)", "require_int")]:
            self.add_numeric_field(fields_frame, label, key, row, dim=True)
            row += 1

        self.add_numeric_field(fields_frame, "Required Sum (x2 to STR/DEX/INT req, x1 to total)", "require_sum", row)
        row += 1
        self.add_numeric_field(fields_frame, "Required Level", "require_level", row)
        row += 1

        # A live icon preview for this field was attempted and removed after
        # it couldn't be made to work reliably in real use - see the note at
        # the top of this file and README.md ("Tentativas descartadas").
        self.add_numeric_field(fields_frame, "Color Set (index into sprite tint palette - see README)", "color_set", row)
        row += 1

        self.add_numeric_field(fields_frame, "Upgrade Option (index into this same list, 0=none)", "upgrade_option_type", row)
        row += 1
        self.upgrade_ref_var = tk.StringVar()
        ttk.Label(fields_frame, textvariable=self.upgrade_ref_var, foreground="#2a7ae2", font=('Arial', 9, 'italic')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(0, 6))
        row += 1

        self.add_numeric_field(fields_frame, "Previous Option (index into this same list, 0=none)", "previous_option_type", row)
        row += 1
        self.previous_ref_var = tk.StringVar()
        ttk.Label(fields_frame, textvariable=self.previous_ref_var, foreground="#2a7ae2", font=('Arial', 9, 'italic')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(0, 6))
        row += 1

        # Bind live cross-reference/swatch refresh whenever these three
        # fields change, so you see the effect immediately while typing.
        for key in ('color_set', 'upgrade_option_type', 'previous_option_type'):
            self.fields[key].trace_add('write', lambda *a: self._refresh_cross_references())

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _refresh_plus_point_hint(self):
        part_text = self.fields['part'].get()
        part_id = next((k for k, v in self.table.PART_NAMES.items() if v == part_text), None)
        self.plus_point_hint_var.set(self.table.PLUS_POINT_HINT.get(part_id, self.table.PLUS_POINT_HINT_DEFAULT))

    def _describe_option(self, index):
        """Human-readable cross-reference label for an option-list index,
        used for Upgrade/Previous Option (both index into THIS SAME list)."""
        if index == NONE_OPTION_INDEX:
            return "(none)"
        if 0 <= index < len(self.table.items):
            opt = self.table.items[index]
            name = opt.name or opt.ename or f"item {index}"
            part_label = self.table.PART_NAMES.get(opt.part, f"part {opt.part}")
            return f"-> #{index}: {name} ({part_label} {opt.plus_point:+d})"
        return f"-> #{index} (out of range)"

    def _refresh_cross_references(self):
        try:
            up = int(self.fields['upgrade_option_type'].get() or 0)
        except ValueError:
            up = 0
        try:
            prev = int(self.fields['previous_option_type'].get() or 0)
        except ValueError:
            prev = 0
        self.upgrade_ref_var.set(self._describe_option(up))
        self.previous_ref_var.set(self._describe_option(prev))

    def add_field(self, parent, label, key, row):
        ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var, width=30)
        entry.grid(row=row, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        self.fields[key] = var
    
    def add_numeric_field(self, parent, label, key, row, dim=False):
        label_kwargs = {"foreground": "#888"} if dim else {}
        ttk.Label(parent, text=f"{label}:", **label_kwargs).grid(row=row, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var, width=15)
        entry.grid(row=row, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        self.fields[key] = var
        
        # Sadece sayısal girişe izin ver
        def validate_numeric(*args):
            value = var.get()
            if value == "":
                return
            try:
                int(value)
            except ValueError:
                # Eğer sayı değilse, son karakteri sil
                var.set(value[:-1])
        
        var.trace_add("write", validate_numeric)
    
    def update_window_title(self):
        """Pencere başlığını güncelle"""
        base_title = "Item Option Editor"
        if self.current_file:
            filename = os.path.basename(self.current_file)
            self.root.title(f"{base_title} - {filename}")
        else:
            self.root.title(base_title)
    
    def open_file(self):
        filename = filedialog.askopenfilename(
            title="Select ItemOption.inf file",
            filetypes=[("INF files", "*.inf"), ("All files", "*.*")]
        )

        if filename:
            if self.table.load_from_file(filename):
                self.current_file = filename
                self.update_window_title()  # Pencere başlığını güncelle
                self.refresh_list()
                messagebox.showinfo("Success", f"File loaded successfully!\n{len(self.table.items)} items found.")
            else:
                messagebox.showerror("Error", "Failed to load file! Check console for details.")
    
    def save_file(self):
        if not self.current_file:
            self.save_as_file()
            return
        
        if self.table.save_to_file(self.current_file):
            messagebox.showinfo("Success", "File saved successfully!")
        else:
            messagebox.showerror("Error", "Failed to save file!")
    
    def save_as_file(self):
        filename = filedialog.asksaveasfilename(
            title="Save file as",
            defaultextension=".inf",
            filetypes=[("INF files", "*.inf"), ("All files", "*.*")]
        )
        
        if filename:
            if self.table.save_to_file(filename):
                self.current_file = filename
                self.update_window_title()  # Pencere başlığını güncelle
                messagebox.showinfo("Success", "File saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save file!")
    
    def refresh_list(self):
        """Listeyi yenile"""
        self.listbox.delete(0, tk.END)
        for i, item in enumerate(self.table.items):
            display_name = item.name if item.name else item.ename if item.ename else f"Item {i}"
            self.listbox.insert(tk.END, f"{i}: {display_name}")
    
    def on_item_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.table.items):
                self.current_selection = index
                self.display_item_details(self.table.items[index])
    
    def display_item_details(self, item):
        """Item detaylarını formda göster"""
        try:
            # Real bug found 2026-07-21: several call sites (change_encoding,
            # remove_item) called this without first updating
            # self.current_selection, so the Item.inf cross-reference
            # preview (which looks up self.current_selection to find which
            # real item uses THIS option) could render a stale/wrong item
            # while every other field correctly showed the new one - exactly
            # the "image doesn't match the text" bug reported. Fixed at the
            # root instead of patching every call site: derive the index
            # directly from the item object every time this runs.
            try:
                self.current_selection = self.table.items.index(item)
            except ValueError:
                pass  # item isn't (yet) in the list - leave current_selection as-is

            self.fields['ename'].set(item.ename)
            self.fields['name'].set(item.name)
            
            part_name = self.table.PART_NAMES.get(item.part, f"Unknown ({item.part})")
            self.fields['part'].set(part_name)
            
            self.fields['plus_point'].set(str(item.plus_point))
            self.fields['price_multiplier'].set(str(item.price_multiplier))
            self.fields['require_str'].set(str(item.require_str))
            self.fields['require_dex'].set(str(item.require_dex))
            self.fields['require_int'].set(str(item.require_int))
            self.fields['require_sum'].set(str(item.require_sum))
            self.fields['require_level'].set(str(item.require_level))
            self.fields['color_set'].set(str(item.color_set))
            self.fields['upgrade_option_type'].set(str(item.upgrade_option_type))
            self.fields['previous_option_type'].set(str(item.previous_option_type))

            self._refresh_plus_point_hint()
            self._refresh_cross_references()
        except Exception as e:
            print(f"Detay gösterme hatası: {e}")
    
    def update_item(self):
        """Seçili item'ı güncelle ve dosyayı otomatik olarak kaydet"""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item!")
            return
        
        index = selection[0]
        if index >= len(self.table.items):
            return
        
        item = self.table.items[index]
        
        try:
            # Alanları güncelle
            item.ename = self.fields['ename'].get()
            item.name = self.fields['name'].get()
            
            part_text = self.fields['part'].get()
            item.part = 0
            for key, value in self.table.PART_NAMES.items():
                if value == part_text:
                    item.part = key
                    break
            else:
                try:
                    if "Unknown" in part_text:
                        item.part = int(part_text.split('(')[1].split(')')[0])
                except:
                    item.part = 0
            
            # Sayısal alanları güncelle
            item.plus_point = int(self.fields['plus_point'].get() or 0)
            item.price_multiplier = int(self.fields['price_multiplier'].get() or 0)
            item.require_str = int(self.fields['require_str'].get() or 0)
            item.require_dex = int(self.fields['require_dex'].get() or 0)
            item.require_int = int(self.fields['require_int'].get() or 0)
            item.require_sum = int(self.fields['require_sum'].get() or 0)
            item.require_level = int(self.fields['require_level'].get() or 0)
            item.color_set = int(self.fields['color_set'].get() or 0)
            item.upgrade_option_type = int(self.fields['upgrade_option_type'].get() or 0)
            item.previous_option_type = int(self.fields['previous_option_type'].get() or 0)
            
            # Listeyi güncelle
            display_name = item.name if item.name else item.ename if item.ename else f"Item {index}"
            self.listbox.delete(index)
            self.listbox.insert(index, f"{index}: {display_name}")
            
            # Güncellendiğini belirten görsel geri bildirim
            original_bg = self.listbox.itemcget(index, 'background')
            self.listbox.itemconfig(index, background='lightgreen')
            self.root.after(300, lambda: self.listbox.itemconfig(index, background=original_bg))
            
            # DOSYAYI OTOMATİK OLARAK KAYDET
            if self.current_file:
                if self.table.save_to_file(self.current_file):
                    messagebox.showinfo("Success", "Item updated and file saved successfully!")
                else:
                    messagebox.showerror("Error", "Item updated but failed to save file!")
            else:
                # Eğer dosya kaydedilmemişse, kullanıcıyı uyar
                result = messagebox.askyesno("Save File", "Item updated successfully!\nWould you like to save the file now?")
                if result:
                    self.save_as_file()
                else:
                    messagebox.showinfo("Success", "Item updated successfully!")
                    
        except ValueError:
            messagebox.showerror("Error", "Please enter only numbers in numeric fields!")
        except Exception as e:
            messagebox.showerror("Error", f"Update error: {str(e)}")
    
    def add_item(self):
        """Yeni item ekle"""
        new_item = ItemOptionInfo()
        new_item.ename = "New Item"
        new_item.name = "Yeni Item"
        
        self.table.items.append(new_item)
        
        index = len(self.table.items) - 1
        display_name = new_item.name if new_item.name else new_item.ename if new_item.ename else f"Item {index}"
        self.listbox.insert(tk.END, f"{index}: {display_name}")
        
        # Yeni item'ı seç
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.listbox.see(index)
        self.current_selection = index  # so the Item.inf cross-reference preview looks up the right option index
        self.display_item_details(new_item)
        
        messagebox.showinfo("Success", "New item added!")
    
    def remove_item(self):
        """Seçili item'ı kaldır"""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item to remove!")
            return
        
        index = selection[0]
        if index < len(self.table.items):
            result = messagebox.askyesno("Confirm", "Are you sure you want to remove this item?")
            if result:
                self.table.items.pop(index)
                self.refresh_list()
                messagebox.showinfo("Success", "Item removed!")
                
                # Eğer item varsa ilk item'ı seç
                if len(self.table.items) > 0:
                    self.listbox.selection_set(0)
                    self.listbox.see(0)
                    self.display_item_details(self.table.items[0])

def main():
    root = tk.Tk()
    app = ItemOptionEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()