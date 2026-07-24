"""
darkeden_sprite.py - DarkEden .ispk sprite pack reader/writer
================================================================
Author: VictorRP7
Written: 2026-07-21

A from-scratch, dependency-light (only Pillow, for the encoder) implementation
of DarkEden's CIndexSprite555 sprite pack format (.ispk/.ispki - used for item
icons, creatures, effects, etc.). There was no existing tool or public
documentation for this format, so it was reverse engineered directly from the
DarkEden client's own C++ source:

    client-master\\Client\\SpriteLib\\CTypePack.h        (container format)
    client-master\\Client\\SpriteLib\\CIndexSprite.cpp   (color table generator)
    client-master\\Client\\SpriteLib\\CIndexSprite555.cpp (per-sprite row format)
    client-master\\Client\\DXLib\\CDirectDraw.h           (RGB555/565 packing)

...then verified byte-for-byte against the real Data\\Ui\\spk\\Item.ispk file
shipped with the client, by hand-decoding its first sprite and comparing every
byte against what this module produces.

FILE FORMAT SUMMARY
--------------------
Container (.ispk): a bare `WORD spriteCount` followed by that many sprite
records, back-to-back. There is NO magic signature and it is NOT a RAR
archive (RAR + the "darkeden" password is only used by the separate .rpk
text-resource format from the UI/translation work in this project).

Per sprite record:
    WORD width
    WORD height
    for each of `height` rows:
        WORD rowLen                     (word-count of everything below)
        WORD segCount                   (number of trans/opaque runs in this row)
        for each of `segCount` segments:
            WORD transCount             (pixels to skip - transparent)
            WORD indexCount             (count of "recolorable" pixels)
            indexCount x WORD           ((colorSet<<8)|gradation, see below)
            WORD normalCount            (count of literal fixed-color pixels)
            normalCount x WORD          (literal RGB565 pixel)
    Any pixels left over at the end of a row (segments not covering the full
    width) are IMPLICITLY transparent and are simply never stored.

The companion .ispki file (when present) is just a fast-seek index: a
`WORD count` followed by `count` DWORD byte-offsets into the .ispk, one per
sprite, letting the game engine seek straight to a sprite instead of
scanning from the start. This module builds its own offset index the first
time it's needed and ignores the .ispki for READING, but keeps it in sync
when a new sprite is appended (see append_sprite_to_pack) so the real game
client can still use its fast lazy-loading path afterwards.

THE COLOR TABLE ("index" pixels)
---------------------------------
Some pixels aren't stored as a literal color - they're stored as
(colorSet, gradation) and looked up in a 495x30 table of colors. This table
is NOT read from any file: the client generates it once at startup from an
algorithm (33 hardcoded hue "seed" colors, each expanded into a 15-step
white-to-hue and hue-to-black gradient = 30 steps total, x 33 seeds = 495
rows). This is how the game recolors the same base artwork for "unique"
glow effects, dye items, etc. build_color_set() below ports that exact
algorithm (CIndexSprite::SetColorSet / GetIndexColor) so recolorable pixels
render with their real in-game color instead of being skipped or guessed at.
"""
import struct
import os
import shutil


def find_sprite_pack(inf_path, spk_filename="Item.ispk"):
    """Both Item.inf and itemOption.inf live at Data\\Info\\<file>.inf; the
    inventory-icon sprite pack lives at the sibling Data\\Ui\\spk\\Item.ispk
    (confirmed via client-master\\Client\\VS_UI\\src\\VS_UI_filepath.h,
    ISPK_ITEM) regardless of which of those two .inf files you started from.
    Shared by ItemINF_Editor.py and ItemOption.py so both can show live icon
    previews. Returns None if the Data folder layout isn't found relative to
    inf_path (the preview is optional - both editors work fine without it)."""
    info_dir = os.path.dirname(inf_path)
    data_dir = os.path.dirname(info_dir)  # .../Data
    candidate = os.path.join(data_dir, "Ui", "spk", spk_filename)
    if os.path.isfile(candidate):
        return candidate
    # case-insensitive fallback scan, since filesystems/exports vary
    ui_dir = os.path.join(data_dir, "Ui", "spk")
    if os.path.isdir(ui_dir):
        for fname in os.listdir(ui_dir):
            if fname.lower() == spk_filename.lower():
                return os.path.join(ui_dir, fname)
    return None


