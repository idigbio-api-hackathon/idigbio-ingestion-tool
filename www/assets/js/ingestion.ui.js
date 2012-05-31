$(function() {
    
    // For testing UI.
    // renderResult([['google', 'http://google.com']])
    
    $('#upload-form').submit(function(event) {
        // we want to submit the form using Ajax (prevent page refresh)
        event.preventDefault();
        
        var rootPath = $('#root-path').val();
        
        // Reset the elements
        $("#result-table-container").removeClass('in');
        $("#progressbar-container").removeClass('in');
        
        // type of data to receive (in our case we're expecting an HTML snippet)
        var typeOfDataToReceive = 'json';
        var callback = function(dataReceived){
            // Disable inputs
            $('#root-path').attr('disabled', true);
            $("#upload-button").attr('disabled', true);
            $("#upload-button").addClass('disabled');
            
            // Show progress bar in animation
            $(".progress-primary").addClass('active');
            $("#progressbar-container").addClass('in');
            
            setTimeout("updateProgress()", 1000)
        };
        
        // now send the form and wait to hear back
        $.post('/services', { rootPath: rootPath }, callback, typeOfDataToReceive)
            .error(function(data) {
                var alert_html =
                ['<div class="alert alert-block alert-error fade" id="upload-alert">',
                '<button class="close" data-dismiss="alert">&times;</button>',
                '<p id="alert-text">',
                '</div>'].join('\n');
                $("#alert-container").html(alert_html);
                $("#upload-alert").show();
                $("#upload-alert").addClass('in');
                var errMsg = "<strong>Error: </strong>" + data.responseText;
                $("#alert-text").html(errMsg);
            });
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
            
            $.getJSON('/services/result', renderResult, typeOfDataToReceive);
            return;
        }
        
        setTimeout("updateProgress()", 4000)
    }, typeOfDataToReceive);
}

renderResult = function(data) {
    $('#result-table-container').addClass('in');
    
    $('#result-table').dataTable({
        "aaData": data,
        "aoColumns": [
            { "sTitle": "Local" },
            { "sTitle": "Online",
              "fnRender": function(obj) {
                var url = obj.aData[ obj.iDataColumn ];
                url = '<a target="_blank" href="' + url + '">'+ url + '</a>';
                return url;
              }
            }
        ],
        "sDom": "<'row'<'span4'l><'span4'T><'span4'f>r>t<'row'<'span6'i><'span6'p>>",
        "bPaginate": true,
        "bLengthChange": true,
        "bFilter": true,
        "bSort": true,
        "bInfo": true,
        "bAutoWidth": true,
        "oTableTools": {
            "sSwfPath": "assets/TableTools/swf/copy_csv_xls_pdf.swf"
        },
        "bDestroy" : true,
        "sPaginationType": "bootstrap"
    });
}
