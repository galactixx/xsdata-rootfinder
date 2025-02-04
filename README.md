# xsdata-rootfinder

A Python package designed to analyze Python source files and identify root models. This package supports different model types, including dataclass, Pydantic, and attrs, making it easy to work with various schema formats.

## Features
- **Single File Analysis:** Identify root models from a single Python source file.
- **Batch Processing:** Analyze multiple files or directories with support for recursion.
- **Model Types:** Supports dataclasses, Pydantic models, and attrs classes.
- **Multiprocessing:** Optional multiprocessing for faster batch analysis.

## Installation
To install `xsdata-rootfinder`, run the following command:

```bash
pip install xsdata-rootfinder
```

## How It Works
The `xsdata-rootfinder` package analyzes Python source files to identify root models. A root model is defined as a class that is present in a file but not referenced within it.

### Functionality Overview
#### `root_finder`
Analyze a single Python source file to find root models.

```python
def root_finder(source: CodeOrStrOrPath, xsd_models: XsdModels = "dataclass") -> Optional[List[RootModel]]:
    ...
```

- **Arguments:**
  - `source`: Python source to analyze (code string, file path, or path-like object).
  - `xsd_models`: Specifies model type (`'dataclass'`, `'pydantic'`, or `'attrs'`).
- **Returns:** List of root models or `None`.

#### Example Usage
```python
from xsdata_rootfinder import root_finder

roots = root_finder("path/to/source.py", xsd_models="pydantic")
```

#### `root_finders`
Analyze multiple files or directories to find root models.

```python
def root_finders(
    source: Union[StrOrPath, Collection[StrOrPath]],
    xsd_models: XsdModels = "dataclass",
    directory_walk: bool = False,
    ignore_init_files: bool = True,
    multiprocessing: Optional[MultiprocessingSettings] = None,
) -> Optional[List[RootModel]]:
    ...
```

- **Arguments:**
  - `source`: One or more paths to analyze.
  - `xsd_models`: Specifies model type (`'dataclass'`, `'pydantic'`, or `'attrs'`).
  - `directory_walk`: Recursively search directories.
  - `ignore_init_files`: Ignore `__init__.py` files.
  - `multiprocessing`: Settings for parallel file processing.
- **Returns:** List of root models or `None`.

#### Example Usage
```python
from xsdata_rootfinder import root_finders

roots = root_finders(
    ["path/to/source1.py", "path/to/source2.py"],
    xsd_models="attrs",
    directory_walk=True,
    multiprocessing=None
)
```

## License
This project is licensed under the terms of the MIT License.

## Workflow Details
GitHub Actions automate CI/CD workflows, including tests and package deployment.

