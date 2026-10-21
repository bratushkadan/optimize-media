import argparse
import hashlib
import re
from collections import defaultdict
from pathlib import Path


def file_hash(path, chunk_size=1024 * 1024):
    sha256 = hashlib.sha256()

    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)

    return sha256.hexdigest()


def find_duplicates(directory):
    sizes = defaultdict(list)

    for path in directory.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue

        try:
            sizes[path.stat().st_size].append(path.resolve())
        except OSError as e:
            print(f"Ошибка доступа: {path}: {e}")

    hashes = defaultdict(list)

    for paths in sizes.values():
        if len(paths) < 2:
            continue

        for path in paths:
            try:
                hashes[file_hash(path)].append(path)
            except OSError as e:
                print(f"Ошибка чтения: {path}: {e}")

    return {
        digest: sorted(set(paths))
        for digest, paths in hashes.items()
        if len(set(paths)) > 1
    }


def build_directory_groups(duplicates):
    """
    Объединяет каталоги, связанные одинаковыми файлами.

    Если A содержит дубликаты из B, а B из C,
    то A, B и C образуют одну группу.
    """
    parent = {}

    def find(x):
        parent.setdefault(x, x)

        if parent[x] != x:
            parent[x] = find(parent[x])

        return parent[x]

    def union(a, b):
        ra, rb = find(a), find(b)

        if ra != rb:
            parent[rb] = ra

    # Связываем каталоги через дубликаты
    for paths in duplicates.values():
        directories = sorted({p.parent for p in paths})

        for directory in directories:
            find(directory)

        for directory in directories[1:]:
            union(directories[0], directory)

    # Собираем группы каталогов
    groups = defaultdict(set)

    for directory in parent:
        groups[find(directory)].add(directory)

    return sorted(
        [sorted(group) for group in groups.values()], key=lambda group: str(group[0])
    )


def choose_directory(directories):
    print("\nКаталоги с дубликатами:")

    for i, directory in enumerate(directories, 1):
        print(f"  [{i}] {directory}")

    if len(directories) == 1:
        print("\nЕдинственный каталог выбран автоматически.")
        return directories[0]

    while True:
        answer = input(
            "\nКакой каталог предпочитать? (номер или s для пропуска): "
        ).strip()

        if answer.lower() == "s":
            return None

        if answer.isdigit():
            index = int(answer) - 1

            if 0 <= index < len(directories):
                return directories[index]

        print("Некорректный выбор.")


def make_delete_plan(duplicates, directories, preferred):
    """
    Формирует список файлов для удаления.

    Если в предпочитаемом каталоге нет копии,
    сохраняет одну копию в другом каталоге.
    """
    directory_set = set(directories)
    delete_plan = []

    for digest, paths in duplicates.items():
        relevant = [path for path in paths if path.parent in directory_set]

        if len(relevant) < 2:
            continue

        # Номерную копию исключаем из кандидатов только при наличии
        # идентичного оригинала в том же каталоге.
        relevant_set = set(relevant)
        candidates = []
        for path in relevant:
            match = re.fullmatch(r"(.+) \(\d+\)", path.stem)
            if match and path.with_name(match.group(1) + path.suffix) in relevant_set:
                continue
            candidates.append(path)

        preferred_files = [path for path in candidates if path.parent == preferred]

        if preferred_files:
            # Сохраняем файлы предпочитаемого каталога без номерных копий оригинала
            keep = set(preferred_files)
        else:
            # Сохраняем одну копию, чтобы не потерять данные
            keep = {sorted(candidates)[0]}

        for path in relevant:
            if path not in keep:
                delete_plan.append((path, digest, tuple(sorted(keep))))

    return delete_plan


def execute_plan(plan, delete=False):
    if not plan:
        print("\nФайлов для удаления нет.")
        return

    print("\nПлан удаления:")

    total_size = 0

    for path, _, kept_paths in plan:
        try:
            size = path.stat().st_size
            total_size += size
            print(f"  DELETE {path}")
            for kept_path in kept_paths:
                print(f"    KEEP {kept_path}")
        except OSError as e:
            print(f"  ERROR  {path}: {e}")

    print(f"\nФайлов: {len(plan)}")
    print(f"Объём: {total_size / 1024 / 1024:.2f} МБ")

    if not delete:
        print("\nРежим предварительного просмотра.")
        print("Для удаления добавьте --delete")
        return

    answer = input("\nУдалить эти файлы? [yes/N]: ")

    if answer.strip().lower() != "yes":
        print("Удаление отменено.")
        return

    removed = 0

    for path, expected_hash, _ in plan:
        try:
            # Проверяем, что файл не изменился после сканирования
            if file_hash(path) != expected_hash:
                print(f"Пропущен изменённый файл: {path}")
                continue

            path.unlink()
            removed += 1

        except OSError as e:
            print(f"Ошибка удаления {path}: {e}")

    print(f"\nУдалено файлов: {removed}")


def main():
    parser = argparse.ArgumentParser(
        description="Поиск и удаление дубликатов с приоритетом каталогов"
    )

    parser.add_argument("directory", type=Path)

    parser.add_argument(
        "--delete", action="store_true", help="Разрешить реальное удаление файлов"
    )

    args = parser.parse_args()
    directory = args.directory.resolve()

    if not directory.is_dir():
        parser.error("Каталог не найден")

    print("Сканирование файлов...")
    duplicates = find_duplicates(directory)

    if not duplicates:
        print("Дубликаты не найдены.")
        return

    groups = build_directory_groups(duplicates)

    print(f"\nНайдено групп каталогов: {len(groups)}")

    for i, directories in enumerate(groups, 1):
        print(f"\n{'=' * 60}")
        print(f"ГРУППА {i}/{len(groups)}")
        print("=" * 60)

        preferred = choose_directory(directories)

        if preferred is None:
            print("Группа пропущена.")
            continue

        print(f"\nПриоритетный каталог: {preferred}")

        plan = make_delete_plan(duplicates, directories, preferred)

        execute_plan(plan, delete=args.delete)


if __name__ == "__main__":
    main()
