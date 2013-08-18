import unittest
from textwrap import dedent
import os
import tempfile
from diff_cover.snippets import Snippet
from diff_cover.tests.helpers import load_fixture, fixture_path


class SnippetTest(unittest.TestCase):

    SRC_CONTENTS = dedent("""
        # Test source
        def test_func(arg):
            print arg
            return arg + 5
    """).strip()

    FIXTURES = {
        'style': 'snippet.css',
        'default': 'snippet_default.html',
        'invalid_violations': 'snippet_invalid_violations.html',
        'no_filename_ext': 'snippet_no_filename_ext.html',
        'unicode': 'snippet_unicode.html',
    }

    def test_style_defs(self):
        style_str = Snippet.style_defs()
        expected_style = load_fixture(self.FIXTURES['style']).strip()
        self.assertEqual(expected_style, style_str)

    def test_format(self):
        self._assert_format(
            self.SRC_CONTENTS, 'test.py',
            4, [4, 6], self.FIXTURES['default']
        )

    def test_format_with_invalid_start_line(self):
        for start_line in [-2, -1, 0]:
            with self.assertRaises(ValueError):
                Snippet('# test', 'test.py', start_line, [])

    def test_format_with_invalid_violation_lines(self):

        # Violation lines outside the range of lines in the file
        # should be ignored.
        self._assert_format(
            self.SRC_CONTENTS, 'test.py',
            1, [-1, 0, 5, 6],
            self.FIXTURES['invalid_violations']
        )

    def test_no_filename_ext(self):

        # No filename extension: should default to text lexer
        self._assert_format(
            self.SRC_CONTENTS, 'test', 
            4, [4, 6],
            self.FIXTURES['no_filename_ext']
        )

    def test_unicode(self):

        unicode_src = u'var = \u0123 \u5872 \u3389'

        self._assert_format(
            unicode_src, 'test.py',
            1, [], self.FIXTURES['unicode']
        )

    def _assert_format(self, src_str, src_filename,
                       start_line, violation_lines,
                       expected_fixture):

        snippet = Snippet(src_str, src_filename,
                          start_line, violation_lines)
        result = snippet.html()

        expected_str = load_fixture(expected_fixture, encoding='utf-8')

        self.assertEqual(result, expected_str)
        self.assertTrue(isinstance(result, unicode))


class SnippetLoaderTest(unittest.TestCase):

    def setUp(self):
        """
        Create a temporary source file.
        """
        _, self._src_path = tempfile.mkstemp()

    def tearDown(self):
        """
        Delete the temporary source file.
        """
        os.remove(self._src_path)

    def test_one_snippet(self):
        self._init_src_file(10)
        violations = [2, 3, 4, 5]
        expected_ranges = [(1, 9)]
        self._assert_line_range(violations, expected_ranges)

    def test_multiple_snippets(self):
        self._init_src_file(100)
        violations = [30, 31, 32, 35, 36, 60, 62]
        expected_ranges = [(26, 40), (56, 66)]
        self._assert_line_range(violations, expected_ranges)

    def test_no_lead_line(self):
        self._init_src_file(10)
        violations = [1, 2, 3]
        expected_ranges = [(1, 7)]
        self._assert_line_range(violations, expected_ranges)

    def test_no_lag_line(self):
        self._init_src_file(10)
        violations = [9, 10]
        expected_ranges = [(5, 10)]
        self._assert_line_range(violations, expected_ranges)

    def test_one_line_file(self):
        self._init_src_file(1)
        violations = [1]
        expected_ranges = [(1, 1)]
        self._assert_line_range(violations, expected_ranges)

    def test_empty_file(self):
        self._init_src_file(0)
        violations = [0]
        expected_ranges = []
        self._assert_line_range(violations, expected_ranges)

    def test_no_violations(self):
        self._init_src_file(10)
        violations = []
        expected_ranges = []
        self._assert_line_range(violations, expected_ranges)

    def _assert_line_range(self, violation_lines, expected_ranges):
        """
        Assert that the snippets loaded using `violation_lines`
        have the correct ranges of lines.

        `violation_lines` is a list of line numbers containing violations
        (which should get included in snippets).

        `expected_ranges` is a list of `(start, end)` tuples representing
        the starting and ending lines expected in a snippet.
        Line numbers start at 1.
        """
        
        # Load snippets from the source file
        snippet_list = Snippet.load_snippets(self._src_path,
                                             violation_lines)

        # Check that we got the right number of snippets
        self.assertEqual(len(snippet_list), len(expected_ranges))

        # Check that the snippets have the desired ranges
        for snippet, line_range in zip(snippet_list, expected_ranges):

            # Expect that the line range is correct
            self.assertEqual(snippet.line_range(), line_range)

            # Expect that the source contents are correct
            start, end = line_range
            self.assertEqual(snippet.text(), self._src_lines(start, end))

    def _init_src_file(self, num_src_lines):
        """
        Write to the temporary file "Line 1", "Line 2", etc.
        up to `num_src_lines`.
        """
        with open(self._src_path, 'w') as src_file:
            src_file.truncate()
            src_file.write(self._src_lines(1, num_src_lines))

    def _src_lines(self, start_line, end_line):
        """
        Test lines to write to the source file
        (Line 1, Line 2, ...).
        """
        return "\n".join([
                "Line {0}".format(line_num)
                for line_num in range(start_line, end_line + 1)
        ])