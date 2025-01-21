from __future__ import annotations

from os import PathLike
import os
from collections import deque
from collections.abc import Collection
from pathlib import Path
from dataclasses import dataclass, field
from concurrent.futures import as_completed, Future, ThreadPoolExecutor
from typing import (
    Callable,
    Deque,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    TypeAlias,
    Union
)

import libcst as cst
from libcst.metadata import CodeRange, MetadataWrapper, PositionProvider
from pathvalidate import validate_filepath, ValidationError

# Typealiases
_ModuleType: TypeAlias = Union[cst.Name, cst.Attribute]

PythonSource: TypeAlias = Union[str, Path]
GenModels: TypeAlias = Literal[
    'dataclass', 'pydantic', 'attrs'
]

# Constants and global variables
_MAX_RETRIES = 3

def _is_dataclass_model(node: cst.ClassDef) -> bool:
    """
    Private function to determine if a `libcst.ClassDef` object is a
    dataclass.
    """
    return (
        _parse_imported_module(decorator.decorator).value == "dataclass"
        for decorator in node.decorators
    )


def _is_pydantic_model(node: cst.ClassDef) -> bool:
    """
    Private function to determine if a `libcst.ClassDef` object is a
    `pydantic.BaseModel`.
    """
    return any(
        _parse_imported_module(base_class.value).value == 'BaseModel'
        for base_class in node.bases
    )


def _is_attrs_model(node: cst.ClassDef) -> bool:
    """
    Private function to determine if a `libcst.ClassDef` object is a
    `attrs.s`.
    """
    return any(
        _parse_imported_module(decorator.decorator).module == 'attrs.s'
        for decorator in node.decorators
    )


def _parse_imported_module(module: _ModuleType) -> _ImportIdentifier:
    """Parse a module node to extract its full module path as an `_ImportIdentifier`."""
    module_levels: List[str] = list()
    module_objects: Deque[_ModuleType] = deque([module])
    while module_objects:
        cur_module_level = module_objects.popleft()
        if isinstance(cur_module_level, cst.Name):
            module_levels.append(cur_module_level.value)
        else:
            module_objects.extend(
                [cur_module_level.attr, cur_module_level.value]
            )

    return _ImportIdentifier.from_levels(module_levels)


def _root_finder(defs: Set[RootModel], refs: Set[str]) -> Optional[List[RootModel]]:
    """
    A private function to identify and return root models from one
    or multiple Python source files.
    """
    root_classes = [
        root_model for root_model in defs
        if root_model.full_module not in refs
    ]
    return None if not root_classes else root_classes


def _create_module_from_levels(levels: List[str]) -> str:
    """Combine module levels into a single dotted module path."""
    return '.'.join(levels)


def _find_all_types_in_subscript(subscript: cst.Subscript, module: Optional[str]) -> Set[str]:
    """
    A private function that returns a set of class names found
    within a `libcst.Subscript` object. Traverses recursively through
    the entire object to find all references to classes.
    """
    classes_found: Set[str] = set()

    def add_module(name: str) -> str:
        res = name if module is None else module + name
        classes_found.add(res)

    def traversal(slice_index: cst.Index) -> None:
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
            add_module(slice_index_value.attr.value)

        # Simply extract the value if object is a cst.Name
        elif isinstance(slice_index_value, cst.Name):
            add_module(slice_index_value.value)

        # If there is a reference to a class as a string, due
        # to TYPE_CHECKING, then strip the value of extra
        # quotations and add to set of classes encountered
        elif isinstance(slice_index_value, cst.SimpleString):
            add_module(slice_index_value.value.strip('"'))

    for sub_element in subscript.slice:
        traversal(sub_element.slice)

    return classes_found


class XSDataRootFinderError(Exception):
    """Custom exception for errors in the XSData root-finding process."""
    def __init__(self, message: str, source: Path) -> None:
        self.message = message
        self.source = source

    def __str__(self) -> str:
        return repr(self)
    
    def __repr__(self) -> str:
        return self.message


@dataclass
class _XSDataCollectedClasses:
    """
    A private data structure to track and consolidate defined and referenced
    classes.
    """
    gen_model: GenModels
    refs: Set[str] = field(default_factory=set)
    defs: Set[str] = field(default_factory=set)
    
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
    
    def visit_and_consolidate(self, source: PythonSource) -> None:
        """Process and consolidate data from a source file, either a str or Path."""
        visitor =  _python_source_visit(source, self.gen_model)
        self._consoildate_classes(visitor)

    def visit_and_consolidate_by_path(self, source: PathLike) -> None:
        """Process and consolidate data from a source file specified as a PathLike object."""
        print(source)
        if not isinstance(source, PathLike):
            raise TypeError("'source' argument must be a PathLike object")

        self.visit_and_consolidate(source)
    

@dataclass(frozen=True)
class _ImportIdentifier:
    """Represents a module-level import identifier with optional attributes."""
    value: str
    attribute: Optional[str] = None

    @property
    def module(self) -> str:
        """"""
        return (
            self.value if self.attribute is None
            else self.attribute + self.value
        )

    @classmethod
    def from_levels(cls, levels: List[str]) -> _ImportIdentifier:
        """"""
        if len(levels) == 1:
            module = _create_module_from_levels(levels)
            return cls(module)
        else:
            attribute = _create_module_from_levels(levels[:-1])
            value = levels[-1]
            return cls(value, attribute)


