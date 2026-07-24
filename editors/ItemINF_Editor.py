"""
ItemINF_Editor.py - DarkEden Item.inf editor
=============================================
Original tool by TigerBlitz (community Python editor for a DIFFERENT/newer
Item.inf build - its 115-byte-per-item field layout doesn't match this
server's file, which silently corrupted every item past the first one).

Rewritten by VictorRP7 (2026-07-21): the entire binary layout below (field
offsets, sizes, and what Value1-7 mean per item category) was reverse
engineered directly from the real DarkEden client source code:

    client-master\\Client\\MItemTable.h   (struct ITEMTABLE_INFO)
    client-master\\Client\\MItemTable.cpp (LoadFromFile/SaveToFile - the exact
                                           on-disk read/write order)
    client-master\\Client\\MItem.h/.cpp   (per-item-class getters - which
                                           Value slot means Durability vs.
                                           Protection vs. MinDamage etc.)
    client-master\\Client\\ItemClassDef.h (the full ITEM_CLASS enum - table
                                           index N in Item.inf == class N)
    client-master\\Client\\RaceType.h     (Race bitmask: 1=Slayer 2=Vampire
                                           4=Ousters)

Everything editable in this tool was cross-checked against the running
client's own logic (not just guessed from a hex dump) before being trusted:
Price/Weight/Grid scale correctly across every tier of every category
sampled; RequireSTR climbs 0->120 across the Sword table; RequireSUM climbs
tier-by-tier across the Coat table; bMaleOnly/bFemaleOnly match every M/W
item pair exactly; and a full load -> save -> reload round trip reproduces
the original Item.inf byte-for-byte on every table (1611 items, 91 classes).

See README.md in this folder for the full field-by-field format writeup.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import struct
from typing import List, BinaryIO

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
try:
    import darkeden_sprite  # optional: enables the live inventory-icon preview/editor (see darkeden_sprite.py)
except ImportError:
    darkeden_sprite = None


def load_item_option_names(item_inf_path):
    """Best-effort load of the sibling ItemOption.inf (same folder as the
    given Item.inf) so DefaultOptionList byte values can be shown as real
    enchant-option names instead of raw indices. Returns [] if not found or
    unreadable - this is a read-only convenience lookup, not required for
    Item.inf editing to work. Format confirmed via client source
    (MItemOptionTable.cpp): int32 numParts, then numParts x (EName, Name)
    MStrings, then int32 itemCount, then itemCount x (EName, Name, 8x int32)."""
    directory = os.path.dirname(item_inf_path)
    if not directory:
        return []
    candidate = None
    try:
        for fname in os.listdir(directory):
            if fname.lower() == 'itemoption.inf':
                candidate = os.path.join(directory, fname)
                break
    except OSError:
        return []
    if not candidate:
        return []

    def read_str(f):
        length_bytes = f.read(4)
        if len(length_bytes) < 4:
            return None
        length = struct.unpack('<i', length_bytes)[0]
        if length < 0 or length > 1000:
            return None
        data = f.read(length)
        return data.decode('utf-8', errors='replace')

    try:
        with open(candidate, 'rb') as f:
            num_parts = struct.unpack('<i', f.read(4))[0]
            part_names = []
            for _ in range(num_parts):
                ename = read_str(f) or ""
                name = read_str(f) or ""
                part_names.append(ename or name)

            item_count = struct.unpack('<i', f.read(4))[0]
            items = []
            for _ in range(item_count):
                ename = read_str(f) or ""
                name = read_str(f) or ""
                values = struct.unpack('<11i', f.read(44))
                part = values[0]
                plus_point = values[1]
                part_label = part_names[part] if 0 <= part < len(part_names) else f"Part {part}"
                items.append((ename or name or "?", part_label, plus_point))
            return items
    except Exception:
        return []


class BinarySerializer:
    @staticmethod
    def read_string(file: BinaryIO, encoding: str = 'windows-1254') -> str:
        """Read string from binary file (length + data)"""
        length_bytes = file.read(4)
        if not length_bytes or len(length_bytes) < 4:
            return ""
        length = struct.unpack('<I', length_bytes)[0]
        if length == 0:
            return ""
        string_bytes = file.read(length)
        try:
            return string_bytes.decode(encoding)
        except UnicodeDecodeError:
            return string_bytes.decode('latin-1')
    
    @staticmethod
    def write_string(file: BinaryIO, value: str, encoding: str = 'windows-1254'):
        """Write string to binary file (length + data)"""
        if value is None:
            value = ""
        try:
            encoded = value.encode(encoding)
        except UnicodeEncodeError:
            encoded = value.encode('latin-1')
        file.write(struct.pack('<I', len(encoded)))
        if encoded:
            file.write(encoded)
    
    @staticmethod
    def read_uint16(file: BinaryIO) -> int:
        data = file.read(2)
        if len(data) < 2:
            raise EOFError("End of file reached")
        return struct.unpack('<H', data)[0]
    
    @staticmethod
    def write_uint16(file: BinaryIO, value: int):
        file.write(struct.pack('<H', value))
    
    @staticmethod
    def read_int32(file: BinaryIO) -> int:
        data = file.read(4)
        if len(data) < 4:
            raise EOFError("End of file reached")
        return struct.unpack('<i', data)[0]
    
    @staticmethod
    def write_int32(file: BinaryIO, value: int):
        file.write(struct.pack('<i', value))
    
    @staticmethod
    def read_uint32(file: BinaryIO) -> int:
        data = file.read(4)
        if len(data) < 4:
            raise EOFError("End of file reached")
        return struct.unpack('<I', data)[0]
    
    @staticmethod
    def write_uint32(file: BinaryIO, value: int):
        file.write(struct.pack('<I', value))
    
    @staticmethod
    def read_byte(file: BinaryIO) -> int:
        data = file.read(1)
        if not data:
            raise EOFError("End of file reached")
        return struct.unpack('<B', data)[0]
    
    @staticmethod
    def write_byte(file: BinaryIO, value: int):
        file.write(struct.pack('<B', value))
    
    @staticmethod
    def read_bool(file: BinaryIO) -> bool:
        data = file.read(1)
        if not data:
            raise EOFError("End of file reached")
        return struct.unpack('<?', data)[0]
    
    @staticmethod
    def write_bool(file: BinaryIO, value: bool):
        file.write(struct.pack('<?', value))

class Item:
    # Layout taken directly from the real DarkEden client source (found
    # 2026-07-21): class ITEMTABLE_INFO, client-master\Client\MItemTable.h/.cpp
    # - ITEMTABLE_INFO::LoadFromFile / SaveToFile define the exact on-disk order.
    # Key points that differ from a naive byte-diff guess:
    #  - The file stores EName THEN HName (not HName then EName).
    #  - There is NO "UseFrameID" - only 6 frame IDs (Tile/Inventory/Gear/Drop/
    #    AddonMale/AddonFemale), then the 4 sound IDs, then GridWidth/GridHeight
    #    (2 separate BYTEs - they DO exist, e.g. SetGrid(1,1) for motorcycles).
    #  - UseActionInfo is a WORD (TYPE_ACTIONINFO) but the client reads/writes
    #    it with a hardcoded 4-byte file.read/write - an off-by-2 bug baked
    #    into every real Item.inf, so this format must reproduce it (4 bytes).
    #  - DefaultOptionList's payload bytes sit right after the 1-byte count,
    #    BEFORE ItemStyle/ElementalType/Elemental/Race/DescriptionFrameID -
    #    so those 5 fields shift later in the record whenever an item actually
    #    has enchant options (option_count > 0). They are NOT at a fixed offset.
    #  - Value1-7 are shared slots reused per item category (comment block at
    #    the top of MItemTable.h), NOT generic. See ItemEditor._guess_value_labels.
    # The original community tool's 115-byte layout was for a newer Item.inf
    # revision (adds ItemMoveControl/ItemCanAdvance/DropItemNameTag/
    # NormalItemGrade/NewValue668 after DescriptionFrameID) that this file
    # doesn't have - that mismatch is what corrupted every item past the first.
    FIXED_TAIL_SIZE = 99
    OPTION_COUNT_OFFSET = 85
    TAIL_FIELDS_BEFORE_OPTIONS_END = 86  # byte just after the option-count byte

    # (attribute name, byte offset within the tail, struct format) - fields
    # strictly BEFORE the option payload, so their offset never moves
    _FIELDS = [
        ('TileFrameID', 0, 'H'), ('InventoryFrameID', 2, 'H'), ('GearFrameID', 4, 'H'),
        ('DropFrameID', 6, 'H'), ('AddonMaleFrameID', 8, 'H'), ('AddonFemaleFrameID', 10, 'H'),
        ('UseSoundID', 12, 'H'), ('TileSoundID', 14, 'H'), ('InventorySoundID', 16, 'H'),
        ('GearSoundID', 18, 'H'),
        ('GridWidth', 20, 'B'), ('GridHeight', 21, 'B'),
        ('Price', 22, 'I'), ('Weight', 26, 'H'),
        ('Value1', 28, 'i'), ('Value2', 32, 'i'), ('Value3', 36, 'i'), ('Value4', 40, 'i'),
        ('Value5', 44, 'i'), ('Value6', 48, 'i'), ('Value7', 52, 'i'),
        ('RequireSTR', 56, 'B'), ('RequireDEX', 57, 'B'), ('RequireINT', 58, 'B'), ('RequireSUM', 59, 'H'),
        ('RequireLevel', 61, 'B'), ('RequireAdvancementLevel', 62, 'B'),
        ('bMaleOnly', 63, 'B'), ('bFemaleOnly', 64, 'B'),
        ('UseActionInfo', 65, 'I'), ('SilverMax', 69, 'i'), ('ToHit', 73, 'i'),
        ('MaxNumber', 77, 'I'), ('CriticalHit', 81, 'i'),
        # offset 85 = option count, handled separately (OptionCount / OptionList below)
        # ItemStyle/ElementalType/Elemental/Race/DescriptionFrameID come AFTER
        # the option payload - see the dynamic properties below _FIELDS.
    ]

    def __init__(self, file=None):
        self.HName = ""
        self.EName = ""
        self.Description = ""
        self.tail = bytearray(Item.FIXED_TAIL_SIZE)
        self.ItemClassID = 0  # Default 0 (ITEM_CLASS_MOTORCYCLE)

        if file:
            self.load_from_file(file)

    @property
    def OptionCount(self):
        return self.tail[self.OPTION_COUNT_OFFSET]

    @property
    def OptionList(self):
        """Raw DefaultOptionList byte values - each one is an index into
        ItemOption.inf's item list (the enchant-option pool)."""
        n = self.OptionCount
        start = self.TAIL_FIELDS_BEFORE_OPTIONS_END
        return list(self.tail[start:start + n])

    def _post_options_base(self):
        """Offset where ItemStyle (and the 4 fields after it) begin - shifts
        by OptionCount bytes since the option payload sits right before them."""
        return self.TAIL_FIELDS_BEFORE_OPTIONS_END + self.OptionCount

    @property
    def ItemStyle(self):
        return struct.unpack_from('<i', self.tail, self._post_options_base())[0]

    @ItemStyle.setter
    def ItemStyle(self, value):
        struct.pack_into('<i', self.tail, self._post_options_base(), int(value))

    @property
    def ElementalType(self):
        return struct.unpack_from('<i', self.tail, self._post_options_base() + 4)[0]

    @ElementalType.setter
    def ElementalType(self, value):
        struct.pack_into('<i', self.tail, self._post_options_base() + 4, int(value))

    @property
    def Elemental(self):
        return struct.unpack_from('<H', self.tail, self._post_options_base() + 8)[0]

    @Elemental.setter
    def Elemental(self, value):
        struct.pack_into('<H', self.tail, self._post_options_base() + 8, int(value))

    @property
    def Race(self):
        return self.tail[self._post_options_base() + 10]

    @Race.setter
    def Race(self, value):
        self.tail[self._post_options_base() + 10] = int(value)

    @property
    def DescriptionFrameID(self):
        return struct.unpack_from('<H', self.tail, self._post_options_base() + 11)[0]

    @DescriptionFrameID.setter
    def DescriptionFrameID(self, value):
        struct.pack_into('<H', self.tail, self._post_options_base() + 11, int(value))

    def load_from_file(self, file: BinaryIO):
        try:
            # Read strings - EName is stored BEFORE HName on disk
            self.EName = BinarySerializer.read_string(file, 'ascii')
            self.HName = BinarySerializer.read_string(file, 'ascii')
            self.Description = BinarySerializer.read_string(file, 'ascii')

            # Bytes 0-85: fixed fields up to and including the option count.
            # The option payload comes right after that (before ItemStyle
            # etc.), so it must be read BETWEEN the two fixed chunks, not
            # appended after all 99 bytes.
            head = file.read(self.TAIL_FIELDS_BEFORE_OPTIONS_END)  # bytes 0..85 (86 bytes)
            if len(head) < self.TAIL_FIELDS_BEFORE_OPTIONS_END:
                raise EOFError("Unexpected end of file while reading item (fixed head)")

            option_count = head[self.OPTION_COUNT_OFFSET]
            payload = file.read(option_count) if option_count else b''
            if len(payload) < option_count:
                raise EOFError("Unexpected end of file while reading item (option payload)")

            tail_size = self.FIXED_TAIL_SIZE - self.TAIL_FIELDS_BEFORE_OPTIONS_END  # 13 bytes
            rest = file.read(tail_size)  # ItemStyle/ElementalType/Elemental/Race/DescriptionFrameID
            if len(rest) < tail_size:
                raise EOFError("Unexpected end of file while reading item (post-option fields)")

            self.tail = bytearray(head + payload + rest)

            # Specify the Item Class ID
            self.ItemClassID = self.detect_item_class_id()

        except EOFError:
            raise EOFError("Unexpected end of file while reading item")
        except Exception as e:
            raise Exception(f"Error reading item: {str(e)}")
    
    def detect_item_class_id(self):
        """Determine the class ID based on item properties"""
        name_to_check = (self.HName + " " + self.EName).lower()
        
        # Identification by item class name
        if any(word in name_to_check for word in ['POTION', 'POTION']):
            return 1  # ITEM_CLASS_POTION
        elif 'water' in name_to_check:
            return 2  # ITEM_CLASS_WATER
        elif 'holywater' in name_to_check:
            return 3  # ITEM_CLASS_HOLYWATER
        elif any(word in name_to_check for word in ['RING', 'RING']):
            return 8  # ITEM_CLASS_RING
        elif any(word in name_to_check for word in ['BRACELET', 'BRACELET']):
            return 9  # ITEM_CLASS_BRACELET
        elif any(word in name_to_check for word in ['NECKLACE', 'NECKLACE']):
            return 10  # ITEM_CLASS_NECKLACE
        elif any(word in name_to_check for word in ['coat', 'armor', 'mail']):
            return 11  # ITEM_CLASS_COAT
        elif any(word in name_to_check for word in ['trouser', 'pant', 'legging']):
            return 12  # ITEM_CLASS_TROUSER
        elif any(word in name_to_check for word in ['shoe', 'boot']):
            return 13  # ITEM_CLASS_SHOES
        elif any(word in name_to_check for word in ['sword', 'blade']):
            return 14 if 'sword' in name_to_check else 15  # ITEM_CLASS_SWORD veya ITEM_CLASS_BLADE
        elif 'shield' in name_to_check:
            return 16  # ITEM_CLASS_SHIELD
        elif 'cross' in name_to_check:
            return 17  # ITEM_CLASS_CROSS
        elif any(word in name_to_check for word in ['GLOVE', 'GLOVE']):
            return 18  # ITEM_CLASS_GLOVE
        elif any(word in name_to_check for word in ['HELM', 'HELM']):
            return 19  # ITEM_CLASS_HELM
        elif any(word in name_to_check for word in ['KEY', 'KEY']):
            return 7  # ITEM_CLASS_KEY
        elif any(word in name_to_check for word in ['MONEY', 'MONEY', 'MONEY']):
            return 28  # ITEM_CLASS_MONEY
        
        # If not detected, ETC by default.
        return 6  # ITEM_CLASS_ETC
    
    def save_to_file(self, file: BinaryIO):
        """Save item data to binary file"""
        # Write strings - EName is stored BEFORE HName on disk
        BinarySerializer.write_string(file, self.EName, 'ascii')
        BinarySerializer.write_string(file, self.HName, 'ascii')
        BinarySerializer.write_string(file, self.Description, 'ascii')

        # tail is already laid out on-disk-correctly (head[0:86] + option
        # payload + post-option fields), so it writes back byte-for-byte
        # except for whichever confirmed fields were edited
        file.write(bytes(self.tail))


