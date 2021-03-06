# This source code is part of the Biotite package and is distributed
# under the 3-Clause BSD License. Please see 'LICENSE.rst' for further
# information.

from typing import Union, List, Tuple, overload
from ...atoms import AtomArray, AtomArrayStack
from ....file import TextFile


class PDBFile(TextFile):
    @overload
    def get_structure(
        self,
        model: None = None,
        insertion_code: List[Tuple[int, str]] = [],
        altloc: List[Tuple[int, str]] = [],
        extra_fields: List[str] = []
    ) -> AtomArrayStack: ...
    @overload
    def get_structure(
        self,
        model: int,
        insertion_code: List[Tuple[int, str]] = [],
        altloc: List[Tuple[int, str]] = [],
        extra_fields: List[str] = []
    ) -> AtomArray: ...
    def set_structure(
        self,
        array: Union[AtomArrayStack, AtomArray]
    ) -> None: ...
