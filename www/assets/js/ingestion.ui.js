$(function() {

    checkAuthentication();
    
    // Certain UI components will be disabled if JS is. This overrides the css
    // that hides them (ingestion.ui.css), making sure they are shown.
    $(".js-required").not('.hidden').css("display", "inherit");
    if ($(".js-required").hasClass('hidden')) {
        $('#unsupported-browser-msg').show();
    }
});

var IMAGE_LICENSES = {
    "CC0": ["CC0", "(Public Domain)", "http://creativecommons.org/publicdomain/zero/1.0/"],
    "CC BY": ["CC BY", "(Attribution)", "http://creativecommons.org/licenses/by/3.0/"],
    "CC BY-SA": ["CC BY-SA", "(Attribution-ShareAlike)", "http://creativecommons.org/licenses/by-sa/3.0/"],
    "CC BY-NC": ["CC BY-NC", "(Attribution-Non-Commercial)", "http://creativecommons.org/licenses/by-nc/3.0/"],
    "CC BY-NC-SA": ["CC BY-NC-SA", "(Attribution-NonCommercial-ShareAlike)", "http://creativecommons.org/licenses/by-nc-sa/3.0/"]
};

var GUID_SYNTAXES = {
    "filename": "{GUID Prefix}/{File Name}",
    "full-path": "{GUID Prefix}/{Full Path}"
}

initMainUI = function() {
    showLastBatchInfo();
    initPreferencePane();
    
    $("body").tooltip({
        selector: '[rel=tooltip]'
    });

    $('#logout-btn').click(function(e) {
        $.ajax({
            url: "/services/config",
            type: 'DELETE'
        }).done(function() {
            location.reload();
        });
    });
    
    $('#upload-form').validate({
        onfocusout: false,
        onkeyup: false,
        onsubmit: false,
        errorPlacement: function(error, element) {},
        highlight: function(element) {
            $(element).closest('.control-group').addClass('error');
        },
        unhighlight: function(element) {
            $(element).closest('.control-group').removeClass('error');
        },
        rules: {
            rootpath: {
                required: true
            }
        }
    });

    $('#upload-form').submit(function(event) {
        event.preventDefault();
        if ($('#upload-form').valid()) {
            postUpload("new");
        } else {
            showAlert('The path cannot be empty.');
        }
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

    $.validator.addMethod("notrailingslash", function(value, element) { 
      return value.indexOf('/', value.length - 1) == -1;
    }, "Please avoid using a trailing slash.");

    $('#settings-form').validate({
        onkeyup: false,
        errorElement:'span',
        errorClass:'help-inline',
        highlight: function(element, errorClass, validClass) {
            $(element).closest('.control-group').addClass('error');
        },
        unhighlight: function (element, errorClass, validClass) { 
            $(element).parents(".error").removeClass('error');
        },
        rules: {
            idprefix: {
                minlength: 3,
                notrailingslash: true,
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
            $('#license-dropdown').val(val);
        }
        hideAndShowPanes();
    });
    

    getPreference('idsyntax', function(val) {
        if (val) {
            $('#idsyntax-dropdown').val(val);
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
    blockUI();
    $.getJSON('/services/auth', function(data) {
        $.unblockUI();
        if (!data) {
            initLoginModal();
        } else {
            initMainUI();
        }
    })
    .error(function(data) {
        $.unblockUI();
        $('#serviceErrorModal').modal();
    });
}

blockUI = function() {
    var div = document.createElement("div");
    var throb = new Throbber({
        color: 'white',
        padding: 30,
        size: 100,
        fade: 200,
        clockwise: false
    }).appendTo(div).start();
    $.blockUI.defaults.css = {}; 
    $.blockUI({ 
        message: div
     });
}

initLoginModal = function() {
    $('#loginModal').modal();

    $('#login-form').validate({
        onkeyup: false,
        errorElement:'span',
        errorClass:'help-inline',
        highlight: function(element, errorClass, validClass) {
            $(element).closest('.control-group').addClass('error');
        },
        unhighlight: function (element, errorClass, validClass) { 
            $(element).parents(".error").removeClass('error');
        },
        rules: {
            accountuuid: {
                rangelength: [32, 36],
                required: true
            },
            apikey: {
                rangelength: [32, 36],
                required: true
            }
        }
    });
    
    $('#login-button').click(function(event) {
        event.preventDefault();
        if ($('#login-button').attr('disabled')) {
            return;
        }

        if (!$('#login-form').valid()) {
            return;
        }
        
        var accountuuid = $("#accountuuid").val();
        var apikey = $("#apikey").val();

        $('#login-button').attr('disabled', true);
        $('#login-button').addClass('disabled');
        new Throbber({
            color: '#005580',
            size: 20
        }).appendTo($('#login-error')[0]).start();

        $.post('/services/auth', { user: accountuuid, password: apikey }, function(data) {
            $('#login-form > .control-group').removeClass('error');
            $('#login-error').addClass('hide');

            $('#loginModal').modal('hide');
            initMainUI();
        }, 'json')
        .error(function(err) {
            if (err.status == 409) {
                $('#login-error').html('Wrong Account UUID and API Key combination..');
                $('#login-button').attr('disabled', false);
                $('#login-button').removeClass('disabled');
            } else {
                $('#login-error').html('Cannot sign in due to iDigBio service unavailable. Please come back later.');
            }
            $('#login-form > .control-group').addClass('error');
            $('#login-error').removeClass('hide');
        });
    });
}

initLicenseSelector = function() {
    $.each(IMAGE_LICENSES, function(key, value) {
        var option = ["<option value=\"", key, "\">", value[0], " ", 
            value[1], "</option>"].join("");
        $("#license-dropdown").append(option);
    });
    
    $("#license-dropdown").change(function(e) {
        var licenseName = $("#license-dropdown").val();
        var license = IMAGE_LICENSES[licenseName];
        showAlert(["The images will be uploaded under the terms of the ", 
                license[0], " ", license[1], " license (see <a href=\"", license[2], 
                "\" target=\"_blank\">definition</a>)."].join(""), 
            null, "alert-info");
        setPreference('imagelicense', licenseName);
    });
}

initIDSyntaxSelector = function() {
    $.each(GUID_SYNTAXES, function(key, value) {
        var option = ["<option value=\"", key, "\">", value, "</option>"].join("");
        $("#idsyntax-dropdown").append(option);
    });
    
    $("#idsyntax-dropdown").change(function(e) {
        var syntaxName = $("#idsyntax-dropdown").val();
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

        $("#logout-btn").attr('disabled', true);
        $("#logout-btn").addClass('disabled');
               
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
            showAlert(errMsg);
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
            showAlert(errMsg, extra, "alert-warning");
            $("#retry-button").click(function(event) {
                event.preventDefault();
                $("#upload-alert").alert('close');
                postUpload("retry");
            });
        } else {
            var msg = "<strong>Welcome!</strong> BTW, your last upload was successful."
            showAlert(msg, "", "alert-success");
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
    $("#upload-alert").addClass(alertType);
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
        
        $("#upload-progressbar").width(progress + '%');
        
        if (progressObj.finished) {
            $(".progress-primary").toggleClass('active');
            
            $('#root-path').attr('disabled', false);
            $("#root-path").removeClass('disabled');
            
            $("#upload-button").attr('disabled', false);
            $("#upload-button").removeClass('disabled');

            $("#logout-btn").attr('disabled', false);
            $("#logout-btn").removeClass('disabled');
            
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
                showAlert(errMsg, extra, "alert-warning");
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
        
        setTimeout("updateProgress()", 4000);
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
