/**
 * Logic specific to uploading files from a root directory.
 */

initDirUploadUI = function() {
    // Set up upload-form
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

//        $("#logout-btn").attr('disabled', true);
//        $("#logout-btn").addClass('disabled');
               
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

initPreferencePane = function() {
//    initLicenseSelector();
    initIDSyntaxSelector();
//    $('#idprefix').focusout(function(e) {
//        setPreference('idprefix', $(this).val());
//    });
//    $('#owneruuid').focusout(function(e) {
//        setPreference('owneruuid', $(this).val());
//    });

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