MAX_COLORSET_SEED = 33
MAX_COLORSET_SEED_MODIFY = 15
MAX_COLORSET = 495  # 33 * 15
MAX_COLORGRADATION = 30
MAX_COLORGRADATION_HALF = 15

# CIndexSprite.cpp: static BYTE rgbPoint[MAX_COLORSET_SEED][3] (0-31 per channel, 555-scale)
RGB_POINTS = [
    (0, 0, 31), (0, 31, 0), (31, 0, 0), (0, 31, 31), (31, 0, 31), (31, 31, 0),
    (0, 0, 16), (0, 16, 0), (16, 0, 0), (0, 16, 16), (16, 0, 16), (16, 16, 0),
    (16, 31, 0), (16, 0, 31), (31, 16, 0), (0, 16, 31), (31, 0, 16), (0, 31, 16),
    (16, 31, 16), (16, 16, 31), (31, 16, 16),
    (16, 31, 31), (31, 16, 31), (31, 31, 16),
    (16, 16, 16), (24, 24, 24), (8, 8, 8),
    (30, 24, 18), (25, 15, 11), (21, 12, 11), (19, 15, 13),
    (21, 18, 11),
    (22, 16, 9),
]


def _color555(r, g, b):
    """Pack 3 channels (0-31 each) into one 555-format WORD: RRRRRGGGGGBBBBB."""
    return ((r & 0x1F) << 10) | ((g & 0x1F) << 5) | (b & 0x1F)


def _get_index_color(step, r0, g0, b0, r1, g1, b1):
    """Port of CIndexSprite::GetIndexColor: linear ramp of `step` 555 colors
    from (r0,g0,b0) to (r1,g1,b1)."""
    if step <= 0:
        return []
    step_1 = float(step - 1) if step > 1 else 1.0
    r, g, b = float(r0), float(g0), float(b0)
    sr, sg, sb = (r1 - r0) / step_1, (g1 - g0) / step_1, (b1 - b0) / step_1
    out = []
    for _ in range(step):
        out.append(_color555(int(r), int(g), int(b)))
        r += sr
        g += sg
        b += sb
    return out


def build_color_set():
    """Port of CIndexSprite::SetColorSet() - builds the 495x30 WORD (555-format)
    color table used to resolve "index" (recolorable) pixels. No file on disk
    holds this - the client generates it at startup from 33 hardcoded hue
    seeds x 15 white/black gradation ramps."""
    color_set = [[0] * MAX_COLORGRADATION for _ in range(MAX_COLORSET)]
    s = 0
    for i in range(MAX_COLORSET_SEED):
        r, g, b = RGB_POINTS[i]
        for j in range(MAX_COLORGRADATION_HALF, 0, -1):
            if j == MAX_COLORGRADATION_HALF:
                ramp1 = _get_index_color(j, 31, 31, 31, r, g, b)
            else:
                prev = color_set[i * MAX_COLORSET_SEED_MODIFY][MAX_COLORGRADATION_HALF - j]
                r0 = (prev >> 10) & 0x1F
                g0 = (prev >> 5) & 0x1F
                b0 = prev & 0x1F
                ramp1 = _get_index_color(j, r0, g0, b0, r, g, b)
            for k, v in enumerate(ramp1):
                color_set[s][k] = v

            ramp2 = _get_index_color(MAX_COLORGRADATION - j, r, g, b, 0, 0, 0)
            for k, v in enumerate(ramp2):
                color_set[s][j + k] = v
            s += 1
    return color_set


