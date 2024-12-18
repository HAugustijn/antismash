# License: GNU Affero General Public License v3 or later
# A copy of GNU AGPL v3 should have been included in this software package in LICENSE.txt.

# for test files, silence irrelevant and noisy pylint warnings
# pylint: disable=use-implicit-booleaness-not-comparison,protected-access,missing-docstring

import unittest

import antismash
from antismash.common import record_processing
from antismash.common.test import helpers
from antismash.config import build_config, destroy_config
from antismash.detection import tigrfam


class TestTIGRFam(unittest.TestCase):
    def setUp(self):
        self.original_min_score = tigrfam.MIN_SCORE
        self.original_max_evalue = tigrfam.MAX_EVALUE
        self.options = build_config(["--tigrfam", "--minimal", "--enable-html"],
                                    isolated=True,
                                    modules=antismash.get_all_modules())

    def tearDown(self):
        self.set_max_evalue(self.original_max_evalue)
        self.set_min_score(self.original_min_score)
        destroy_config()

    def set_max_evalue(self, evalue):
        tigrfam.MAX_EVALUE = evalue

    def set_min_score(self, score):
        tigrfam.MIN_SCORE = score

    def check_add_to_record(self, input_file, results):
        record = record_processing.parse_input_sequence(input_file)[0]
        assert not record.get_antismash_domains_by_tool("tigrfam")
        results.add_to_record(record)
        assert len(record.get_antismash_domains_by_tool("tigrfam")) == len(results.hits)

    def test_reuse(self):
        nisin = helpers.get_path_to_nisin_genbank()
        record = record_processing.parse_input_sequence(nisin)[0]

        results = helpers.run_and_regenerate_results_for_module(nisin, tigrfam, self.options)
        json = results.to_json()
        assert len(results.hits) == 2
        self.check_add_to_record(nisin, results)

        # test regeneration when thresholds are less restrictive
        new_score_threshold = self.original_min_score - .1
        self.set_min_score(new_score_threshold)
        new_results = tigrfam.regenerate_previous_results(json, record, self.options)
        assert new_results is None
        self.set_min_score(self.original_min_score)

        new_evalue_threshold = self.original_max_evalue + .1
        self.set_max_evalue(new_evalue_threshold)
        new_results = tigrfam.regenerate_previous_results(json, record, self.options)
        assert new_results is None
        self.set_max_evalue(self.original_max_evalue)

        # test regeneration when evalue threshold is more restrictive
        new_evalue_threshold = sorted(hit.evalue for hit in results.hits)[0]
        assert new_evalue_threshold < self.original_max_evalue
        new_hits = []
        for hit in results.hits:
            if hit.evalue <= new_evalue_threshold:
                new_hits.append(hit)
        new_hits.sort(key=lambda x: x.evalue)
        assert len(new_hits) == 1

        self.set_max_evalue(new_evalue_threshold)
        new_results = tigrfam.regenerate_previous_results(json, record, self.options)
        self.set_max_evalue(self.original_max_evalue)
        assert sorted(new_results.hits, key=lambda x: x.evalue) == new_hits
        self.check_add_to_record(nisin, results)

        # test regeneration when score threshold is more restrictive
        new_score_threshold = sorted(hit.score for hit in results.hits)[1]
        assert new_score_threshold > tigrfam.MIN_SCORE
        new_hits = []
        for hit in results.hits:
            if hit.score >= new_score_threshold:
                new_hits.append(hit)
        new_hits.sort(key=lambda x: x.score)
        assert len(new_hits) == 1

        self.set_min_score(new_score_threshold)
        new_results = tigrfam.regenerate_previous_results(json, record, self.options)
        self.set_min_score(self.original_min_score)
        assert sorted(new_results.hits, key=lambda x: x.score) == new_hits
        self.check_add_to_record(nisin, results)