@dataclass(frozen=True)
class RootModel:
    """Represents the root model for an unreferenced class in a module."""
    module: Optional[str]
    name: str
    start_line_no: int
    end_line_no: int

    @property
    def full_module(self) -> str:
        """Return the full module path of the root model, including its name."""
        return (
            self.name
            if self.module is None else self.module + self.name
        )

    @classmethod
    def from_cst_class(
        cls, span: CodeRange, node: cst.ClassDef, module: Optional[str]
    ) -> RootModel:
        """Create a `RootModel` instance from a `cst.ClassDef` and its metadata."""
        class_name = node.name.value
        start_line = span.start.line
        end_line = span.end.line
        return cls(
            module, class_name, start_line, end_line
        )


@dataclass(frozen=True)
class MultiprocessingSettings:
    """Settings for enabling and configuring multiprocessing."""
    enabled: bool = False
    max_workers: Optional[int] = None
    timeout: Optional[int] = None


class _XSDataRootFinderVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    """Visitor class to parse and extract class references from Python source."""
    def __init__(self, gen_model: GenModels, module: Optional[str]) -> None:
        self.gen_model = gen_model
        self.module = module
        self.class_trace: Deque[cst.ClassDef] = deque([])
        self.ref_classes: Set[str] = set()
        self.defined_classes: Set[RootModel] = set()

    def _is_relevant_model(self) -> bool:
        """
        A private function that determines if a given `libcst.ClassDef`
        object is a class that was generated by `xsdata`.
        """
        MODELS_CHECKS: Dict[GenModels, Callable[[cst.ClassDef]], bool] = {
            'dataclass': _is_dataclass_model,
            'pydantic': _is_pydantic_model,
            'attrs': _is_attrs_model
        }

        model_func = MODELS_CHECKS.get(self.gen_model)
        if model_func is None:
            raise ValueError(
                "'gen_model' must be one of ('dataclass', 'pydantic', 'attrs')"
            )

        class_node = self.class_trace.popleft()
        self.class_trace.appendleft(class_node)
        return model_func(class_node)
    
    def _add_class_to_ref(self, name: str) -> None:
        """"""
        module = name if self.module is None else self.module + name
        self.ref_classes.add(module)

    def _attribute_ann_assign(self, node: cst.Attribute) -> None:
        """Handle annotations that are qualified names (e.g., module.Class)."""
        class_name = node.attr.value
        self._add_class_to_ref(class_name)

    def _name_ann_assign(self, node: cst.Name) -> None:
        """Handle annotations that are simple names (e.g., int, MyClass)."""
        class_name = node.value
        self._add_class_to_ref(class_name)

    def _subscript_ann_assign(self, node: cst.Subscript) -> None:
        """Handle annotations that are subscripted types (e.g., List[int])."""
        classes_found = _find_all_types_in_subscript(node, self.module)
        self.ref_classes.update(classes_found)

    def _simple_string_ann_assign(self, node: cst.SimpleString) -> None:
        """Handle annotations represented as simple strings (e.g., "MyClass")."""
        class_name = node.value.strip('"')
        self._add_class_to_ref(class_name)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Set the currently visited class definition."""
        if not self.class_trace:
            span = self.get_metadata(PositionProvider, node)
            root_model = RootModel.from_cst_class(span, node, self.module)
            self.defined_classes.add(root_model)
        
        self.class_trace.appendleft(node)
    
    def leave_ClassDef(self, _: cst.ClassDef) -> None:
        """Clear the currently visited class definition."""
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


def _read_python_file(source: PythonSource) -> str:
    """
    A private function to read and return the content of a Python file or
    validate input as a source.
    """
    if os.path.isfile(source):
        with open(source, "r") as py_file:
            python_file = py_file.read()

        return python_file

    try:
        py_source_as_path = Path(source)
        validate_filepath(file_path=py_source_as_path)
    except ValidationError:
        pass
    else:
        raise FileNotFoundError(
            "If path is passed in as the source, it must link to an existing file"
        )
    return source


def _python_source_visit(source: PythonSource, gen_model: GenModels) -> _XSDataRootFinderVisitor:
    """Parse a Python source file and extract class definitions and references."""
    source = _read_python_file(source)
    python_module = MetadataWrapper(cst.parse_module(source))
    module_name = None if not os.path.isfile(source) else Path(source).stem
    visitor = _XSDataRootFinderVisitor(gen_model, module_name)
    python_module.visit(visitor)
    return visitor


def root_finder(source: PythonSource, gen_model: GenModels = 'dataclass') -> Optional[List[RootModel]]:
    """Identify and return root models from a single Python source file."""
    visitor = _python_source_visit(source, gen_model)
    return visitor.root_finder()


def root_finders(
    sources: Collection[PathLike],
    gen_model: GenModels = 'dataclass',
    multiprocessing: MultiprocessingSettings = MultiprocessingSettings()
) -> Optional[List[RootModel]]:
    """Identify and return root models from multiple Python source files."""
    consolidated_classes = _XSDataCollectedClasses(gen_model)
    if multiprocessing.enabled:
        with ThreadPoolExecutor(multiprocessing.max_workers) as thread_executor:
            futures: Dict[Future, str] = {
                thread_executor.submit(
                    consolidated_classes.visit_and_consolidate_by_path, source
                ): source
                for source in sources
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
                            "Task was not completed succesfully", fut_source
                        ) from e
    else:
        for source in sources:
            consolidated_classes.visit_and_consolidate_by_path(source)

    return consolidated_classes.root_finder()