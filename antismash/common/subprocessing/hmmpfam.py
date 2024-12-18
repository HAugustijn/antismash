# License: GNU Affero General Public License v3 or later
# A copy of GNU AGPL v3 should have been included in this software package in LICENSE.txt.

""" A collection of functions for running hmmpfam2.
"""

from io import StringIO
import logging
from typing import List, Optional

from .base import execute, get_config, SearchIO

_THREADING_SUPPORT = True


def run_hmmpfam2(query_hmmfile: str, target_sequence: str, extra_args: List[str] = None
                 ) -> list[SearchIO.QueryResult]:
    """ Run hmmpfam2 over the provided HMM file and fasta input

        Arguments:
            query_hmmfile: the HMM file to use
            target_sequence: a string in fasta format of the sequence to run

        Returns:
            a list of results as parsed by SearchIO
    """
    global _THREADING_SUPPORT  # pylint: disable=global-statement
    config = get_config()
    command = [config.executables.hmmpfam2]

    if extra_args:
        command.extend(extra_args)
    base_options = list(command)
    # Only use multithreading in hmmpfam2 if supported in the hmmpfam2 build
    if _THREADING_SUPPORT:
        command.extend(["--cpu", str(config.cpus)])
    command.extend([query_hmmfile, '-'])

    result = execute(command, stdin=target_sequence)
    # if it was an error due to no threading support
    if not result.successful() and _THREADING_SUPPORT and "threads support is not compiled" in result.stderr:
        # prevent further runs with threading
        _THREADING_SUPPORT = False
        # run again without the cpu option
        result = execute(base_options + [query_hmmfile, "-"], stdin=target_sequence)
    if not result.successful():
        logging.debug('hmmpfam2 returned %d: %r while searching %r', result.return_code,
                      result.stderr, query_hmmfile)
        raise RuntimeError(f"hmmpfam2 problem while running {command}: {result.stderr}")
    res_stream = StringIO(result.stdout)
    return list(SearchIO.parse(res_stream, 'hmmer2-text'))


def get_alignment_against_profile(sequence: str, db_path: str, profile_name: str, max_evalue: float = 0.1,
                                  ) -> Optional[SearchIO.QueryResult]:
    """ Aligns the given sequence against the given profile.

        Arguments:
            sequence: the protein sequence to align to the reference
            db_path: the path of the profile to align the translation against
            profile_name: the name of the specific profile within the database to align against
            max_evalue: the maximum evalue threshold for any hits

        Returns:
            the first hit for the query against the named profile
    """
    args = ["-E", str(max_evalue)]
    results = run_hmmpfam2(db_path, f">query\n{sequence}", extra_args=args)
    if not (results and results[0].hsps):
        return None

    for hit in results[0].hsps:
        if hit.hit_id == profile_name:
            return hit

    return None


def run_hmmpfam2_help() -> str:
    """ Get the help output of hmmpfam2 """
    hmmpfam2 = get_config().executables.hmmpfam2
    command = [
        hmmpfam2,
        "-h",
    ]

    help_text = execute(command).stdout
    if not help_text.startswith("hmmpfam"):
        raise RuntimeError(f"unexpected output from hmmpfam2: {hmmpfam2!r}, check path")

    return help_text


def run_hmmpfam2_version() -> str:
    """ Get the version of the hmmpfam2 binary """
    version_line = run_hmmpfam2_help().split('\n')[1]
    return version_line.split()[1]
