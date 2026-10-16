# See what changed between two text files

A small read-only Python tool built step by step. Give it an old and a new text file. It compares them line by line with Python's `difflib` module, counts the lines added and removed, and shows the first 20 lines of a unified difference (the usual `+` and `-` layout). It has no code that writes to a file.

## Run it

    python make_sample.py                                   # makes four made-up files in sample/
    python filediff.py sample/menu_old.txt sample/menu_new.txt
    python -m unittest -v                                   # 32 small fixture tests

On Windows, if `python` is not found, use `py`.

## Files

- `filediff.py` - the tool
- `make_sample.py` - makes four made-up menu files: an old one, an identical copy, a changed one and one with Windows line endings
- `test_filediff.py` - tests

## Notes

- A changed line counts as one line removed and one line added.
- Line endings are not compared, and neither is a missing last line ending. Files that differ only in those are reported as the same text. Spaces at the end of a line are compared.
- Files are read as UTF-8 (a leading byte order mark is ignored). Other encodings are reported as not valid UTF-8.
- Only the first 20 lines of the difference are shown. The counts cover the whole difference.
- Difference reports can look different for the same pair of files in other tools. This one uses one line of surrounding context.
- Tests check that both files keep the same bytes and modified time, and that no file is created.
- Tested only on small made-up files. Python 3.10 and 3.12 on Linux, and, by GitHub Actions, Python 3.12 on Windows and Ubuntu. Not tested on a Windows 10 or 11 desktop or on large files.
- Educational example, no warranty. Use at your own risk.
- Code is MIT licensed (see LICENSE). Python is a separate project with its own license; this repository does not include it.


## Setup and filesystem safety repair

Use a new empty lesson folder. Setup creates four fictional files exclusively
in a NEW sample folder. Existing files/folders, traversal spellings and linked/
reparse parents are refused. It never resets a previous sample folder. Use a
different new lesson folder after an interrupted setup.

Final checker refuses input/ancestor filesystem links/reparse points, hardlinks,
directories, special entries and traversal spellings before reading. Stop editors
and sync; no hostile-race guarantee. It reads whole files and materializes the
difference, so memory/time can be large; difflib has quadratic worst-case time.
Not a resource sandbox. A leading UTF-8 BOM is ignored. Same normalized text
is not proof of identical bytes. Output exposes file paths and difference text;
keep private output private. No network/upload code is used, but cloud sync and
other software are outside its control.

Two Windows and two Ubuntu full replays pass 32 tests. Each platform pair differs
only in unittest time. Windows skips Unix FIFO; Ubuntu runs it. Symlink tests
can skip where unavailable. Four setup tests and seven filesystem-input tests
join the original 21 text comparison tests. Tests/recorder clean up only their
own unique temporary folders and record exact visible file versions. No claim
of real-data, large-file, every-filesystem or Windows desktop validation.

Sources:
- https://docs.python.org/3/library/difflib.html
- https://docs.python.org/3/library/pathlib.html
- https://docs.python.org/3/library/stat.html
