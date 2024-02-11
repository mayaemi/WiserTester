import argparse
import filecmp
import os
import shutil


class DirUtilities:
    class dircmp(filecmp.dircmp):
        def phase3(self):
            fcomp = filecmp.cmpfiles(self.left, self.right, self.common_files, shallow=False)
            self.same_files, self.diff_files, self.funny_files = fcomp

    @staticmethod
    def dir_is_same(dir1, dir2):
        compared = DirUtilities.dircmp(dir1, dir2)
        if compared.left_only or compared.right_only:
            print(compared.right_only)
            print(compared.left_only)
            return False
        return all(
            DirUtilities.dir_is_same(os.path.join(dir1, subdir), os.path.join(dir2, subdir)) for subdir in compared.common_dirs
        )

    @staticmethod
    def clear_directories(directories):
        for directory in directories:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            print(f"Cleared {directory}")

    @classmethod
    def run(cls):
        parser = argparse.ArgumentParser(description="Utilities for directory comparison and management.")
        parser.add_argument("--compare", nargs=2, help="Compare two directories.")
        parser.add_argument("--clear", nargs="+", help="Clear specified directories.")
        args = parser.parse_args()

        if args.compare:
            dir1, dir2 = args.compare
            is_same = cls.dir_is_same(dir1, dir2)
            print(f"Directories are {'the same' if is_same else 'different'}.")

        if args.clear:
            cls.clear_directories(args.clear)


if __name__ == "__main__":
    DirUtilities.run()


"""
example usage commands
python utilities.py --compare "data/expectations" "data/outputs" 
python utilities.py --clear "data/comparison_reports" "data/outputs" 
"""
