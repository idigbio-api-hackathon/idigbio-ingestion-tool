$(function() {
    
    // For testing UI.
    // renderResult([['google', 'http://google.com']])
    
    showLastBatchInfo()
    
    initLicenseSelector()
    
    $("#root-path").tooltip()
    
    $('#upload-form').submit(function(event) {
        // we want to submit the form using Ajax (prevent page refresh)
        event.preventDefault();
        
        postUpload("new")
    });
});

initLicenseSelector = function() {
    var licenses = {
      "cc0": ["CC0", "(Public Domain)", "http://creativecommons.org/publicdomain/zero/1.0/"],
      "cc-by": ["CC BY", "(Attribution)", "http://creativecommons.org/licenses/by/3.0/"],
      "cc-by-sa": ["CC BY-SA", "(Attribution-ShareAlike)", "http://creativecommons.org/licenses/by-sa/3.0/"],
      "cc-by-nc": ["CC BY-NC", "(Attribution-Non-Commercial)", "http://creativecommons.org/licenses/by-nc/3.0/"],
      "cc-by-nc-sa": ["CC BY-NC-SA", "(Attribution-NonCommercial-ShareAlike)", "http://creativecommons.org/licenses/by-nc-sa/3.0/"]
    };

    $.each(licenses, function(key, value) {
        var li = ["<li><a name=\"", key, "\" href=\"#\">", value[0], " ", 
            value[1], "</a><a href=\"", value[2], 
            "\" target=\"_blank\">definition</a></li>"].join("");
        $("ul.dropdown-menu").append(li);
    });
    
    if ($.cookie("idigbiolicense")) {
        var licenseName = $.cookie("idigbiolicense");
        $("#license-value").val(licenseName);
        $("#license-selector").html(["License: ", licenses[licenseName][0], " <span class=\"caret\"></span> "].join(""));
    }

    $("ul.dropdown-menu li a[name]").click(function(e) {
        e.preventDefault();
        if ($("#license-selector").hasClass("disabled")) {
            // This dropdown could be temporarily disbled when an ongoing upload
            // is in progress.
            return;
        }
        var licenseName = $(e.target)[0].name;
        $.cookie("idigbiolicense", licenseName, { expires: 365 });
        $("#license-value").val(licenseName);
        var license = licenses[licenseName]
        $("#license-selector").html(["License: ", license[0], " <span class=\"caret\"></span> "].join(""));
        showAlert(["The pictures will be uploaded under the terms of the ", 
                license[0], " ", license[1], " license (see <a href=\"", license[2], 
                "\" target=\"_blank\">definition</a>)."].join(""), 
            null, "alert-info");
    });
}


postUpload = function(action) {
    
    // Reset the elements
    $("#result-table-container").removeClass('in');
    $("#progressbar-container").removeClass('in');
    
    var callback = function(dataReceived){
        // Disable inputs
        $('#root-path').attr('disabled', true);
        $("#root-path").addClass('disabled');
        
        $("#upload-button").attr('disabled', true);
        $("#upload-button").addClass('disabled');
        
        $("#license-selector").attr('disabled', true);
        $("#license-selector").addClass('disabled');
        
        // Clear up UI.
        $("#upload-alert").alert('close');
        
        // Show progress bar in animation
        $(".progress-primary").addClass('active');
        $("#progressbar-container").addClass('in');
        
        setTimeout("updateProgress()", 1000)
    };
    
    // now send the form and wait to hear back
    if (action == "new") {
        var rootPath = $('#root-path').val();
        var license = $('#license-value').val();
        $.post('/services', { rootPath: rootPath, license: license }, callback, 
                'json')
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
    additionalElement = additionalElement || "";
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
            
            $('#root-path').attr('disabled', false);
            $("#root-path").removeClass('disabled');
            
            $("#upload-button").attr('disabled', false);
            $("#upload-button").removeClass('disabled');
            
            $("#license-selector").attr('disabled', false);
            $("#license-selector").removeClass('disabled');
            
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
