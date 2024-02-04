import filecmp


class dircmp(filecmp.dircmp):
    """
    Compare the content of dir1 and dir2. In contrast with filecmp.dircmp, this
    subclass compares the content of files with the same path.
    """

    def phase3(self):
        """
        Find out differences between common files.
        Ensure we are using content comparison with shallow=False.
        """
        fcomp = filecmp.cmpfiles(self.left, self.right, self.common_files,
                                 shallow=True)
        self.same_files, self.diff_files, self.funny_files = fcomp


import os.path


def dir_is_same(dir1, dir2):
    """
    Compare two directory trees content.
    Return False if they differ, True is they are the same.
    """
    compared = dircmp(dir1, dir2, )
    if (compared.left_only or compared.right_only):
        print(compared.right_only)
        print(compared.left_only)
        return False
    for subdir in compared.common_dirs:
        if not dir_is_same(os.path.join(dir1, subdir), os.path.join(dir2, subdir)):
            return False
    return True


def file_is_same(dir1, dir2):
    """
    Compare two directory trees content.
    Return False if they differ, True is they are the same.
    """
    compared = dircmp(dir1, dir2, )
    if (compared.left_only or compared.right_only):
        print(compared.right_only)
        print(compared.left_only)
        return False
    for subdir in compared.common_dirs:
        if not dir_is_same(os.path.join(dir1, subdir), os.path.join(dir2, subdir)):
            return False
    return True


print(dir_is_same('data/inputs', 'data/outputs'))
