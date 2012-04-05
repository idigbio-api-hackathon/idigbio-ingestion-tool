
$(function() {
    $("input:submit", ".data-injection-box").button();
    $("input:text", ".data-injection-box")
        .button()
        .css({
            'font' : 'inherit',
            'color' : 'inherit',
            'text-align' : 'left',
            'outline' : 'none',
            'cursor' : 'text'
        });
    
    $('#upload-form').submit(function(event){
        // we want to submit the form using Ajax (prevent page refresh)
        event.preventDefault();
        var rootPath = $('#root-path').val();
        
        var callback = function(dataReceived){
            $.get()
        };
        
        // type of data to receive (in our case we're expecting an HTML snippet)
        var typeOfDataToReceive = 'json';
        
        var url = '/services';
        
        // now send the form and wait to hear back
        $.post(url, { rootPath: rootPath }, callback, typeOfDataToReceive);
        
        $("#uploading-dialog").dialog();
        
        setTimeout("updateProgress()", 4000)
    });
});

updateProgress = function() {
    var url = '/services';
    var typeOfDataToReceive = 'text';
    $.getJSON(url, function(progressObj) {
        var total = progressObj.total;
        var remaining = progressObj.remaining;
        var uploaded = total - remaining
        
        var progress = Math.floor(uploaded / total * 100);
        
        $("#progresstext").text("Finished " + uploaded + " out of " + total + ".");
        
        $("#progressbar").progressbar({
            value: progress
        });
        
        if (progress >= 100) {
            return;
        }
        
        setTimeout("updateProgress()", 4000)
    }, typeOfDataToReceive);
    
}