def _rgb565_to_888(word):
    """Unpack a 565-format WORD (RRRRRGGGGGGBBBBB, 5-6-5 bits) - the on-disk
    format for "normal" literal pixels - into standard 8-bit-per-channel RGB."""
    r = (word >> 11) & 0x1F
    g = (word >> 5) & 0x3F
    b = word & 0x1F
    return (r * 255 // 31, g * 255 // 63, b * 255 // 31)


def _rgb555_to_888(word):
    """Unpack a 555-format WORD (0RRRRRGGGGGBBBBB, 5-5-5 bits) - what the
    generated color table stores - into standard 8-bit-per-channel RGB."""
    r = (word >> 10) & 0x1F
    g = (word >> 5) & 0x1F
    b = word & 0x1F
    return (r * 255 // 31, g * 255 // 31, b * 255 // 31)


class SpritePack:
    """Sequential-scan reader for a .ispk file. Builds a byte-offset index
    on first access (equivalent to what the real client keeps in the
    companion .ispki file) so repeated lookups don't rescan from the start."""

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.data = f.read()
        self.count = struct.unpack_from('<H', self.data, 0)[0]
        self._offsets = None

    def _build_offsets(self):
        offsets = []
        pos = 2
        data = self.data
        for _ in range(self.count):
            offsets.append(pos)
            w, h = struct.unpack_from('<HH', data, pos)
            pos += 4
            if w and h:
                for _ in range(h):
                    row_len = struct.unpack_from('<H', data, pos)[0]
                    pos += 2 + row_len * 2
        self._offsets = offsets

    def decode(self, index, color_set, index_slot_colorset=(360, 360)):
        """Decode sprite `index` to (width, height, rgb_bytes, mask_bytes).
        mask_bytes is one byte per pixel, 0=transparent/255=opaque - use it
        to composite onto whatever background color you like.
        index_slot_colorset: which of the 495 ColorSet rows to use for
        "recolorable" pixel slot 0 / slot 1 (the game picks this per-item at
        equip/render time via SetUsingColorSet; there's no static per-item
        assignment in Item.inf itself, so this is a reasonable neutral
        default - a mid grey hue - rather than a guess at a specific tint)."""
        if self._offsets is None:
            self._build_offsets()
        if not (0 <= index < self.count):
            raise IndexError(f"sprite index {index} out of range (0..{self.count-1})")

        data = self.data
        pos = self._offsets[index]
        width, height = struct.unpack_from('<HH', data, pos)
        pos += 4
        rgb = bytearray(width * height * 3)
        mask = bytearray(width * height)

        if not width or not height:
            return width, height, bytes(rgb), bytes(mask)

        for y in range(height):
            # rowLen is a WORD count (not byte count) covering everything
            # from segCount through the last pixel word of this row.
            row_len = struct.unpack_from('<H', data, pos)[0]
            pos += 2
            row_end = pos + row_len * 2
            row_pos = pos
            x = 0
            seg_count = struct.unpack_from('<H', data, row_pos)[0]
            row_pos += 2
            for _ in range(seg_count):
                # Each segment: skip `trans_count` transparent pixels, then
                # draw `index_count` recolorable pixels, then `normal_count`
                # literal-color pixels (read below) before the next segment.
                trans_count, index_count = struct.unpack_from('<HH', data, row_pos)
                row_pos += 4
                x += trans_count
                for _ in range(index_count):
                    word = struct.unpack_from('<H', data, row_pos)[0]
                    row_pos += 2
                    slot = (word >> 8) & 0xFF
                    gradation = word & 0xFF
                    cs_index = index_slot_colorset[1] if slot else index_slot_colorset[0]
                    if 0 <= cs_index < len(color_set) and 0 <= gradation < MAX_COLORGRADATION:
                        r, g, b = _rgb555_to_888(color_set[cs_index][gradation])
                    else:
                        r, g, b = (255, 0, 255)  # obviously-wrong magenta if out of range
                    if 0 <= x < width:
                        off3 = (y * width + x) * 3
                        rgb[off3:off3 + 3] = bytes((r, g, b))
                        mask[y * width + x] = 255
                    x += 1
                normal_count = struct.unpack_from('<H', data, row_pos)[0]
                row_pos += 2
                for _ in range(normal_count):
                    word = struct.unpack_from('<H', data, row_pos)[0]
                    row_pos += 2
                    r, g, b = _rgb565_to_888(word)
                    if 0 <= x < width:
                        off3 = (y * width + x) * 3
                        rgb[off3:off3 + 3] = bytes((r, g, b))
                        mask[y * width + x] = 255
                    x += 1
            pos = row_end

        return width, height, bytes(rgb), bytes(mask)


def to_ppm(width, height, rgb, mask, bg=(48, 48, 64)):
    """Composite rgb/mask onto a solid background and return a binary PPM
    (P6) blob - Tkinter's PhotoImage(data=...) reads this directly, no PIL
    dependency needed."""
    out = bytearray(width * height * 3)
    for i in range(width * height):
        if mask[i]:
            out[i * 3:i * 3 + 3] = rgb[i * 3:i * 3 + 3]
        else:
            out[i * 3:i * 3 + 3] = bytes(bg)
    header = f"P6\n{width} {height}\n255\n".encode('ascii')
    return header + bytes(out)


def _rgb888_to_565(r, g, b):
    """Pack standard 8-bit-per-channel RGB down into an on-disk 565 WORD
    (the format the sprite pack stores literal/"normal" pixels in)."""
    return ((r * 31 // 255) << 11) | ((g * 63 // 255) << 5) | (b * 31 // 255)


def encode_sprite_from_image(image_path, max_size=96, alpha_threshold=128):
    """Build one CIndexSprite555 sprite record (raw bytes: WORD width, WORD
    height, then per-row [WORD rowLen, rowLen WORDs]) from an arbitrary
    image file, using Pillow. Every opaque pixel is stored as a literal
    RGB565 "normal" pixel (indexCount always 0) - this format supports the
    game's recolorable-tint system too, but that's for built-in art; a
    freshly added custom icon has no reason to use it. Transparency is
    binary (alpha_threshold cut), matching the sprite format itself, which
    has no partial-alpha/blending concept - only "drawn" or "skipped"."""
    from PIL import Image

    img = Image.open(image_path).convert("RGBA")
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    width, height = img.size
    pixels = img.load()

    out = bytearray()
    out += struct.pack('<HH', width, height)

    for y in range(height):
        row_words = []
        segments = []  # list of (trans_count, [rgb565 words])
        x = 0
        while x < width:
            trans_start = x
            while x < width and pixels[x, y][3] < alpha_threshold:
                x += 1
            trans_count = x - trans_start
            if x >= width:
                break  # trailing transparency is implicit, don't store it
            run = []
            while x < width and pixels[x, y][3] >= alpha_threshold:
                r, g, b, a = pixels[x, y]
                run.append(_rgb888_to_565(r, g, b))
                x += 1
            segments.append((trans_count, run))

        row_words.append(len(segments))
        for trans_count, run in segments:
            row_words.append(trans_count)
            row_words.append(0)  # indexCount - unused for custom art
            row_words.append(len(run))
            row_words.extend(run)

        out += struct.pack('<H', len(row_words))
        out += struct.pack(f'<{len(row_words)}H', *row_words)

    return bytes(out), width, height


def append_sprite_to_pack(ispk_path, sprite_bytes):
    """Append one new sprite record to the end of a real .ispk file (and its
    companion .ispki offset-index file, if present), bumping the sprite
    count by 1. Returns the new sprite's index (== old sprite count), which
    is what you assign to Item.inf's InventoryFrameID to reference it.

    Existing sprites are never touched - their bytes, offsets, and indices
    are completely unaffected, so nothing already in the game can break.
    A one-time pristine backup ("<file>.original_backup") is created before
    the FIRST modification ever made to a given file; later calls skip it so
    that backup always reflects the true original, not an already-edited copy.
    """
    backup_path = ispk_path + ".original_backup"
    if not os.path.exists(backup_path):
        shutil.copy2(ispk_path, backup_path)

    with open(ispk_path, 'rb') as f:
        spk_data = f.read()
    old_count = struct.unpack_from('<H', spk_data, 0)[0]
    new_offset = len(spk_data)
    new_index = old_count

    new_spk_data = struct.pack('<H', old_count + 1) + spk_data[2:] + sprite_bytes
    with open(ispk_path, 'wb') as f:
        f.write(new_spk_data)

    ispki_path = os.path.splitext(ispk_path)[0] + os.path.splitext(ispk_path)[1].replace('spk', 'spki')
    if os.path.isfile(ispki_path):
        ispki_backup = ispki_path + ".original_backup"
        if not os.path.exists(ispki_backup):
            shutil.copy2(ispki_path, ispki_backup)
        with open(ispki_path, 'rb') as f:
            ispki_data = f.read()
        ispki_count = struct.unpack_from('<H', ispki_data, 0)[0]
        new_ispki_data = (struct.pack('<H', ispki_count + 1) + ispki_data[2:]
                          + struct.pack('<I', new_offset))
        with open(ispki_path, 'wb') as f:
            f.write(new_ispki_data)

    return new_index
