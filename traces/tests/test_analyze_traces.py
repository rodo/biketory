from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from traces.models import Trace

from ._helpers import make_user, small_route


class AnalyzeTracesTests(TestCase):

    def setUp(self):
        self.user = make_user()

    def _create_trace(self, status):
        trace = Trace.objects.create(
            gpx_file="test.gpx",
            route=small_route(),
            uploaded_by=self.user,
            status=status,
        )
        return trace

    @patch("traces.management.commands.analyze_traces.award_trace_badges")
    @patch("traces.management.commands.analyze_traces.extract_surfaces")
    def test_not_analyzed_defers_both_jobs(self, mock_extract, mock_badges):
        trace = self._create_trace(Trace.STATUS_NOT_ANALYZED)
        call_command("analyze_traces")
        mock_extract.defer.assert_called_once_with(trace_id=trace.pk)
        mock_badges.defer.assert_called_once_with(trace_id=trace.pk)

    @patch("traces.management.commands.analyze_traces.award_trace_badges")
    @patch("traces.management.commands.analyze_traces.extract_surfaces")
    def test_surface_extracted_defers_badges_only(self, mock_extract, mock_badges):
        trace = self._create_trace(Trace.STATUS_SURFACE_EXTRACTED)
        call_command("analyze_traces")
        mock_extract.defer.assert_not_called()
        mock_badges.defer.assert_called_once_with(trace_id=trace.pk)

    @patch("traces.management.commands.analyze_traces.award_trace_badges")
    @patch("traces.management.commands.analyze_traces.extract_surfaces")
    def test_analyzed_traces_ignored(self, mock_extract, mock_badges):
        self._create_trace(Trace.STATUS_ANALYZED)
        call_command("analyze_traces")
        mock_extract.defer.assert_not_called()
        mock_badges.defer.assert_not_called()

    @patch("traces.management.commands.analyze_traces.award_trace_badges")
    @patch("traces.management.commands.analyze_traces.extract_surfaces")
    def test_no_traces_defers_nothing(self, mock_extract, mock_badges):
        call_command("analyze_traces")
        mock_extract.defer.assert_not_called()
        mock_badges.defer.assert_not_called()

    @patch("traces.management.commands.analyze_traces.award_trace_badges")
    @patch("traces.management.commands.analyze_traces.extract_surfaces")
    def test_mixed_statuses(self, mock_extract, mock_badges):
        t1 = self._create_trace(Trace.STATUS_NOT_ANALYZED)
        t2 = self._create_trace(Trace.STATUS_SURFACE_EXTRACTED)
        self._create_trace(Trace.STATUS_ANALYZED)

        call_command("analyze_traces")

        mock_extract.defer.assert_called_once_with(trace_id=t1.pk)
        self.assertEqual(mock_badges.defer.call_count, 2)
        called_ids = {c.kwargs["trace_id"] for c in mock_badges.defer.call_args_list}
        self.assertEqual(called_ids, {t1.pk, t2.pk})
