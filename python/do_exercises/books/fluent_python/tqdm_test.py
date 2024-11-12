import argparse
import time
import unittest

from itertools import cycle

from tqdm import tqdm


# for i in tqdm(range(1000)):
#     time.sleep(0.01)


def owns_cycle(iter_obj):
    while True:
        yield from iter_obj


class Test(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_for_owns_cycle(self):
        res = list("abcabcabcabc")
        sham = []
        cnt = 0
        for e in owns_cycle("abc"):
            cnt += 1
            sham.append(e)
            time.sleep(0.2)
            if cnt == len(res):
                break
        self.assertEqual(sham, res)


if __name__ == '__main__':
    unittest.main()

# if __name__ == '__main__':
#     parse = argparse.ArgumentParser("argparse test")
#
#     parse.add_argument("-a", metavar="A")
#     parse.add_argument("aaa")
#
#     args = parse.parse_args()
