$(function() {
    

    checkAuthentication();
    
    // Certain UI components will be disabled if JS is. This overrides the css
    // that hides them (ingestion.ui.css), making sure they are shown.
    $(".js-required").css("display", "inherit");
});

var IMAGE_LICENSES = {
    "CC0": ["CC0", "(Public Domain)", "http://creativecommons.org/publicdomain/zero/1.0/"],
    "CC BY": ["CC BY", "(Attribution)", "http://creativecommons.org/licenses/by/3.0/"],
    "CC BY-SA": ["CC BY-SA", "(Attribution-ShareAlike)", "http://creativecommons.org/licenses/by-sa/3.0/"],
    "CC BY-NC": ["CC BY-NC", "(Attribution-Non-Commercial)", "http://creativecommons.org/licenses/by-nc/3.0/"],
    "CC BY-NC-SA": ["CC BY-NC-SA", "(Attribution-NonCommercial-ShareAlike)", "http://creativecommons.org/licenses/by-nc-sa/3.0/"]
};

var GUID_SYNTAXES = {
    "full-path": "{GUID Prefix}/{File Name}",
    "filename": "{GUID Prefix}/{Full Path}"
}

initMainUI = function() {
    showLastBatchInfo();
    initPreferencePane();
    
    $("body").tooltip({
        selector: '[rel=tooltip]'
    });
    
    $('#upload-form').submit(function(event) {
        // we want to submit the form using Ajax (prevent page refresh)
        event.preventDefault();
        postUpload("new")
    });
}

initPreferencePane = function() {
    initLicenseSelector();
    initIDSyntaxSelector();
    $('#idprefix').focusout(function(e) {
        setPreference('idprefix', $(this).val());
    });
    $('#owneruuid').focusout(function(e) {
        setPreference('owneruuid', $(this).val());
    });

    $('#settings-form').validate({
        ignore: "",
        onfocusout: false,
        onkeyup: false,
        onsubmit: false,
        errorPlacement: function(error, element) {},
        highlight: function(label) {
            //$(label).closest('.control-group').addClass('error');
        },
        rules: {
            idprefix: {
                minlength: 3,
                required: true
            },
            idsyntax: {
                required: true
            },
            imagelicense: {
                required: true
            }
        }
    });

    $('#collapseOne').on('hidden', function (e) {
        if (!$('#settings-form').valid()) {
            $('#collapseOne').collapse('show');

            showAlert('You must set all non-optional preferences to continue.');
        }
    });

    $('#collapseTwo').on('shown', function (e) {
        if (!$('#settings-form').valid()) {
            $('#collapseTwo').collapse('hide');
            $('#collapseOne').collapse('show');
        }
    });

    hideAndShowPanes = function() {
        if ($('#settings-form').valid()) {
            $('#collapseTwo').addClass('in');
            $('#collapseOne').removeClass('in');
        } else {
            $('#collapseOne').addClass('in');
            $('#collapseTwo').removeClass('in');
        }
    }

    getPreference('imagelicense', function(val) {
        if (val) {
            $('#imagelicense').val(val);
            $("#license-selector").html(["License: ", IMAGE_LICENSES[val][0], " <span class=\"caret\"></span> "].join(""));
        }
        hideAndShowPanes();
    });
    

    getPreference('idsyntax', function(val) {
        if (val) {
            $('#idsyntax').val(val);
            $("#idsyntax-selector").html(["Use: ", GUID_SYNTAXES[val], " <span class=\"caret\"></span> "].join(""));
        }
        hideAndShowPanes();
    });

    getPreference('idprefix', function(val) {
        if (val) $('#idprefix').val(val);
        hideAndShowPanes();
    });

    val = getPreference('owneruuid', function(val) {
        if (val) $('#owneruuid').val(val);
        hideAndShowPanes();
    });
}


checkAuthentication = function() {
    $.getJSON('/services/auth', function(data) {
        if (!data) {
            initLoginModal();
        } else {
            initMainUI();
        }
    })
    .error(function(data) {
       $('#serviceErrorModal').modal();
    });
}

initLoginModal = function() {
    $('#loginModal').modal();
    
    $('#login-button').click(function(event) {
        event.preventDefault();
        
        var accountuuid = $("#account-uuid").val();
        var apikey = $("#api-key").val();
        
        $.post('/services/auth', { user: accountuuid, password: apikey }, function(data) {
            $('#login-form').removeClass('error');
            $('#login-error').addClass('hide');

            $('#loginModal').modal('hide');
            initMainUI();
        }, 'json')
        .error(function(err) {
            if (err.status == 409) {
                $('#login-error').html('Wrong Account UUID and API Key combination..');
            } else {
                $('#login-error').html('iDigBio service unavailable. Please come back later.');
            }
            $('#login-form').addClass('error');
            $('#login-error').removeClass('hide');
        });
    });
}

initLicenseSelector = function() {
    $.each(IMAGE_LICENSES, function(key, value) {
        var li = ["<li><a name=\"", key, "\" href=\"#\">", value[0], " ", 
            value[1], "</a><a href=\"", value[2], 
            "\" target=\"_blank\">definition</a></li>"].join("");
        $("#license-dropdown").append(li);
    });
    
    $("#license-dropdown li a[name]").click(function(e) {
        e.preventDefault();
        var licenseName = $(e.target)[0].name;
        $("#imagelicense").val(licenseName);
        var license = IMAGE_LICENSES[licenseName];
        $("#license-selector").html(["License: ", license[0], " <span class=\"caret\"></span> "].join(""));
        showAlert(["The pictures will be uploaded under the terms of the ", 
                license[0], " ", license[1], " license (see <a href=\"", license[2], 
                "\" target=\"_blank\">definition</a>)."].join(""), 
            null, "alert-info");
        setPreference('imagelicense', licenseName);
    });
}

