"""План удаления WebP при наличии одноимённого изображения другого формата.

Совпадение определяется по имени и каталогу, а не по содержимому изображения.
"""

import argparse
import hashlib
import mimetypes
from collections import defaultdict
from pathlib import Path


# Растровые, векторные, многослойные, HDR, медицинские и RAW-форматы.
IMAGE_EXTENSIONS = set('''
 jpg jpeg jpe jfif jif jfi jp2 j2k j2c jpc jpf jpx jpm mj2 jxl jxr hdp wdp
 png apng gif bmp dib rle tif tiff heic heif hif avif avifs heics heifs
 ico cur icns ani pcx dcx tga targa icb vda vst psd psb pdd xcf ora kra krz
 pdn cpt psp pspimage pspbrush sai sai2 clip procreate afphoto affinity
 svg svgz ai eps epsf epsi ps pdf cdr cdt cmx cgm wmf emf odg otg
 pbm pgm ppm pnm pam pfm p7 xbm xpm xwd sun ras rgb rgba bw sgi int inta
 hdr pic rgbe xyze exr sxr mxr dpx cin fits fit fts fz fpx pcd pdd
 dds ktx ktx2 pvr astc basis blp wal vtf qoi farbfeld ff flif bpg
 jng mng mif miff mat mpc mtv viff vicar vic art iff ilbm lbm ham
 six sixel picon picons otb wbmp wbm wpg xif fax g3 g4 jbig jbg jb2 jbig2
 dicom dcm dcm30 acr ima nrrd nhdr nii
 3fr ari arw bay bmq cap cine cr2 cr3 crw cs1 dc2 dcr dng drf dsc
 erf fff gpr iiq k25 kdc mdc mef mos mrw nef nrw obm orf pef ptx pxn
 qtk r3d raf raw rdc rw1 rw2 rwl rwz sr2 srf srw sti x3f ia iq kc2
'''.split())


def image_extensions():
    mimetypes.init()
    extensions = {'.' + ext for ext in IMAGE_EXTENSIONS}
    for mapping in (mimetypes.types_map, mimetypes.common_types):
        extensions.update(ext.lower() for ext, mime in mapping.items()
                          if mime.startswith('image/'))
    return extensions - {'.webp'}


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def scan(directory, extensions):
    by_directory = defaultdict(list)
    for path in directory.rglob('*'):
        if path.is_file() and not path.is_symlink():
            by_directory[path.parent].append(path)

    for parent in sorted(by_directory):
        paths = sorted(by_directory[parent])
        alternatives = defaultdict(list)
        for path in paths:
            if path.suffix.lower() in extensions:
                alternatives[path.stem].append(path)
        for path in paths:
            if path.suffix.lower() == '.webp':
                yield path, alternatives.get(path.stem, [])


def make_delete_plan(directory, extensions):
    plan = []
    total_size = 0
    retained = 0
    print('\nПлан удаления (совпадение имени, без сравнения изображений):')
    for path, alternatives in scan(directory, extensions):
        if not alternatives:
            print(f'  RETAIN {path}')
            retained += 1
            continue
        try:
            expected_hash = file_hash(path)
            # Пустой или недоступный аналог не подтверждает наличие оригинала.
            kept = []
            for alternative in alternatives:
                try:
                    if alternative.stat().st_size > 0:
                        kept.append((alternative, file_hash(alternative)))
                except OSError as error:
                    print(f'  ERROR  {alternative}: {error}')
            if not kept:
                print(f'  RETAIN {path} (нет непустого доступного аналога)')
                retained += 1
                continue
            total_size += path.stat().st_size
            plan.append((path, expected_hash, kept))
            print(f'  DELETE {path}')
            for alternative, _ in kept:
                print(f'    KEEP {alternative}')
        except OSError as error:
            print(f'  ERROR  {path}: {error}')
    print(f'\nФайлов для удаления: {len(plan)}')
    print(f'Сохранено без удаления: {retained}')
    print(f'Объём: {total_size / 1024 / 1024:.2f} МБ')
    return plan


def execute_plan(plan, delete=False):
    if not plan:
        print('\nФайлов для удаления нет.')
        return
    if not delete:
        print('\nРежим предварительного просмотра.')
        print('Для удаления добавьте --delete')
        return
    if input('\nУдалить эти файлы? [yes/N]: ').strip().lower() != 'yes':
        print('Удаление отменено.')
        return
    removed = 0
    for path, expected_hash, kept in plan:
        try:
            if path.is_symlink() or file_hash(path) != expected_hash:
                print(f'Пропущен изменённый файл: {path}')
                continue
            available = False
            for alternative, original_hash in kept:
                try:
                    if not alternative.is_symlink() and file_hash(alternative) == original_hash:
                        available = True
                        break
                except OSError:
                    continue
            if not available:
                print(f'Пропущен файл без неизменённого аналога: {path}')
                continue
            path.unlink()
            removed += 1
        except OSError as error:
            print(f'Ошибка удаления {path}: {error}')
    print(f'\nУдалено файлов: {removed}')


def main():
    parser = argparse.ArgumentParser(description=(
        'Удаление WebP при наличии в том же каталоге изображения с тем же '
        'именем и другим расширением. Содержимое изображений не сравнивается.'
    ))
    parser.add_argument('directory', type=Path)
    parser.add_argument('--delete', action='store_true', help='Разрешить реальное удаление файлов')
    parser.add_argument('--extra-extension', action='append', default=[], metavar='EXT',
                        help='Добавить расширение аналога (можно повторять)')
    args = parser.parse_args()
    directory = args.directory.expanduser().resolve()
    if not directory.is_dir():
        parser.error('Каталог не найден')
    extensions = image_extensions()
    extensions.update('.' + ext.lower().lstrip('.') for ext in args.extra_extension)
    extensions.discard('.webp')
    print('Сканирование файлов...')
    execute_plan(make_delete_plan(directory, extensions), delete=args.delete)


if __name__ == '__main__':
    main()