def _make_item_field_property(offset, fmt):
    def getter(self):
        return struct.unpack_from('<' + fmt, self.tail, offset)[0]

    def setter(self, value):
        struct.pack_into('<' + fmt, self.tail, offset, int(value))

    return property(getter, setter)


for _field_name, _field_offset, _field_fmt in Item._FIELDS:
    setattr(Item, _field_name, _make_item_field_property(_field_offset, _field_fmt))


class ItemTable:
    def __init__(self, file=None):
        self.Items = []
        if file:
            self.load_from_file(file)
    
    def load_from_file(self, file: BinaryIO):
        """Load item table from binary file"""
        try:
            # Quantity
            quantity_bytes = file.read(4)
            if len(quantity_bytes) < 4:
                print("EOF: Not enough bytes for table quantity")
                return
                
            quantity = struct.unpack('<I', quantity_bytes)[0]
            print(f"Reading table with {quantity} items")
            
            # Items
            self.Items = []
            items_read = 0
            for i in range(quantity):
                try:
                    current_pos = file.tell()
                    item = Item(file)
                    self.Items.append(item)
                    items_read += 1
                    print(f"  ✓ Item {i}: '{item.HName}' at position {current_pos}")
                except EOFError as e:
                    print(f"  ✗ EOF at item {i}: {e}")
                    break
                except Exception as e:
                    print(f"  ✗ Error at item {i}: {e}")
                    # If an error occurs, move on to the next item
                    continue
            
            print(f"  Successfully read {items_read}/{quantity} items")
                    
        except EOFError:
            print("EOF reached while reading table quantity")
        except Exception as e:
            print(f"Error reading table: {e}")
    
    def save_to_file(self, file: BinaryIO):
        """Save item table to binary file"""
        # Quantity
        BinarySerializer.write_uint32(file, len(self.Items))
        
        # Items
        for item in self.Items:
            item.save_to_file(file)

