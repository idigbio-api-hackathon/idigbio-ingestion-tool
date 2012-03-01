/**
 * Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida 
 * This software may be used and distributed according to the terms of the MIT
 * license: http://www.opensource.org/licenses/mit-license.php
 */
package idigbio.storage.dataingestion;

import javax.swing.SwingUtilities;
import javax.swing.UIManager;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.javabuilders.swing.SwingJavaBuilder;

public class ClientApp {
    private static final Logger logger = LoggerFactory.getLogger(ClientApp.class);

    public static void main(String[] args) {
        SwingUtilities.invokeLater(new Runnable() {
            public void run() {
                // activate internationalization
                SwingJavaBuilder.getConfig().addResourceBundle("idigbio.storage.dataingestion.ClientApp");
                try {
                    UIManager.setLookAndFeel(UIManager
                            .getSystemLookAndFeelClassName());
                    new FileDropFrame().setVisible(true);
                    logger.info("ClientApp initialized.");
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        });
    }

}