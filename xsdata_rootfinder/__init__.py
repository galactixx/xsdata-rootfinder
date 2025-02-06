from __future__ import annotations

import importlib.util
import re
import sys
import os
import sysconfig
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Collection
from threading import Semaphore
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from functools import lru_cache
from os import PathLike
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Deque,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

_IS_PY_3_10 = sys.version_info >= (3, 10)

if _IS_PY_3_10:
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


def _normalize_path(path: str) -> str:
    """Normalize a file system path by resolving case and double slashes."""
    return os.path.normcase(os.path.normpath(path))


# Constants and global variables
_STDLIB_PATH = _normalize_path(sysconfig.get_paths()["stdlib"])
_THIRDPTYLIB_PATHS: Set[str] = {
    _normalize_path(sysconfig.get_paths()[path]) for path in ("purelib", "platlib")
}
_PRIMITIVE_TYPES = {
    "int",
    "str",
    "float",
    "bool",
    "complex",
    "bytes",
    "bytearray",
    "memoryview",
}


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


def _is_xsdata_import(module: _ImportIdentifier) -> bool:
    """Check if the module belongs to the 'xsdata' library namespace."""
    return module.module.startswith("xsdata")


def _is_builtin_type(annotation: str) -> bool:
    """Determine if the given annotation is a Python primitive type."""
    return annotation in _PRIMITIVE_TYPES


@lru_cache(maxsize=None)
def _find_import_spec(module: _ImportIdentifier) -> _PythonModuleSpec:
    """
    Locate and return the import specification for a module, identifying
    whether it is standard library or third-party.
    """
    module_parts = module.parts
    name = module_parts[0]
    package = (
        _create_module_from_levels(module_parts[1:]) if len(module_parts) > 1 else None
    )
    spec = importlib.util.find_spec(name, package)

    is_stdlib = False
    is_third_party = False

    if spec is not None and spec.origin is not None:
        origin_path = _normalize_path(spec.origin)
        is_third_party = any(
            origin_path.startswith(path) for path in _THIRDPTYLIB_PATHS
        )
        is_stdlib_path = origin_path.startswith(_STDLIB_PATH)
        is_stdlib = is_stdlib_path and not is_third_party
    return _PythonModuleSpec(module, is_third_party, is_stdlib)


@lru_cache(maxsize=None)
def _get_module_defined_classes(path: Path) -> Set[str]:
    """
    Retrieve the set of class names defined in a Python module at the
    given path.
    """
    if not path.exists():
        return set()

    python_code = _read_python_file(path)
    module = cst.parse_module(python_code)
    class_def_visitor = _XSDataClassDefFinderVisitor()
    module.visit(class_def_visitor)
    return class_def_visitor.defined_classes


def _module_has_class(path: Path, name: str) -> bool:
    """
    Check if a class with the given name exists in the Python module at the
    specified path.
    """
    defined_classes = _get_module_defined_classes(path)
    return name in defined_classes


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


@dataclass(frozen=True)
class _PythonModuleSpec:
    """
    Represents metadata about a Python module, including its import
    classification.
    """

    identifier: _ImportIdentifier
    third_party_import: bool
    stdlib_import: bool

    @property
    def irrelevant_module(self) -> bool:
        """
        Check if the module is irrelevant by being either part of the standard
        library or the 'xsdata' library.
        """
        return self.stdlib_import or _is_xsdata_import(self.identifier)

    @property
    def is_python_library(self) -> bool:
        """
        Determine if the module is a Python library, either third-party or
        otherwise classified as irrelevant.
        """
        return self.third_party_import or self.irrelevant_module


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

    def visit_and_consolidate_by_path(self, source: Path) -> None:
        """Process and consolidate data from a source file as a `StrOrPath` object."""
        print(source)
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


@dataclass
class _LocalImportSearch:
    """
    Stores the result of a local import search, including the referenced
    class and its library classification.
    """

    referenced_class: Optional[_ReferencedClass] = None
    is_python_library: bool = False


@dataclass(frozen=True)
class MultiprocessingSettings:
    """
    Settings for enabling and configuring multiprocessing.

    This class encapsulates the configuration for running tasks in parallel
    using multiprocessing. It allows setting the number of worker threads,
    and defining a timeout for each task.

    Attributes:
        max_workers (int | None): The maximum number of workers (threads)
            to use for multiprocessing. If `None`, the default thread pool size
            is used.
        timeout (int | None): The timeout (in seconds) for each task. If `None`,
            no timeout is applied.
    """

    max_workers: Optional[int] = None
    timeout: Optional[int] = None
    path_batch: int = 50


