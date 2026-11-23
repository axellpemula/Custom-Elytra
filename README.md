# Custom-Elytra

Sebuah Texture/Resource Packs skin custom elytra untuk **Minecraft Bedrock Edition**.
Model elytra samurai + katana dengan beberapa varian skin *fantasy* yang bisa dipilih
langsung di dalam game.

![Preview skin](docs/skins-preview.png)

## Daftar skin

| Subpack | Nuansa |
| --- | --- |
| `Samurai (Original)` | Hitam & emas dengan bilah merah (desain awal) |
| `Fantasy - Frost` | Es: armor biru pucat, bilah cyan, kristal putih |
| `Fantasy - Inferno` | Api: armor tembaga gelap, bilah merah-oranye menyala |
| `Fantasy - Void` | Void: armor ungu gelap, bilah magenta, aksen ungu terang |
| `Fantasy - Verdant` | Alam: armor hijau lumut, bilah hijau zamrud |
| `Fantasy - Astral` | Astral: armor indigo, bilah pink, emas tetap hangat |
| `Fantasy - Celestial` | Suci: armor perak/baja terang, bilah keemasan |

## Cara pakai

1. Build pack-nya (atau pakai file dari folder `dist/`):

   ```bash
   python3 tools/build_mcpack.py
   ```

   Hasilnya: `dist/Skin-Custom-Elytra.mcpack`.

2. Import `.mcpack` ke Minecraft (klik dua kali di Windows, atau *Open with →
   Minecraft* di Android/iOS).
3. Aktifkan pack di **Settings → Global Resources**.
4. Ganti skin: **Settings → Global Resources → paket ini → ikon gerigi
   (Pack Settings) → geser pilihan ke varian yang diinginkan → Done**.
   Skin aktif langsung berubah tanpa perlu restart.

Saat pertama dipasang, pack otomatis memakai **Samurai (Original)** — jadi
tampilan elytra tidak berubah sampai kamu memilih varian fantasy sendiri.
Subpack terakhir di `manifest.json` adalah yang jadi default, dan urutan
`memory_tier` mengatur urutan pilihan di slider.

> Kalau lebih suka tanpa build, folder `Custom Elytra/` bisa langsung di-zip
> (isi zip di root, bukan folder-nya), lalu rename `.zip` → `.mcpack`.

## Struktur

```
Custom Elytra/
├── manifest.json              # uuid pack + daftar subpacks
├── attachables/elytra.json    # pasang tekstur ke elytra vanilla
├── models/mobs.json           # geometry.elytra (model samurai)
├── animations/                # idle, gliding, sneak, swim, sleep
├── animation_controllers/
├── textures/models/intity/samurai.png   # tekstur default
└── subpacks/                  # 1 folder per skin
    ├── original_samurai/
    └── fantasy_*/             # pack_icon.png + tekstur hasil recolor
```

## Mengembangkan skin

Varian dibuat otomatis dari tekstur asli oleh `tools/generate_variants.py`.
Tekstur samurai hanya memakai 32 warna solid, dan tiap warna dipetakan ke salah
satu *family* (armor metal, trim emas, bilah merah, kristal cyan, dst). Generator
menggeser family tersebut ke palet tema baru di ruang HSV, jadi shading pixel art
dan alpha aslinya tetap utuh.

Menambah tema baru: tambahkan entri ke `THEMES` di
`tools/generate_variants.py`, lalu jalankan

```bash
python3 tools/generate_variants.py   # tekstur + icon + manifest subpacks
python3 tools/build_preview.py       # docs/skins-preview.png
python3 tools/build_mcpack.py        # dist/Skin-Custom-Elytra.mcpack
```

Butuh `pillow` (`pip install pillow`).

## Kredit

- Model & tekstur asli: **xVoid Axell**
- Varian skin fantasy: dibuat otomatis dari palet asli