initIDSyntaxSelector = function() {
    $.each(GUID_SYNTAXES, function(key, value) {
        var li = ["<li><a name=\"", key, "\" href=\"#\">", value, "</a></li>"].join("");
        $("#idsyntax-dropdown").append(li);
    });
    
    $("#idsyntax-dropdown li a[name]").click(function(e) {
        e.preventDefault();
        if ($("#idsyntax-selector").hasClass("disabled")) {
            // This dropdown could be temporarily disbled when an ongoing upload
            // is in progress.
            return;
        }
        var syntaxName = $(e.target)[0].name;
        $("#idsyntax").val(syntaxName);
        $("#idsyntax-selector").html(["Use: ", GUID_SYNTAXES[syntaxName], " <span class=\"caret\"></span> "].join(""));
        setPreference('idsyntax', syntaxName);
    });
}


// This method handles both new uploads and resumes. 
// Here the `action` can be `new` or `retry`.
// In the case of new upload, the progress bar and result table are initially 
// hidden and needs to be made visible.
// In the case of retrying, they need to be 'cleaned' before being updated with
// new progress information.
postUpload = function(action) {
    // Reset the elements
    $("#result-table-container").removeClass('in');
    $("#result-table-container").removeClass('hide');
    $("#progressbar-container").removeClass('in');
    $("#progressbar-container").removeClass('hide');
    
    var callback = function(dataReceived){
        // Disable inputs
        $('#root-path').attr('disabled', true);
        $("#root-path").addClass('disabled');
        
        $("#upload-button").attr('disabled', true);
        $("#upload-button").addClass('disabled');
               
        // Clean up UI.
        $("#upload-alert").alert('close');
        
        // Show progress bar in animation
        $(".progress-primary").addClass('active');
        $("#progressbar-container").addClass('in');
        
        setTimeout("updateProgress()", 1000);
    };
    
    // now send the form and wait to hear back
    if (action == "new") {
        var rootPath = $('#root-path').val();

        $.post('/services', { rootPath: rootPath }, callback, 
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
showAlert = function(message, additionalElement, alertType, container) {
    additionalElement = additionalElement || "";
    alertType = alertType || "alert-error";
    container = container || "#alert-container";
    
    var alert_html =
        ['<div class="alert alert-block fade" id="upload-alert">',
        '<button class="close" data-dismiss="alert">&times;</button>',
        '<p id="alert-text">',
        '<div id="alert-extra">',
        '</div>'].join('\n');
    $(container).html(alert_html);
    $("#upload-alert").show();
    $("#upload-alert").addClass('in');
    $("#upload-alert").addClass(alertType)
    $("#alert-text").html(message);
    $("#alert-extra").html(additionalElement);
}

updateProgress = function() {
    var url = '/services/progress';
    
    $.getJSON(url, function(progressObj) {
        
        var progress = progressObj.total == 0 ? 100 : 
            Math.floor((progressObj.successes + progressObj.fails + 
                progressObj.skips) / progressObj.total * 100);
        
        
        $("#progresstext").text(["Progress: (Successful:" + progressObj.successes,
             ", Skipped: " + progressObj.skips,
             ", Failed: " + progressObj.fails,
             ", Total to upload: " + progressObj.total,
             ")"].join(""));
        
        $("#upload-progressbar").width(progress + '%')
        
        if (progressObj.finished) {
            $(".progress-primary").toggleClass('active');
            
            $('#root-path').attr('disabled', false);
            $("#root-path").removeClass('disabled');
            
            $("#upload-button").attr('disabled', false);
            $("#upload-button").removeClass('disabled');
            
            if (progressObj.fails > 0 || progressObj.total == 0) {
                if (progressObj.fails > 0) {
                    var errMsg = ["<p><strong>Warning!</strong> ",
                        "This upload was not entirely successful. ",
                        "You can retry it at a later time."].join("");
                    if (progress < 100) {
                        errMsg += [' Upload aborted before all images are tried ', 
                            'due to continuing erroneous network conditions.'].join('');
                    }
                    var extra = ['<p><button id="retry-button" type="submit"',
                        'class="btn btn-warning">Retry failed uploads</button></p>'].join("");
                } else {
                    var errMsg = ["<p><strong>Warning!</strong> ",
                        "Nothing is uploaded. Maybe the folder is empty or the network is down? ",
                        "Please check the folder and network connection and ",
                        "retry it by clicking the 'Upload' button."].join("");
                }
                showAlert(errMsg, extra, "alert-warning")
                $("#retry-button").click(function(event) {
                    event.preventDefault();
                    $("#upload-alert").alert('close');
                    postUpload("retry");
                });
            }
            
            if (progressObj.total > 0) {
                // If we haven't tried one file, no need to get results.
                $.getJSON('/services/result', renderResult);
            }
            
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
            "sSwfPath": "assets/TableTools/swf/copy_csv_xls_pdf.swf",
            "aButtons": [
                "csv",
                "pdf"
            ]
        },
        "bDestroy" : true,
        "sPaginationType": "bootstrap"
    });
}

getPreference = function(name, callback) {
    $.getJSON('/services/config', { name: name }, function(data) {
        callback(data);
    })
    .error(function(data) {
        callback(null);
    });
}

setPreference = function(name, val) {
    $.post('/services/config', { name: name, value: val }, function() { }, 'json');
}
