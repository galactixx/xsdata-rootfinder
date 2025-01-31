from __future__ import annotations

import importlib.util
import re
import sys
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Collection
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import lru_cache
from os import PathLike
from pathlib import Path
from typing import (
    ClassVar,
    Deque,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

IS_PY_3_1 = sys.version_info >= (3, 10)

if IS_PY_3_1:
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

import libcst as cst
from libcst.metadata import CodeRange, MetadataWrapper, PositionProvider
from pathvalidate import ValidationError, validate_filepath

# Typealiases
_ModuleType: TypeAlias = Union[cst.Name, cst.Attribute]

StrOrPath: TypeAlias = Union[str, PathLike[str]]
CodeOrStrOrPath: TypeAlias = Union[str, PathLike[str]]
XsdModels: TypeAlias = Literal["dataclass", "pydantic", "attrs"]

# Constants and global variables
_MAX_RETRIES = 3


class _AbstractModelCheck(ABC):
    """
    An abstract base class for running model checks on `libcst.ClassDef`
    objects.
    """

    __model_module__: ClassVar[str]

    def __init__(self, imports: _Imports) -> None:
        self.imports = imports

    @abstractmethod
    def run_model_check(self, node: cst.ClassDef) -> bool:
        """Run the model check for a `libcst.ClassDef` object."""
        pass

    def _parse_imported_module(self, expression: cst.BaseExpression) -> bool:
        """Check if the imported module matches the expected model module."""
        module = _parse_imported_module(cast(_ModuleType, expression))
        found_module = self.imports.find_common_import(module)
        is_imported = False

        if found_module is not None:
            module_from_file = self.imports.get_import(found_module)
            is_imported = module_from_file.module == self.__model_module__

        if not is_imported and self.imports.import_stars:
            import_remaining = re.sub(
                f"\\.{re.escape(module.module)}$", "", self.__model_module__
            )
            is_imported = import_remaining in self.imports.import_stars
        return is_imported


class _DataclassModelCheck(_AbstractModelCheck):
    """A class that checks implementation for dataclass decorators."""

    __model_module__: ClassVar[str] = "dataclasses.dataclass"

    def run_model_check(self, node: cst.ClassDef) -> bool:
        """Verify if the given CST class uses the dataclass decorator."""
        return any(
            self._parse_imported_module(decorator.decorator)
            for decorator in node.decorators
        )


class _PydanticModelCheck(_AbstractModelCheck):
    """A class that checks implementation for Pydantic BaseModel inheritance."""

    __model_module__: ClassVar[str] = "pydantic.BaseModel"

    def run_model_check(self, node: cst.ClassDef) -> bool:
        """Verify if the given CST class inherits from Pydantic BaseModel."""
        return any(
            self._parse_imported_module(base_class.value) for base_class in node.bases
        )


class _AttrsModelCheck(_AbstractModelCheck):
    """A class that checks implementation for attrs decorators."""

    __model_module__: ClassVar[str] = "attr.s"

    def run_model_check(self, node: cst.ClassDef) -> bool:
        """Verify if the given CST class uses the attrs decorator."""
        return any(
            self._parse_imported_module(decorator.decorator)
            for decorator in node.decorators
        )


def _parse_imported_module(module: _ModuleType) -> _ImportIdentifier:
    """
    Parses a module node to extract its full module path as an
    `_ImportIdentifier`.
    """
    module_levels: List[str] = list()
    module_objects: Deque[_ModuleType] = deque([module])
    while module_objects:
        cur_module_level = module_objects.popleft()
        if isinstance(cur_module_level, cst.Name):
            module_levels.append(cur_module_level.value)
        else:
            cur_module_attr = cur_module_level.attr
            cur_module_value = cast(_ModuleType, cur_module_level.value)
            module_objects.extendleft([cur_module_attr, cur_module_value])
    return _ImportIdentifier.from_levels(module_levels)


def _root_finder(
    defs: Set[RootModel], refs: Set[_ReferencedClass]
) -> Optional[List[RootModel]]:
    """
    Identify and return root models from one or multiple Python source
    files.
    """
    root_classes = [
        root_model for root_model in defs if root_model._referenced_class not in refs
    ]
    root_classes.sort(key=lambda x: (x.path, x.name))
    return None if not root_classes else root_classes


def _create_module_from_levels(levels: List[str]) -> str:
    """Combines module levels into a single dotted module path."""
    return ".".join(levels)


def _decompose_module(module: str) -> List[str]:
    """Splits a module path into its individual components."""
    return module.split(".")


@lru_cache(maxsize=None)
def _is_from_standard_library(module: str) -> bool:
    """Determine if the given module is part of the Python standard library."""
    spec = importlib.util.find_spec(module)
    return spec is not None and spec.origin == "stdlib"


@lru_cache(maxsize=None)
def _module_has_class(path: Path, name: str) -> bool:
    """
    Check if a class with the given name exists in the Python module at the
    specified path.
    """
    if not path.exists():
        return False

    python_code = _read_python_file(path)
    module = cst.parse_module(python_code)
    class_def_visitor = _XSDataClassDefFinderVisitor(name)
    try:
        module.visit(class_def_visitor)
    except _XSDataStopTraversalError:
        pass
    return class_def_visitor.found


def _parse_import_alias(import_alias: cst.ImportAlias) -> Tuple[str, _ImportIdentifier]:
    """Parses an import alias into its alias and module components."""
    alias: _ModuleType
    if import_alias.asname is not None:
        alias = cast(cst.Name, import_alias.asname.name)
    else:
        alias = import_alias.name

    alias = _parse_imported_module(alias).module
    module = _parse_imported_module(import_alias.name)
    return alias, module


class _XSDataStopTraversalError(Exception):
    """Custom exception to stop CST traversal when a target class is found."""

    pass


class XSDataRootFinderError(Exception):
    """
    Custom exception for errors encountered during the XSData root-finding
    process.

    This exception is raised when the process of identifying root models in
    Python source files fails due to issues such as file processing errors,
    timeouts, or unexpected conditions.

    Attributes:
        message (str): A detailed message describing the error.
        source (Path): The file path associated with the error, providing
            context about where the error occurred.
    """

    def __init__(self, message: str, source: Path) -> None:
        self.message = message
        self.source = source

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return self.message


@dataclass
class _XSDataCollectedClasses:
    """Tracks and consolidate defined and referenced classes."""

    xsd_models: XsdModels
    refs: Set[_ReferencedClass] = field(default_factory=set)
    defs: Set[RootModel] = field(default_factory=set)

    def _consoildate_classes(self, visitor: _XSDataRootFinderVisitor) -> None:
        """
        Merge referenced and defined classes from a visitor into the current
        instance.
        """
        self.refs.update(visitor.ref_classes)
        self.defs.update(visitor.defined_classes)

    def root_finder(self) -> Optional[List[RootModel]]:
        """Identify and return root models from one or more Python source files."""
        return _root_finder(defs=self.defs, refs=self.refs)

    def visit_and_consolidate(self, source: CodeOrStrOrPath) -> None:
        """Process and consolidate data from a source file, either a str or Path."""
        visitor = _python_source_visit(source, self.xsd_models)
        self._consoildate_classes(visitor)

    def visit_and_consolidate_by_path(self, source: StrOrPath) -> None:
        """Process and consolidate data from a source file as a `StrOrPath` object."""
        if not Path(source).is_file():
            raise FileNotFoundError(
                "Every object in 'source' argument must must link to an existing file"
            )

        self.visit_and_consolidate(source)


@dataclass
class _Imports:
    """
    Manages and queries imported modules found when parsing python
    source code.
    """

    imports: Dict[str, _ImportIdentifier] = field(default_factory=dict)
    import_stars: Set[str] = field(default_factory=set)

    def find_common_import(self, module: _ImportIdentifier) -> Optional[str]:
        """Find the most specific common import for the given module."""
        module_parts = module.parts
        for idx in range(len(module_parts), 0, -1):
            str_module = _create_module_from_levels(module_parts[:idx])
            if str_module in self.imports:
                return str_module
        return None

    def get_import(self, module: str) -> _ImportIdentifier:
        """Retrieve the `_ImportIdentifier` for the specified module."""
        return self.imports[module]

    def add_import_star(self, module: _ImportIdentifier) -> None:
        """Add a star import for the given module."""
        self.import_stars.add(module.module)

    def add_import(self, alias: str, module: _ImportIdentifier) -> None:
        """Add an import to store based on the alias."""
        self.imports[alias] = module


@dataclass(frozen=True)
class _ImportIdentifier:
    """
    A class that represents a module-level import identifier with
    optional attributes.
    """

    value: str
    attribute: Optional[str] = None

    @property
    def parts(self) -> List[str]:
        """Returns the module path as a list of components."""
        return _decompose_module(self.module)

    @property
    def module(self) -> str:
        """Returns the full module path as a string."""
        return (
            self.value if self.attribute is None else f"{self.attribute}.{self.value}"
        )

    @classmethod
    def from_levels(cls, levels: List[str]) -> _ImportIdentifier:
        """Create an `_ImportIdentifier` from module levels."""
        if len(levels) == 1:
            module = _create_module_from_levels(levels)
            return cls(module)
        else:
            attribute = _create_module_from_levels(levels[:-1])
            value = levels[-1]
            return cls(value, attribute)

    def module_to_path(self, py_file_path: Path) -> Optional[Path]:
        """
        Resolve the file path of the module by checking different directory
        structures relative to the given Python file path.
        """
        module_as_path = Path(*self.parts).parent.with_suffix(".py")

        # First test for whether the module is in the same directory
        same_dir_path = py_file_path.with_name(module_as_path.name)
        if _module_has_class(same_dir_path, self.value):
            return same_dir_path

        # Next, test for whether the module is in a deeper directory
        deeper_path = py_file_path.parent / module_as_path
        if _module_has_class(deeper_path, self.value):
            return deeper_path

        # Finally, we assume the path is in another directory
        py_file_path_str = str(py_file_path)
        pattern = re.compile(f"({re.escape(module_as_path.parts[0])})")
        sub_path_match = pattern.search(py_file_path_str)

        if sub_path_match is not None:
            for match in range(1, len(sub_path_match.groups()) + 1):
                common_path = sub_path_match.group(match)
                start_path = py_file_path_str[: sub_path_match.start(match)]

                pred_path = Path(start_path, common_path, *self.parts[1:])
                pred_path = pred_path.parent.with_suffix(".py")
                if _module_has_class(pred_path, self.value):
                    return pred_path
        return None


@dataclass(frozen=True)
class RootModel:
    """
    Represents the root model for an unreferenced class in a module.

    A root model is a class definition that exists in a Python source file
    but is not referenced within the same file. This class captures metadata
    about such classes, including their name, location within the file, and
    the file's path.

    Attributes:
        path (Optional[Path]): The file path where the class is defined. Can
            be `None` if the source is not associated with a file
            (e.g., in-memory code).
        name (str): The name of the class.
        start_line_no (int): The starting line number of the class definition
            in the file.
        end_line_no (int): The ending line number of the class definition in
            the file.
    """

    path: Optional[Path]
    name: str
    start_line_no: int
    end_line_no: int

    @property
    def _referenced_class(self) -> _ReferencedClass:
        """
        Returns a `_ReferencedClass` object representing this root model.
        """
        return _ReferencedClass(self.path, self.name)

    @classmethod
    def _from_cst_class(
        cls, span: CodeRange, node: cst.ClassDef, path: Optional[Path]
    ) -> RootModel:
        """
        Creates a `RootModel` instance from a `libcst.ClassDef` object
        and its metadata.
        """
        class_name = node.name.value
        start_line = span.start.line
        end_line = span.end.line
        return cls(path, class_name, start_line, end_line)


@dataclass(frozen=True)
class _ReferencedClass:
    """A dataclass used to uniquely identify referenced classes."""

    path: Optional[Path]
    name: str


@dataclass(frozen=True)
class MultiprocessingSettings:
    """
    Settings for enabling and configuring multiprocessing.

    This class encapsulates the configuration for running tasks in parallel
    using multiprocessing. It allows enabling or disabling multiprocessing,
    setting the number of worker threads, and defining a timeout for each task.

    Attributes:
        enabled (bool): Whether multiprocessing is enabled. Default is `False`.
        max_workers (int | None): The maximum number of workers (threads)
            to use for multiprocessing. If `None`, the default thread pool size
            is used.
        timeout (int | None): The timeout (in seconds) for each task. If `None`,
            no timeout is applied.
    """

    enabled: bool = False
    max_workers: Optional[int] = None
    timeout: Optional[int] = None


class _XSDataClassDefFinderVisitor(cst.CSTVisitor):
    """A visitor class to search for a class definition in a CST module."""

    def __init__(self, class_name: str) -> None:
        self.class_name = class_name
        self.found = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """
        Visit a class definition node and check if its name matches the target
        class name.
        """
        self.found = node.name.value == self.class_name
        if self.found:
            raise _XSDataStopTraversalError
        return not self.found


class _XSDataRootFinderVisitor(cst.CSTVisitor):
    """
    A visitor class to parse and extract class references from Python
    source files.
    """

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, xsd_models: XsdModels, path: Optional[Path]) -> None:
        self.xsd_models = xsd_models
        self.path = path
        self.imports = _Imports()
        self.class_trace: Deque[cst.ClassDef] = deque([])
        self.ref_classes: Set[_ReferencedClass] = set()
        self.defined_classes: Set[RootModel] = set()

    def _is_relevant_model(self) -> bool:
        """
        Determines if a given `libcst.ClassDef` object is a class that was
        generated by `xsdata`.
        """
        MODELS_CHECKS: Dict[XsdModels, Type[_AbstractModelCheck]] = {
            "dataclass": _DataclassModelCheck,
            "pydantic": _PydanticModelCheck,
            "attrs": _AttrsModelCheck,
        }

        ModelCheck = MODELS_CHECKS.get(self.xsd_models)
        if ModelCheck is None:
            raise ValueError(
                "'xsd_models' must be one of ('dataclass', 'pydantic', 'attrs')"
            )

        model_check = ModelCheck(self.imports)

        class_node = self.class_trace.popleft()
        self.class_trace.appendleft(class_node)
        is_valid_model = model_check.run_model_check(class_node)
        return is_valid_model

    def _add_class_to_refs(self, name: str) -> None:
        """
        Adds a `_ReferencedClass` object representing a class name to the
        reference set.
        """
        if _is_from_standard_library(name):
            return None

        in_module_ref = _ReferencedClass(self.path, name)
        ref_class = in_module_ref if self.path is None else self._get_local_import(name)

        if ref_class is None:
            ref_class = in_module_ref
        self.ref_classes.add(ref_class)

    def _attribute_ann_assign(self, node: cst.Attribute) -> None:
        """Handles annotations that are qualified names (e.g., module.Class)."""
        class_name = node.attr.value
        self._add_class_to_refs(class_name)

    def _name_ann_assign(self, node: cst.Name) -> None:
        """Handles annotations that are simple names (e.g., int, MyClass)."""
        class_name = node.value
        self._add_class_to_refs(class_name)

    def _subscript_ann_assign(self, node: cst.Subscript) -> None:
        """Handles annotations that are subscripted types (e.g., List[int])."""

        def find_all_types_in_subscript(subscript: cst.Subscript) -> None:
            """
            Parses and retrieves all class names found within a `libcst.Subscript` object.
            Traverses recursively through the entire object to find all references
            to classes.
            """

            def traversal(base_slice: cst.BaseSlice) -> None:
                slice_index = cast(cst.Index, base_slice)
                slice_index_value = slice_index.value

                # If the value of the index is a cst.Subscript, then
                # iteration through each value needs to occur and
                # recursion continues
                if isinstance(slice_index_value, cst.Subscript):
                    for sub_element in slice_index_value.slice:
                        traversal(sub_element.slice)

                # If the value is a cst.Attribute, then extract the
                # value of the top-level portion of the attribute
                elif isinstance(slice_index_value, cst.Attribute):
                    self._add_class_to_refs(slice_index_value.attr.value)

                # Simply extract the value if object is a cst.Name
                elif isinstance(slice_index_value, cst.Name):
                    self._add_class_to_refs(slice_index_value.value)

                # If there is a reference to a class as a string, due
                # to TYPE_CHECKING, then strip the value of extra
                # quotations and add to set of classes encountered
                elif isinstance(slice_index_value, cst.SimpleString):
                    self._add_class_to_refs(slice_index_value.value.strip('"'))

            for sub_element in subscript.slice:
                traversal(sub_element.slice)

        find_all_types_in_subscript(node)

    def _simple_string_ann_assign(self, node: cst.SimpleString) -> None:
        """Handles annotations represented as simple strings (e.g., "MyClass")."""
        class_name = node.value.strip('"')
        self._add_class_to_refs(class_name)

    def _get_local_import(self, module: str) -> Optional[_ReferencedClass]:
        """Retrieve a locally imported class as a `_ReferencedClass`, if available."""
        identifier = _ImportIdentifier.from_levels(_decompose_module(module))
        found_module = self.imports.find_common_import(identifier)
        py_source_path = cast(Path, self.path)

        # Check if is not appearing in an "import *"
        if found_module is not None:
            module_from_file = self.imports.get_import(found_module)
            path_from_module = module_from_file.module_to_path(py_source_path)
            if path_from_module is not None:
                return _ReferencedClass(path_from_module, module_from_file.value)

        # Check whether it was imported in an "import *"
        for star in self.imports.import_stars:
            star_module = _ImportIdentifier.from_levels(
                _decompose_module(star) + identifier.parts
            )
            star_path = star_module.module_to_path(py_source_path)
            if star_path is not None:
                return _ReferencedClass(star_path, star_module.value)
        return None

    def _get_inherited_local_classes(self, node: cst.ClassDef) -> None:
        """Identify and add local classes inherited by the current class node."""
        for base_class in node.bases:
            identifier = _parse_imported_module(cast(_ModuleType, base_class.value))
            self._add_class_to_refs(identifier.module)

    def visit_Import(self, node: cst.Import) -> None:
        """Parses and consolidates any import statements found."""
        for import_alias in node.names:
            alias, module = _parse_import_alias(import_alias)
            self.imports.add_import(alias, module)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        """Parses and consolidates any import-from statements found."""
        if len(node.relative) and self.path is not None:
            start_index = len(self.path.parts) - len(node.relative) - 1
            module = _ImportIdentifier(self.path.parts[start_index])

            if node.module is not None:
                non_relative_module = _parse_imported_module(node.module)
                module = _ImportIdentifier.from_levels(
                    module.parts + non_relative_module.parts
                )
        else:
            module = _parse_imported_module(cast(_ModuleType, node.module))

        if isinstance(node.names, cst.ImportStar):
            self.imports.add_import_star(module)
            return None

        for import_alias in node.names:
            alias, non_alias = _parse_import_alias(import_alias)
            combined_module = _ImportIdentifier.from_levels(
                module.parts + non_alias.parts
            )
            self.imports.add_import(alias, combined_module)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """
        Set the currently visited `libcst.ClassDef` object and updates the
        defined class store.
        """
        if not self.class_trace:  # To ensure only top-level classes are parsed
            span = self.get_metadata(PositionProvider, node)
            root_model = RootModel._from_cst_class(span, node, self.path)
            self.defined_classes.add(root_model)

            # Check if any generated models are inherited
            self._get_inherited_local_classes(node)
        self.class_trace.appendleft(node)

    def leave_ClassDef(self, _: cst.ClassDef) -> None:
        """Clear the currently visited `libcst.ClassDef` object."""
        _ = self.class_trace.popleft()

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        """Identify and process annotations within class definitions."""
        if self.class_trace and self._is_relevant_model():
            annotation_node = node.annotation.annotation

            # If the annotation is a cst.Subscript, which is
            # represented like:
            #   - List[int], Dict[str, List[int]], Union[int, str],
            #     Optional[int]
            if isinstance(annotation_node, cst.Subscript):
                self._subscript_ann_assign(annotation_node)

            # If the annotation is a cst.Name which is
            # represented like:
            #   - int, ClassDef, MyClass
            elif isinstance(annotation_node, cst.Name):
                self._name_ann_assign(annotation_node)

            # If the annotation is a cst.Attribute which can
            # be represented like:
            #   - typing.List, libcst.ClassDef, my_module.MyClass
            elif isinstance(annotation_node, cst.Attribute):
                self._attribute_ann_assign(annotation_node)

            # If the annotation is a cst.SimpleString which can
            # be represented like:
            #   - "MyClass", "my_module.MyClass"
            elif isinstance(annotation_node, cst.SimpleString):
                self._simple_string_ann_assign(annotation_node)

    def root_finder(self) -> Optional[List[RootModel]]:
        """Identify and return root models from a single Python source file."""
        return _root_finder(defs=self.defined_classes, refs=self.ref_classes)


