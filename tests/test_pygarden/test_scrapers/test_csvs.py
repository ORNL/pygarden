"""Tests for the csvs module."""

import pytest
from pathlib import Path

from pygarden.scrapers.csvs import get_csv, glob_csvs


class TestCsvs:
    """Test cases for the csvs module."""

    def test_get_csv_existing_file(self, tmp_path):
        """Test get_csv with an existing CSV file."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n")
        # Override parse_dates since test CSV doesn't have those columns
        df = get_csv(str(csv_file), parse_dates=False)
        assert df is not None
        assert len(df) == 2
        assert "name" in df.columns
        assert "age" in df.columns

    def test_get_csv_nonexistent_file(self, tmp_path):
        """Test get_csv with a nonexistent file."""
        csv_file = tmp_path / "nonexistent.csv"
        df = get_csv(str(csv_file))
        # Should return None or handle gracefully
        assert df is None or df.empty

    def test_get_csv_with_kwargs(self, tmp_path):
        """Test get_csv with additional pandas arguments."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n")
        # Override parse_dates since test CSV doesn't have those columns
        df = get_csv(str(csv_file), sep=",", header=0, parse_dates=False)
        assert df is not None
        assert len(df) == 2

    def test_glob_csvs_existing_directory(self, tmp_path):
        """Test glob_csvs with a directory containing CSV files."""
        test_dir = tmp_path / "csv_dir"
        test_dir.mkdir()
        (test_dir / "file1.csv").write_text("a,b\n1,2\n")
        (test_dir / "file2.csv").write_text("c,d\n3,4\n")
        (test_dir / "file.txt").write_text("not a csv")
        csvs = glob_csvs(str(test_dir))
        assert len(csvs) == 2
        assert any("file1.csv" in csv for csv in csvs)
        assert any("file2.csv" in csv for csv in csvs)

    def test_glob_csvs_empty_directory(self, tmp_path):
        """Test glob_csvs with an empty directory."""
        test_dir = tmp_path / "empty_dir"
        test_dir.mkdir()
        csvs = glob_csvs(str(test_dir))
        assert csvs == []

    def test_glob_csvs_nonexistent_directory(self, tmp_path):
        """Test glob_csvs with a nonexistent directory."""
        csvs = glob_csvs(str(tmp_path / "nonexistent"))
        assert csvs == []

    def test_glob_csvs_file_not_directory(self, tmp_path):
        """Test glob_csvs with a file path instead of directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("not a directory")
        csvs = glob_csvs(str(test_file))
        assert csvs == []

