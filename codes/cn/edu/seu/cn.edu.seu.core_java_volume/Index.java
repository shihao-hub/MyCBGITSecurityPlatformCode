package cn.edu.seu.core_java_volume;

import java.util.*;

public class Index {
    private static String _toStringOfList(List<?> list) {
        var res = new StringBuilder();
        res.append("[");
        for (Object o : list) {
            res.append(o.toString());
            res.append(", ");
        }
        res.append("]");
        if (!list.isEmpty()) {
            res.delete(res.length() - 3, res.length() - 1);
        }
        return res.toString();
    }

    private static String _toStringOfMap(Map<?, ?> map) {
        var res = new StringBuilder();
        res.append(map);
        return res.toString();
    }
    

    public static String toString(Object obj) {
        var cls = obj.getClass();
        if (Arrays.stream(cls.getInterfaces()).anyMatch(v -> v == List.class)) {
            return _toStringOfList((List<?>) obj);
        } else if (Arrays.stream(cls.getInterfaces()).anyMatch(v -> v == Map.class)) {
            return _toStringOfMap((Map<?, ?>) obj);
        }
        return obj.toString();
    }

    private static <K, V> void _checkArguments(Map<K, V> map, List<K> keys, List<V> values) {
        if (keys.size() != values.size()) {
            throw new IllegalArgumentException("参数 keys 和 values 的长度不一致");
        }
    }

    public static <K, V> Map<K, V> mapPutAll(Map<K, V> map, List<K> keys, List<V> values) {
        _checkArguments(map, keys, values);

        for (int i = 0; i < keys.size(); ++i) {
            map.put(keys.get(i), values.get(i));
        }
        return map;
    }

    public enum Size {
        SMALL, MEDIUM, LARGE, EXTRA_LARGE
    }

    public static void main(String[] args) {
        class Local {
            Map<String, Object> generateSOMap() {
                Map<String, Object> map = new HashMap<>();
                map.put("1", new ArrayList<String>());
                map.put("2", mapPutAll(new HashMap<>(), List.of("1", "2", "3"), List.of("111", "222", "333")));
                map.put("3", null);
                map.put("4", 1);
                map.put("5", "String");
                return map;
            }

            Map<String, String> generateSSMap() {
                Map<String, String> map = new HashMap<>();
                // 泛型，KV，编译期检测
                mapPutAll(map, List.of("1", "2", "3"), List.of("111", "222", "333"));
                return map;
            }
        }

        // 局部内部类非常时候代码重构！举个例子，Local 类中的函数只能直接使用当前函数中的 final 变量！多好。
        var local = new Local();

        // JDK 10 后支持类型推断，方便太多了！
        var ssMap = local.generateSSMap();
        System.out.println(ssMap);

        var soMap = local.generateSOMap();
        System.out.println(soMap);

        var small = Size.SMALL;
        System.out.println(small);
        System.out.println(small.getClass());

        System.out.println(toString(new ArrayList<>(List.of(1, 2))));
        System.out.println(toString(mapPutAll(new HashMap<>(), List.of(1, 2, 3), List.of(11, 22, 33))));
    }
}


