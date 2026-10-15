"""Makes made-up text files to practise on.

Run: python make_sample.py
"""
from pathlib import Path

FILES = {
    "menu_old.txt": "Tea\nCoffee\nJuice\nWater\nMilk\n",
    "menu_same.txt": "Tea\nCoffee\nJuice\nWater\nMilk\n",
    "menu_new.txt": "Tea\nCoffee\nLemonade\nWater\nMilk\nCake\n",
    "menu_windows.txt": "Tea\r\nCoffee\r\nJuice\r\nWater\r\nMilk\r\n",
}


def make(folder):
    folder = Path(folder)
    folder.mkdir(exist_ok=True)
    for name, text in FILES.items():
        (folder / name).write_bytes(text.encode("utf-8"))
    return folder


if __name__ == "__main__":
    make("sample")
    print("Made sample/menu_old.txt, menu_same.txt, menu_new.txt and menu_windows.txt")
