"""
Load snippets from source files to show violation lines
in HTML reports.
"""

from pygments import highlight
from pygments.lexers import TextLexer, guess_lexer_for_filename
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound


class Snippet(object):
    """
    A source code snippet.
    """

    VIOLATION_COLOR = '#ffcccc'
    DIV_CSS_CLASS = 'snippet'
    BORDER_CSS = "{ border: 1px solid #bdbdbd; }"

    # Number of extra lines to include before and after
    # each snippet to provide context.
    NUM_CONTEXT_LINES = 4

    # Maximum distance between two violations within
    # a snippet.  If violations are further apart,
    # should split into two snippets.
    MAX_GAP_IN_SNIPPET = 4

    def __init__(self, src_str, src_filename,
                 start_line, violation_lines):
        """
        Create a source code snippet.

        `src_filename` is the name of the source file,
        used to determine the source file language.

        `start_line` is the line number of first line
        in `src_str`.  The first line in the file is
        line number 1.

        `violation_lines` is a list of line numbers
        to highlight as violations.

        Raises a `ValueError` if `start_line` is less than 1
        """
        if start_line < 1:
            raise ValueError('Start line must be >= 1')

        self._src_str = src_str
        self._src_filename = src_filename
        self._start_line = start_line
        self._violation_lines = violation_lines

    @classmethod
    def style_defs(cls):
        """
        Return the CSS style definitions required
        by the formatted snippet.
        """
        formatter = HtmlFormatter()
        formatter.style.highlight_color = cls.VIOLATION_COLOR
        border_css = ".{0}table {1}\n".format(
            cls.DIV_CSS_CLASS,
            cls.BORDER_CSS
        )
        return border_css + formatter.get_style_defs()

    def html(self):
        """
        Return an HTML representation of the snippet.
        """
        try:
            lexer = guess_lexer_for_filename(
                self._src_filename,
                self._src_str
            )
        except ClassNotFound:
            lexer = TextLexer()

        # Ensure that we don't strip newlines from
        # the source file when lexing.
        lexer.stripnl = False

        formatter = HtmlFormatter(
            cssclass=self.DIV_CSS_CLASS,
            linenos=True,
            linenostart=self._start_line,
            hl_lines=self._shift_lines(
                self._violation_lines,
                self._start_line
            ),
            lineanchors=self._src_filename
        )

        return highlight(self._src_str, lexer, formatter)

    def text(self):
        """
        Return a text (unicode) representation of the snippet.
        """
        return self._src_str

    def line_range(self):
        """
        Return a tuple of the form `(start_line, end_line)`
        indicating the start and end line number of the snippet.
        """
        num_lines = len(self._src_str.split('\n'))
        end_line = self._start_line + num_lines - 1
        return (self._start_line, end_line)

    @classmethod
    def load_snippets_html(cls, src_path, violation_lines):
        """
        Load snippets from the file at `src_path` and format
        them as HTML.

        See `load_snippets()` for details.
        """
        snippet_list = cls.load_snippets(src_path, violation_lines)
        return [snippet.html() for snippet in snippet_list]

    @classmethod
    def load_snippets(cls, src_path, violation_lines):
        """
        Load snippets from the file at `src_path` to show
        violations on lines in the list `violation_lines`
        (list of line numbers, starting at index 0).

        The file at `src_path` should be a text file (not binary).

        Returns a list of `Snippet` instances.

        Raises an `IOError` if the file could not be loaded.
        """
        # Load the contents of the file
        with open(src_path) as src_file:
            contents = src_file.read()

        # Construct a list of snippet ranges
        src_lines = contents.split('\n')
        snippet_ranges = cls._snippet_ranges(len(src_lines), violation_lines)

        # Convert the snippet ranges into snippet objects
        return [
            Snippet(
                "\n".join(src_lines[start - 1:end]),
                src_path,
                start, violation_lines
            ) for (start, end) in snippet_ranges
        ]

    @classmethod
    def _snippet_ranges(cls, num_src_lines, violation_lines):
        """
        Given the number of source file lines and list of
        violation line numbers, return a list of snippet
        ranges of the form `(start_line, end_line)`.

        Each snippet contains a few extra lines of context
        before/after the first/last violation.  Nearby
        violations are grouped within the same snippet.
        """
        current_range = (None, None)
        lines_since_last_violation = 0
        snippet_ranges = []
        for line_num in range(1, num_src_lines + 1):

            # If we have not yet started a snippet,
            # check if we can (is this line a violation?)
            if current_range[0] is None:
                if line_num in violation_lines:

                    # Expand to include extra context, but not before line 1
                    snippet_start = max(1, line_num - cls.NUM_CONTEXT_LINES)
                    current_range = (snippet_start, None)
                    lines_since_last_violation = 0

            # If we are within a snippet, check if we
            # can end the snippet (have we gone enough
            # lines without hitting a violation?)
            elif current_range[1] is None:
                if line_num in violation_lines:
                    lines_since_last_violation = 0

                elif lines_since_last_violation > cls.MAX_GAP_IN_SNIPPET:

                    # Expand to include extra context, but not after last line
                    snippet_end = line_num - lines_since_last_violation
                    snippet_end = min(
                        num_src_lines,
                        snippet_end + cls.NUM_CONTEXT_LINES
                    )
                    current_range = (current_range[0], snippet_end)

                    # Store the snippet and start looking for the next one
                    snippet_ranges.append(current_range)
                    current_range = (None, None)

            # Another line since the last violation
            lines_since_last_violation += 1

        # If we started a snippet but didn't finish it, do so now
        if current_range[0] is not None and current_range[1] is None:
            snippet_ranges.append((current_range[0], num_src_lines))

        return snippet_ranges

    @staticmethod
    def _shift_lines(line_num_list, start_line):
        """
        Shift all line numbers in `line_num_list` so that
        `start_line` is treated as line 1.

        For example, `[5, 8, 9]` with `start_line=3` would
        become `[3, 6, 7]`.

        Assumes that all entries in `line_num_list` are greater
        than or equal to `start_line`; otherwise, they will
        be excluded from the list.
        """
        return [line_num - start_line + 1
                for line_num in line_num_list
                if line_num >= start_line]
