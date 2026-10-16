import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import filediff
import make_sample


def run(a, b=None):
    b = a if b is None else b
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


class SafeSetup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sample = self.root / 'sample'

    def test_existing_folder_preserves_nested_bytes_and_mtime(self):
        (self.sample / 'nested').mkdir(parents=True)
        keep = self.sample / 'nested' / 'keep'
        keep.write_bytes(b'KEEP')
        before = keep.read_bytes(), keep.stat().st_mtime_ns
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, (keep.read_bytes(), keep.stat().st_mtime_ns))

    def test_existing_file_preserved(self):
        self.sample.write_bytes(b'KEEP')
        before = self.sample.read_bytes(), self.sample.stat().st_mtime_ns
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, (self.sample.read_bytes(), self.sample.stat().st_mtime_ns))

    def test_repeat_preserves_every_output(self):
        make_sample.make(self.sample)
        before = {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.iterdir()}
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.iterdir()})

    def test_cli_repeat_preserves_every_output(self):
        import subprocess, sys
        script = self.root / 'make_sample.py'
        shutil.copyfile(Path(make_sample.__file__).resolve(), script)
        make_sample.make(self.sample)
        before = {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.iterdir()}
        result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('sample already exists', result.stderr)
        self.assertEqual(before, {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.iterdir()})


class InputSafety(Base):
    def test_hardlink_refused_preserves_target(self):
        target = self.sample / 'menu_old.txt'
        before = target.read_bytes(), target.stat().st_mtime_ns
        link = self.dir / 'hard.ini'
        os.link(target, link)
        code, out = run(link)
        self.assertEqual(code, 2)
        self.assertIn('singly linked', out)
        self.assertEqual(before, (target.read_bytes(), target.stat().st_mtime_ns))

    def test_directory_refused(self):
        code, out = run(self.sample)
        self.assertEqual(code, 2)
        self.assertIn('regular file', out)

    def test_fifo_refused_without_blocking(self):
        if not hasattr(os, 'mkfifo'):
            self.skipTest('Unix named pipes unavailable')
        import subprocess, sys
        pipe = self.dir / 'pipe.txt'
        os.mkfifo(pipe)
        result = subprocess.run([sys.executable, str(Path(filediff.__file__).resolve()), str(pipe), str(pipe)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn('regular file', result.stdout)

    def test_existing_and_dangling_file_symlinks_refused(self):
        target = self.sample / 'menu_old.txt'
        before = target.read_bytes(), target.stat().st_mtime_ns
        link = self.dir / 'link.zip'
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        code, out = run(link)
        self.assertEqual(code, 2)
        self.assertIn('Links/reparse', out)
        link.unlink()
        missing = self.dir / 'absent.txt'
        link.symlink_to(missing)
        code, out = run(link)
        self.assertEqual(code, 2)
        self.assertFalse(missing.exists())
        self.assertEqual(before, (target.read_bytes(), target.stat().st_mtime_ns))

    def test_parent_directory_symlink_refused(self):
        link = self.dir / 'linked'
        try:
            link.symlink_to(self.sample, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        code, out = run(link / 'menu_old.txt')
        self.assertEqual(code, 2)
        self.assertIn('Links/reparse', out)

    def test_parent_traversal_refused(self):
        path = self.sample / '..' / 'sample' / 'menu_old.txt'
        code, out = run(path)
        self.assertEqual(code, 2)
        self.assertIn('Parent-traversal', out)

    def test_self_loop_symlink_refused(self):
        link = self.dir / 'loop'
        try:
            link.symlink_to(link)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        code, out = run(link)
        self.assertEqual(code, 2)
        self.assertIn('Links/reparse', out)




if __name__ == "__main__":
    unittest.main()
