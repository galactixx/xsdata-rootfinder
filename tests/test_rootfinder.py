from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pytest

from xsdata_rootfinder import RootModel, StrOrPath, XsdModels, root_finder, root_finders

# Constants and global variables used when testing
ROOT_FINDER_PATH = Path("./tests/examples/root_finder/").resolve()
ROOT_FINDER_ONE_PATH = ROOT_FINDER_PATH / "test_one.py"
ROOT_FINDER_TWO_PATH = ROOT_FINDER_PATH / "test_two.py"
ROOT_FINDER_THREE_PATH = ROOT_FINDER_PATH / "test_three.py"

ROOT_FINDERS_PATH = Path("./tests/examples/root_finders/").resolve()
ROOT_FINDERS_ONE_PATH = ROOT_FINDERS_PATH / "test_one"
ROOT_FINDERS_TWO_PATH = ROOT_FINDERS_PATH / "test_two"
ROOT_FINDERS_THREE_PATH = ROOT_FINDERS_PATH / "test_three"


@dataclass(frozen=True)
class RootFinderTestCase:
    """
    Dataclass representing a test case for both the `root_finder` and
    `root_finders` functions.
    """

    path: StrOrPath
    xsd_model: XsdModels
    root_models: Optional[List[RootModel]]


@pytest.mark.parametrize(
    "test_case",
    [
        RootFinderTestCase(
            path=ROOT_FINDER_ONE_PATH,
            xsd_model="dataclass",
            root_models=[
                RootModel(
                    path=ROOT_FINDER_ONE_PATH,
                    name="Catalog",
                    start_line_no=99,
                    end_line_no=111,
                ),
                RootModel(
                    path=ROOT_FINDER_ONE_PATH,
                    name="Customer",
                    start_line_no=175,
                    end_line_no=193,
                ),
                RootModel(
                    path=ROOT_FINDER_ONE_PATH,
                    name="Warehouse",
                    start_line_no=137,
                    end_line_no=149,
                ),
            ],
        ),
        RootFinderTestCase(
            path=ROOT_FINDER_TWO_PATH,
            xsd_model="dataclass",
            root_models=[
                RootModel(
                    path=ROOT_FINDER_TWO_PATH,
                    name="AuditManager",
                    start_line_no=138,
                    end_line_no=144,
                ),
                RootModel(
                    path=ROOT_FINDER_TWO_PATH,
                    name="NotificationService",
                    start_line_no=170,
                    end_line_no=182,
                ),
                RootModel(
                    path=ROOT_FINDER_TWO_PATH,
                    name="SystemAdministrator",
                    start_line_no=122,
                    end_line_no=134,
                ),
            ],
        ),
        RootFinderTestCase(
            path=ROOT_FINDER_THREE_PATH,
            xsd_model="dataclass",
            root_models=[
                RootModel(
                    path=ROOT_FINDER_THREE_PATH,
                    name="CustomerServiceManager",
                    start_line_no=197,
                    end_line_no=215,
                ),
                RootModel(
                    path=ROOT_FINDER_THREE_PATH,
                    name="OfficeManager",
                    start_line_no=301,
                    end_line_no=319,
                ),
                RootModel(
                    path=ROOT_FINDER_THREE_PATH,
                    name="PayrollManager",
                    start_line_no=263,
                    end_line_no=275,
                ),
                RootModel(
                    path=ROOT_FINDER_THREE_PATH,
                    name="ProjectManager",
                    start_line_no=219,
                    end_line_no=231,
                ),
            ],
        ),
    ],
)
def test_root_finder_by_path(test_case: RootFinderTestCase) -> None:
    """Test function for the `root_finder` function."""
    root_models = root_finder(test_case.path, test_case.xsd_model)
    assert test_case.root_models == root_models


@pytest.mark.parametrize(
    "test_case",
    [
        RootFinderTestCase(
            path=ROOT_FINDERS_ONE_PATH,
            xsd_model="dataclass",
            root_models=[
                RootModel(
                    path=ROOT_FINDERS_ONE_PATH / "models_one.py",
                    name="MyRoot",
                    start_line_no=108,
                    end_line_no=132,
                ),
                RootModel(
                    path=ROOT_FINDERS_ONE_PATH / "models_three.py",
                    name="AnotherRoot",
                    start_line_no=62,
                    end_line_no=95,
                ),
            ],
        ),
        RootFinderTestCase(
            path=ROOT_FINDERS_TWO_PATH,
            xsd_model="dataclass",
            root_models=[
                RootModel(
                    path=ROOT_FINDERS_TWO_PATH / "models_four.py",
                    name="GammaRoot",
                    start_line_no=42,
                    end_line_no=83,
                ),
                RootModel(
                    path=ROOT_FINDERS_TWO_PATH / "models_one.py",
                    name="AlphaRoot",
                    start_line_no=108,
                    end_line_no=132,
                ),
                RootModel(
                    path=ROOT_FINDERS_TWO_PATH / "models_three.py",
                    name="BetaRoot",
                    start_line_no=61,
                    end_line_no=86,
                ),
            ],
        ),
        RootFinderTestCase(
            path=ROOT_FINDERS_THREE_PATH,
            xsd_model="dataclass",
            root_models=[
                RootModel(
                    path=ROOT_FINDERS_THREE_PATH / "models_two.py",
                    name="OmegaRoot",
                    start_line_no=162,
                    end_line_no=223,
                )
            ],
        ),
    ],
)
def test_root_finders(test_case: RootFinderTestCase) -> None:
    """Test function for the `root_finders` function."""
    root_models = root_finders(test_case.path, test_case.xsd_model)
    assert test_case.root_models == root_models
