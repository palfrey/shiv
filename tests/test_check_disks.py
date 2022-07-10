import os
from ..check_disks import decide_files
import json
import pytest
import os.path

from pathlib import Path

check_names = [
    x
    for x in Path(__file__).parent.joinpath("checks").glob("*")
    if not x.name.endswith(".json")
]


@pytest.mark.parametrize("fname", check_names)
def test_check_disks(fname):
    fname = str(fname.relative_to(Path(__file__).parent.parent))
    res = list(decide_files(fname))
    outname = fname + ".json"
    if os.path.exists(outname):
        expected = json.load(open(outname))
    else:
        expected = None
        json.dump(res, open(outname, "w"))

    assert res == expected