def _read_python_file(source: CodeOrStrOrPath) -> str:
    """
    Reads and returns the content of a Python file or validate input
    as a source.
    """
    if Path(source).is_file():
        with open(source, "r") as py_file:
            python_file = py_file.read()
        return python_file

    try:
        py_source_as_path = Path(source)
        validate_filepath(file_path=py_source_as_path)
    except ValidationError:
        res_source = str(source)
    else:
        raise FileNotFoundError(
            "If path is passed in as the source, it must link to an existing file"
        )
    return res_source


def _python_source_visit(
    source: CodeOrStrOrPath, xsd_models: XsdModels
) -> _XSDataRootFinderVisitor:
    """
    Parses a Python source file and extracts class definitions and references.
    """
    source_path = None if not Path(source).is_file() else Path(source).resolve()
    source = _read_python_file(source)
    python_module = MetadataWrapper(cst.parse_module(source))
    visitor = _XSDataRootFinderVisitor(xsd_models, source_path)
    python_module.visit(visitor)
    return visitor


def root_finder(
    source: CodeOrStrOrPath, xsd_models: XsdModels = "dataclass"
) -> Optional[List[RootModel]]:
    """
    Identify and return root models from a single Python source file.

    A root model is a class that is defined in the given Python file but is
    not referenced within that file. This function analyzes a single Python
    source file and extracts all such unreferenced classes that match the
    specified model type (e.g., dataclass, Pydantic, or attrs).

    Args:
        source (`CodeOrStrOrPath`): The Python source to analyze. This can be
            a string representing the code content or path, or a path-like object
            pointing to a Python file.
        xsd_models (`XsdModels`): Specifies the type of models to look for.
            Can be one of `'dataclass'` (default), `'pydantic'`, or `'attrs'`.

    Returns:
        Optional[List[`RootModel`]]: A list of `RootModel` instances representing
            unreferenced class definitions in the file, or `None` if no root
            models are found.
    """
    visitor = _python_source_visit(source, xsd_models)
    return visitor.root_finder()


