import unittest

from genschema.comparators.format import FormatDetector


class TestFormatDetector(unittest.TestCase):
    def test_detects_datetime_with_t_separator(self):
        self.assertEqual(FormatDetector.detect("2025-02-24T11:30:47"), "date-time")

    def test_detects_datetime_with_space_separator(self):
        self.assertEqual(FormatDetector.detect("2025-02-24 11:30:47"), "date-time")
