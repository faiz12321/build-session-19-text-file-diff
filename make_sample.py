"""Makes made-up text files to practise on.

Run: python make_sample.py
"""
from pathlib import Path
import stat

FILES = {
    "menu_old.txt": "Tea\nCoffee\nJuice\nWater\nMilk\n",
    "menu_same.txt": "Tea\nCoffee\nJuice\nWater\nMilk\n",
    "menu_new.txt": "Tea\nCoffee\nLemonade\nWater\nMilk\nCake\n",
    "menu_windows.txt": "Tea\r\nCoffee\r\nJuice\r\nWater\r\nMilk\r\n",
}


def make(folder):
    folder = Path(folder).absolute()
    if '..' in folder.parts:
        raise OSError('Parent-traversal setup paths are not supported.')
    for parent in reversed(folder.parents):
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise OSError('Linked/reparse parents are not supported.')
    folder.mkdir()
    for name, text in FILES.items():
        with (folder / name).open("xb") as handle:
            handle.write(text.encode("utf-8"))
    return folder


if __name__ == "__main__":
    try:
        make(Path(__file__).absolute().parent / "sample")
    except FileExistsError:
        raise SystemExit("Stopped: sample already exists. Nothing was replaced or deleted.")
    print("Made sample/menu_old.txt, menu_same.txt, menu_new.txt and menu_windows.txt")
