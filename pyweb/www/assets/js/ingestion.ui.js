$(function() {
    $('#upload-form').submit(function(event){
        // we want to submit the form using Ajax (prevent page refresh)
        event.preventDefault();
        var rootPath = $('#root-path').val();
        
        var callback = function(dataReceived){
        };
        
        // type of data to receive (in our case we're expecting an HTML snippet)
        var typeOfDataToReceive = 'json';
        
        var url = '/services';
        
        // now send the form and wait to hear back
        $.post(url, { rootPath: rootPath }, callback, typeOfDataToReceive);
        
        $('#root-path').attr('disabled', true);
        $("#upload-button").attr('disabled', true);
        $("#upload-button").toggleClass('disabled');
        $(".progress-primary").toggleClass('active');
        $("#progressbar-container").toggleClass('in');
        setTimeout("updateProgress()", 1000)
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
        
        $("#progresstext").text("Finished " + uploaded + " out of " + total + " files.");
        
        $("#upload-progressbar").width(progress + '%')
        
        if (progress >= 100) {
            $(".progress-primary").toggleClass('active');
            $("#upload-button").attr('disabled', false);
            $("#upload-button").toggleClass('disabled');
            $('#root-path').attr('disabled', false);
            return;
        }
        
        setTimeout("updateProgress()", 4000)
    }, typeOfDataToReceive);
    
}