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
                    start_line_no=119,
                    end_line_no=135,
                ),
                RootModel(
                    path=ROOT_FINDER_ONE_PATH,
                    name="Customer",
                    start_line_no=211,
                    end_line_no=233,
                ),
                RootModel(
                    path=ROOT_FINDER_ONE_PATH,
                    name="Warehouse",
                    start_line_no=165,
                    end_line_no=181,
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
                    start_line_no=158,
                    end_line_no=168,
                ),
                RootModel(
                    path=ROOT_FINDER_TWO_PATH,
                    name="NotificationService",
                    start_line_no=198,
                    end_line_no=214,
                ),
                RootModel(
                    path=ROOT_FINDER_TWO_PATH,
                    name="SystemAdministrator",
                    start_line_no=138,
                    end_line_no=154,
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
                    start_line_no=237,
                    end_line_no=259,
                ),
                RootModel(
                    path=ROOT_FINDER_THREE_PATH,
                    name="OfficeManager",
                    start_line_no=361,
                    end_line_no=383,
                ),
                RootModel(
                    path=ROOT_FINDER_THREE_PATH,
                    name="PayrollManager",
                    start_line_no=315,
                    end_line_no=331,
                ),
                RootModel(
                    path=ROOT_FINDER_THREE_PATH,
                    name="ProjectManager",
                    start_line_no=263,
                    end_line_no=279,
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
                    start_line_no=124,
                    end_line_no=152,
                ),
                RootModel(
                    path=ROOT_FINDERS_ONE_PATH / "models_three.py",
                    name="AnotherRoot",
                    start_line_no=74,
                    end_line_no=111,
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
                    start_line_no=50,
                    end_line_no=96,
                ),
                RootModel(
                    path=ROOT_FINDERS_TWO_PATH / "models_one.py",
                    name="AlphaRoot",
                    start_line_no=124,
                    end_line_no=152,
                ),
                RootModel(
                    path=ROOT_FINDERS_TWO_PATH / "models_three.py",
                    name="BetaRoot",
                    start_line_no=73,
                    end_line_no=102,
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
                    start_line_no=161,
                    end_line_no=222,
                )
            ],
        ),
    ],
)
def test_root_finders(test_case: RootFinderTestCase) -> None:
    """Test function for the `root_finders` function."""
    root_models = root_finders(test_case.path, test_case.xsd_model)
    assert test_case.root_models == root_models
