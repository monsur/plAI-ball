"""Tests for podcaster.src.archive — S3 upload of output files."""

from pathlib import Path
from unittest.mock import patch, MagicMock


class TestArchiveRun:
    @patch("podcaster.src.archive.os.getenv", return_value="fake-key")
    @patch("podcaster.src.archive.boto3")
    def test_uploads_all_files_in_output_dir(self, mock_boto3, mock_getenv, mock_args):
        from podcaster.src.archive import run

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        # Create some files in the output dir
        output_dir = Path(mock_args.output_dir)
        for name in ["20250501-transcript.txt", "20250501-audio.mp3", "prompt.txt"]:
            (output_dir / name).write_text("content")

        run(mock_args)

        assert mock_s3.upload_file.call_count == 3

    @patch("podcaster.src.archive.os.getenv", return_value="fake-key")
    @patch("podcaster.src.archive.boto3")
    def test_uses_correct_s3_paths(self, mock_boto3, mock_getenv, mock_args):
        from podcaster.src.archive import run

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        (Path(mock_args.output_dir) / "test.txt").write_text("content")

        run(mock_args)

        upload_call = mock_s3.upload_file.call_args
        s3_path = upload_call[0][2]
        assert s3_path.startswith(f"archive/{mock_args.date}/")
        assert s3_path.endswith("test.txt")

    @patch("podcaster.src.archive.os.getenv", return_value="fake-key")
    @patch("podcaster.src.archive.boto3")
    def test_uses_correct_bucket(self, mock_boto3, mock_getenv, mock_args):
        from podcaster.src.archive import run

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        (Path(mock_args.output_dir) / "test.txt").write_text("content")

        run(mock_args)

        upload_call = mock_s3.upload_file.call_args
        bucket = upload_call[0][1]
        assert bucket == "plai-ball"

    @patch("podcaster.src.archive.os.getenv", return_value="fake-key")
    @patch("podcaster.src.archive.boto3")
    def test_uploads_files_in_subdirectories(self, mock_boto3, mock_getenv, mock_args):
        from podcaster.src.archive import run

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        # Create a nested file
        subdir = Path(mock_args.output_dir) / "data"
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "boxscore.html").write_text("content")

        run(mock_args)

        upload_call = mock_s3.upload_file.call_args
        s3_path = upload_call[0][2]
        assert "data/boxscore.html" in s3_path

    @patch("podcaster.src.archive.os.getenv", return_value="fake-key")
    @patch("podcaster.src.archive.boto3")
    def test_no_files_means_no_uploads(self, mock_boto3, mock_getenv, mock_args):
        from podcaster.src.archive import run

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        run(mock_args)

        mock_s3.upload_file.assert_not_called()
