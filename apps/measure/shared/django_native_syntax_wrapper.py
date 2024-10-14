import collections
import json

from django.core.serializers import serialize


def _django_serialize_one(one_qs):
    if isinstance(one_qs, collections.Iterable):
        raise Exception("one_qs 不能是 iterable！")

    res = {}
    data = json.loads(serialize("json", [one_qs]))[0]
    res.update({"id": data.get("pk")})
    res.update(data.get("fields"))
    return res


def django_serialize(queryset, many=False):
    """ 个人封装的 django json
        many=False, 返回单个实例转成的 dict
        many=True, 返回一个列表
    """
    if not many:
        return _django_serialize_one(queryset)
    return [_django_serialize_one(e) for e in queryset]
