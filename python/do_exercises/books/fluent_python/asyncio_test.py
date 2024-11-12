import cgi
import collections
import pprint

CommonConfig = collections.namedtuple("CommonConfig", "name base_url path")
config = [
    CommonConfig("get", "http://127.0.0.1/", "courses"),
    CommonConfig("get", "http://127.0.0.1/", "courses/1"),
    CommonConfig("post", "http://127.0.0.1/", "courses"),
    CommonConfig("put", "http://127.0.0.1/", "courses/1"),
    CommonConfig("delete", "http://127.0.0.1/", "courses/1"),
]

# a = 1
# print(f"{{a}}") # a

pprint.pprint([str(e) for e in config])


class Dispatcher:
    def __init__(self):
        # <option,function>
        self.choices = {}

    def not_allowed_method(self, *args, **kwargs):
        raise TypeError(f"不存在这个选项，对话终止")

    def __call__(self, *args, **kwargs):
        if "option" not in kwargs:
            raise KeyError(f"option")

        option = kwargs["option"]

        handler = self.choices.get(option, None)
        if not handler:
            handler = self.not_allowed_method
        return handler(*args, **kwargs)

    def register(self, option, function):
        self.choices[option] = function
        return function
