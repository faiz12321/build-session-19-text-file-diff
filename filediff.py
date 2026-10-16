"""Shows what changed between two text files without changing either.

Run: python filediff.py OLD.txt NEW.txt
Exit code: 0 = same text, 1 = different, 2 = could not read.
"""
import difflib
import sys
from pathlib import Path
import stat

SHOW = 20  # how many lines of the difference to print


def regular_input(path):
    """Reject links, reparse points, special files and hard-linked inputs.

    This check is not a hostile-race guarantee. Keep the file/tree still.
    """
    path = Path(path).absolute()
    if ".." in path.parts:
        raise OSError("Parent-traversal input paths are not supported.")
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise OSError("Links/reparse points are not supported.")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
        raise OSError("Input must be an ordinary, singly linked regular file.")
    return path


def read_lines(path):
    path = regular_input(path)
    # Text mode turns \r\n and \r into \n. Splitting on \n only keeps other
    # characters (such as a form feed) inside their line.
    with open(path, encoding="utf-8-sig", newline=None) as f:
        lines = f.read().split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def compare(old_path, new_path):
    old = read_lines(old_path)
    new = read_lines(new_path)
    diff = list(difflib.unified_diff(old, new, fromfile=old_path, tofile=new_path, n=1, lineterm=""))
    body = diff[2:]  # the first two lines are the file names
    added = sum(1 for d in body if d.startswith("+"))
    removed = sum(1 for d in body if d.startswith("-"))
    return {"old_lines": len(old), "new_lines": len(new), "added": added,
            "removed": removed, "diff": diff}


def report(r):
    print("Old file:", r["old_lines"], "lines. New file:", r["new_lines"], "lines.")
    if not r["diff"]:
        print("The text is the same.")
        print("Line endings and a missing last line ending are not compared.")
        return 0
    print("Lines added:", r["added"], " Lines removed:", r["removed"])
    for line in r["diff"][:SHOW]:
        print(line)
    if len(r["diff"]) > SHOW:
        print("... and", len(r["diff"]) - SHOW, "more lines of difference. Showing the first", str(SHOW) + ".")
    print("Neither file was changed.")
    return 1


def main(argv):
    if len(argv) != 3:
        print("Usage: python filediff.py OLD.txt NEW.txt")
        return 2
    try:
        result = compare(argv[1], argv[2])
    except UnicodeDecodeError:
        print("One of the files is not valid UTF-8 text.")
        return 2
    except OSError as e:
        print("Could not read the file:", e)
        return 2
    return report(result)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
