package cn.edu.seu.core_java_volume;

import java.awt.*;
import java.io.*;
import javax.swing.*;

public class ImageViewer {
    public static final int START_X = 600;
    public static final int START_Y = 300;

    public static void main(String[] args) {
        EventQueue.invokeLater(() -> {
            var frame = new ImageViewerFrame();

            frame.setTitle("ImageViewer");
            frame.setBounds(START_X, START_Y, ImageViewerFrame.DEFAULT_WIDTH, ImageViewerFrame.DEFAULT_HEIGHT);
            frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            frame.setVisible(true);
        });
    }
}

class ImageViewerFrame extends JFrame {
    public static final int DEFAULT_WIDTH = 300;
    public static final int DEFAULT_HEIGHT = 400;

    public static String getPathOfJFileChooser(JFileChooser chooser) {
        return chooser.getSelectedFile().getPath();
    }

    public ImageViewerFrame() throws HeadlessException {
        setSize(DEFAULT_WIDTH, DEFAULT_HEIGHT);

        // 用 label 展示图片
        var imageLabel = new JLabel();
        add(imageLabel);

//        var textLabel = new JLabel();
//        add(textLabel);
//        textLabel.setText("\u2122\u2122\u2122\u2122");

        // 文件选择器
        var chooser = new JFileChooser();
        chooser.setCurrentDirectory(new File("./src/main/resources"));

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
                var image = new ImageIcon(name);
                imageLabel.setIcon(image);
                int offsetX = 10, offsetY = 30;
                setSize(image.getIconWidth() + offsetX, image.getIconHeight() + offsetY);
            }
        });

        var exitItem = new JMenuItem("Exit");
        file_menu.add(exitItem);
        exitItem.addActionListener(event -> System.exit(0));
    }
}
