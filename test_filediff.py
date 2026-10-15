import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import filediff
import make_sample


def run(a, b):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = filediff.main(["filediff.py", str(a), str(b)])
    return code, buf.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.sample = make_sample.make(self.dir / "sample")

    def write(self, name, text=None, raw=None):
        p = self.dir / name
        p.write_bytes(raw if raw is not None else text.encode("utf-8"))
        return p


class Samples(Base):
    def test_same(self):
        code, out = run(self.sample / "menu_old.txt", self.sample / "menu_same.txt")
        self.assertEqual(code, 0)
        self.assertIn("The text is the same.", out)

    def test_changed(self):
        code, out = run(self.sample / "menu_old.txt", self.sample / "menu_new.txt")
        self.assertEqual(code, 1)
        self.assertIn("Lines added: 2  Lines removed: 1", out)
        self.assertIn("-Juice", out)
        self.assertIn("+Lemonade", out)
        self.assertIn("+Cake", out)
        self.assertIn("Neither file was changed.", out)

    def test_windows_line_endings_not_a_difference(self):
        code, out = run(self.sample / "menu_old.txt", self.sample / "menu_windows.txt")
        self.assertEqual(code, 0)
        self.assertIn("Line endings", out)

    def test_swapped_order_reverses_counts(self):
        code, out = run(self.sample / "menu_new.txt", self.sample / "menu_old.txt")
        self.assertIn("Lines added: 1  Lines removed: 2", out)

    def test_sample_files(self):
        self.assertEqual(sorted(p.name for p in self.sample.iterdir()),
                         ["menu_new.txt", "menu_old.txt", "menu_same.txt", "menu_windows.txt"])


class Lines(Base):
    def test_missing_last_line_ending_not_a_difference(self):
        a = self.write("a.txt", "x\ny\n")
        b = self.write("b.txt", "x\ny")
        self.assertEqual(run(a, b)[0], 0)

    def test_empty_files_same(self):
        a = self.write("a.txt", "")
        b = self.write("b.txt", "")
        code, out = run(a, b)
        self.assertEqual(code, 0)
        self.assertIn("Old file: 0 lines", out)

    def test_empty_vs_one_line(self):
        a = self.write("a.txt", "")
        b = self.write("b.txt", "hello\n")
        code, out = run(a, b)
        self.assertEqual(code, 1)
        self.assertIn("Lines added: 1  Lines removed: 0", out)

    def test_a_blank_line_counts(self):
        a = self.write("a.txt", "x\ny\n")
        b = self.write("b.txt", "x\n\ny\n")
        code, out = run(a, b)
        self.assertEqual(code, 1)
        self.assertIn("Lines added: 1", out)

    def test_trailing_space_is_a_difference(self):
        a = self.write("a.txt", "x\n")
        b = self.write("b.txt", "x \n")
        self.assertEqual(run(a, b)[0], 1)

    def test_changed_line_starting_with_dashes_counted(self):
        a = self.write("a.txt", "x\n-- note\ny\n")
        b = self.write("b.txt", "x\ny\n")
        code, out = run(a, b)
        self.assertIn("Lines added: 0  Lines removed: 1", out)

    def test_changed_line_starting_with_plus_counted(self):
        a = self.write("a.txt", "x\ny\n")
        b = self.write("b.txt", "x\n++ note\ny\n")
        code, out = run(a, b)
        self.assertIn("Lines added: 1  Lines removed: 0", out)

    def test_form_feed_stays_inside_its_line(self):
        a = self.write("a.txt", "a\x0cb\n")
        self.assertEqual(filediff.read_lines(a), ["a\x0cb"])

    def test_old_mac_line_endings(self):
        a = self.write("a.txt", "", raw=b"x\ry\r")
        self.assertEqual(filediff.read_lines(a), ["x", "y"])

    def test_byte_order_mark_ignored(self):
        a = self.write("a.txt", "", raw=b"\xef\xbb\xbfx\n")
        b = self.write("b.txt", "x\n")
        self.assertEqual(run(a, b)[0], 0)

    def test_only_first_20_lines_shown(self):
        a = self.write("a.txt", "".join("old%d\n" % i for i in range(30)))
        b = self.write("b.txt", "".join("new%d\n" % i for i in range(30)))
        code, out = run(a, b)
        self.assertEqual(code, 1)
        self.assertIn("Lines added: 30  Lines removed: 30", out)
        self.assertIn("more lines of difference", out)
        self.assertLessEqual(len(out.splitlines()), 20 + 6)


class Errors(Base):
    def test_not_utf8(self):
        a = self.write("a.txt", "x\n")
        b = self.write("b.txt", "", raw=b"caf\xe9\n")
        code, out = run(a, b)
        self.assertEqual(code, 2)
        self.assertIn("not valid UTF-8", out)

    def test_missing_file(self):
        a = self.write("a.txt", "x\n")
        code, out = run(a, self.dir / "none.txt")
        self.assertEqual(code, 2)
        self.assertIn("Could not read", out)

    def test_usage(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(filediff.main(["filediff.py", "only-one.txt"]), 2)


class ReadOnly(Base):
    def test_bytes_and_time_unchanged(self):
        names = ["menu_old.txt", "menu_new.txt"]
        before = {n: ((self.sample / n).read_bytes(), os.stat(self.sample / n).st_mtime_ns) for n in names}
        run(self.sample / names[0], self.sample / names[1])
        for n in names:
            self.assertEqual((self.sample / n).read_bytes(), before[n][0])
            self.assertEqual(os.stat(self.sample / n).st_mtime_ns, before[n][1])

    def test_no_new_files(self):
        before = sorted(p.name for p in self.dir.rglob("*"))
        run(self.sample / "menu_old.txt", self.sample / "menu_new.txt")
        self.assertEqual(sorted(p.name for p in self.dir.rglob("*")), before)


if __name__ == "__main__":
    unittest.main()
