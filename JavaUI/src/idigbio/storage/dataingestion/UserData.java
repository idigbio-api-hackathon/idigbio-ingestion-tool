/**
 * Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida This
 * software may be used and distributed according to the terms of the MIT
 * license: http://www.opensource.org/licenses/mit-license.php
 */
package idigbio.storage.dataingestion;

import java.beans.PropertyChangeListener;
import java.beans.PropertyChangeSupport;

public class UserData {
    private String selectedPath;

    public String getSelectedPath() {
        return selectedPath;
    }

    public void setSelectedPath(String selectedPath) {
        this.selectedPath = selectedPath;
    }
    
    //databinding support
    private PropertyChangeSupport support = new PropertyChangeSupport(this);
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
}
