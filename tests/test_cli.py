"""Tests for CLI module."""

from __future__ import annotations

import argparse

from podstock.cli import create_parser


class TestCreateParser:
    """Tests for create_parser function."""

    def test_creates_parser(self) -> None:
        """Creates argument parser."""
        parser = create_parser()

        assert isinstance(parser, argparse.ArgumentParser)

    def test_podcast_list_subcommand(self) -> None:
        """Has podcast list subcommand."""
        parser = create_parser()
        args = parser.parse_args(["podcast", "list"])

        assert args.command == "podcast"
        assert args.podcast_command == "list"

    def test_download_subcommand(self) -> None:
        """Has download subcommand."""
        parser = create_parser()
        args = parser.parse_args(["download", "--podcast", "bp"])

        assert args.command == "download"
        assert args.podcast == "bp"

    def test_transcribe_subcommand(self) -> None:
        """Has transcribe subcommand."""
        parser = create_parser()
        args = parser.parse_args(["transcribe"])

        assert args.command == "transcribe"

    def test_analyze_subcommand(self) -> None:
        """Has analyze subcommand."""
        parser = create_parser()
        args = parser.parse_args(["analyze", "bp-2024-12-18"])

        assert args.command == "analyze"
        assert args.episode == "bp-2024-12-18"

    def test_report_subcommand(self) -> None:
        """Has report subcommand."""
        parser = create_parser()
        args = parser.parse_args(["report"])

        assert args.command == "report"

    def test_status_subcommand(self) -> None:
        """Has status subcommand."""
        parser = create_parser()
        args = parser.parse_args(["status"])

        assert args.command == "status"

    def test_data_dir_option(self) -> None:
        """Has --data-dir global option."""
        parser = create_parser()
        args = parser.parse_args(["--data-dir", "/custom/path", "status"])

        assert args.data_dir == "/custom/path"

    def test_verbose_option(self) -> None:
        """Has --verbose global option."""
        parser = create_parser()
        args = parser.parse_args(["-v", "status"])

        assert args.verbose is True


class TestPodcastSubcommands:
    """Tests for podcast subcommand parsing."""

    def test_podcast_list(self) -> None:
        """Parses podcast list command."""
        parser = create_parser()
        args = parser.parse_args(["podcast", "list"])

        assert args.command == "podcast"
        assert args.podcast_command == "list"

    def test_podcast_add(self) -> None:
        """Parses podcast add command."""
        parser = create_parser()
        args = parser.parse_args([
            "podcast", "add", "Test Podcast", "https://example.com/feed.xml",
        ])

        assert args.podcast_command == "add"
        assert args.name == "Test Podcast"
        assert args.url == "https://example.com/feed.xml"

    def test_podcast_add_skip_validation(self) -> None:
        """Parses podcast add with --skip-validation."""
        parser = create_parser()
        args = parser.parse_args([
            "podcast", "add", "Test", "https://example.com/feed.xml",
            "--skip-validation",
        ])

        assert args.skip_validation is True

    def test_podcast_remove(self) -> None:
        """Parses podcast remove command."""
        parser = create_parser()
        args = parser.parse_args(["podcast", "remove", "test-id"])

        assert args.podcast_command == "remove"
        assert args.id == "test-id"

    def test_podcast_info(self) -> None:
        """Parses podcast info command."""
        parser = create_parser()
        args = parser.parse_args(["podcast", "info", "bp"])

        assert args.podcast_command == "info"
        assert args.id == "bp"


class TestDownloadOptions:
    """Tests for download command options."""

    def test_download_podcast_filter(self) -> None:
        """Parses --podcast option."""
        parser = create_parser()
        args = parser.parse_args(["download", "--podcast", "bp"])

        assert args.podcast == "bp"

    def test_download_podcast_short(self) -> None:
        """Parses -p short option."""
        parser = create_parser()
        args = parser.parse_args(["download", "-p", "bp"])

        assert args.podcast == "bp"

    def test_download_latest(self) -> None:
        """Parses --latest option."""
        parser = create_parser()
        args = parser.parse_args(["download", "--latest", "5"])

        assert args.latest == 5

    def test_download_force(self) -> None:
        """Parses --force flag."""
        parser = create_parser()
        args = parser.parse_args(["download", "--force"])

        assert args.force is True


class TestTranscribeOptions:
    """Tests for transcribe command options."""

    def test_transcribe_model(self) -> None:
        """Parses --model option."""
        parser = create_parser()
        args = parser.parse_args(["transcribe", "--model", "large-v3"])

        assert args.model == "large-v3"

    def test_transcribe_podcast_filter(self) -> None:
        """Parses --podcast option."""
        parser = create_parser()
        args = parser.parse_args(["transcribe", "--podcast", "bp"])

        assert args.podcast == "bp"

    def test_transcribe_episode(self) -> None:
        """Parses --episode option."""
        parser = create_parser()
        args = parser.parse_args(["transcribe", "--episode", "bp-2024-12-18"])

        assert args.episode == "bp-2024-12-18"

    def test_transcribe_force(self) -> None:
        """Parses --force flag."""
        parser = create_parser()
        args = parser.parse_args(["transcribe", "-f"])

        assert args.force is True


class TestAnalyzeOptions:
    """Tests for analyze command options."""

    def test_analyze_episode_required(self) -> None:
        """Episode ID is required."""
        parser = create_parser()
        args = parser.parse_args(["analyze", "bp-2024-12-18"])

        assert args.episode == "bp-2024-12-18"

    def test_analyze_input(self) -> None:
        """Parses --input option."""
        parser = create_parser()
        args = parser.parse_args(["analyze", "bp-2024-12-18", "--input", "response.txt"])

        assert args.input == "response.txt"


class TestReportOptions:
    """Tests for report command options."""

    def test_report_output(self) -> None:
        """Parses --output option."""
        parser = create_parser()
        args = parser.parse_args(["report", "--output", "report.md"])

        assert args.output == "report.md"

    def test_report_podcast_filter(self) -> None:
        """Parses --podcast option."""
        parser = create_parser()
        args = parser.parse_args(["report", "--podcast", "bp"])

        assert args.podcast == "bp"
