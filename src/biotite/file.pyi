# This source code is part of the Biotite package and is distributed
# under the 3-Clause BSD License. Please see 'LICENSE.rst' for further
# information.

from typing import Generic, TypeVar, Union, TextIO, BinaryIO
from .copyable import Copyable


_T_io = TypeVar("_T_io", TextIO, BinaryIO)

class File(Copyable, Generic[_T_io]):
    def __init__(self) -> None: ...
    def read(self, file: Union[str, _T_io]) -> None: ...
    def write(self, file: Union[str, _T_io]) -> None: ...

class TextFile(File[TextIO]):
    def __init__(self) -> None: ...
    def read(self, file: Union[str, TextIO]) -> None: ...
    def write(self, file: Union[str, TextIO]) -> None: ...
    def __str__(self) -> str: ...

class InvalidFileError(Exception):
    ...