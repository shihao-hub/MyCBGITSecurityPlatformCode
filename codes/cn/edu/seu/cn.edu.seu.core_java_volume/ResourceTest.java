package cn.edu.seu.core_java_volume;

import java.util.Arrays;
import java.util.Scanner;

public class ResourceTest {
    public static void main(String[] args) throws ClassNotFoundException {
        var resourceCls = ResourceTest.class;
        // 查找资源从 package 目录下找，解释一下下面这个的含义。
        //      cn.edu.seu.core_java_volume -> ./
        //      cn.edu.seu -> ../
        //      cn.edu -> ../../
        //      cn -> ../../../
        //      . -> ../../../../
        var url = resourceCls.getResource("../../../../img.png");
        System.out.println(url);

        // 用户输入类名，程序输入该类中所有的方法和构造器的签名
        System.out.println("请输入正确的类名");
        var scanner = new Scanner(System.in);
        var className = scanner.next();
        var cls = Class.forName(className);
        System.out.println(cls.getSuperclass());
        System.out.println(cls.getModifiers());
        System.out.println(Arrays.toString(cls.getDeclaredConstructors()));
    }
}
