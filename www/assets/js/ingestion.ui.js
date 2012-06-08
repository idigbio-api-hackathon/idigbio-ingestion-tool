$(function() {
    
    // For testing UI.
    // renderResult([['google', 'http://google.com']])
    
    showLastBatchInfo()
    
    $("#root-path").tooltip()
    
    $('#upload-form').submit(function(event) {
        // we want to submit the form using Ajax (prevent page refresh)
        event.preventDefault();
        
        postUpload("new")
    });
});


postUpload = function(action) {
    
    // Reset the elements
    $("#result-table-container").removeClass('in');
    $("#progressbar-container").removeClass('in');
    
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
    if (action == "new") {
    var rootPath = $('#root-path').val();
        $.post('/services', { rootPath: rootPath }, callback, 'json')
            .error(function(data) {
                var errMsg = "<strong>Error! </strong>" + data.responseText;
                showAlert(errMsg)
            });
    } else {
        $.post('/services', callback, 'json')
            .error(function(data) {
                var errMsg = "<strong>Error! </strong>" + data.responseText;
                showAlert(errMsg)
            });
    }
}

showLastBatchInfo = function() {
    $.getJSON('/services/batch', function(batch) {
        if ($.isEmptyObject(batch)) {
            return;
        }
            
        if (!batch.finished) {
            var start_time = batch.start_time;
            var errMsg = ["<p><strong>Warning!</strong> Your last upload from directory ",
            batch.root, " which started at ", start_time,
            ' was not entirely successful.</p>'].join("");
            var extra = '<p><button id="retry-button" type="submit" class="btn btn-warning">Retry failed uploads</button></p>';
            showAlert(errMsg, extra, "alert-warning")
            $("#retry-button").click(function(event) {
                event.preventDefault();
                $("#upload-alert").alert('close');
                postUpload("retry");
            });
        } else {
            var msg = "<strong>Welcome!</strong> BTW, you last upload was successful."
            showAlert(msg, "", "alert-success")
        }
    }, "json");
}

/**
 * Display an alert message in the designated alert container.
 * @param {HTML string} message 
 * @param {HTML string} [additionalElement] Additional element(s) in the second row.
 * @param {String} [alertType] The alert type, i.e. Bootstrap class, default to 
 *   alert-error.
 */
showAlert = function(message, additionalElement, alertType) {
    alertType = alertType || "alert-error";
    
    var alert_html =
        ['<div class="alert alert-block fade" id="upload-alert">',
        '<button class="close" data-dismiss="alert">&times;</button>',
        '<p id="alert-text">',
        '<div id="alert-extra">',
        '</div>'].join('\n');
    $("#alert-container").html(alert_html);
    $("#upload-alert").show();
    $("#upload-alert").addClass('in');
    $("#upload-alert").addClass(alertType)
    $("#alert-text").html(message);
    $("#alert-extra").html(additionalElement);
}

updateProgress = function() {
    var url = '/services';
    
    $.getJSON(url, function(progressObj) {
        
        var progress = Math.floor((progressObj.successes + progressObj.fails + 
            progressObj.skips) / progressObj.total * 100);
        
        $("#progresstext").text(["Progress: (Successful:" + progressObj.successes,
             ", Skipped: " + progressObj.skips,
             ", Failed: " + progressObj.fails,
             ", Total to upload: " + progressObj.total,
             ")"].join(""));
        
        $("#upload-progressbar").width(progress + '%')
        
        if (progress >= 100) {
            $(".progress-primary").toggleClass('active');
            $("#upload-button").attr('disabled', false);
            $("#upload-button").toggleClass('disabled');
            $('#root-path').attr('disabled', false);
            
            if (progressObj.fails > 0) {
                var errMsg = ["<p><strong>Warning!</strong> ",
                    "This upload was not entirely successful. ",
                    "You can retry it at a later time."].join("");
                var extra = '<p><button id="retry-button" type="submit" class="btn btn-warning">Retry failed uploads</button></p>';
                showAlert(errMsg, extra, "alert-warning")
                $("#retry-button").click(function(event) {
                    event.preventDefault();
                    $("#upload-alert").alert('close');
                    postUpload("retry");
                });
            }
            
            $.getJSON('/services/result', renderResult);
            return;
        }
        
        setTimeout("updateProgress()", 4000)
    });
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
                var text;
                if (url == null) {
                    text = "<span class=\"label label-important\">This image is not successfully uploaded.</span>"
                } else {
                    text = '<a target="_blank" href="' + url + '">'+ url + '</a>';
                }
                return text;
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
