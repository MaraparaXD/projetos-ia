"""OS-managed local lock: automatically released if the CLI process dies."""
from contextlib import contextmanager
import os
from pathlib import Path


@contextmanager
def execution_lock(root: Path):
    path = root / 'runtime.lock'
    if path.is_symlink():
        raise PermissionError('Lock não pode ser link simbólico.')
    with path.open('a+b') as fd:
        fd.seek(0, 2)
        if fd.tell() == 0:
            fd.write(b'0')
            fd.flush()
        fd.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise PermissionError('Outra execução deste projeto está ativa.') from exc
        try:
            yield
        finally:
            fd.seek(0)
            if os.name == 'nt':
                msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
