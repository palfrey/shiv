import os
from ..check_disks import decide_files
import yaml
import pytest
import os.path

from pathlib import Path

check_names = [
    x
    for x in Path(__file__).parent.joinpath("checks").glob("*")
    if not x.name.endswith(".yaml")
]


@pytest.mark.parametrize("fname", check_names)
def test_check_disks(fname):
    fname = str(fname.relative_to(Path(__file__).parent.parent))
    res = list(decide_files(fname))
    outname = fname + ".yaml"
    if os.path.exists(outname):
        expected = yaml.safe_load(open(outname))
    else:
        expected = None
        yaml.dump(res, open(outname, "w"))

    assert res == expected
