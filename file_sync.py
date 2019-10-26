from os import walk
from os import makedirs
from os.path import exists
from os.path import getsize
from os.path import getctime
from os.path import join
from os.path import relpath
from argparse import ArgumentParser


class DirFileKey:

    def __init__(self, name, creation_time, size=None):
        self.name = name
        self.creation_time = creation_time
        self.size = size

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)): return NotImplemented
        return self.creation_time == other.creation_time and self.name == other.name and self.size == other.size

    def __str__(self) -> str:
        return f'{self.name}_{self.creation_time}_{self.size}'

    def __hash__(self) -> int:
        return hash((self.creation_time, self.name, self.size))


class DirFile:

    def __init__(self, base_path, relative_path, name, is_dir=None, is_file=None):
        self.relative_path = relative_path
        self.name = name

        full_path = join(base_path, relative_path, name)
        creation_time = getctime(full_path)
        if is_dir:
            self.key = DirFileKey(name, creation_time)
        elif is_file:
            size = getsize(full_path)
            self.key = DirFileKey(name, creation_time, size)

    def __hash__(self):
        return hash((self.relative_path, self.name))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.relative_path == other.relative_path and self.name == other.name

    def __str__(self):
        return join(self.relative_path, self.name)
        # return f'{self.relative_path}/{self.name}'

    def __repr__(self):
        # Needed for usage in tuples in list
        return self.__str__()


def get_directory_contents(base_path):
    dirs = []
    files = []
    for (dir_path, dir_names, file_names) in walk(base_path):
        if dir_path == base_path:
            relative_path = ''
        else:
            relative_path = relpath(dir_path, base_path)
        dirs.extend([DirFile(base_path, relative_path, dir_name, is_dir=True) for dir_name in dir_names])
        files.extend([DirFile(base_path, relative_path, file_name, is_file=True) for file_name in file_names])

    return dirs, files


def check_duplicate_names(dir_files, names):
    if len(names) != len(dir_files):
        for name in names:
            first = None
            for dir_file in dir_files:
                if name == dir_file.name:
                    if first is None:
                        first = dir_file
                    else:
                        raise Exception(f'Directory/File with same name found: {first} and {dir_file}')
        raise Exception('Names and dir_files lengths don\'t match, but unable to find duplicate name')


def find_missing_and_moved(src, dest):
    dest_set = set(dest)
    dest_name_to_dirfile_map = {dir_file.name: dir_file for dir_file in dest}
    check_duplicate_names(dest, dest_name_to_dirfile_map)

    missing = []
    moved = []  # Array of tuples, original and new path
    for dir_file in src:
        if dir_file not in dest_set:
            if dir_file.name in dest_name_to_dirfile_map:
                moved.append((dir_file, dest_name_to_dirfile_map[dir_file.name]))
            else:
                missing.append(dir_file)

    return missing, moved


def find_deleted(src, dest):
    src_name_set = {dir_file.name for dir_file in src}
    check_duplicate_names(src, src_name_set)

    deleted = []

    for dir_file in dest:
        if dir_file.name not in src_name_set:
            deleted.append(dir_file)

    return deleted


def get_changes(src, dest):
    src_dirs, src_files = get_directory_contents(src)
    dest_dirs, dest_files = get_directory_contents(dest)

    missing_dirs, moved_dirs = find_missing_and_moved(src_dirs, dest_dirs)
    missing_files, moved_files = find_missing_and_moved(src_files, dest_files)
    deleted_dirs = find_deleted(src_dirs, dest_dirs)
    deleted_files = find_deleted(src_files, dest_files)

    return missing_dirs, missing_files, moved_dirs, moved_files, deleted_dirs, deleted_files


def print_list(title, to_print):
    print('---------------------------------------------------------------')
    print(title)
    print('---------------------------------------------------------------')
    for item in to_print:
        print(item)
    print('---------------------------------------------------------------\n\n')


def create_directory(dir_path):
    if not exists(dir_path):
        makedirs(dir_path)
        print(f'Directory created: {dir_path}')
    else:
        print(f'Error: directory {dir_path} already exists, cannot create new directory')


def create_required_directories(dest, missing, moved):
    print('Creating required directories')
    for dir_file in missing:
        dir_path = join(dest, str(dir_file))
        # dir_path = f'{dest}{str(dir_file)}'
        create_directory(dir_path)
    for (new_dir_file, orig_dir_file) in moved:
        dir_path = join(dest, str(new_dir_file))
        # dir_path = f'{dest}{str(new_dir_file)}'
        create_directory(dir_path)
    print('\n\n')


def main(src, dest, delete_move_dir_path, sync):
    # TODO: get directory hashes

    missing_dirs, missing_files, moved_dirs, moved_files, deleted_dirs, deleted_files = get_changes(src, dest)

    print_list('Missing dirs', missing_dirs)
    print_list('Missing files', missing_files)
    print_list('Moved dirs', moved_dirs)
    print_list('Moved files', moved_files)
    print_list('Deleted dirs', deleted_dirs)
    print_list('Deleted files', deleted_files)

    if sync:
        if delete_move_dir_path is None:
            delete_move_dir_path = join(dest, 'deleted')  # '/home/sarthak/file_sync_test/test/deleted'
            if not exists(delete_move_dir_path):
                create_directory(delete_move_dir_path)

        create_required_directories(dest, missing_dirs, moved_dirs)

    # TODO: compare new directory hash


if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument('--src', type=str, required=True, help='Source directory to sync from')
    parser.add_argument('--dest', type=str, required=True, help='Destination directory to sync to')
    parser.add_argument('--delete-dir', type=str, default=None, help='Destination directory to sync to. Directory with the name "deleted" in dest by default')
    parser.add_argument('--sync', type=bool, default=False, help='Sync the actual files otherwise just print the changes')
    args = parser.parse_args()
    main(args.src, args.dest, args.delete_dir, args.sync)
