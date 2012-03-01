/**
 * Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
 * This software may be used and distributed according to the terms of the
 * MIT license: http://www.opensource.org/licenses/mit-license.php 
 */
package idigbio.storage.dataingestion;

import java.awt.datatransfer.DataFlavor;
import java.awt.datatransfer.Transferable;
import java.awt.datatransfer.UnsupportedFlavorException;
import java.awt.dnd.DropTarget;
import java.awt.dnd.DropTargetDragEvent;
import java.awt.dnd.DropTargetDropEvent;
import java.awt.dnd.DropTargetEvent;
import java.awt.dnd.DropTargetListener;
import java.beans.PropertyChangeListener;
import java.beans.PropertyChangeSupport;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import javax.swing.JFrame;
import javax.swing.JOptionPane;
import javax.swing.JTextArea;
import org.javabuilders.BuildResult;
import org.javabuilders.annotations.DoInBackground;
import org.javabuilders.event.BackgroundEvent;
import org.javabuilders.event.CancelStatus;
import org.javabuilders.swing.SwingJavaBuilder;

@SuppressWarnings({"serial", "unused"})
public class FileDropFrame extends JFrame implements DropTargetListener {
    private BuildResult result;
    private UserData userData;
    private DropTarget dropTarget;
    private JTextArea txaSelectedPath;

    public UserData getUserData() {
        return userData;
    }

    public FileDropFrame() {
        userData = new UserData();
        result = SwingJavaBuilder.build(this);
        dropTarget = new DropTarget(txaSelectedPath, this);
        txaSelectedPath.setDragEnabled(true);
    }

    //databinding support
    private PropertyChangeSupport support = null ;
    public void addPropertyChangeListener(PropertyChangeListener listener) {
        support.addPropertyChangeListener(listener);
    }
    public void addPropertyChangeListener(String propertyName, PropertyChangeListener listener) {
        support.addPropertyChangeListener(propertyName, listener);
    }
    public void removePropertyChangeListener(PropertyChangeListener listener) {
        support.removePropertyChangeListener(listener);
    }
    public void removePropertyChangeListener(String propertyName, PropertyChangeListener listener) {
        support.removePropertyChangeListener(propertyName, listener);
    }
    
    @Override
    public void dragEnter(DropTargetDragEvent arg0) {
        // TODO Auto-generated method stub
        
    }

    @Override
    public void dragExit(DropTargetEvent arg0) {
        // TODO Auto-generated method stub
        
    }

    @Override
    public void dragOver(DropTargetDragEvent arg0) {
        // TODO Auto-generated method stub
        
    }

    @Override
    public void drop(DropTargetDropEvent evt) {
        final List result = new ArrayList();
        int action = evt.getDropAction();
        evt.acceptDrop(action);
        try {
            Transferable data = evt.getTransferable();
            DataFlavor flavors[] = data.getTransferDataFlavors();
            if (data.isDataFlavorSupported(DataFlavor.javaFileListFlavor)) {
                List<File> list = (List<File>) data.getTransferData(
                    DataFlavor.javaFileListFlavor);
                processFiles(list);
            }
        } catch (UnsupportedFlavorException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            evt.dropComplete(true);
            repaint();
        }
        
    }

    private void processFiles(List<File> list) {
        this.txaSelectedPath.setText(list.get(0).getAbsolutePath());
    }

    @Override
    public void dropActionChanged(DropTargetDragEvent arg0) {
        // TODO Auto-generated method stub
    }
    
    private void cancel() {
        setVisible(false);
    }
    
    private void done() {
        JOptionPane.showMessageDialog(this, "Demo finished.");
    }
    
    @DoInBackground(cancelable = true, indeterminateProgress = false, progressStart = 1, progressEnd = 100)
    private void upload(BackgroundEvent evt) {
     // simulate a long running save to a database
        for (int i = 0; i < 100; i++) {
            // progress indicator
            evt.setProgressValue(i + 1);
            evt.setProgressMessage("" + i + "% done...");
            // check if cancel was requested
            if (evt.getCancelStatus() != CancelStatus.REQUESTED) {
                // sleep
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                }
            } else {
                // cancel requested, let's abort
                evt.setCancelStatus(CancelStatus.COMPLETED);
                break;
            }
        }
    }

}