package cn.edu.seu.core_java_volume;

import java.awt.*;
import java.io.*;
import javax.swing.*;

public class ImageViewer {
    public static void main(String[] args) {
        EventQueue.invokeLater(() -> {
            var frame = new ImageViewerFrame();

            frame.setTitle("ImageViewer");
            frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            frame.setVisible(true);
        });
    }
}

class ImageViewerFrame extends JFrame {
    private static final int DEFAULT_WIDTH = 300;
    private static final int DEFAULT_HEIGHT = 400;

    public static String getPathOfJFileChooser(JFileChooser chooser) {
        return chooser.getSelectedFile().getPath();
    }

    public ImageViewerFrame() throws HeadlessException {
        setSize(DEFAULT_WIDTH, DEFAULT_HEIGHT);

        // 用 label 展示图片
        var label = new JLabel();
        add(label);

        // 文件选择器
        var chooser = new JFileChooser();
        chooser.setCurrentDirectory(new File("."));

        // 菜单栏
        var menuBar = new JMenuBar();
        setJMenuBar(menuBar);

        var file_menu = new JMenu("File");
        menuBar.add(file_menu);

        var openItem = new JMenuItem("Open");
        file_menu.add(openItem);
        openItem.addActionListener(event -> {
            int res = chooser.showOpenDialog(null);
            if (res == JFileChooser.APPROVE_OPTION) {
                String name = getPathOfJFileChooser(chooser);
                label.setIcon(new ImageIcon(name));
            }
        });

        var exitItem = new JMenuItem("Exit");
        file_menu.add(exitItem);
        exitItem.addActionListener(event -> System.exit(0));
    }
}