def root_finders(
    source: Union[StrOrPath, Collection[StrOrPath]],
    xsd_models: XsdModels = "dataclass",
    directory_walk: bool = False,
    ignore_init_files: bool = True,
    multiprocessing: MultiprocessingSettings = MultiprocessingSettings(),
) -> Optional[List[RootModel]]:
    """
    Identify and return root models from multiple Python source files.

    A root model is a class that is defined in the given Python file but is
    not referenced within that file. This function analyzes one or more Python
    source files or directories and extracts all unreferenced classes that
    match the specified model type (e.g., dataclass, Pydantic, or attrs). It
    supports optional multiprocessing for parallel processing of files.

    Args:
        source (`StrOrPath` | Collection[`StrOrPath`]): The source(s) to
            analyze. This can be a single path-like object (file or directory),
            a collection of path-like objects representing multiple files. If a
            directory is provided, its Python files will be included for analysis.
        xsd_models (`XsdModels`): Specifies the type of models to look for. Can
            be one of `'dataclass'` (default), `'pydantic'`, or `'attrs'`.
        directory_walk (bool): If `True`, recursively searches for Python files
            within a directory. If `False`, only searches the immediate directory
            for Python files. Only applicable if a directory is passed as the
            `source` argument.
        ignore_init_files (bool): If `True`, ignores Python `__init__.py` files
            during the root-finding process.
        multiprocessing (`MultiprocessingSettings`): Settings to enable and
            configure multiprocessing.

    Returns:
        Optional[List[`RootModel`]]: A list of `RootModel` instances representing
            unreferenced class definitions across all files, or `None` if no root
            models are found.
    """

    def is_init_file(path: StrOrPath) -> bool:
        return ignore_init_files and Path(path).name == "__init__.py"

    consolidated_classes = _XSDataCollectedClasses(xsd_models)

    # Normalize sources into a list of file paths
    if isinstance(source, (str, PathLike)) and Path(source).is_dir():
        source = list(
            Path(source).rglob("*.py") if directory_walk else Path(source).glob("*.py")
        )
    elif isinstance(source, (str, PathLike)):
        source = [Path(source)]

    # Apply multiprocessing if enabled by user
    if multiprocessing.enabled:
        with ThreadPoolExecutor(multiprocessing.max_workers) as thread_executor:
            futures = {
                thread_executor.submit(
                    consolidated_classes.visit_and_consolidate_by_path, path
                ): path
                for path in source
                if not is_init_file(path)
            }
            for future in as_completed(futures):
                fut_source = futures[future]
                retry_counter = 0
                while True:
                    try:
                        future.result(timeout=multiprocessing.timeout)
                        break
                    except TimeoutError as e:
                        retry_counter += 1
                        if retry_counter > _MAX_RETRIES:
                            raise TimeoutError(e)
                    except Exception as e:
                        raise XSDataRootFinderError(
                            "Task was not completed succesfully", Path(fut_source)
                        ) from e
    # Otherwise, default to iteration of sources
    else:
        for path in source:
            if not is_init_file(path):
                consolidated_classes.visit_and_consolidate_by_path(path)

    return consolidated_classes.root_finder()
