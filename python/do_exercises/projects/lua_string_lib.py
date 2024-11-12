import functools
import numbers
import re
import types
from typing import Pattern, AnyStr, Dict, List
from types import FunctionType


def find(s: str, pattern: Pattern[AnyStr], init: int = 0, plain=False):
    """

    :param s: 被搜索串
    :param pattern: 正则模式串
    :param init: 开始查找的位置
    :param plain: True->不是正则匹配，False->是正则匹配
    :return: 如果找到匹配的串则返回两个值：匹配串的开始索引和结束索引，否则返回 None
    """
    if plain:
        pos = s.find(pattern.pattern, init)
        if pos == -1:
            return None
        else:
            return pos, pos + len(pattern.pattern) - 1
    else:
        m = pattern.search(s, pos=init)
        if m is None:
            return None
        return m.start(), m.end() - 1


def match(s: str, pattern: Pattern[AnyStr], init=0):
    """
    和 find 区别似乎不是太大，主要 match 的返回值是捕获的结果或者是整个配对字符串
    :param s:
    :param pattern:
    :param init: 开始查找的位置
    :return: 成功配对时，会返回配对表达式中的所有捕获结果。
    如果没有设置捕获标记，则返回整个配对字符串。
    没有成功匹配时，返回 None
    """
    m = pattern.search(s, pos=init)
    if m is None:
        return None
    groups = m.groups()
    return len(groups) == 0 and m.group() or groups


def gmatch(s: str, pattern: Pattern[AnyStr]):
    """
    找出所有匹配的结果，返回一个迭代器。
    :param s:
    :param pattern:
    :return:
    """
    for e in pattern.finditer(s):
        yield e.groups()


def gsub(s: str, pattern: Pattern[AnyStr], repl, m=None) -> str:
    """
    Q1: C语言处理长字符串性能较高，用 Python 处理的话是不是会凭空耗费很多空间呢？
        假如说，我存储26个字母的地址，那是不是再怎么也消耗不了多少空间？不太对吧？
    N1: 在 Python 中，我们通常不需要检查某个对象的类型，只需要关注它能不能具备像字符串或列表那样的方法和属性，
        这就是著名的鸭子检验。因此，只需要使用 isinstance 即可。
        如果想显式地检查给定对象是否属于某一特定类型(而不是它的子类)，可以使用 type，
        但通常用这样的语句 type(var) is some_type，而不是 type(var) == some_type。
        记住，编写函数的时候，不检查对象类型，是Python的惯例，不要把 Java 的习惯带过来。


    返回一个替换后的副本，原串中的所有符合参数 pattern 的子串都将被 repl 所指定的字符串所替代；
    如果指定了 m， 则只会替换前 m 个匹配的字串；
    repl -> str, dict, function
    str -> 成功会直接替换（此处功能还不够完整）
    dict -> 根据匹配到的子串作为键，在 repl 中搜索，如果不存在，则以整个字符串为键，如果这个也没有，必须抛出异常
    function -> 以匹配到的子串作为函数的参数，匹配不成功时会以整个字符串为参数。
    如果返回 False 或者 None，则替换不会发生；
    如果返回 数字 或者 字符串，则直接替换；
    如果返回其他类型，报错
    :param s:
    :param pattern:
    :param repl:
    :param m:
    :return:
    """
    if not isinstance(repl, str) \
            and not isinstance(repl, dict) \
            and not isinstance(repl, types.FunctionType):
        raise RuntimeError("FIXME")

    # 下面这两个是未实现的内容
    if m is not None:
        raise RuntimeError("TODO")
    if isinstance(repl, types.FunctionType):
        raise RuntimeError("TODO")

    replace_pos_list: List[tuple] = []
    for e in pattern.finditer(s):
        replace_pos_list.append((e.start(), e.end() - 1))

    rep_list = None
    if isinstance(repl, dict):
        rep_list = [repl.get(s[e[0]:(e[1] + 1)], repl[s]) for e in replace_pos_list]
    elif isinstance(repl, types.FunctionType):
        def fn_type_relative(_ret, _rep_list, _e):
            if isinstance(_ret, str) or isinstance(_ret, (int, float)):
                _rep_list.append(str(_ret))
            elif _ret is False or _ret is None:
                _rep_list.append(_e)
            else:
                raise RuntimeError("规约错误，不允许出现其他类型")

        rep_list = []
        # 下面这部分有点奇怪
        # if len(replace_pos_list) == 0:
        #     ret = repl(s)
        #     fn_type_relative(ret, rep_list, s)

        for e in replace_pos_list:
            ret = repl(e)
            fn_type_relative(ret, rep_list, e)
    res = []
    end_pos = len(replace_pos_list) + 1
    if m is not None:
        end_pos = min(m + 1, end_pos)
    for i in range(end_pos):
        rpl = replace_pos_list
        if i == end_pos - 1:
            res.append(s[(rpl[i - 1][1] + 1):])
            break
        if i == 0:
            res.append(s[:rpl[i][0]])
        else:
            res.append(s[(rpl[i - 1][1] + 1):rpl[i][0]])
        if rep_list is not None:
            res.append(rep_list[i])
        else:
            res.append(repl)
    return "".join(res)


if __name__ == '__main__':
    print(find("abca", re.compile("a"), init=1, plain=True))
    print()
    print(find("abca", re.compile("abc"), init=0, plain=False))
    print()
    print(match("ac1bc123", re.compile(r"[a-zA-Z][a-zA-Z]\d"), init=0))
    print()
    print("---")
    end = False
    try:
        next(gmatch("a", re.compile(r"([a-zA-Z])(\d)")))
    except StopIteration as e:
        print(repr(e))
        print(123)
        end = True
    print("end = {}".format(end))
    for k, v in gmatch("a1b1c1d12222222e2", re.compile(r"([a-zA-Z])(\d)")):
        print(k, v)
    print("---")
    print()
    print(gsub("abc1abc1abc1abc1def2g", re.compile(r"[a-zA-Z][a-zA-Z][a-zA-Z]"), {
        "abc": "cba",
        "abc1abc1abc1abc1def2g": "[:]"
    }))
    print()
    print(type(1.1))
    print(type(1))
    print(type((123 + 0j)))
