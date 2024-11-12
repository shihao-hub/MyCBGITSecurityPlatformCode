from abc import ABC, abstractmethod


# 抽象元素类
class Element(ABC):
    @abstractmethod
    def accept(self, visitor):
        pass


# 具体元素类A
class ElementA(Element):
    def __init__(self, value):
        self.value = value

    def accept(self, visitor):
        visitor.visit_element_a(self)


# 具体元素类B
class ElementB(Element):
    def __init__(self, value):
        self.value = value

    def accept(self, visitor):
        visitor.visit_element_b(self)


# 抽象访问者类
class Visitor(ABC):
    @abstractmethod
    def visit_element_a(self, element_a):
        pass

    @abstractmethod
    def visit_element_b(self, element_b):
        pass


# 具体访问者类A
class VisitorA(Visitor):
    def visit_element_a(self, element_a):
        print("VisitorA is visiting ElementA, value = ", element_a.value)

    def visit_element_b(self, element_b):
        print("VisitorA is visiting ElementB, value = ", element_b.value)


# 具体访问者类B
class VisitorB(Visitor):
    def visit_element_a(self, element_a):
        print("VisitorB is visiting ElementA, value = ", element_a.value)

    def visit_element_b(self, element_b):
        print("VisitorB is visiting ElementB, value = ", element_b.value)


# 对象结构类
class ObjectStructure:
    def __init__(self):
        self.elements = []

    def attach(self, element):
        self.elements.append(element)

    def detach(self, element):
        self.elements.remove(element)

    def accept(self, visitor):
        for element in self.elements:
            element.accept(visitor)


# 测试
if __name__ == "__main__":
    object_structure = ObjectStructure()
    element_a = ElementA("A")
    element_b = ElementB("B")
    object_structure.attach(element_a)
    object_structure.attach(element_b)
    visitor_a = VisitorA()
    visitor_b = VisitorB()
    object_structure.accept(visitor_a)
    object_structure.accept(visitor_b)