class _XSDataClassDefFinderVisitor(cst.CSTVisitor):
    """A visitor class to search for all class definitions in a CST module."""

    def __init__(self) -> None:
        self.defined_classes: Set[str] = set()
        self.class_trace: Deque[str] = deque([])

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Visit a class definition node and append to set of defined classes."""
        if not self.class_trace:
            self.defined_classes.add(node.name.value)
        self.class_trace.appendleft(node.name.value)

    def leave_ClassDef(self, _: cst.ClassDef) -> None:
        """Clear the currently visited `libcst.ClassDef` object."""
        self.class_trace.popleft()


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
        self.defined_class_names: Set[str] = set()

    def _is_relevant_model(self, class_node: cst.ClassDef) -> bool:
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
        is_valid_model = model_check.run_model_check(class_node)
        return is_valid_model

    def _add_class_to_refs(self, name: str) -> None:
        """
        Adds a `_ReferencedClass` object representing a class name to the
        reference set.
        """
        search: Optional[_LocalImportSearch] = None
        if _is_builtin_type(name):
            return None

        if name in self.defined_class_names or self.path is None:
            ref_class = _ReferencedClass(self.path, name)
        else:
            identifier = _ImportIdentifier.from_levels(_decompose_module(name))
            found_import = self.imports.find_common_import(identifier)

            if found_import is not None:
                module_from_file = self.imports.get_import(found_import)
                import_spec = _find_import_spec(module_from_file)
                if import_spec.irrelevant_module:
                    return None

                search = self._get_local_import(module_from_file, self.path)
                search.is_python_library = import_spec.third_party_import

            if found_import is None or (
                search is not None and search.referenced_class is None
            ):
                search = self._get_local_import_star(identifier, self.path)

            if (
                search is not None
                and search.referenced_class is None
                and search.is_python_library
            ):
                return None

            if search is not None and search.referenced_class is not None:
                ref_class = search.referenced_class
            else:
                ref_class = _ReferencedClass(self.path, identifier.value)
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

    def _get_local_import(
        self, identifier: _ImportIdentifier, path: Path
    ) -> _LocalImportSearch:
        """Retrieve a locally imported class as a `_LocalImportSearch`, if available."""
        local_import_search = _LocalImportSearch()
        path_from_module = identifier.module_to_path(path)
        if path_from_module is not None:
            local_import_search.referenced_class = _ReferencedClass(
                path_from_module, identifier.value
            )
        return local_import_search

    def _get_local_import_star(
        self, identifier: _ImportIdentifier, path: Path
    ) -> _LocalImportSearch:
        """Retrieve a locally imported class as a `_LocalImportSearch`, if available."""
        local_import_search = _LocalImportSearch()
        for star in self.imports.import_stars:
            star_module = _ImportIdentifier.from_levels(
                _decompose_module(star) + identifier.parts
            )
            import_spec = _find_import_spec(star_module)
            if (
                import_spec.is_python_library
                and not local_import_search.is_python_library
            ):
                local_import_search.is_python_library = True

            if import_spec.irrelevant_module:
                continue

            star_path = star_module.module_to_path(path)
            if star_path is not None:
                local_import_search.referenced_class = _ReferencedClass(
                    star_path, star_module.value
                )
                break
        return local_import_search

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
        # To ensure only top-level classes are parsed
        if not self.class_trace and self._is_relevant_model(node):
            span = self.get_metadata(PositionProvider, node)
            root_model = RootModel._from_cst_class(span, node, self.path)
            self.defined_classes.add(root_model)
            self.defined_class_names.add(node.name.value)

            # Check if any generated models are inherited
            self._get_inherited_local_classes(node)
        self.class_trace.appendleft(node)

    def leave_ClassDef(self, _: cst.ClassDef) -> None:
        """Clear the currently visited `libcst.ClassDef` object."""
        self.class_trace.popleft()

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        """Identify and process annotations within class definitions."""
        class_node = self.class_trace.popleft()
        self.class_trace.appendleft(class_node)
        if self.class_trace and self._is_relevant_model(class_node):
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


class _PendingPathsList(List[Future[None]]):
    """"""

    def __init__(
        self,
        paths: Generator[Path, None, None],
        thread: ThreadPoolExecutor,
        collected: _XSDataCollectedClasses,
        multiprocessing: MultiprocessingSettings,
        task_semaphore: Semaphore,
    ) -> None:
        super().__init__()
        self._paths = paths
        self._thread = thread
        self._collected = collected
        self._multiprocessing = multiprocessing
        self._task_semaphore = task_semaphore

    def remove_future(self, future: Future[None]) -> None:
        """"""
        self.remove(future)
        future.result(timeout=self._multiprocessing.timeout)
        self._task_semaphore.release()
        self.add_future()

    def add_future(self) -> None:
        """"""
        try:
            path = next(self._paths)
            future = self._thread.submit(
                self._collected.visit_and_consolidate_by_path, path
            )
            self._task_semaphore.acquire()
            self.append(future)
        except StopIteration:
            pass


class _AbstractPathResolver(ABC):
    """"""

    def __init__(self, directory_walk: bool, ignore_init: bool) -> None:
        self.directory_walk = directory_walk
        self.ignore_init = ignore_init

    @abstractmethod
    def get_python_files(self) -> Generator[Path, None, None]:
        """"""
        pass

    def _is_init_file(self, path: Path) -> bool:
        """"""
        return self.ignore_init and path.name == "__init__.py"

    def _find_directory_files(self, path: Path) -> Generator[Path, None, None]:
        """"""
        directory_files = (
            path.rglob("*.py") if self.directory_walk else path.glob("*.py")
        )
        for file in directory_files:
            if not self._is_init_file(file):
                yield file


class _CollectionPathResolver(_AbstractPathResolver):
    """"""

    def __init__(
        self, sources: Collection[StrOrPath], *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.sources = sources

    def get_python_files(self) -> Generator[Path, None, None]:
        """"""
        for source in self.sources:
            source_path = Path(source)
            if not source_path.exists():
                raise FileNotFoundError(
                    "If path is passed in as the source, it must link to an existing file"
                )

            if source_path.is_dir():
                source_nested_files = self._find_directory_files(source_path)
                for nested_file in source_nested_files:
                    yield nested_file
            elif not self._is_init_file(source_path):
                yield source_path


class _DirectoryPathResolver(_AbstractPathResolver):
    """"""

    def __init__(self, source: StrOrPath, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.source = source

    def get_python_files(self) -> Generator[Path, None, None]:
        """"""
        for nested_file in self._find_directory_files(Path(self.source)):
            yield nested_file


def _resolve_python_file_paths(
    sources: Union[StrOrPath, Collection[StrOrPath]],
    directory_walk: bool,
    ignore_init_files: bool,
) -> Generator[Path, None, None]:
    """"""
    resolver: _AbstractPathResolver
    common_args = (directory_walk, ignore_init_files)
    if isinstance(sources, Collection):
        resolver = _CollectionPathResolver(sources, *common_args)
    else:
        resolver = _DirectoryPathResolver(sources, *common_args)
    return resolver.get_python_files()


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
    sources: Union[StrOrPath, Collection[StrOrPath]],
    xsd_models: XsdModels = "dataclass",
    directory_walk: bool = False,
    ignore_init_files: bool = True,
    multiprocessing: Optional[MultiprocessingSettings] = None,
) -> Optional[List[RootModel]]:
    """
    Identify and return root models from multiple Python source files.

    A root model is a class that is defined in the given Python file but is
    not referenced within that file. This function analyzes one or more Python
    source files or directories and extracts all unreferenced classes that
    match the specified model type (e.g., dataclass, Pydantic, or attrs). It
    supports optional multiprocessing for parallel processing of files.

    Args:
        sources (`StrOrPath` | Collection[`StrOrPath`]): The source(s) to
            analyze. This can be a single directory as a path-like object,
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
        multiprocessing (`MultiprocessingSettings` | None): Settings to enable and
            configure multiprocessing. Defaults to None.

    Returns:
        Optional[List[`RootModel`]]: A list of `RootModel` instances representing
            unreferenced class definitions across all files, or `None` if no root
            models are found.
    """
    consolidated_classes = _XSDataCollectedClasses(xsd_models)

    # Normalize sources into a list of file paths
    paths = _resolve_python_file_paths(sources, directory_walk, ignore_init_files)
    if multiprocessing is None:
        for path in paths:
            consolidated_classes.visit_and_consolidate_by_path(path)
    else:
        task_semaphore = Semaphore(multiprocessing.path_batch)
        with ThreadPoolExecutor(multiprocessing.max_workers) as thread_executor:
            pending_tasks = _PendingPathsList(
                paths,
                thread_executor,
                consolidated_classes,
                multiprocessing,
                task_semaphore,
            )
            for _ in range(multiprocessing.path_batch):
                pending_tasks.add_future()

            while pending_tasks:
                for future in as_completed(pending_tasks[:]):
                    pending_tasks.remove_future(future)
    return consolidated_classes.root_finder()