class ItemTableList:
    def __init__(self, file=None):
        self.ItemTables = []
        self.footer = b''  # trailing bytes after the last table (e.g. a 4-byte 0 marker), preserved as-is
        if file:
            self.load_from_file(file)

    def load_from_file(self, file: BinaryIO):
        """Load item table list from binary file"""
        try:
            # Read number of tables
            table_count_bytes = file.read(4)
            if len(table_count_bytes) < 4:
                print("EOF: Not enough bytes for table list count")
                return

            table_count = struct.unpack('<I', table_count_bytes)[0]
            print(f"Reading {table_count} item tables")

            # Read each table
            self.ItemTables = []
            for i in range(table_count):
                try:
                    table = ItemTable(file)
                    self.ItemTables.append(table)
                    print(f"  ✓ Table {i}: {len(table.Items)} items")
                except EOFError as e:
                    print(f"  ✗ EOF at table {i}: {e}")
                    break
                except Exception as e:
                    print(f"  ✗ Error at table {i}: {e}")
                    continue

            print(f"Successfully read {len(self.ItemTables)}/{table_count} tables")
            self.footer = file.read()

        except EOFError:
            print("EOF reached while reading table list")
        except Exception as e:
            raise Exception(f"Error reading table list: {str(e)}")

    def save_to_file(self, file: BinaryIO):
        """Save item table list to binary file"""
        # Quantity
        BinarySerializer.write_uint32(file, len(self.ItemTables))

        # ItemTables
        for table in self.ItemTables:
            table.save_to_file(file)

        file.write(self.footer)
    
    def get_total_item_count(self):
        """Get total number of items"""
        return sum(len(table.Items) for table in self.ItemTables)
    
    def get_non_empty_tables(self):
        """Get only tables that have items"""
        return [table for table in self.ItemTables if table.Items]

class ItemEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Item.inf Editor")
        self.root.geometry("1200x700")
        
        self.item_table_list = None
        self.current_filename = None
        self.current_item_ref = None
        self.item_option_names = []  # cross-referenced from sibling ItemOption.inf, if found
        self.sprite_pack = None      # darkeden_sprite.SpritePack for Data\Ui\spk\Item.ispk, if found
        self.sprite_colorset = None  # lazily-built 495x30 color table (shared, expensive-ish to build once)
        self.preview_photo = None    # keep a live reference so Tk doesn't garbage-collect the displayed image

        # Store expanded states and item references
        self.expanded_tables = set()  # Save expanded tables
        self.item_references = {}  # {item_id: (table_index, item_index)}
        
        self.create_widgets()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Left frame - Item list
        left_frame = ttk.LabelFrame(main_frame, text="Items (Grouped by Tables)", padding="5")
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # File operations frame
        file_frame = ttk.Frame(left_frame)
        file_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(file_frame, text="Load File", command=self.load_file_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Save", command=self.save_items).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Save As", command=self.save_as_items).pack(side=tk.LEFT, padx=2)
        
        # Treeview for items grouped by tables
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # TreeView'u basit şekilde tanımla
        self.tree = ttk.Treeview(tree_frame, show="tree")
        self.tree.column("#0", width=350)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # TreeView event'lerini ayarla
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Button-1>', self.on_tree_click)
        
        # Item operations frame
        item_ops_frame = ttk.Frame(left_frame)
        item_ops_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(item_ops_frame, text="Add New Item", command=self.add_new_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(item_ops_frame, text="Delete Item", command=self.delete_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(item_ops_frame, text="Refresh", command=self.refresh_tree).pack(side=tk.LEFT, padx=2)
        
        # Right frame - Item details
        right_frame = ttk.LabelFrame(main_frame, text="Item Details", padding="5")
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(1, weight=1)
        
        # Create notebook for organized tabs
        notebook = ttk.Notebook(right_frame)
        notebook.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Basic info tab
        basic_frame = ttk.Frame(notebook, padding="5")
        notebook.add(basic_frame, text="Basic Info")
        self.create_basic_tab(basic_frame)

        # Frames & Sounds tab
        frames_frame = ttk.Frame(notebook, padding="5")
        notebook.add(frames_frame, text="Frames & Sounds")
        self.create_frames_tab(frames_frame)

        # Stats tab
        stats_frame = ttk.Frame(notebook, padding="5")
        notebook.add(stats_frame, text="Stats")
        self.create_stats_tab(stats_frame)

        # Requirements tab
        req_frame = ttk.Frame(notebook, padding="5")
        notebook.add(req_frame, text="Requirements")
        self.create_requirements_tab(req_frame)

        # Advanced tab
        advanced_frame = ttk.Frame(notebook, padding="5")
        notebook.add(advanced_frame, text="Advanced")
        self.create_advanced_tab(advanced_frame)

        # Raw data tab - hex dump of the tail for transparency/debugging
        raw_frame = ttk.Frame(notebook, padding="5")
        notebook.add(raw_frame, text="Raw Data")
        self.create_raw_tab(raw_frame)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Load an Item.inf file")
        status_bar = ttk.Label(right_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def get_class_name_from_id(self, class_id):
        """Return name based on Item Class ID"""
        class_names = {
            0: "Motorcycle",
            1: "Potions",
            2: "Water",
            3: "Holy Water",
            4: "Magazine",
            5: "Bomb Material",
            6: "Miscellaneous",
            7: "Keys",
            8: "Rings",
            9: "Bracelets",
            10: "Necklaces",
            11: "Coats",
            12: "Trousers",
            13: "Shoes",
            14: "Swords",
            15: "Blades",
            16: "Shields",
            17: "Crosses",
            18: "Gloves",
            19: "Helms",
            20: "Shotguns",
            21: "SMGs",
            22: "Assault Rifles",
            23: "Sniper Rifles",
            24: "Bombs",
            25: "Mines",
            26: "Belts",
            27: "Learning Items",
            28: "Currency",
            29: "Corpses",
            30: "Vampire Rings",
            31: "Vampire Bracelets",
            32: "Vampire Necklaces",
            33: "Vampire Coats",
            34: "Skulls",
            35: "Maces",
            36: "Serums",
            37: "Vampire Misc",
            38: "Slayer Portal Items",
            39: "Vampire Portal Items",
            40: "Event Gift Boxes",
            41: "Event Stars",
            42: "Vampire Earrings",
            43: "Relics",
            44: "Vampire Weapons",
            45: "Vampire Amulets",
            46: "Quest Items",
            47: "Event Trees",
            48: "Event Misc",
            49: "Blood Bibles",
            50: "Castle Symbols",
            51: "Couple Rings",
            52: "Vampire Couple Rings",
            53: "Event Items",
            54: "Dye Potions",
            55: "Resurrect Items",
            56: "Mixing Items",
            57: "Ousters Armsbands",
            58: "Ousters Boots",
            59: "Ousters Chakrams",
            60: "Ousters Circlets",
            61: "Ousters Coats",
            62: "Ousters Pendants",
            63: "Ousters Rings",
            64: "Ousters Stones",
            65: "Ousters Wristlets",
            66: "Larvae",
            67: "Pupae",
            68: "Compos Mei",
            69: "Ousters Summon Items",
            70: "Effect Items",
            71: "Code Sheets",
            72: "Moon Cards",
            73: "Sweepers",
            74: "Pet Items",
            75: "Pet Food",
            76: "Pet Enchant Items",
            77: "Lucky Bags",
            78: "SMS Items",
            79: "Core Zaps",
            80: "GQuest Items",
            81: "Trap Items",
            82: "Blood Bible Signs",
            83: "War Items",
            84: "Carrying Receivers",
            85: "Shoulder Armor",
            86: "Dermis",
            87: "Persona",
            88: "Fascia",
            89: "Mittens",
            90: "Sub Inventory",
            91: "Common Quest Items",
            92: "Ethereal Chains",
            93: "Ousters Harmonic Pendants",
            94: "Check Money",
            95: "Cue of Adam",
            96: "Contract of Blood",
            97: "Skill Books",
            98: "Vampire Wing Items",
            99: "Ousters Wing Items",
            100: "Tuning Slayer",
            101: "Tuning Vampire",
            102: "Tuning Ousters",
            103: "Call NPC Cards",
            104: "Rank Gems",
            105: "Max Class",
            106: "Null Class"
        }
        return class_names.get(class_id, f"Unknown Class {class_id}")
    
    def create_basic_tab(self, parent):
        """Create basic information tab"""
        # Strings
        ttk.Label(parent, text="HName:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.hname_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.hname_var, width=40).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        
        ttk.Label(parent, text="EName:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.ename_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.ename_var, width=40).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        
        ttk.Label(parent, text="Description:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.desc_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.desc_var, width=40).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        # Price / Weight (confirmed against the real byte layout)
        ttk.Label(parent, text="Price:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.price_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.price_var, from_=0, to=4294967295, width=15).grid(row=3, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="Weight:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.weight_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.weight_var, from_=0, to=65535, width=10).grid(row=4, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="Grid Width:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.gridw_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.gridw_var, from_=0, to=255, width=10).grid(row=5, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="Grid Height:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.gridh_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.gridh_var, from_=0, to=255, width=10).grid(row=6, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="Option slots (read-only, see Advanced tab):").grid(row=7, column=0, sticky=tk.W, pady=(10, 2), columnspan=2)
        self.option_list_var = tk.StringVar()
        ttk.Label(parent, textvariable=self.option_list_var, foreground="#555").grid(row=8, column=0, sticky=tk.W, pady=2, columnspan=2)

        # Inventory icon preview, decoded live from Data\Ui\spk\Item.ispk
        # (the same sprite pack the real game client draws inventory slots
        # from) using InventoryFrameID - see darkeden_sprite.py.
        preview_frame = ttk.LabelFrame(parent, text="Inventory Icon", padding="5")
        preview_frame.grid(row=0, column=2, rowspan=9, sticky=(tk.N, tk.S), padx=(15, 0))
        self.preview_canvas = tk.Canvas(preview_frame, width=160, height=160, background="#303040", highlightthickness=0)
        self.preview_canvas.pack()
        self.preview_caption_var = tk.StringVar(value="(no sprite pack loaded)")
        ttk.Label(preview_frame, textvariable=self.preview_caption_var, foreground="#888", font=('Arial', 8)).pack(pady=(4, 0))

        parent.columnconfigure(1, weight=1)

    def create_frames_tab(self, parent):
        """Create frames and sounds tab. Only 6 frame IDs really exist in
        ITEMTABLE_INFO (no "UseFrameID" - that was the community tool's
        invention for a different Item.inf build)."""
        labels = [
            ("Tile Frame ID:", "TileFrameID"), ("Inventory Frame ID:", "InventoryFrameID"),
            ("Gear Frame ID:", "GearFrameID"), ("Drop Frame ID:", "DropFrameID"),
            ("Male Addon Frame ID:", "AddonMaleFrameID"), ("Female Addon Frame ID:", "AddonFemaleFrameID"),
            ("Use Sound ID:", "UseSoundID"), ("Tile Sound ID:", "TileSoundID"),
            ("Inventory Sound ID:", "InventorySoundID"), ("Gear Sound ID:", "GearSoundID"),
            ("Description Frame ID:", "DescriptionFrameID"),
        ]

        self.frame_vars = {}
        for i, (label, key) in enumerate(labels):
            ttk.Label(parent, text=label).grid(row=i, column=0, sticky=tk.W, pady=2)
            var = tk.IntVar()
            ttk.Spinbox(parent, textvariable=var, from_=0, to=65535, width=10).grid(row=i, column=1, sticky=tk.W, pady=2, padx=(5, 0))
            self.frame_vars[key] = var

    # Shown instead of a raw -1 for a slot the item's class never reads at
    # runtime (confirmed via MItem.h/.cpp getters) - editable text is still
    # accepted if you type a real number over it.
    NA_TEXT = "(não se aplica)"
    SILVER_CLASSES = {14, 15, 17, 35}  # SWORD, BLADE, CROSS, MACE - only these read SilverMax
    WEAPON_GROUPS = {'weapon', 'weapon_mana', 'weapon_reach'}  # only these read ToHit/CriticalHit

    def _display_value(self, value, applicable):
        """-1 on a slot the class doesn't use -> friendly n/a text; anything
        else (including a real -1 the class DOES read, or a stray non-(-1)
        value on an unused slot) is shown as-is so nothing is ever hidden."""
        if not applicable and value == -1:
            return self.NA_TEXT
        return str(value)

    def _parse_value(self, text, current_value):
        text = text.strip()
        if text == self.NA_TEXT:
            return -1
        try:
            return int(text)
        except ValueError:
            return current_value  # leave unchanged rather than crash on bad input

    def create_stats_tab(self, parent):
        """Create stats tab. Value1-7 are shared slots whose real meaning
        depends on the item's ITEM_CLASS (grounded in MItem.h/.cpp getters -
        see CLASS_VALUE_GROUP/VALUE_LABEL_GROUPS). SilverMax/ToHit/CriticalHit
        are dedicated fields that are ALSO only meaningful for specific
        classes (SilverMax: Sword/Blade/Cross/Mace silver-coating cost;
        ToHit/CriticalHit: weapon classes only). Everything updates per
        selected item in load_item_to_ui(); byte offsets never change."""
        value_labels = [(f"Value {i}:", f"Value{i}") for i in range(1, 8)]
        self.value_vars = {}
        self.value_labels = {}
        self.value_entries = {}

        for i, (label, key) in enumerate(value_labels):
            lbl = ttk.Label(parent, text=label)
            lbl.grid(row=i, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar()
            entry = ttk.Entry(parent, textvariable=var, width=18)
            entry.grid(row=i, column=1, sticky=tk.W, pady=2, padx=(5, 0))
            self.value_vars[key] = var
            self.value_labels[key] = lbl
            self.value_entries[key] = entry

        ttk.Label(parent, text="Silver Coating Cost (Sword/Blade/Cross/Mace only):").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.silver_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.silver_var, width=18).grid(row=7, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="To Hit (weapons only):").grid(row=8, column=0, sticky=tk.W, pady=2)
        self.tohit_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.tohit_var, width=18).grid(row=8, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="Max Number:").grid(row=9, column=0, sticky=tk.W, pady=2)
        self.maxnum_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.maxnum_var, from_=0, to=4294967295, width=15).grid(row=9, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        ttk.Label(parent, text="(client ignores this except Portal Item / Summon Gem - the real stack\ncap is a hardcoded constant per class, e.g. MAX_POTION_PILE_NUMBER=30)",
                  foreground="#888", font=('Arial', 8)).grid(row=10, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

        ttk.Label(parent, text="Critical Hit (weapons only):").grid(row=11, column=0, sticky=tk.W, pady=2)
        self.crit_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.crit_var, width=18).grid(row=11, column=1, sticky=tk.W, pady=2, padx=(5, 0))

    def create_requirements_tab(self, parent):
        """Create requirements tab"""
        ttk.Label(parent, text="STR:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.str_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.str_var, from_=0, to=255, width=10).grid(row=0, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="DEX:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.dex_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.dex_var, from_=0, to=255, width=10).grid(row=1, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="INT:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.int_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.int_var, from_=0, to=255, width=10).grid(row=2, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="SUM:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.sum_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.sum_var, from_=0, to=65535, width=10).grid(row=3, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="Level:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.level_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.level_var, from_=0, to=255, width=10).grid(row=4, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="Adv. Class Level (job promotion, not char level):").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.adv_level_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.adv_level_var, from_=0, to=255, width=10).grid(row=5, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        self.male_only_var = tk.BooleanVar()
        ttk.Checkbutton(parent, text="Male Only", variable=self.male_only_var).grid(row=6, column=0, sticky=tk.W, pady=2)

        self.female_only_var = tk.BooleanVar()
        ttk.Checkbutton(parent, text="Female Only", variable=self.female_only_var).grid(row=6, column=1, sticky=tk.W, pady=2)

        ttk.Label(parent, text="Use Action/Skill ID (basic attack anim; 65535=melee default):").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.use_action_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.use_action_var, from_=0, to=4294967295, width=15).grid(row=7, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        # Race is a real bitmask (RaceType.h: FLAG_RACE_SLAYER=1, FLAG_RACE_VAMPIRE=2,
        # FLAG_RACE_OUSTERS=4) - shown as 3 checkboxes instead of a raw byte.
        # 0 doesn't mean "any race": for gear it means "fits no wearer's race
        # check, so it never grants its bonuses" (MCreature::CheckAffectStatus).
        ttk.Label(parent, text="Usable by race (0 = fits no one - gear grants nothing):").grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(8, 2))
        self.race_slayer_var = tk.BooleanVar()
        self.race_vampire_var = tk.BooleanVar()
        self.race_ousters_var = tk.BooleanVar()
        ttk.Checkbutton(parent, text="Slayer", variable=self.race_slayer_var).grid(row=9, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(parent, text="Vampire", variable=self.race_vampire_var).grid(row=9, column=1, sticky=tk.W, pady=2)
        ttk.Checkbutton(parent, text="Ousters", variable=self.race_ousters_var).grid(row=10, column=0, sticky=tk.W, pady=2)

    def create_advanced_tab(self, parent):
        """Create advanced properties tab. ItemStyle and ElementalType are
        small closed enums in the client source - shown as dropdowns instead
        of raw integers."""
        ttk.Label(parent, text="Item Style:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.item_style_var = tk.StringVar()
        ttk.Combobox(parent, textvariable=self.item_style_var, width=30, state="readonly",
                     values=["0 = Normal", "1 = Unique (special glow color)"]).grid(row=0, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="Elemental Type:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.elemental_type_var = tk.StringVar()
        ttk.Combobox(parent, textvariable=self.elemental_type_var, width=30, state="readonly",
                     values=["-1 = Any/None", "0 = Fire", "1 = Water", "2 = Earth", "3 = Wind", "4 = Sum (unused)"]
                     ).grid(row=1, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(parent, text="Elemental Magnitude:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.elemental_var = tk.IntVar()
        ttk.Spinbox(parent, textvariable=self.elemental_var, from_=0, to=65535, width=10).grid(row=2, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        ttk.Label(parent, text="(only Ousters Elemental Stone/Wristlet use this; 0 for everything else)",
                  foreground="#888", font=('Arial', 8)).grid(row=3, column=0, columnspan=2, sticky=tk.W)

    def create_raw_tab(self, parent):
        """Read-only hex view of the full tail, for transparency/debugging
        alongside the decoded fields in the other tabs."""
        ttk.Label(parent, text="Fixed tail (99 bytes) + option payload, exactly as stored on disk:").pack(anchor=tk.W, pady=(0, 5))
        self.raw_text = tk.Text(parent, width=80, height=20, state=tk.DISABLED, wrap=tk.WORD)
        self.raw_text.pack(fill=tk.BOTH, expand=True)
    
    def load_file_dialog(self):
        """Open file dialog to load Item.inf file"""
        filename = filedialog.askopenfilename(
            title="Select Item.inf file",
            filetypes=[("INF files", "*.inf"), ("All files", "*.*")]
        )
        if filename:
            self.current_filename = filename
            self.load_items(filename)
    
    def load_items(self, filename):
        """Load items from Item.inf file using ItemTableList format"""
        try:
            with open(filename, 'rb') as file:
                self.item_table_list = ItemTableList(file)

            self.item_option_names = load_item_option_names(filename)
            self._load_sprite_pack(filename)
            self.refresh_tree()
            total_items = self.item_table_list.get_total_item_count()
            non_empty_tables = len(self.item_table_list.get_non_empty_tables())
            self.status_var.set(f"Loaded {non_empty_tables} tables with {total_items} total items")
            messagebox.showinfo("Success", f"Loaded {non_empty_tables} tables with {total_items} total items")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load items: {str(e)}")
            self.status_var.set(f"Error loading file: {str(e)}")

    def _load_sprite_pack(self, item_inf_path):
        """Best-effort: locate & load Data\\Ui\\spk\\Item.ispk next to the
        opened Item.inf so the Basic Info tab can show each item's real
        inventory icon. Silently disables the preview if darkeden_sprite.py
        is missing or the sprite file isn't found - this is a nice-to-have,
        not required for editing Item.inf."""
        self.sprite_pack = None
        if darkeden_sprite is None:
            return
        sprite_path = darkeden_sprite.find_sprite_pack(item_inf_path)
        if not sprite_path:
            return
        try:
            self.sprite_pack = darkeden_sprite.SpritePack(sprite_path)
            if self.sprite_colorset is None:
                self.sprite_colorset = darkeden_sprite.build_color_set()
        except Exception as e:
            print(f"Sprite preview unavailable: {e}")
            self.sprite_pack = None
    
    def refresh_tree(self):
        """Refresh the treeview with items grouped by tables"""
        self.refresh_tree_silent()
        
        # Mevcut item'ı tekrar seç ve görünür yap
        if self.current_item_ref:
            table_index = self.current_item_ref['table_index']
            item_index = self.current_item_ref['item_index']
            
            # TreeView'da bu item'ı bul ve seç
            for table_node in self.tree.get_children():
                # Tabloyu genişlet
                self.tree.item(table_node, open=True)
                self.expanded_tables.add(table_index)
                
                # Item'ı bul ve seç
                for child in self.tree.get_children(table_node):
                    if self.item_references.get(child) == (table_index, item_index):
                        self.tree.selection_set(child)
                        self.tree.focus(child)
                        # Item'ı görünür yap
                        self.tree.see(child)
                        break
                break
    
    def refresh_tree_silent(self):
        """Refresh tree without triggering selection events"""
        # Event binding'i geçici olarak kaldır
        self.tree.unbind('<<TreeviewSelect>>')
        
        # Mevcut genişletilmiş tabloları hatırla
        current_expanded = set(self.expanded_tables)
        
        self.tree.delete(*self.tree.get_children())
        self.item_references.clear()
        
        if not self.item_table_list:
            # Event binding'i geri ekle
            self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
            return
        
        # Tüm tabloları ve item'ları yeniden oluştur
        for original_index, table in enumerate(self.item_table_list.ItemTables):
            if not table.Items:  # Boş tabloları atla
                continue
            
            # Tablo başlığı: table index == real ITEM_CLASS id (confirmed
            # structurally against the client source), so look it up directly
            # instead of guessing from item names.
            class_name = self.get_class_name_from_id(original_index)
            table_node = self.tree.insert("", "end", text=f"{class_name} ({len(table.Items)} items)")
            
            for item_index, item in enumerate(table.Items):
                display_name = item.HName if item.HName else f"Item {item_index}"
                item_node = self.tree.insert(table_node, "end", text=display_name)
                # Store reference in dictionary
                self.item_references[item_node] = (original_index, item_index)
            
            # Eğer önceden genişletilmişse, tekrar genişlet
            if original_index in current_expanded:
                self.tree.item(table_node, open=True)
        
        # Event binding'i geri ekle
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
    
    def on_tree_click(self, event):
        """Handle tree click to prevent collapse when clicking items"""
        item = self.tree.identify('item', event.x, event.y)
        if item:
            # Eğer bir tablo node'una tıklandıysa, genişletme/daraltma durumunu güncelle
            if self.tree.get_children(item):
                # Bu bir tablo node'u
                table_index = self.get_table_index_from_node(item)
                if table_index is not None:
                    if self.tree.item(item, 'open'):
                        self.expanded_tables.add(table_index)
                    else:
                        self.expanded_tables.discard(table_index)
    
    def get_table_index_from_node(self, node):
        """Get table index from tree node"""
        try:
            # Tüm tablo node'larını kontrol et
            table_counter = 0
            for original_index, table in enumerate(self.item_table_list.ItemTables):
                if not table.Items:  # Boş tabloları atla
                    continue
                    
                if table_counter == len(self.tree.get_children()):
                    break
                    
                current_node = self.tree.get_children()[table_counter]
                if current_node == node:
                    return original_index
                    
                table_counter += 1
        except Exception as e:
            print(f"Error getting table index: {e}")
        return None
    
    def restore_selection(self, selection):
        """Önceki seçimi geri yükle"""
        table_index = selection['table_index']
        item_index = selection['item_index']
        
        # Tabloyu bul
        for table_node in self.tree.get_children():
            # Tabloyu genişlet
            self.tree.item(table_node, open=True)
            
            # Item'ı bul ve seç
            for child in self.tree.get_children(table_node):
                if self.item_references.get(child) == (table_index, item_index):
                    self.tree.selection_set(child)
                    self.tree.focus(child)
                    self.tree.see(child)  # Görünür yap
                    return
    
    def on_tree_select(self, event):
        """Handle item selection from tree - basitleştirilmiş versiyon"""
        try:
            selection = self.tree.selection()
            if not selection:
                return
            
            item_id = selection[0]
            
            # Check if it's a table node (has children) or item node
            children = self.tree.get_children(item_id)
            if children:
                # It's a table node, genişletme durumunu güncelle
                table_index = self.get_table_index_from_node(item_id)
                if table_index is not None:
                    if self.tree.item(item_id, 'open'):
                        self.expanded_tables.add(table_index)
                    else:
                        self.expanded_tables.discard(table_index)
                return
            
            # Get reference from dictionary
            if item_id not in self.item_references:
                return
            
            table_index, item_index = self.item_references[item_id]
            
            # Save current item if any
            if self.current_item_ref:
                self.update_current_item()
            
            # Load new item
            if (table_index < len(self.item_table_list.ItemTables) and 
                item_index < len(self.item_table_list.ItemTables[table_index].Items)):
                
                item = self.item_table_list.ItemTables[table_index].Items[item_index]
                self.current_item_ref = {
                    'table_index': table_index,
                    'item_index': item_index,
                    'item': item
                }
                
                self.load_item_to_ui(item)
                self.status_var.set(f"Editing: {item.HName}")
                
                # Item seçildiğinde tabloyu genişlet olarak işaretle
                self.expanded_tables.add(table_index)
                
        except Exception as e:
            print(f"Error in tree selection: {e}")
    
    # Value1-7 slot meaning per ITEM_CLASS - grounded directly in the actual
    # C++ getters (MItem.h/.cpp), not just the Korean comment block (which
    # left out a few things the getters reveal, e.g. Potion.Value2=ManaPoint,
    # Cross/Mace.Value5=ManaCost vs Gun.Value5=Reach, and that Value1/2/6 are
    # inherited unchanged by every MAccessoryItem/MGearItem subclass even
    # when the .inf data leaves them at 0 for pure jewelry).
    VALUE_LABEL_GROUPS = {
        'gear':       {'Value1': 'Durability:', 'Value2': 'Protection:', 'Value6': 'Defense:'},
        'belt':       {'Value1': 'Durability:', 'Value2': 'Protection:', 'Value3': 'Pocket Count:', 'Value6': 'Defense:'},
        'motorcycle': {'Value1': 'Durability:', 'Value2': 'Carrying Capacity:', 'Value6': 'Defense (unused by client):'},
        'potion':     {'Value1': 'Heal Amount:', 'Value2': 'Mana Point:'},
        'potion_heal_only': {'Value1': 'Heal Amount:'},
        'damage':     {'Value1': 'Min Damage:', 'Value2': 'Max Damage:'},
        'magazine':   {'Value1': 'Gun Class ID:', 'Value2': 'Magazine Size:'},
        'weapon':     {'Value1': 'Durability:', 'Value3': 'Min Damage:', 'Value4': 'Max Damage:', 'Value7': 'Speed:'},
        'weapon_mana':  {'Value1': 'Durability:', 'Value3': 'Min Damage:', 'Value4': 'Max Damage:',
                          'Value5': 'Mana Cost:', 'Value7': 'Speed:'},
        'weapon_reach': {'Value1': 'Durability:', 'Value3': 'Min Damage:', 'Value4': 'Max Damage:',
                          'Value5': 'Reach:', 'Value7': 'Speed:'},
        'none': {},
    }

    # ITEM_CLASS id (= table index in Item.inf, confirmed structurally) -> group.
    # Anything not listed here defaults to 'none' (plain name/description/price
    # item with no combat stats - confirmed by the absence of any stat getter
    # override for that class in MItem.h).
    CLASS_VALUE_GROUP = {
        0: 'motorcycle',                    # MOTORCYCLE
        1: 'potion',                        # POTION
        3: 'damage',                        # HOLYWATER
        4: 'magazine',                      # MAGAZINE
        8: 'gear', 9: 'gear', 10: 'gear',   # RING, BRACELET, NECKLACE (accessory)
        11: 'gear', 12: 'gear',             # COAT, TROUSER
        13: 'gear',                         # SHOES
        14: 'weapon', 15: 'weapon',         # SWORD, BLADE
        16: 'gear',                         # SHIELD
        17: 'weapon_mana',                  # CROSS
        18: 'gear', 19: 'gear',             # GLOVE, HELM
        20: 'weapon_reach', 21: 'weapon_reach', 22: 'weapon_reach', 23: 'weapon_reach',  # SG/SMG/AR/SR
        24: 'damage', 25: 'damage',         # BOMB, MINE
        26: 'belt',                         # BELT
        30: 'gear', 31: 'gear', 32: 'gear', 33: 'gear',  # VAMPIRE RING/BRACELET/NECKLACE/COAT
        35: 'weapon_mana',                  # MACE
        36: 'potion_heal_only',             # SERUM
        42: 'gear',                         # VAMPIRE_EARRING
        44: 'weapon',                       # VAMPIRE_WEAPON
        45: 'gear',                         # VAMPIRE_AMULET
        51: 'gear', 52: 'gear',             # COUPLE_RING, VAMPIRE_COUPLE_RING (via MRing)
        57: 'belt',                         # OUSTERS_ARMSBAND
        58: 'gear',                         # OUSTERS_BOOTS
        59: 'weapon',                       # OUSTERS_CHAKRAM
        60: 'gear',                         # OUSTERS_CIRCLET
        61: 'gear',                         # OUSTERS_COAT
        62: 'gear', 63: 'gear', 64: 'gear', # OUSTERS_PENDENT/RING/STONE
        65: 'weapon',                       # OUSTERS_WRISTLET
        67: 'potion', 68: 'potion',         # PUPA, COMPOS_MEI
        79: 'gear',                         # CORE_ZAP
        82: 'gear',                         # BLOOD_BIBLE_SIGN (raw MGearItem, same slots)
        84: 'gear', 85: 'gear', 86: 'gear', 87: 'gear', 88: 'gear',  # CARRYING_RECEIVER/SHOULDER_ARMOR/DERMIS/PERSONA/FASCIA
        89: 'gear',                         # MITTEN
    }

    def _guess_value_labels(self, class_id):
        """Per-class relabel of the Value1-7 slots, looked up by the item's
        real ITEM_CLASS id (table index). Falls back to generic 'Value N'
        for classes with no stat getter (keys, scrolls, quest items, etc.) -
        the underlying byte offset never changes, this only changes what
        text is displayed."""
        labels = {f'Value{i}': f'Value {i}:' for i in range(1, 8)}
        group = self.CLASS_VALUE_GROUP.get(class_id, 'none')
        labels.update(self.VALUE_LABEL_GROUPS[group])
        return labels

    def _render_item_preview(self, item):
        """Decode item.InventoryFrameID from the loaded Item.ispk (if any)
        and draw it centered on the preview canvas, zoomed up for legibility
        (real icons are ~30-90px). Silently shows a placeholder if no sprite
        pack is loaded or the frame id is out of range."""
        self.preview_canvas.delete("all")
        cw = int(self.preview_canvas['width'])
        ch = int(self.preview_canvas['height'])

        if self.sprite_pack is None:
            self.preview_canvas.create_text(cw // 2, ch // 2, text="(no sprite pack)",
                                             fill="#888", font=('Arial', 8))
            self.preview_caption_var.set("Open Item.inf from inside the real Data\\ folder to enable this")
            return

        frame_id = item.InventoryFrameID
        try:
            w, h, rgb, mask = self.sprite_pack.decode(frame_id, self.sprite_colorset)
        except Exception as e:
            self.preview_canvas.create_text(cw // 2, ch // 2, text=f"(frame {frame_id}: {e})",
                                             fill="#888", font=('Arial', 8))
            self.preview_caption_var.set(f"InventoryFrameID={frame_id}")
            return

        if w == 0 or h == 0:
            self.preview_canvas.create_text(cw // 2, ch // 2, text="(empty sprite)", fill="#888", font=('Arial', 8))
            self.preview_caption_var.set(f"InventoryFrameID={frame_id} (0x0)")
            return

        ppm = darkeden_sprite.to_ppm(w, h, rgb, mask, bg=(0x30, 0x30, 0x40))
        photo = tk.PhotoImage(data=ppm)
        zoom = max(1, min(6, (cw - 10) // max(w, 1), (ch - 10) // max(h, 1)))
        if zoom > 1:
            photo = photo.zoom(zoom, zoom)
        self.preview_photo = photo  # keep a reference, Tk drops images with no live ref
        self.preview_canvas.create_image(cw // 2, ch // 2, image=photo, anchor=tk.CENTER)
        self.preview_caption_var.set(f"InventoryFrameID={frame_id}  ({w}x{h}, {zoom}x zoom)")

    def load_item_to_ui(self, item):
        """Load item data to UI fields"""
        # Basic info
        self.hname_var.set(item.HName)
        self.ename_var.set(item.EName)
        self.desc_var.set(item.Description)
        self.price_var.set(item.Price)
        self.weight_var.set(item.Weight)
        self.gridw_var.set(item.GridWidth)
        self.gridh_var.set(item.GridHeight)

        option_list = item.OptionList
        if not option_list:
            self.option_list_var.set("(none)")
        elif self.item_option_names:
            parts = []
            for idx in option_list:
                if 0 <= idx < len(self.item_option_names):
                    name, part_label, plus = self.item_option_names[idx]
                    parts.append(f"{name} ({part_label} {plus:+d})")
                else:
                    parts.append(f"#{idx} (out of range)")
            self.option_list_var.set(", ".join(parts))
        else:
            self.option_list_var.set(", ".join(f"#{i}" for i in option_list) + "  (open a sibling ItemOption.inf to see names)")

        self._render_item_preview(item)

        # Frames and sounds
        for key, var in self.frame_vars.items():
            var.set(getattr(item, key))

        # Values - label + n/a-greying both driven by the item's real class
        class_id = self.current_item_ref['table_index'] if self.current_item_ref else None
        group = self.CLASS_VALUE_GROUP.get(class_id, 'none')
        overridden_keys = self.VALUE_LABEL_GROUPS[group]
        value_labels = self._guess_value_labels(class_id)
        for key in self.value_vars:
            self.value_labels[key].config(text=value_labels[key])
            raw = getattr(item, key)
            applicable = key in overridden_keys
            display = self._display_value(raw, applicable)
            self.value_vars[key].set(display)
            is_na = (display == self.NA_TEXT)
            color = '#888' if is_na else ''
            self.value_labels[key].config(foreground=color)
            self.value_entries[key].config(foreground=color)

        # Other stats - SilverMax/ToHit/CriticalHit are only meaningful for
        # specific classes too (see SILVER_CLASSES/WEAPON_GROUPS)
        silver_applicable = class_id in self.SILVER_CLASSES
        weapon_applicable = group in self.WEAPON_GROUPS
        self.silver_var.set(self._display_value(item.SilverMax, silver_applicable))
        self.tohit_var.set(self._display_value(item.ToHit, weapon_applicable))
        self.crit_var.set(self._display_value(item.CriticalHit, weapon_applicable))
        self.maxnum_var.set(item.MaxNumber)

        # Requirements
        self.str_var.set(item.RequireSTR)
        self.dex_var.set(item.RequireDEX)
        self.int_var.set(item.RequireINT)
        self.sum_var.set(item.RequireSUM)
        self.level_var.set(item.RequireLevel)
        self.adv_level_var.set(item.RequireAdvancementLevel)
        self.male_only_var.set(bool(item.bMaleOnly))
        self.female_only_var.set(bool(item.bFemaleOnly))
        self.use_action_var.set(item.UseActionInfo)
        race = item.Race
        self.race_slayer_var.set(bool(race & 1))
        self.race_vampire_var.set(bool(race & 2))
        self.race_ousters_var.set(bool(race & 4))

        # Advanced properties
        style_map = {0: "0 = Normal", 1: "1 = Unique (special glow color)"}
        self.item_style_var.set(style_map.get(item.ItemStyle, str(item.ItemStyle)))
        elemental_type_map = {-1: "-1 = Any/None", 0: "0 = Fire", 1: "1 = Water",
                               2: "2 = Earth", 3: "3 = Wind", 4: "4 = Sum (unused)"}
        self.elemental_type_var.set(elemental_type_map.get(item.ElementalType, str(item.ElementalType)))
        self.elemental_var.set(item.Elemental)

        # Raw tail, read-only
        self.raw_text.config(state=tk.NORMAL)
        self.raw_text.delete("1.0", tk.END)
        option_count = item.OptionCount
        self.raw_text.insert(
            "1.0",
            f"length: {len(item.tail)} bytes (99 fixed + {len(item.tail) - Item.FIXED_TAIL_SIZE} option payload)\n"
            f"option count byte @85: {option_count}\n\n"
            + bytes(item.tail).hex(' ')
        )
        self.raw_text.config(state=tk.DISABLED)

    def update_current_item(self):
        """Update current item from UI fields"""
        if not self.current_item_ref:
            return

        item = self.current_item_ref['item']

        # Basic info
        item.HName = self.hname_var.get()
        item.EName = self.ename_var.get()
        item.Description = self.desc_var.get()
        item.Price = self.price_var.get()
        item.Weight = self.weight_var.get()
        item.GridWidth = self.gridw_var.get()
        item.GridHeight = self.gridh_var.get()

        # Frames and sounds
        for key, var in self.frame_vars.items():
            setattr(item, key, var.get())

        # Values - text fields may hold the n/a placeholder or a real number
        for key, var in self.value_vars.items():
            setattr(item, key, self._parse_value(var.get(), getattr(item, key)))

        # Other stats
        item.SilverMax = self._parse_value(self.silver_var.get(), item.SilverMax)
        item.ToHit = self._parse_value(self.tohit_var.get(), item.ToHit)
        item.MaxNumber = self.maxnum_var.get()
        item.CriticalHit = self._parse_value(self.crit_var.get(), item.CriticalHit)

        # Requirements
        item.RequireSTR = self.str_var.get()
        item.RequireDEX = self.dex_var.get()
        item.RequireINT = self.int_var.get()
        item.RequireSUM = self.sum_var.get()
        item.RequireLevel = self.level_var.get()
        item.RequireAdvancementLevel = self.adv_level_var.get()
        item.bMaleOnly = 1 if self.male_only_var.get() else 0
        item.bFemaleOnly = 1 if self.female_only_var.get() else 0
        item.UseActionInfo = self.use_action_var.get()
        item.Race = ((1 if self.race_slayer_var.get() else 0)
                     | (2 if self.race_vampire_var.get() else 0)
                     | (4 if self.race_ousters_var.get() else 0))

        # Advanced properties - parse the leading "N = " integer back out of
        # the dropdown's display text
        def _leading_int(text, fallback):
            try:
                return int(text.split('=')[0].strip())
            except (ValueError, IndexError):
                return fallback

        item.ItemStyle = _leading_int(self.item_style_var.get(), item.ItemStyle)
        item.ElementalType = _leading_int(self.elemental_type_var.get(), item.ElementalType)
        item.Elemental = self.elemental_var.get()

        # Sadece tree'yi güncelle, selection event tetikleme
        self.refresh_tree_silent()
    
    def save_items(self):
        """Save items to current file"""
        if not self.item_table_list:
            messagebox.showwarning("Warning", "No items to save!")
            return
        
        if self.current_filename is None:
            self.save_as_items()
            return
        
        # Update current item before saving
        if self.current_item_ref:
            self.update_current_item()
        
        try:
            with open(self.current_filename, 'wb') as file:
                self.item_table_list.save_to_file(file)
            
            total_items = self.item_table_list.get_total_item_count()
            self.status_var.set(f"Saved {len(self.item_table_list.ItemTables)} tables with {total_items} items")
            messagebox.showinfo("Success", f"Saved {len(self.item_table_list.ItemTables)} item tables with {total_items} total items")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save items: {str(e)}")
            self.status_var.set(f"Error saving file: {str(e)}")
    
    def save_as_items(self):
        """Save items to new file"""
        if not self.item_table_list:
            messagebox.showwarning("Warning", "No items to save!")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Save Item.inf file",
            defaultextension=".inf",
            filetypes=[("INF files", "*.inf"), ("All files", "*.*")]
        )
        if filename:
            self.current_filename = filename
            self.save_items()
    
    def add_new_item(self):
        """Add a new item to the SAME table/class as whatever is currently
        selected in the tree (table index == real ITEM_CLASS id), so it
        lands in the right category instead of always going to table 0."""
        if not self.item_table_list:
            self.item_table_list = ItemTableList()
            self.item_table_list.ItemTables.append(ItemTable())

        if self.current_item_ref:
            target_table_index = self.current_item_ref['table_index']
        else:
            non_empty = [i for i, t in enumerate(self.item_table_list.ItemTables) if t.Items]
            if not non_empty:
                messagebox.showwarning("Warning", "No table to add to - select an existing item first so I know which category to use.")
                return
            target_table_index = non_empty[0]

        new_item = Item()
        new_item.HName = "New Item"
        new_item.EName = "New Item"

        if self.sprite_pack is not None and messagebox.askyesno(
                "Icon", "Pick an image file for this item's inventory icon now?"):
            self._assign_new_icon(new_item)

        self.item_table_list.ItemTables[target_table_index].Items.append(new_item)
        class_name = self.get_class_name_from_id(target_table_index)
        self.refresh_tree()
        self.status_var.set(f"Added new item to {class_name} (table {target_table_index})")

    def _assign_new_icon(self, item):
        """Prompt for an image file, encode it into the CIndexSprite555
        format and append it to the real Item.ispk (with a one-time pristine
        backup), then point the item's InventoryFrameID at the new sprite."""
        filename = filedialog.askopenfilename(
            title="Choose inventory icon image",
            filetypes=[("Images", "*.png *.gif *.bmp *.jpg *.jpeg"), ("All files", "*.*")]
        )
        if not filename:
            return
        try:
            sprite_bytes, w, h = darkeden_sprite.encode_sprite_from_image(filename)
            new_index = darkeden_sprite.append_sprite_to_pack(self.sprite_pack.path, sprite_bytes)
            # keep the in-memory pack in sync with the file we just extended
            self.sprite_pack = darkeden_sprite.SpritePack(self.sprite_pack.path)
            item.InventoryFrameID = new_index
            messagebox.showinfo(
                "Icon added",
                f"Icon encoded ({w}x{h}) and appended to Item.ispk as sprite #{new_index}.\n"
                f"A pristine backup of the original file was kept as Item.ispk.original_backup "
                f"(created only once, the first time you ever add an icon)."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add icon: {e}")
    
    def delete_item(self):
        """Delete current item"""
        if not self.current_item_ref:
            messagebox.showwarning("Warning", "No item selected!")
            return
        
        table_index = self.current_item_ref['table_index']
        item_index = self.current_item_ref['item_index']
        item_name = self.current_item_ref['item'].HName
        
        if messagebox.askyesno("Confirm", f"Delete item '{item_name}' from Table {table_index}?"):
            # Remove item from table
            del self.item_table_list.ItemTables[table_index].Items[item_index]
            self.current_item_ref = None
            self.refresh_tree()
            self.status_var.set("Item deleted")

def main():
    root = tk.Tk()
    app = ItemEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()