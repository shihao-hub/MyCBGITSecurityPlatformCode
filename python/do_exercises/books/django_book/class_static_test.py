from django.utils.decorators import classonlymethod
from django.views import View
from django.views.generic import DetailView
from django.views.generic import ListView


class Dog:
    def __init__(self):
        self.a = "a"

    def fn(self, *args):
        print(self, args)

    @property
    def s_fn(*args):
        print(args)
        pass

    @classmethod
    def c_fn(cls, *args):
        print(cls, args)

    class_value = c_fn


dog = Dog()
print(vars(dog)) # 等价于调用 __dict__
# dog.fn(1, 2, 3)
# Dog.s_fn(1, 2, 3)
print(type(dog.s_fn))
# Dog.c_fn(1, 2, 3)
# print(Dog.as_view())

print(dog.class_value)
dog.class_value = 1
print(dog.class_value)
print(Dog.class_value)

# print(dog.__class__.__name__)
# print(dog.__dict__)
# print(dog.__name__)
